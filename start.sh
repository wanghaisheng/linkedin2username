#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to start the FastAPI server
start_fastapi_server() {
    if command_exists uvicorn; then
        echo "Starting FastAPI server..."
        uvicorn server:app --reload
    else
        echo "Error: uvicorn is not installed. Please install it using 'pip install uvicorn'."
        exit 1
    fi
}

# Detect the operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux"
    start_fastapi_server
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS"
    start_fastapi_server
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "Detected Windows"
    start_fastapi_server
else
    echo "Unsupported operating system"
    exit 1
fi
