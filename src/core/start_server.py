#!/usr/bin/env python3
import os
import sys
import signal
import subprocess
import socket
import atexit
import time
import psutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if we're running in a virtual environment
def activate_venv():
    """Activate virtual environment if it exists."""
    venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
    if os.path.isdir(venv_path):
        print(f"Found virtual environment at {venv_path}")
        # If we're not already in the venv, restart the script within the venv
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("Activating virtual environment...")

            # Check for Unix-style path (venv/bin/python)
            venv_python = os.path.join(venv_path, "bin", "python")

            # Check for Windows-style path (venv\Scripts\python.exe) if Unix path doesn't exist
            if not os.path.exists(venv_python):
                venv_python = os.path.join(venv_path, "Scripts", "python.exe")

            if os.path.exists(venv_python):
                print(f"Restarting with {venv_python}")
                os.execl(venv_python, venv_python, *sys.argv)
            else:
                print(f"Warning: Could not find Python executable in {venv_path}")
        else:
            print("Already running in virtual environment")
    else:
        print("No virtual environment found at '.venv'")

# Try to activate virtual environment
activate_venv()

def get_ip_address():
    """Get the IP address of the machine."""
    try:
        # Try to get the IP address using socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except:
        # Fallback to localhost if unable to determine IP
        return "127.0.0.1"

def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_uvicorn_processes(port=None):
    """Find all running uvicorn processes, optionally filtering by port."""
    uvicorn_pids = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if this is a uvicorn process
            if proc.info['name'] == 'python' or 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and ('uvicorn' in ' '.join(cmdline) or 'main:api' in ' '.join(cmdline) or 'src.core.main:api' in ' '.join(cmdline)):
                    # If port is specified, check if this process is using that port
                    if port is None or (f"--port={port}" in cmdline or f"--port {port}" in ' '.join(cmdline)):
                        uvicorn_pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return uvicorn_pids

def stop_uvicorn(port=None):
    """Stop all running uvicorn processes, optionally filtering by port."""
    print("Checking for running uvicorn processes...")
    uvicorn_pids = find_uvicorn_processes(port)

    if not uvicorn_pids:
        print("No running uvicorn processes found.")
        return

    print(f"Found uvicorn processes with PIDs: {uvicorn_pids}")
    print("Stopping uvicorn processes...")

    # Kill each uvicorn process
    for pid in uvicorn_pids:
        try:
            print(f"Killing process {pid}...")
            os.kill(pid, signal.SIGTERM)

            # Wait for the process to terminate
            try:
                process = psutil.Process(pid)
                process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                # If process doesn't exist or timeout, try SIGKILL
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        except ProcessLookupError:
            print(f"Process {pid} not found.")
        except Exception as e:
            print(f"Error killing process {pid}: {e}")

    print("All uvicorn processes have been stopped.")

    # Small delay to ensure processes are fully terminated
    time.sleep(1)

def start_uvicorn(host="0.0.0.0", port=3000, reload=True):
    """Start the uvicorn server."""
    # Ensure logs directory exists
    os.makedirs("src/logs", exist_ok=True)

    # Get the IP address
    ip_address = get_ip_address() if host == "0.0.0.0" else host

    print(f"Starting Corgres application with uvicorn...")
    print(f"Application will be accessible at: http://{ip_address}:{port}")

    # Check if we're in a virtual environment and use its uvicorn if available
    venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
    python_cmd = "python"

    if os.path.isdir(venv_path):
        # Check for Unix-style path (venv/bin/python)
        venv_python = os.path.join(venv_path, "bin", "python")

        # Check for Windows-style path (venv\Scripts\python.exe) if Unix path doesn't exist
        if not os.path.exists(venv_python):
            venv_python = os.path.join(venv_path, "Scripts", "python.exe")

        if os.path.exists(venv_python):
            python_cmd = venv_python
            print(f"Using virtual environment python: {venv_python}")
        else:
            print(f"Warning: Could not find python in virtual environment at {venv_path}")
            print("Using system python instead.")

    # Start uvicorn
    reload_flag = "--reload" if reload else ""
    cmd = [python_cmd, "-m", "uvicorn", "src.core.main:api", f"--host={host}", f"--port={port}"]
    if reload:
        cmd.append("--reload")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return process

def restart_services(host="0.0.0.0", port=3000, reload=True):
    """Restart all services."""
    print("Restarting services...")
    stop_uvicorn(port)
    return start_uvicorn(host, port, reload)

def cleanup():
    """Clean up resources when the script exits."""
    print("\nShutting down services...")
    stop_uvicorn()
    print("All services have been stopped.")

def main():
    """Main function to run the application."""
    # Register the cleanup function to be called on exit
    atexit.register(cleanup)

    # Handle keyboard interrupts
    def signal_handler(sig, frame):
        print("\nReceived keyboard interrupt. Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Start the Corgres application with uvicorn')
    parser.add_argument('--host', type=str, default="0.0.0.0", help='Host to bind to')
    parser.add_argument('--port', type=int, default=3000, help='Port to bind to')
    parser.add_argument('--no-reload', action='store_true', help='Disable auto-reload')
    args = parser.parse_args()

    host = args.host
    port = args.port
    reload = not args.no_reload

    # Check if the port is already in use
    if is_port_in_use(port):
        print(f"Port {port} is already in use. Stopping existing process...")
        stop_uvicorn(port)

    # Start uvicorn
    process = start_uvicorn(host, port, reload)

    # Keep the script running to handle signals and monitor the process
    try:
        while True:
            # Check if the process is still running
            if process.poll() is not None:
                print(f"uvicorn process exited with code {process.returncode}")
                # Print any error output
                stderr = process.stderr.read()
                if stderr:
                    print(f"Error output: {stderr}")

                # If the process exited due to port already in use, try to stop the existing process and restart
                if "Address already in use" in stderr:
                    print("Detected 'Address already in use' error. Attempting to stop existing process and restart...")
                    stop_uvicorn(port)
                    time.sleep(2)  # Wait a bit for the port to be released
                    process = start_uvicorn(host, port, reload)
                else:
                    # For other errors, just exit
                    break

            # Sleep to avoid high CPU usage
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
