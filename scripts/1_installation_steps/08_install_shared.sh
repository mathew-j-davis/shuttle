#!/bin/bash
set -e

# Parse command line arguments
dev_mode=""
dry_run=false
for arg in "$@"; do
  if [ "$arg" = "-e" ] || [ "$arg" = "--editable" ]; then
    dev_mode="-e"
  elif [ "$arg" = "--dry-run" ]; then
    dry_run=true
  fi
done

# Install the shared library
echo "Installing shared library (shuttle_common)..."
cd "$(dirname "$0")/../../src/shared_library" || exit 1

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

echo "Shared library installation complete."
