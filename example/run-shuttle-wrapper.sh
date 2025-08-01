#!/bin/bash
# /usr/local/bin/run-shuttle - Production wrapper for shuttle
# This script sources the virtual environment and environment variables before running shuttle

set -euo pipefail

# Source environment variables
if [[ -f /etc/shuttle/shuttle_env.sh ]]; then
    source /etc/shuttle/shuttle_env.sh
else
    echo "Error: Environment file /etc/shuttle/shuttle_env.sh not found" >&2
    exit 1
fi

# Activate virtual environment
if [[ -f /opt/shuttle/venv/bin/activate ]]; then
    source /opt/shuttle/venv/bin/activate
else
    echo "Error: Virtual environment not found at /opt/shuttle/venv" >&2
    exit 1
fi

# Ensure required environment variables are set
export SHUTTLE_CONFIG_PATH="${SHUTTLE_CONFIG_PATH:-/etc/shuttle/config.conf}"

# Log the execution
logger -t shuttle "Starting shuttle execution by user $(whoami)"

# Execute shuttle with all passed arguments
exec python3 -m shuttle.shuttle "$@"