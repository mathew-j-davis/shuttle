#!/bin/bash

# Install system packages
echo "checking for microsoft defender..."

# Check if mdatp is installed
if ! command -v mdatp &>/dev/null; then
    echo "mdatp (Microsoft Defender ATP) not found."
    echo "Please follow the official Microsoft instructions to install mdatp:"
    echo "https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually"
else
    echo "mdatp is already installed."
fi

echo "All done!"