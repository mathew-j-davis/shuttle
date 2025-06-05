#!/bin/bash

# Install system packages
echo "Updating package lists..."
sudo apt-get update -y

# Install lsof for checking if files are open
echo "Installing lsof..."
sudo apt-get install -y lsof

# Install GPG if not present
echo "Installing/updating GPG..."
sudo apt-get install -y gnupg

echo "All done!"