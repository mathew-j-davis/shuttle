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

# Install the shuttle defender application
echo "Installing shuttle defender application..."
cd "$(dirname "$0")/../../src/shuttle_defender_test_app" || exit 1

if [ "$dry_run" = true ]; then
  if [ -n "$dev_mode" ]; then
    echo "[DRY RUN] Would install in development mode: pip install -e ."
  else
    echo "[DRY RUN] Would install in standard mode: pip install ."
  fi
else
  if [ -n "$dev_mode" ]; then
    echo "Installing in development mode..."
    pip install -e .
  else
    echo "Installing in standard mode..."
    pip install .
  fi
fi

echo "Shuttle defender application installation complete."
