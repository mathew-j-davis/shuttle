#!/bin/bash
set -e

# Parse command line arguments
dev_mode=""
for arg in "$@"; do
  if [ "$arg" = "-e" ] || [ "$arg" = "--editable" ]; then
    dev_mode="-e"
  fi
done

# Install the shared library
echo "Installing shared library (shuttle_common)..."
cd "$(dirname "$0")/../../src/shared_library" || exit 1

if [ -n "$dev_mode" ]; then
  echo "Installing in development mode..."
  pip install -e .
else
  echo "Installing in standard mode..."
  pip install .
fi

echo "Shared library installation complete."
