import os
import time
from utils.logger import get_api_logger, get_app_logger, get_data_processing_logger, get_database_logger, get_error_logger, get_all_logs

def test_logging():
    """Test the logging system"""
    print("Testing logging system...")
    
    # Create loggers
    api_logger = get_api_logger()
    app_logger = get_app_logger()
    data_logger = get_data_processing_logger()
    db_logger = get_database_logger()
    error_logger = get_error_logger()
    
    # Log some messages
    api_logger.info("API test log message")
    app_logger.info("App test log message")
    data_logger.info("Data processing test log message")
    db_logger.info("Database test log message")
    error_logger.error("Error test log message")
    
    # Wait for logs to be written
    time.sleep(1)
    
    # Get all logs
    logs = get_all_logs(max_entries=10)
    
    # Check if logs were created
    if len(logs) >= 5:
        print("✅ Logging test passed! Found logs:")
        for i, log in enumerate(logs[:5]):
            print(f"{i+1}. [{log['type']}] {log['message']}")
    else:
        print("❌ Logging test failed! Not enough logs found.")
        print(f"Found {len(logs)} logs:")
        for i, log in enumerate(logs):
            print(f"{i+1}. [{log['type']}] {log['message']}")
    
    # Check if log files were created
    log_files = []
    for root, _, files in os.walk("logs"):
        for file in files:
            if file.endswith(".log"):
                log_files.append(os.path.join(root, file))
    
    if len(log_files) >= 5:
        print("\n✅ Log files created successfully!")
        print("Log files:")
        for file in log_files:
            print(f"- {file}")
    else:
        print("\n❌ Not all log files were created!")
        print("Log files found:")
        for file in log_files:
            print(f"- {file}")

if __name__ == "__main__":
    test_logging()