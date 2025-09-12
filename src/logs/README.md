# Logging System

This directory contains log files for the Excel ETL for Softone ERP application.

## Directory Structure

- **api/**: Logs related to API operations (requests, responses)
- **app/**: Logs related to general application operations
- **data_processing/**: Logs related to data processing operations (ETL)
- **database/**: Logs related to database operations
- **errors/**: Error logs from all components

## Log Format

Logs are stored in the following format:

```
YYYY-MM-DD HH:MM:SS - [COMPONENT] - [LEVEL] - [MESSAGE]
```

Where:
- **YYYY-MM-DD HH:MM:SS**: Timestamp
- **COMPONENT**: Component name (api, app, data_processing, database, errors)
- **LEVEL**: Log level (INFO, WARNING, ERROR, DEBUG)
- **MESSAGE**: Log message

## Log Rotation

- Per-file rotation: Logs are automatically rotated when they reach 10MB in size. The system keeps up to 5 backup files for each log file.
- Total folder cap: The entire `src/logs` directory is capped at 100MB by default. When the total size exceeds the cap, the system automatically prunes the oldest `.log` files first until the total size falls below 90% of the cap. This preserves the most recent diagnostics while keeping disk usage bounded.
- You can override the cap by setting the environment variable `LOGS_MAX_TOTAL_MB` (e.g., `LOGS_MAX_TOTAL_MB=200`).

## Viewing Logs

Logs can be viewed in the application UI by navigating to the `/logs` endpoint.

## Log Levels

- **INFO**: General information about system operation
- **WARNING**: Warning messages that don't affect system operation but might indicate issues
- **ERROR**: Error messages that affect system operation
- **DEBUG**: Detailed debug information (only available in development mode)