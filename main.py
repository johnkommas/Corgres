import socket

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

from etl import process_excel_file, get_column_mapping_template
from utils.logger import get_api_logger, get_app_logger, get_data_processing_logger, get_error_logger, get_all_logs

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
    from etl import read_excel
    try:
        df = read_excel(file_path)
        column_names = df.columns.tolist()
        data_logger.info(f"Read Excel file with {len(df)} rows and {len(column_names)} columns")
    except Exception as e:
        error_msg = f"Error reading column names: {str(e)}"
        error_logger.error(error_msg)
        column_names = []

    return {"filename": filename, "file_path": file_path, "column_names": column_names}

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
    column_mapping: str = Form(...)
):
    """
    Process an Excel file with the provided column mapping
    """
    api_logger.info(f"Processing file: {filename}")

    try:
        # Parse the column mapping JSON
        mapping_dict = json.loads(column_mapping)
        data_logger.info(f"Column mapping: {mapping_dict}")

        # Validate the input file exists
        input_path = os.path.join("uploads", filename)
        if not os.path.exists(input_path):
            error_msg = f"File {filename} not found"
            error_logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"processed_{timestamp}_{filename}"
        output_path = os.path.join("processed", output_filename)

        # Process the file
        data_logger.info(f"Starting ETL process for {input_path}")
        result_path = process_excel_file(input_path, output_path, mapping_dict)
        data_logger.info(f"ETL process completed. Output file: {result_path}")

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
    Download a processed Excel file
    """
    api_logger.info(f"Download requested for file: {filename}")

    file_path = os.path.join("processed", filename)
    if not os.path.exists(file_path):
        error_msg = f"File {filename} not found"
        error_logger.error(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)

    api_logger.info(f"Serving file for download: {file_path}")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def get_ip_address():
    """
    Gets the local IP address by connecting to Google's DNS server.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

if __name__ == "__main__":
    import uvicorn
    my_ip = get_ip_address()  # Use 0.0.0.0 to listen on all available network interfaces
    port = 3000

    app_logger.info(f"Starting server on {my_ip}:{port}")
    uvicorn.run("main:api", host=my_ip, port=port, log_level="info", reload=False)
