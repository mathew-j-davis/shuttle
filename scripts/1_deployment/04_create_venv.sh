#!/bin/bash

# Check if Python3 and pip are installed
if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
    echo "Python3 and/or pip3 are not installed. Please run install_python.sh first."
    exit 1
fi

# Check if SHUTTLE_VENV_PATH is set
if [ -z "$SHUTTLE_VENV_PATH" ]; then
    echo "SHUTTLE_VENV_PATH environment variable is not set."
    echo "Please run 00_set_env.sh first."
    exit 1
fi

# Create a virtual environment
echo "Creating a virtual environment at $SHUTTLE_VENV_PATH..."
python3 -m venv "$SHUTTLE_VENV_PATH"

# set exec permissions on activate
echo "Set execute permissions on virtual environment activate..."
chmod +x "$SHUTTLE_VENV_PATH/bin/activate"


