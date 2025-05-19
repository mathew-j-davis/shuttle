#!/bin/bash
set -e

# Parse command line arguments
dev_mode=""
for arg in "$@"; do
  if [ "$arg" = "-e" ] || [ "$arg" = "--editable" ]; then
    dev_mode="-e"
  fi
done

# Install the shared library first (dependency)
echo "Installing shared library dependency first..."
# Pass arguments through to the shared library script
"$(dirname "$0")/install_shared.sh" "$@"

# Install the shuttle defender application
echo "Installing shuttle defender application..."
cd "$(dirname "$0")/../../src/shuttle_defender" || exit 1

if [ -n "$dev_mode" ]; then
  echo "Installing in development mode..."
  pip install -e .
else
  echo "Installing in standard mode..."
  pip install .
fi

echo "Shuttle defender application installation complete."
