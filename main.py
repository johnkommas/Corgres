import socket
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import os
import json
import shutil
import uuid
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import re

from etl import process_excel_file, get_column_mapping_template, validate_main_unit_measurement, read_excel, validate_column_values, load_row_mappings, add_row_mapping
from utils.logger import get_api_logger, get_app_logger, get_data_processing_logger, get_error_logger, get_all_logs
from email_scanner import get_emails_with_attachments, save_attachment_from_email, list_mail_folders
from column_mapper import add_mapping, get_suggestions

# Function to process logs and generate statistics
def process_logs_for_stats(logs, log_type='all', days=7, start_date=None, end_date=None):
    """
    Process logs and generate statistics for charts

    Args:
        logs: List of log entries
        log_type: Type of logs to filter (all, api, app, data_processing, database, errors)
        days: Number of days to include
        start_date: Start date for filtering (format: YYYY-MM-DD)
        end_date: End date for filtering (format: YYYY-MM-DD)

    Returns:
        Dictionary with statistics
    """
    # Filter logs by type if specified
    if log_type != 'all':
        logs = [log for log in logs if log['type'] == log_type]

    # Filter logs by date range
    filtered_logs = []
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        end = end.replace(hour=23, minute=59, second=59)  # Include the entire end day

        for log in logs:
            log_date = log['timestamp']
            if start <= log_date <= end:
                filtered_logs.append(log)
    else:
        # Use the last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_logs = [log for log in logs if log['timestamp'] >= cutoff_date]

    # Initialize counters
    stats = {
        'total': len(filtered_logs),
        'by_level': defaultdict(int),
        'by_logger': defaultdict(int),
        'by_day': defaultdict(int),
        'by_hour': defaultdict(int),
        'time_series': defaultdict(lambda: defaultdict(int)),
        'message_counts': defaultdict(int)  # For tracking common messages
    }

    # Process each log entry
    for log in filtered_logs:
        # Check if the log message uses tabs or dashes as separators
        if "\t" in log['message']:
            # New format with tabs
            log_parts = log['message'].split("\t")
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle format with brackets
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['by_level'][log_level] += 1
        else:
            # Old format with dashes
            log_parts = log['message'].split(' - ')
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle both formats (with or without brackets)
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['by_level'][log_level] += 1

        # Count by logger type
        stats['by_logger'][log['type']] += 1

        # Count by day
        day = log['timestamp'].strftime('%Y-%m-%d')
        stats['by_day'][day] += 1

        # Count by hour
        hour = log['timestamp'].strftime('%H')
        stats['by_hour'][hour] += 1

        # Time series data (by day and log level)
        day = log['timestamp'].strftime('%Y-%m-%d')

        # Extract message content for common messages tracking
        actual_message = ""

        # Check if the log message uses tabs or dashes as separators
        if "\t" in log['message']:
            # New format with tabs
            log_parts = log['message'].split("\t")
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle format with brackets
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['time_series'][day][log_level] += 1

                # Extract actual message content (parts after the log level)
                if len(log_parts) >= 4:
                    actual_message = log_parts[3].strip()
        else:
            # Old format with dashes
            log_parts = log['message'].split(' - ')
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle both formats (with or without brackets)
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['time_series'][day][log_level] += 1

                # Extract actual message content (parts after the log level)
                if len(log_parts) >= 4:
                    actual_message = log_parts[3].strip()

        # Count message occurrences if we have a valid message
        if actual_message:
            stats['message_counts'][actual_message] += 1

    # Convert defaultdicts to regular dicts for JSON serialization
    stats['by_level'] = dict(stats['by_level'])
    stats['by_logger'] = dict(stats['by_logger'])
    stats['by_day'] = dict(stats['by_day'])
    stats['by_hour'] = dict(stats['by_hour'])
    stats['time_series'] = {k: dict(v) for k, v in stats['time_series'].items()}

    # Convert message counts to array of objects sorted by count
    message_counts = dict(stats['message_counts'])
    common_messages = [
        {'message': message, 'count': count}
        for message, count in message_counts.items()
    ]
    # Sort by count in descending order and limit to top 10
    common_messages.sort(key=lambda x: x['count'], reverse=True)
    stats['common_messages'] = common_messages[:10]

    # Remove the message_counts from the final stats
    del stats['message_counts']

    return stats

# Initialize loggers
api_logger = get_api_logger()
app_logger = get_app_logger()
data_logger = get_data_processing_logger()
error_logger = get_error_logger()

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("processed", exist_ok=True)

api = FastAPI(
    title="Softone ERP Excel Formatter",
    description="An application to process Excel files for Softone ERP system",
    version="1.0.0",
    docs_url=None,  # Disable Swagger UI
    redoc_url=None  # Disable ReDoc
)

# Log application startup
app_logger.info("Application starting up")

# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
api.mount("/static", StaticFiles(directory="static"), name="static")
api.mount("/images", StaticFiles(directory="images"), name="images")

@api.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint that serves the index.html file
    """
    api_logger.info("Serving index.html")
    with open("static/index.html") as f:
        return f.read()

@api.get("/logs", response_class=HTMLResponse)
async def logs_page():
    """
    Endpoint that serves the logs.html file
    """
    api_logger.info("Serving logs.html")
    try:
        with open("static/logs.html") as f:
            return f.read()
    except FileNotFoundError:
        error_logger.error("logs.html not found")
        raise HTTPException(status_code=404, detail="Logs page not found")

@api.get("/api/logs")
async def get_logs(limit: int = 100):
    """
    API endpoint to get logs
    """
    api_logger.info(f"Retrieving logs with limit {limit}")
    try:
        logs = get_all_logs(max_entries=limit)
        return {"logs": logs}
    except Exception as e:
        error_msg = f"Error retrieving logs: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/api/logs/stats")
async def get_log_stats(
    log_type: str = 'all',
    days: int = 7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
):
    """
    API endpoint to get log statistics for charts

    Args:
        log_type: Type of logs to filter (all, api, app, data_processing, database, errors)
        days: Number of days to include
        start_date: Start date for filtering (format: YYYY-MM-DD)
        end_date: End date for filtering (format: YYYY-MM-DD)
        limit: Maximum number of log entries to process

    Returns:
        Dictionary with log statistics
    """
    api_logger.info(f"Retrieving log statistics: type={log_type}, days={days}, start_date={start_date}, end_date={end_date}")
    try:
        # Get logs
        logs = get_all_logs(max_entries=limit)

        # Process logs for statistics
        stats = process_logs_for_stats(logs, log_type, days, start_date, end_date)

        return stats
    except Exception as e:
        error_msg = f"Error retrieving log statistics: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel file for processing
    """
    api_logger.info(f"Received file upload: {file.filename}")

    if not file.filename.endswith(('.xls', '.xlsx')):
        error_msg = f"Invalid file type: {file.filename}"
        error_logger.warning(error_msg)
        raise HTTPException(status_code=400, detail="Only Excel files (.xls, .xlsx) are allowed")

    # Generate a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{file.filename}"
    file_path = os.path.join("uploads", filename)

    # Save the uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        api_logger.info(f"File saved to {file_path}")
    except Exception as e:
        error_msg = f"Error saving file: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    # Read the Excel file to get column names
    from etl import read_excel, get_unique_column_values
    try:
        df = read_excel(file_path)
        column_names = df.columns.tolist()
        data_logger.info(f"Read Excel file with {len(df)} rows and {len(column_names)} columns")

        # Get suggestions for column mapping based on previous mappings
        suggestions = get_suggestions(column_names)
        data_logger.info(f"Generated {len(suggestions)} column mapping suggestions")

        # Get unique values for each column
        unique_values = get_unique_column_values(df)
        data_logger.info(f"Extracted unique values for {len(unique_values)} columns")
    except Exception as e:
        error_msg = f"Error reading column names: {str(e)}"
        error_logger.error(error_msg)
        column_names = []
        suggestions = {}
        unique_values = {}

    return {"filename": filename, "file_path": file_path, "column_names": column_names, "suggestions": suggestions, "unique_values": unique_values}

@api.get("/mail-folders/")
async def get_mail_folders():
    """
    List all available mail folders in the Gmail account

    Returns:
        List of available mail folders
    """
    api_logger.info("Listing available mail folders")

    try:
        # Check if the required environment variables are set
        gmail_user = os.getenv("GMAIL_USER")
        gmail_pass = os.getenv("GMAIL_PASS")

        if not gmail_user or not gmail_pass:
            error_msg = "Missing Gmail credentials. Please check your environment variables."
            error_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Get all available mail folders
        folders = list_mail_folders()

        # Check if the configured folder exists
        configured_folder = os.getenv("MAIL_FOLDER", "INBOX")
        folder_exists = configured_folder in folders

        return {
            "folders": folders,
            "configured_folder": configured_folder,
            "folder_exists": folder_exists
        }
    except Exception as e:
        error_msg = f"Error listing mail folders: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/scan-emails/")
async def scan_emails(days: int = 7, folders: str = None):
    """
    Scan emails for Excel attachments

    Args:
        days (int): Number of days to look back for emails
        folders (str): Comma-separated list of folders to scan

    Returns:
        List of emails with Excel attachments
    """
    api_logger.info(f"Scanning emails for Excel attachments (last {days} days)")

    try:
        # Check if the required environment variables are set
        gmail_user = os.getenv("GMAIL_USER")
        gmail_pass = os.getenv("GMAIL_PASS")

        # Parse folders parameter or use default from environment
        mail_folders = []
        if folders:
            mail_folders = folders.split(',')
            api_logger.info(f"Using folders from request: {mail_folders}")
        else:
            # If no folders specified, use the configured folder from environment
            default_folder = os.getenv("MAIL_FOLDER", "INBOX")
            mail_folders = [default_folder]
            api_logger.info(f"Using default folder from environment: {default_folder}")

        if not gmail_user or not gmail_pass:
            error_msg = "Missing Gmail credentials. Please check your environment variables."
            error_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        api_logger.info(f"Scanning folders: {mail_folders}")

        # Get emails with attachments from all selected folders
        emails = get_emails_with_attachments(days, mail_folders)

        # If no emails were found, it could be due to an error or just no matching emails
        if not emails:
            # Check the error logs to see if there was an error
            # This is a simple approach - in a production app, you might want to use a more robust method
            api_logger.info("No emails with Excel attachments found. This could be normal or due to an error.")

        # Remove raw attachment data from response
        for email in emails:
            if "_raw_attachments" in email:
                del email["_raw_attachments"]

        return {"emails": emails}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error scanning emails: {str(e)}"
        error_logger.error(error_msg)

        # Provide more specific error messages based on the exception
        if "authentication failed" in str(e).lower() or "login failed" in str(e).lower():
            error_msg = "Gmail authentication failed. Please check your credentials."
        elif "select failed" in str(e).lower() or "folder not found" in str(e).lower():
            error_msg = f"Failed to select mail folder '{os.getenv('MAIL_FOLDER', 'INBOX')}'. The folder may not exist."
        elif "network" in str(e).lower() or "connect" in str(e).lower():
            error_msg = "Network error while connecting to Gmail. Please check your internet connection."

        raise HTTPException(status_code=500, detail=error_msg)

@api.post("/fetch-attachment/")
async def fetch_attachment(email_id: str = Form(...), attachment_index: int = Form(0), folders: str = Form(None)):
    """
    Fetch an attachment from an email and save it to the uploads directory

    Args:
        email_id (str): ID of the email
        attachment_index (int): Index of the attachment to fetch
        folders (str): Comma-separated list of folders to scan

    Returns:
        Information about the saved attachment
    """
    api_logger.info(f"Fetching attachment {attachment_index} from email {email_id}")

    try:
        # Parse folders parameter
        mail_folders = None
        if folders:
            mail_folders = folders.split(',')
            api_logger.info(f"Using folders from request: {mail_folders}")

        # Get all emails with attachments from the specified folders
        emails = get_emails_with_attachments(folders=mail_folders)

        # Find the email with the specified ID
        email_data = None
        for email in emails:
            if email["id"] == email_id:
                email_data = email
                break

        if not email_data:
            error_msg = f"Email with ID {email_id} not found"
            error_logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        # Save the attachment
        file_path = save_attachment_from_email(email_data, attachment_index)

        if not file_path:
            error_msg = f"Failed to save attachment from email {email_id}"
            error_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Get the filename from the path
        filename = os.path.basename(file_path)

        # Read the Excel file to get column names
        from etl import read_excel, get_unique_column_values
        try:
            df = read_excel(file_path)
            column_names = df.columns.tolist()
            data_logger.info(f"Read Excel file with {len(df)} rows and {len(column_names)} columns")

            # Get suggestions for column mapping based on previous mappings
            suggestions = get_suggestions(column_names)
            data_logger.info(f"Generated {len(suggestions)} column mapping suggestions")

            # Get unique values for each column
            unique_values = get_unique_column_values(df)
            data_logger.info(f"Extracted unique values for {len(unique_values)} columns")
        except Exception as e:
            error_msg = f"Error reading column names: {str(e)}"
            error_logger.error(error_msg)
            column_names = []
            suggestions = {}
            unique_values = {}

        return {"filename": filename, "file_path": file_path, "column_names": column_names, "suggestions": suggestions, "unique_values": unique_values}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error fetching attachment: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/column-mapping-template/")
async def get_mapping_template():
    """
    Get a template for column mapping
    """
    api_logger.info("Retrieving column mapping template")
    template = get_column_mapping_template()
    return template

@api.post("/process/")
async def process_file(
    background_tasks: BackgroundTasks,
    filename: str = Form(...),
    column_mapping: str = Form(...),
    value_mapping: Optional[str] = Form(None),
    accept_auto_mapping: Optional[str] = Form(None),
    skip_auto_mapping: Optional[str] = Form(None)
):
    """
    Process an Excel file with the provided column mapping
    """
    api_logger.info(f"Processing file: {filename}")
    api_logger.info(f"accept_auto_mapping: {accept_auto_mapping}, type: {type(accept_auto_mapping)}")
    api_logger.info(f"skip_auto_mapping: {skip_auto_mapping}, type: {type(skip_auto_mapping)}")

    try:
        # Parse the column mapping JSON
        mapping_dict = json.loads(column_mapping)
        data_logger.info(f"Column mapping: {mapping_dict}")

        # Parse value mapping if provided
        value_mapping_dict = {}
        if value_mapping:
            value_mapping_dict = json.loads(value_mapping)
            data_logger.info(f"Value mapping: {value_mapping_dict}")

        # Validate the input file exists
        input_path = os.path.join("uploads", filename)
        if not os.path.exists(input_path):
            error_msg = f"File {filename} not found"
            error_logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        # Read the Excel file
        df = read_excel(input_path)

        # Map columns according to the mapping
        from etl import map_columns
        df = map_columns(df, mapping_dict)

        # Load existing row mappings
        row_mappings = load_row_mappings()
        data_logger.info(f"Loaded row mappings for {len(row_mappings)} columns")

        # Check if there are any values that would be mapped
        potential_mappings = {}
        for column, mappings in row_mappings.items():
            if column in df.columns:
                # Find values in the dataframe that have mappings
                column_values = df[column].astype(str).unique().tolist()
                applicable_mappings = {}
                for val in column_values:
                    if val in mappings:
                        applicable_mappings[val] = mappings[val]

                if applicable_mappings:
                    potential_mappings[column] = applicable_mappings

        # If there are potential mappings and no value_mapping provided, and skip_auto_mapping is not set,
        # return them to the frontend for confirmation
        if potential_mappings and not value_mapping and not skip_auto_mapping:
            api_logger.info(f"Found potential mappings: {potential_mappings}")
            api_logger.info("Returning potential mappings to frontend for confirmation")
            return {
                "auto_mapping_available": True,
                "potential_mappings": potential_mappings
            }

        # Log the decision based on flags
        if accept_auto_mapping and accept_auto_mapping.lower() == 'true':
            api_logger.info("User accepted automatic mappings")
        elif skip_auto_mapping and skip_auto_mapping.lower() == 'true':
            api_logger.info("User declined automatic mappings")
        elif not potential_mappings:
            api_logger.info("No potential mappings found")
        else:
            api_logger.info("Proceeding with normal processing")

        # Apply existing row mappings to the data if:
        # 1. accept_auto_mapping is set to 'true' (user explicitly accepted the mappings)
        # 2. There are no potential mappings (no auto-mapping scenario)
        # 3. value_mapping is provided (user has provided manual mappings)
        if (accept_auto_mapping and accept_auto_mapping.lower() == 'true') or not potential_mappings or value_mapping:
            # Log which condition triggered the mapping application
            if accept_auto_mapping and accept_auto_mapping.lower() == 'true':
                data_logger.info("Applying mappings because user accepted automatic mappings")
            elif not potential_mappings:
                data_logger.info("Applying mappings because no potential mappings were found")
            elif value_mapping:
                data_logger.info("Applying mappings because user provided manual mappings")
            for column, mappings in row_mappings.items():
                if column in df.columns:
                    data_logger.info(f"Applying existing row mappings to {column}")
                    # Replace values according to the mapping
                    df[column] = df[column].map(
                        lambda x: mappings.get(str(x), x) if str(x) in mappings else x
                    )

        # Validate Main Unit Measurement values
        validation_result = validate_main_unit_measurement(df)
        data_logger.info(f"Validation result: {validation_result}")

        # If validation failed and no value mapping provided, return validation result
        if not validation_result["valid"] and not value_mapping:
            api_logger.info("Validation failed. Returning validation result to frontend.")
            return {
                "validation_required": True,
                "validation_result": validation_result
            }

        # If value mapping provided, apply it to the data
        if value_mapping_dict:
            # Get the column name from the validation result
            column = validation_result.get("column", "Main Unit Measurement")

            if column in df.columns:
                data_logger.info(f"Applying value mapping to {column}")
                # Replace values according to the mapping
                df[column] = df[column].map(
                    lambda x: value_mapping_dict.get(x, x) if x in value_mapping_dict else x
                )

                # Store the mappings for future use
                for original_value, mapped_value in value_mapping_dict.items():
                    add_row_mapping(column, original_value, mapped_value)

                # Validate again after mapping
                validation_result = validate_column_values(df, column)
                data_logger.info(f"Validation result after mapping: {validation_result}")

                # If still invalid, return error
                if not validation_result["valid"]:
                    error_msg = f"Invalid {column} values after mapping"
                    error_logger.error(error_msg)
                    raise HTTPException(status_code=400, detail=error_msg)

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"processed_{timestamp}_{filename}"
        output_path = os.path.join("processed", output_filename)

        # Export to Excel
        from etl import export_to_excel
        result_path = export_to_excel(df, output_path)
        data_logger.info(f"ETL process completed. Output file: {result_path}")

        # Store column mapping for future use
        data_logger.info(f"Storing column mapping for future use")
        add_mapping(mapping_dict)

        api_logger.info(f"File processed successfully: {output_filename}")
        return {"message": "File processed successfully", "output_filename": output_filename}

    except json.JSONDecodeError:
        error_msg = "Invalid column mapping format"
        error_logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"Error processing file: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a processed Excel file and clear processed and uploads folders
    """
    api_logger.info(f"Download requested for file: {filename}")

    file_path = os.path.join("processed", filename)
    if not os.path.exists(file_path):
        error_msg = f"File {filename} not found"
        error_logger.error(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)

    api_logger.info(f"Serving file for download: {file_path}")
    response = FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Clear processed and uploads folders after download
    try:
        # Keep the current file being downloaded
        current_file = os.path.basename(file_path)

        # Clear processed folder (except the file being downloaded)
        for file in os.listdir("processed"):
            if file != current_file:
                file_to_remove = os.path.join("processed", file)
                if os.path.isfile(file_to_remove):
                    os.remove(file_to_remove)
                    api_logger.info(f"Removed processed file: {file}")

        # Clear uploads folder
        for file in os.listdir("uploads"):
            file_to_remove = os.path.join("uploads", file)
            if os.path.isfile(file_to_remove):
                os.remove(file_to_remove)
                api_logger.info(f"Removed uploaded file: {file}")

        api_logger.info("Processed and uploads folders cleared successfully")
    except Exception as e:
        error_msg = f"Error clearing folders: {str(e)}"
        error_logger.error(error_msg)
        # Don't raise an exception here to ensure the download still works

    return response

@api.get("/api/flash-files")
async def flash_files():
    """
    Delete all files in the processed and uploads folders
    Returns the count of deleted files
    """
    api_logger.info("Flash Files requested")

    deleted_count = 0

    try:
        # Count files before deletion
        processed_files = [f for f in os.listdir("processed") if os.path.isfile(os.path.join("processed", f))]
        uploads_files = [f for f in os.listdir("uploads") if os.path.isfile(os.path.join("uploads", f))]

        total_files = len(processed_files) + len(uploads_files)

        # Clear processed folder
        for file in processed_files:
            file_to_remove = os.path.join("processed", file)
            os.remove(file_to_remove)
            deleted_count += 1
            api_logger.info(f"Removed processed file: {file}")

        # Clear uploads folder
        for file in uploads_files:
            file_to_remove = os.path.join("uploads", file)
            os.remove(file_to_remove)
            deleted_count += 1
            api_logger.info(f"Removed uploaded file: {file}")

        api_logger.info(f"Processed and uploads folders cleared successfully. Deleted {deleted_count} files.")
        return {"message": "Folders cleared successfully", "deleted_count": deleted_count}

    except Exception as e:
        error_msg = f"Error clearing folders: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/api/files-count")
async def get_files_count():
    """
    Get the count of files in the processed and uploads folders
    """
    api_logger.info("Files count requested")

    try:
        # Count files
        processed_files = [f for f in os.listdir("processed") if os.path.isfile(os.path.join("processed", f))]
        uploads_files = [f for f in os.listdir("uploads") if os.path.isfile(os.path.join("uploads", f))]

        total_files = len(processed_files) + len(uploads_files)

        api_logger.info(f"Files count: {total_files} (Processed: {len(processed_files)}, Uploads: {len(uploads_files)})")
        return {
            "total": total_files,
            "processed": len(processed_files),
            "uploads": len(uploads_files)
        }

    except Exception as e:
        error_msg = f"Error counting files: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

def get_ip_address():
    """
    Gets the local IP address by connecting to Google's DNS server.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def ensure_folders_exist():
    """
    Ensure that required folders exist
    """
    required_folders = ["processed", "uploads"]
    for folder in required_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            app_logger.info(f"Created folder: {folder}")
        else:
            app_logger.info(f"Folder exists: {folder}")

if __name__ == "__main__":
    import uvicorn
    my_ip = get_ip_address()  # Use 0.0.0.0 to listen on all available network interfaces
    port = 3000

    # Ensure required folders exist
    ensure_folders_exist()

    app_logger.info(f"Starting server on {my_ip}:{port}")
    uvicorn.run("main:api", host=my_ip, port=port, log_level="info", reload=False)
