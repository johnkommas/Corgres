# Softone ERP Excel Formatter

An application to process Excel files for the Softone ERP system by rearranging columns to fit the required format.

## Description

This application provides an ETL (Extract, Transform, Load) process for Excel files containing product information for the Softone ERP system. It allows users to:

1. Upload Excel files with product data
2. Map source columns to the required Softone ERP format
3. Process the data (transform and rearrange columns)
4. Download the processed Excel file

The application ensures that all required columns for the Softone ERP system are present in the output file, including product information and logistics data.

## Technical Stack

- **Backend**: FastAPI, Uvicorn (development), Gunicorn (production), Pandas
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Data Processing**: Pandas for Excel manipulation

## Getting Started

### Prerequisites

- Python 3.7+
- pip

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```
   # Core dependencies
   pip install fastapi uvicorn pandas openpyxl python-dotenv

   # For start_server.py script (process management)
   pip install psutil

   # Optional: for production deployment
   pip install gunicorn
   ```

3. Configure environment variables:
   Create a `.env` file in the root directory with the following variables:
   ```
   GMAIL_USER="your-gmail-username"
   GMAIL_PASS="your-gmail-app-password"
   MAIL_FOLDER="INBOX"
   ```
   Note: If you're using Gmail with 2FA, you'll need to create an App Password. Go to your Google Account > Security > App Passwords.

4. Run the application:
   ```
   # Option 1: Using uvicorn directly
   uvicorn main:api --reload

   # Option 2: Running the Python script (which uses uvicorn internally)
   python main.py

   # Option 3: Using the start_server.py script (handles "Address already in use" errors)
   ./start_server.py
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:3000/
   ```

## How to Use

1. **Upload Excel File**: Click "Choose File" to select an Excel file (.xls or .xlsx) containing your product data, then click "Upload".

2. **Configure Column Mapping**: Map your source Excel columns to the required Softone ERP format. For each required field, enter the corresponding column name from your Excel file.

3. **Process File**: Click "Process File" to transform your data according to the mapping.

4. **Download Result**: Once processing is complete, click "Download Processed File" to get the transformed Excel file.

## Required Columns

The application requires the following columns for the Softone ERP system:

- Product Barcode
- Pallete Barcode
- Description
- Main Unit Measurement
- Vat Category
- Weight
- Height
- Width
- Length
- Storage Location
- Min Stock Level
- Max Stock Level
- Reorder Point

## Application Features

- Modern, intuitive user interface with step-by-step guidance
- Responsive design that works on desktop and mobile devices
- Visual feedback during file processing
- Clear success/error messages
- Streamlined workflow for efficient data transformation

## Project Structure

- `main.py`: The main FastAPI application that handles file processing
- `etl.py`: ETL module for Excel data transformation
- `static/`: Directory for static files
  - `index.html`: The beautifully designed user interface with modern styling
- `uploads/`: Directory for temporarily storing uploaded Excel files
- `processed/`: Directory for storing transformed Excel files
- `test_etl.py`: Test script for the ETL functionality

## Testing

To run the ETL tests:

```
python test_etl.py
```

## Server Management

### Using start_server.py

The `start_server.py` script provides a robust way to start the application while handling common issues like "Address already in use" errors. It offers the following features:

- Automatically detects and activates virtual environments
- Checks if the port is already in use and stops conflicting processes
- Restarts the server if it crashes
- Provides clear feedback about server status
- Handles graceful shutdown on keyboard interrupts

To use the script with custom settings:

```
# Basic usage (uses default settings: host=0.0.0.0, port=3000, with auto-reload)
./start_server.py

# Custom host and port
./start_server.py --host 127.0.0.1 --port 8080

# Disable auto-reload for production
./start_server.py --no-reload
```

The script requires the `psutil` package for process management:

```
pip install psutil
```

## Production Deployment

For production environments, it's recommended to use Gunicorn with Uvicorn workers:

1. Install Gunicorn:
   ```
   pip install gunicorn
   ```

2. Run with Gunicorn and Uvicorn workers:
   ```
   gunicorn main:api -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000
   ```

   This setup provides better performance and reliability for production workloads.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
