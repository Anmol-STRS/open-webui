#!/usr/bin/env python3
"""
Open WebUI Launcher
Starts both frontend (npm) and backend (uvicorn) servers
"""

import subprocess
import sys
import os
import time
import platform
import signal
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

# Store process references
processes = []

def cleanup(signum=None, frame=None):
    """Clean up processes on exit"""
    print_warning("\nShutting down servers...")

    for process in processes:
        try:
            if platform.system() == "Windows":
                process.terminate()
            else:
                process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
            print_success(f"Stopped process {process.pid}")
        except Exception as e:
            print_error(f"Error stopping process: {e}")

    print_success("All servers stopped")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def check_node():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run(['node', '--version'],
                              capture_output=True,
                              text=True)
        version = result.stdout.strip()
        print_success(f"Node.js: {version}")
        return True
    except FileNotFoundError:
        print_error("Node.js is not installed!")
        print_info("Download from: https://nodejs.org/")
        return False

def check_python():
    """Check if Python is installed"""
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_success(f"Python: {version}")
    return True

def check_npm_packages():
    """Check if npm packages are installed"""
    if not os.path.exists('node_modules'):
        print_warning("npm packages not installed")
        print_info("Installing npm packages...")
        subprocess.run(['npm', 'install'], check=True)
        print_success("npm packages installed")
    else:
        print_success("npm packages found")

def check_python_packages():
    """Check if Python packages are installed"""
    try:
        import fastapi
        import uvicorn
        print_success("Python packages found")
        return True
    except ImportError:
        print_warning("Python packages not fully installed")
        print_info("Installing Python packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'backend/requirements.txt'])
        print_success("Python packages installed")
        return True

def start_backend():
    """Start the backend server"""
    print_info("Starting backend server...")

    backend_dir = Path('backend')

    env = os.environ.copy()
    env['CORS_ALLOW_ORIGIN'] = 'http://localhost:5173'
    env['PORT'] = '8080'

    # Start uvicorn
    if platform.system() == "Windows":
        process = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'open_webui.main:app',
             '--port', '8080', '--host', '0.0.0.0', '--reload'],
            cwd=backend_dir,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
        )
    else:
        process = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'open_webui.main:app',
             '--port', '8080', '--host', '0.0.0.0', '--reload'],
            cwd=backend_dir,
            env=env
        )

    processes.append(process)
    print_success(f"Backend started (PID: {process.pid})")
    print_info("Backend URL: http://localhost:8080")
    return process

def start_frontend():
    """Start the frontend server"""
    print_info("Starting frontend server...")

    # Start npm dev server
    if platform.system() == "Windows":
        # On Windows, use cmd.exe to run npm
        process = subprocess.Popen(
            ['cmd', '/c', 'npm', 'run', 'dev'],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            shell=True
        )
    else:
        process = subprocess.Popen(['npm', 'run', 'dev'])

    processes.append(process)
    print_success(f"Frontend started (PID: {process.pid})")
    print_info("Frontend URL: http://localhost:5173")
    return process

def main():
    print_header("Open WebUI - React Preview Edition")

    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    print_info(f"Working directory: {script_dir}")

    # Check prerequisites
    print_header("Checking Prerequisites")

    if not check_python():
        sys.exit(1)

    if not check_node():
        sys.exit(1)

    print_header("Installing Dependencies")

    try:
        check_npm_packages()
        check_python_packages()
    except Exception as e:
        print_error(f"Failed to install dependencies: {e}")
        sys.exit(1)

    print_header("Starting Servers")

    try:
        # Start backend first
        backend_process = start_backend()
        time.sleep(3)  # Give backend time to start

        # Start frontend
        frontend_process = start_frontend()
        time.sleep(2)

        print_header("Open WebUI is Running!")
        print_success("✓ Backend:  http://localhost:8080")
        print_success("✓ Frontend: http://localhost:5173")
        print()
        print_info("React Preview Feature Included!")
        print_info("- Generate React code in chat")
        print_info("- Click 'Preview' button")
        print_info("- View live interactive components")
        print()
        print_warning("Press Ctrl+C to stop all servers")
        print()

        # Wait for processes
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print_error("Backend process stopped unexpectedly")
                cleanup()

            if frontend_process.poll() is not None:
                print_error("Frontend process stopped unexpectedly")
                cleanup()

            time.sleep(1)

    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print_error(f"Error: {e}")
        cleanup()
        sys.exit(1)

if __name__ == '__main__':
    main()
