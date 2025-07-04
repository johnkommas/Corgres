import os
import time
from utils.logger import get_api_logger, get_app_logger, get_data_processing_logger, get_database_logger, get_error_logger

def test_chart_logs():
    """Generate logs for testing charts"""
    print("Generating logs for testing charts...")
    
    # Create loggers
    api_logger = get_api_logger()
    app_logger = get_app_logger()
    data_logger = get_data_processing_logger()
    db_logger = get_database_logger()
    error_logger = get_error_logger()
    
    # Generate logs with different levels
    for i in range(10):
        # API logs
        api_logger.info(f"API info log {i}")
        if i % 3 == 0:
            api_logger.warning(f"API warning log {i}")
        if i % 5 == 0:
            api_logger.error(f"API error log {i}")
        
        # App logs
        app_logger.info(f"App info log {i}")
        if i % 4 == 0:
            app_logger.warning(f"App warning log {i}")
        if i % 7 == 0:
            app_logger.error(f"App error log {i}")
        
        # Data processing logs
        data_logger.info(f"Data processing info log {i}")
        if i % 3 == 1:
            data_logger.warning(f"Data processing warning log {i}")
        if i % 6 == 0:
            data_logger.error(f"Data processing error log {i}")
        
        # Database logs
        db_logger.info(f"Database info log {i}")
        if i % 5 == 2:
            db_logger.warning(f"Database warning log {i}")
        if i % 8 == 0:
            db_logger.error(f"Database error log {i}")
        
        # Add a small delay to spread logs over time
        time.sleep(0.1)
    
    print("Logs generated successfully!")
    print("Now you can view the charts at http://localhost:3000/logs")

if __name__ == "__main__":
    test_chart_logs()