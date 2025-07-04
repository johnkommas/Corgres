#!/usr/bin/env python3
"""
Main entry point for the Corgres application.
This file imports and runs the application from the new structure.
"""
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the API from the core module
from src.core.main import api

if __name__ == "__main__":
    import uvicorn
    from src.core.main import get_ip_address, ensure_folders_exist

    my_ip = get_ip_address()  # Use 0.0.0.0 to listen on all available network interfaces
    port = 3000

    # Ensure required folders exist
    ensure_folders_exist()

    print(f"Starting server on {my_ip}:{port}")
    uvicorn.run("src.core.main:api", host=my_ip, port=port, log_level="info", reload=False)
