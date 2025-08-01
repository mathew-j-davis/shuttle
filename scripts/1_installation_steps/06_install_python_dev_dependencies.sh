#!/bin/bash

# Parse command line arguments
DRY_RUN=false
VERBOSE=false
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=true
  elif [ "$arg" = "--verbose" ]; then
    VERBOSE=true
  fi
done

# Install Python packages from requirements.txt
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

echo "Installing Python packages from requirements.txt..."
echo "Requirements file: $REQUIREMENTS_FILE"

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo "ERROR: Requirements file not found: $REQUIREMENTS_FILE"
    exit 1
fi

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would install Python packages: pip3 install -r $REQUIREMENTS_FILE"
    echo "[DRY RUN] Packages that would be installed:"
    cat "$REQUIREMENTS_FILE"
else
    # Use --force-reinstall directly to handle permission conflicts
    echo "Installing with --force-reinstall to handle any permission conflicts..."
    pip3 install --force-reinstall -r "$REQUIREMENTS_FILE"
fi

echo "All done!"