"""
Setup script for The Library.
Quick development setup and index building.
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install Python requirements"""
    print("Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build_index():
    """Build the search index"""
    print("Building search index...")

    # Ensure index directory exists
    os.makedirs("index", exist_ok=True)

    # Run indexer
    subprocess.check_call([sys.executable, "-m", "indexer.build_index"])

def start_api():
    """Start the FastAPI development server"""
    print("Starting API server...")
    subprocess.check_call([
        sys.executable, "-m", "uvicorn",
        "api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ])

def main():
    print("The Library - Setup Script")
    print("=" * 30)

    if len(sys.argv) < 2:
        print("Usage: python setup.py [install|index|run|all]")
        print("  install - Install dependencies")
        print("  index   - Build search index")
        print("  run     - Start API server")
        print("  all     - Do all of the above")
        return

    command = sys.argv[1]

    if command == "install":
        install_requirements()
    elif command == "index":
        build_index()
    elif command == "run":
        start_api()
    elif command == "all":
        install_requirements()
        build_index()
        start_api()
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()