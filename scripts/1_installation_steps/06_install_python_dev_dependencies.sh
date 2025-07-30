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
    # Try normal install first, capture all output to detect errors
    echo "Attempting pip install..."
    install_output=$(pip3 install -r "$REQUIREMENTS_FILE" 2>&1)
    install_exit_code=$?
    
    echo "Pip install completed with exit code: $install_exit_code"
    echo "=== PIP OUTPUT START ==="
    echo "$install_output"
    echo "=== PIP OUTPUT END ==="
    
    # Check for various error patterns that indicate we should retry
    should_retry=false
    error_reason=""
    
    # Check exit code
    if [[ $install_exit_code -ne 0 ]]; then
        should_retry=true
        error_reason="non-zero exit code ($install_exit_code)"
    fi
    
    # Check for permission errors (multiple patterns)
    if echo "$install_output" | grep -qi "permission denied"; then
        should_retry=true
        error_reason="${error_reason:+$error_reason and }permission denied error"
    fi
    
    if echo "$install_output" | grep -qi "errno 13"; then
        should_retry=true
        error_reason="${error_reason:+$error_reason and }errno 13 error"
    fi
    
    if echo "$install_output" | grep -qi "could not install packages due to.*oserror"; then
        should_retry=true
        error_reason="${error_reason:+$error_reason and }OSError during installation"
    fi
    
    if echo "$install_output" | grep -qi "error.*installing.*permission"; then
        should_retry=true
        error_reason="${error_reason:+$error_reason and }installation permission error"
    fi
    
    if [[ "$should_retry" == "true" ]]; then
        echo "ERROR DETECTED: $error_reason"
        echo "Retrying with --force-reinstall to handle conflicts..."
        pip3 install --force-reinstall --no-deps -r "$REQUIREMENTS_FILE"
    else
        echo "Installation appears successful"
    fi
fi

echo "All done!"