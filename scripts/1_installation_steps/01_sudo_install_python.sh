#!/bin/bash

# Parse command line arguments for dry-run
DRY_RUN=false
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=true
  fi
done

# Install Python 3 and pip
if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would install Python3 and pip:"
    echo "[DRY RUN]   sudo apt-get install -y python3 python3-pip"
    echo "[DRY RUN]   sudo apt install python3-venv"
else
    echo "Installing Python3 and pip..."
    sudo apt-get install -y python3 python3-pip
    sudo apt install python3-venv
fi

echo "All done!"