import os
import imaplib
import email
from email.header import decode_header
import datetime
import tempfile
import shutil
from typing import List, Dict, Optional, Tuple
from src.utils.logger import get_app_logger, get_error_logger

# Initialize loggers
app_logger = get_app_logger()
error_logger = get_error_logger()

def list_mail_folders():
    """
    List all available mail folders in the Gmail account

    Returns:
        List[str]: List of available mail folders
    """
    mail = connect_to_gmail()
    if not mail:
        error_logger.error("Failed to connect to Gmail to list folders")
        return []

    try:
        status, folder_list = mail.list()
        if status != 'OK':
            error_logger.error(f"Failed to list mail folders: {status}")
            return []

        folders = []
        for folder in folder_list:
            if folder:
                # Parse the folder name from the response
                # Format is typically: (flags) "separator" "folder_name"
                folder_parts = folder.decode().split(' "')
                if len(folder_parts) >= 3:
                    folder_name = folder_parts[2].strip('"')
                    folders.append(folder_name)

        mail.logout()
        app_logger.info(f"Found {len(folders)} mail folders")
        return folders
    except Exception as e:
        error_logger.error(f"Error listing mail folders: {str(e)}")
        return []

def connect_to_gmail():
    """
    Connect to Gmail using IMAP

    Returns:
        imaplib.IMAP4_SSL or None: IMAP connection object or None if connection fails
    """
    try:
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_pass = os.getenv("GMAIL_PASS")

        app_logger.info(f"Attempting to connect to Gmail with user: {gmail_user}")

        if not gmail_user or not gmail_pass:
            error_msg = "Missing Gmail credentials (GMAIL_USER and/or GMAIL_PASS)."
            error_logger.error(error_msg)
            raise ValueError(error_msg)

        # Connect to IMAP Server
        try:
            app_logger.info("Creating IMAP SSL connection to imap.gmail.com")
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
        except Exception as e:
            error_msg = f"Failed to create IMAP connection: {str(e)}"
            error_logger.error(error_msg)
            return None

        try:
            app_logger.info(f"Attempting to login with user: {gmail_user}")
            mail.login(gmail_user, gmail_pass)
            app_logger.info("Successfully connected to Gmail")
            return mail
        except imaplib.IMAP4.error as e:
            error_msg = f"Failed to login to Gmail: {e}"
            error_logger.error(error_msg)

            # Check for common error messages
            error_str = str(e).lower()
            if "invalid credentials" in error_str or "authentication failed" in error_str:
                error_logger.error("Authentication failed. Please check your Gmail username and password.")
                error_logger.error("If you're using Gmail, make sure you're using an App Password if 2FA is enabled.")
            elif "application-specific password" in error_str:
                error_logger.error("You need to use an App Password. Go to your Google Account > Security > App Passwords.")

            return None
    except ValueError as e:
        error_logger.error(f"Error: {e}")
        return None
    except Exception as e:
        error_msg = f"Unexpected error connecting to Gmail: {str(e)}"
        error_logger.error(error_msg)
        return None

def get_emails_with_attachments(days: int = 7, folders: List[str] = None) -> List[Dict]:
    """
    Scan emails for attachments in the specified folders

    Args:
        days (int): Number of days to look back for emails
        folders (List[str]): List of folders to scan

    Returns:
        List[Dict]: List of dictionaries containing email information and attachment details
    """
    try:
        mail = connect_to_gmail()
        if not mail:
            return []

        # Use provided folders or default to INBOX
        if not folders:
            folders = [os.getenv("MAIL_FOLDER", "INBOX")]

        email_list = []

        # Calculate the date for the search (N days ago)
        date_N_days_ago = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")

        # Process each folder
        for mail_folder in folders:
            app_logger.info(f"Scanning folder: {mail_folder}")

            # Select the mailbox
            try:
                status, data = mail.select(mail_folder)
                if status != 'OK':
                    error_msg = f"Failed to select mail folder '{mail_folder}': {data[0].decode() if data else 'Unknown error'}"
                    error_logger.error(error_msg)
                    # Skip this folder and continue with the next one
                    continue

                app_logger.info(f"Selected mail folder: {mail_folder}")
            except Exception as e:
                error_logger.error(f"Error selecting mail folder '{mail_folder}': {str(e)}")
                # Skip this folder and continue with the next one
                continue

            # Search for emails from the last N days
            search_criteria = f'(SINCE "{date_N_days_ago}")'
            status, messages = mail.search(None, search_criteria)

            if status != 'OK':
                error_logger.error(f"Error searching for emails in folder '{mail_folder}': {status}")
                # Skip this folder and continue with the next one
                continue

            if not messages or not messages[0]:
                app_logger.info(f"No messages found in folder '{mail_folder}'")
                # Skip this folder and continue with the next one
                continue

            # Process each email in this folder
            for message_id in messages[0].split():
                status, msg_data = mail.fetch(message_id, '(RFC822)')

                if status != 'OK':
                    error_logger.error(f"Error fetching email {message_id} from folder '{mail_folder}': {status}")
                    continue

                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                # Get email details
                subject = decode_email_header(email_message["Subject"])
                from_address = decode_email_header(email_message["From"])
                date_str = email_message["Date"]

                # Parse the date
                try:
                    date_obj = email.utils.parsedate_to_datetime(date_str)
                    date_formatted = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    date_formatted = date_str

                # Check for attachments
                attachments = []

                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue

                        filename = part.get_filename()
                        if filename:
                            # Decode filename if needed
                            filename = decode_email_header(filename)

                            # Check if it's an Excel file
                            if filename.lower().endswith(('.xls', '.xlsx')):
                                content_type = part.get_content_type()
                                attachments.append({
                                    "filename": filename,
                                    "content_type": content_type,
                                    "part": part
                                })

                if attachments:
                    email_list.append({
                        "id": message_id.decode(),
                        "subject": subject,
                        "from": from_address,
                        "date": date_formatted,
                        "folder": mail_folder,  # Add folder information
                        "attachments": [{"filename": a["filename"], "content_type": a["content_type"]} for a in attachments],
                        "_raw_attachments": attachments  # Keep raw attachment data for later use
                    })

            # Close the current mailbox before moving to the next one
            mail.close()

        # Logout after processing all folders
        mail.logout()

        app_logger.info(f"Found {len(email_list)} emails with Excel attachments across {len(folders)} folders")
        return email_list

    except Exception as e:
        error_logger.error(f"Error scanning emails: {str(e)}")
        return []

def save_attachment_from_email(email_data: Dict, attachment_index: int = 0) -> Optional[str]:
    """
    Save an attachment from an email to the uploads directory

    Args:
        email_data (Dict): Email data containing the attachment
        attachment_index (int): Index of the attachment to save

    Returns:
        Optional[str]: Path to the saved file or None if failed
    """
    try:
        if not email_data or "_raw_attachments" not in email_data or not email_data["_raw_attachments"]:
            error_logger.error("No attachment data found")
            return None

        if attachment_index >= len(email_data["_raw_attachments"]):
            error_logger.error(f"Attachment index {attachment_index} out of range")
            return None

        attachment = email_data["_raw_attachments"][attachment_index]
        filename = attachment["filename"]
        part = attachment["part"]

        # Generate a unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_email_{filename}"
        file_path = os.path.join("src/data/uploads", unique_filename)

        # Save the attachment
        with open(file_path, 'wb') as f:
            f.write(part.get_payload(decode=True))

        app_logger.info(f"Saved attachment to {file_path}")
        return file_path

    except Exception as e:
        error_logger.error(f"Error saving attachment: {str(e)}")
        return None

def decode_email_header(header):
    """
    Decode email header

    Args:
        header: Email header to decode

    Returns:
        str: Decoded header
    """
    if not header:
        return ""

    try:
        decoded_header = decode_header(header)
        header_parts = []

        for part, encoding in decoded_header:
            if isinstance(part, bytes):
                if encoding:
                    header_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                else:
                    header_parts.append(part.decode('utf-8', errors='replace'))
            else:
                header_parts.append(str(part))

        return " ".join(header_parts)
    except:
        return str(header)
