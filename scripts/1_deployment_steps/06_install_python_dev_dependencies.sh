#!/bin/bash

# Install Python packages from requirements.txt
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

echo "Installing Python packages from requirements.txt..."
echo "Requirements file: $REQUIREMENTS_FILE"

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo "ERROR: Requirements file not found: $REQUIREMENTS_FILE"
    exit 1
fi

pip3 install -r "$REQUIREMENTS_FILE"

echo "All done!"