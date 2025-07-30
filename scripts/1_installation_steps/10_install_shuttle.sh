#!/bin/bash
set -e

# Parse command line arguments
dev_mode=""
dry_run=false
VERBOSE=false
for arg in "$@"; do
  if [ "$arg" = "-e" ] || [ "$arg" = "--editable" ]; then
    dev_mode="-e"
  elif [ "$arg" = "--dry-run" ]; then
    dry_run=true
  elif [ "$arg" = "--verbose" ]; then
    VERBOSE=true
  fi
done

# Install the shared library first (dependency)
echo "Installing shared library dependency first..."
# Pass arguments through to the shared library script
"$(dirname "$0")/08_install_shared.sh" "$@"

# Install the shuttle application
echo "Installing shuttle application..."
cd "$(dirname "$0")/../../src/shuttle_app" || exit 1

if [ "$dry_run" = true ]; then
  if [ -n "$dev_mode" ]; then
    echo "[DRY RUN] Would install in development mode: pip install -e ."
  else
    echo "[DRY RUN] Would install in standard mode: pip install ."
  fi
else
  if [ -n "$dev_mode" ]; then
    echo "Installing in development mode..."
    install_output=$(pip install -e . 2>&1)
    install_exit_code=$?
    
    if [[ $install_exit_code -ne 0 ]] || echo "$install_output" | grep -q "Permission denied\|OSError.*Errno 13"; then
      if echo "$install_output" | grep -q "Permission denied\|OSError.*Errno 13"; then
        echo "Permission error detected, trying with --force-reinstall..."
      else
        echo "Standard install failed (exit code: $install_exit_code), trying with --force-reinstall..."
      fi
      echo "Original error output:"
      echo "$install_output"
      echo "Retrying with --force-reinstall..."
      pip install --force-reinstall -e .
    else
      echo "$install_output"
    fi
  else
    echo "Installing in standard mode..."
    install_output=$(pip install . 2>&1)
    install_exit_code=$?
    
    if [[ $install_exit_code -ne 0 ]] || echo "$install_output" | grep -q "Permission denied\|OSError.*Errno 13"; then
      if echo "$install_output" | grep -q "Permission denied\|OSError.*Errno 13"; then
        echo "Permission error detected, trying with --force-reinstall..."
      else
        echo "Standard install failed (exit code: $install_exit_code), trying with --force-reinstall..."
      fi
      echo "Original error output:"
      echo "$install_output"
      echo "Retrying with --force-reinstall..."
      pip install --force-reinstall .
    else
      echo "$install_output"
    fi
  fi
fi

echo "Shuttle application installation complete."
