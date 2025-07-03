# Excel ETL for Softone ERP

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
   pip install fastapi uvicorn pandas openpyxl

   # Optional: for production deployment
   pip install gunicorn
   ```

3. Run the application:
   ```
   # Option 1: Using uvicorn directly
   uvicorn main:app --reload

   # Option 2: Running the Python script (which uses uvicorn internally)
   python main.py
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000/
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

## Production Deployment

For production environments, it's recommended to use Gunicorn with Uvicorn workers:

1. Install Gunicorn:
   ```
   pip install gunicorn
   ```

2. Run with Gunicorn and Uvicorn workers:
   ```
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```

   This setup provides better performance and reliability for production workloads.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
