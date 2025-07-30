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
    # Try normal install first, capture output to detect permission errors
    install_output=$(pip3 install -r "$REQUIREMENTS_FILE" 2>&1)
    install_exit_code=$?
    
    # Check for permission errors in output even if exit code was 0
    if [[ $install_exit_code -ne 0 ]] || echo "$install_output" | grep -q "Permission denied\|OSError.*Errno 13"; then
        if echo "$install_output" | grep -q "Permission denied\|OSError.*Errno 13"; then
            echo "Permission error detected in pip output, trying with --force-reinstall..."
        else
            echo "Standard install failed (exit code: $install_exit_code), trying with --force-reinstall..."
        fi
        echo "Original error output:"
        echo "$install_output"
        echo "Retrying with --force-reinstall to handle conflicts..."
        pip3 install --force-reinstall --no-deps -r "$REQUIREMENTS_FILE"
    else
        echo "$install_output"
    fi
fi

echo "All done!"