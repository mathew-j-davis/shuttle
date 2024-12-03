#!/bin/bash

# Install system packages
echo "Updating package lists..."
sudo apt-get update -y

# Install lsof for checking if files are open
echo "Installing lsof..."
sudo apt-get install -y lsof

# Install zip for compressing and encrypting files
echo "Installing zip..."
sudo apt-get install -y zip



# Install Python packages from requirements.txt
echo "Installing Python packages from requirements.txt..."
pip3 install -r requirements.txt

# Check if mdatp is installed
if ! command -v mdatp &>/dev/null; then
    echo "mdatp (Microsoft Defender ATP) not found."
    echo "Please follow the official Microsoft instructions to install mdatp:"
    echo "https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually"
else
    echo "mdatp is already installed."
fi

echo "All done!"