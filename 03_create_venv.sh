#!/bin/bash

# Check if Python3 and pip are installed
if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
    echo "Python3 and/or pip3 are not installed. Please run install_python.sh first."
    exit 1
fi

# Create a virtual environment
echo "Creating a virtual environment..."
python3 -m venv venv


# set exec permissions on activate
echo "Set execute permissions on virtual environment activate..."
chmod +x ./venv/bin/activate

# Activate the virtual environment
echo "Activating the virtual environment..."
. venv/bin/activate

# windows gitbash
#source venv/Scripts/activate

