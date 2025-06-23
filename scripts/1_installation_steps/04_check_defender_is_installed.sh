#!/bin/bash

# Parse command line arguments for dry-run
DRY_RUN=false
VERBOSE=false
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=true
  elif [ "$arg" = "--verbose" ]; then
    VERBOSE=true
  fi
done

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would check for Microsoft Defender:"
    echo "[DRY RUN]   command -v mdatp"
    if ! command -v mdatp &>/dev/null; then
        echo "[DRY RUN] mdatp (Microsoft Defender ATP) not found."
        echo "[DRY RUN] Would display installation instructions"
    else
        echo "[DRY RUN] mdatp is already installed."
    fi
else
    # Check for Microsoft Defender
    echo "checking for microsoft defender..."

    # Check if mdatp is installed
    if ! command -v mdatp &>/dev/null; then
        echo "mdatp (Microsoft Defender ATP) not found."
        echo "Please follow the official Microsoft instructions to install mdatp:"
        echo "https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually"
    else
        echo "mdatp is already installed."
    fi
fi

echo "All done!"