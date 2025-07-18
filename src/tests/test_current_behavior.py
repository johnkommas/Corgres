#!/usr/bin/env python3
"""
Script to test the current visitor statistics behavior.
This will start the server and allow us to see how the user count is currently displayed.
"""

import subprocess
import time
import webbrowser
import sys
import os

def test_current_behavior():
    print("Testing current visitor statistics behavior...")
    print("=" * 50)
    
    # Change to project directory
    project_dir = "/Users/johnkommas/PycharmProjects/Corgres"
    os.chdir(project_dir)
    
    try:
        # Start the server
        print("Starting the server...")
        server_process = subprocess.Popen([sys.executable, "main.py"], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Open the selection page in browser
        print("Opening selection page in browser...")
        webbrowser.open("http://localhost:5000/selection")
        
        print("\nCurrent behavior:")
        print("1. The user count should be visible as text in the Excel Formatter card")
        print("2. It shows '0 users' when no one is using the app")
        print("3. It shows 'X user(s)' when people are using the app")
        print("\nExpected change:")
        print("1. The user count text should be hidden")
        print("2. On mouse hover over the card, it should show the count as a tooltip")
        print("\nPress Ctrl+C to stop the server and continue with implementation...")
        
        # Wait for user to stop
        server_process.wait()
        
    except KeyboardInterrupt:
        print("\nStopping server...")
        server_process.terminate()
        server_process.wait()
        print("Server stopped. Ready to implement changes.")
    except Exception as e:
        print(f"Error: {e}")
        if 'server_process' in locals():
            server_process.terminate()

if __name__ == "__main__":
    test_current_behavior()