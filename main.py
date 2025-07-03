from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import os
import json
import shutil
import uuid
from typing import Dict, Optional
from datetime import datetime

from etl import process_excel_file, get_column_mapping_template

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("processed", exist_ok=True)

api = FastAPI(
    title="Excel ETL for Softone ERP",
    description="An application to process Excel files for Softone ERP system",
    version="1.0.0",
    docs_url=None,  # Disable Swagger UI
    redoc_url=None  # Disable ReDoc
)

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

@api.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint that serves the index.html file
    """
    with open("static/index.html") as f:
        return f.read()

@api.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel file for processing
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xls, .xlsx) are allowed")

    # Generate a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{file.filename}"
    file_path = os.path.join("uploads", filename)

    # Save the uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": filename, "file_path": file_path}

@api.get("/column-mapping-template/")
async def get_mapping_template():
    """
    Get a template for column mapping
    """
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
    try:
        # Parse the column mapping JSON
        mapping_dict = json.loads(column_mapping)

        # Validate the input file exists
        input_path = os.path.join("uploads", filename)
        if not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail=f"File {filename} not found")

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"processed_{timestamp}_{filename}"
        output_path = os.path.join("processed", output_filename)

        # Process the file
        result_path = process_excel_file(input_path, output_path, mapping_dict)

        return {"message": "File processed successfully", "output_filename": output_filename}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid column mapping format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a processed Excel file
    """
    file_path = os.path.join("processed", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    import uvicorn
    my_ip = "0.0.0.0"  # Use 0.0.0.0 to listen on all available network interfaces
    uvicorn.run("main:api", host=my_ip, port=3000, log_level="info", reload=False)
