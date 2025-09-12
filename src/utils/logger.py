import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import List, Tuple

# Create logs directory if it doesn't exist
os.makedirs("src/logs/api", exist_ok=True)
os.makedirs("src/logs/app", exist_ok=True)
os.makedirs("src/logs/data_processing", exist_ok=True)
os.makedirs("src/logs/database", exist_ok=True)
os.makedirs("src/logs/errors", exist_ok=True)

# Root logs directory and cap
LOGS_DIR = "src/logs"
# Allow override via env var; default 100 MB
MAX_LOGS_TOTAL_MB = int(os.getenv("LOGS_MAX_TOTAL_MB", "100"))
MAX_LOGS_TOTAL_BYTES = MAX_LOGS_TOTAL_MB * 1024 * 1024
# When pruning, reduce to 90% of cap to avoid frequent churn
PRUNE_TARGET_BYTES = int(MAX_LOGS_TOTAL_BYTES * 0.9)

# Define log format
LOG_FORMAT = "%(asctime)s\t[%(name)s]\t[%(levelname)s]\t[%(message)s]"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def _list_log_files() -> List[str]:
    files: List[str] = []
    for root, _, filenames in os.walk(LOGS_DIR):
        for fname in filenames:
            if fname.endswith('.log'):
                files.append(os.path.join(root, fname))
    return files

def _directory_size_bytes(path: str) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                continue
    return total

def enforce_logs_quota():
    """Ensure total size of all logs stays under MAX_LOGS_TOTAL_BYTES.

    Strategy: delete oldest log files first until total <= PRUNE_TARGET_BYTES.
    This is safer than flushing everything at once and preserves recent diagnostics.
    """
    try:
        total = _directory_size_bytes(LOGS_DIR)
        if total <= MAX_LOGS_TOTAL_BYTES:
            return

        # Build list of (path, mtime, size)
        entries: List[Tuple[str, float, int]] = []
        for path in _list_log_files():
            try:
                stat = os.stat(path)
                entries.append((path, stat.st_mtime, stat.st_size))
            except OSError:
                continue
        # Sort by mtime ascending (oldest first)
        entries.sort(key=lambda x: x[1])

        # Delete until under target
        for path, _, size in entries:
            try:
                os.remove(path)
            except OSError:
                continue
            total -= size
            if total <= PRUNE_TARGET_BYTES:
                break
    except Exception:
        # Never let quota enforcement crash the application
        pass

def get_logger(name, log_file, level=logging.INFO):
    """
    Create or retrieve a logger with the specified name and log file.
    Ensures handlers are not added multiple times to avoid duplicate log lines.

    Args:
        name: Logger name
        log_file: Path to the log file
        level: Logging level

    Returns:
        Logger instance
    """
    # Enforce quota before opening/creating handlers
    enforce_logs_quota()

    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Prevent propagation to root to avoid double logging via root handlers
    logger.propagate = False

    # If handlers already exist, reuse the existing logger (avoid duplicates)
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # Create file handler for logging to a file
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Create console handler for logging to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Run quota enforcement immediately on import as well
enforce_logs_quota()

# Create loggers for different components
def get_api_logger():
    """Get logger for API operations"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"src/logs/api/api_{today}.log"
    return get_logger("api", log_file)

def get_app_logger():
    """Get logger for general application operations"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"src/logs/app/app_{today}.log"
    return get_logger("app", log_file)

def get_data_processing_logger():
    """Get logger for data processing operations"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"src/logs/data_processing/data_processing_{today}.log"
    return get_logger("data_processing", log_file)

def get_database_logger():
    """Get logger for database operations"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"src/logs/database/database_{today}.log"
    return get_logger("database", log_file)

def get_error_logger():
    """Get logger for errors"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"src/logs/errors/errors_{today}.log"
    return get_logger("errors", log_file, level=logging.ERROR)

# Function to get all logs for display in UI
def get_all_logs(max_entries=100):
    """
    Get all logs from all log files

    Args:
        max_entries: Maximum number of log entries to return. If None, returns all logs.

    Returns:
        List of log entries sorted by date (newest first)
    """
    logs = []

    # Get all log files
    log_files = []
    for root, _, files in os.walk("src/logs"):
        for file in files:
            if file.endswith(".log"):
                log_files.append(os.path.join(root, file))

    # Read log entries from each file
    for log_file in log_files:
        try:
            with open(log_file, "r") as f:
                for line in f:
                    # Parse log entry
                    try:
                        # Check if the log entry uses tabs or dashes as separators
                        if "\t" in line:
                            # New format with tabs
                            parts = line.split("\t")
                            timestamp_str = parts[0].strip()
                            timestamp = datetime.strptime(timestamp_str, DATE_FORMAT)

                            # Extract component from the log entry
                            if len(parts) >= 2:
                                component_part = parts[1].strip()
                                if component_part.startswith("[") and component_part.endswith("]"):
                                    component = component_part[1:-1]  # Remove brackets
                                else:
                                    component = component_part
                            else:
                                # Fallback to getting log type from file path
                                component = os.path.basename(os.path.dirname(log_file))
                        else:
                            # Old format with dashes
                            timestamp_str = line.split(" - ")[0].strip()
                            timestamp = datetime.strptime(timestamp_str, DATE_FORMAT)

                            # Extract log level and component from the log entry
                            parts = line.split(" - ")
                            if len(parts) >= 3:
                                # Try to extract component from the log entry
                                component_part = parts[1].strip()
                                if component_part.startswith("[") and component_part.endswith("]"):
                                    component = component_part[1:-1]  # Remove brackets
                                else:
                                    component = component_part
                            else:
                                # Fallback to getting log type from file path
                                component = os.path.basename(os.path.dirname(log_file))

                        # Use component as log_type
                        log_type = component

                        logs.append({
                            "timestamp": timestamp,
                            "type": log_type,
                            "message": line.strip(),
                            "raw": line.strip()
                        })
                    except Exception:
                        # Skip malformed log entries
                        continue
        except Exception:
            # Skip if file can't be read
            continue

    # Sort logs by timestamp (newest first)
    logs.sort(key=lambda x: x["timestamp"], reverse=True)

    # Limit number of entries if max_entries is not None
    if max_entries is not None:
        return logs[:max_entries]
    else:
        return logs
