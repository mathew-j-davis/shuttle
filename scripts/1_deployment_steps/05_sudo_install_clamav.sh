#!/bin/bash

# Install clamav for checking if files are open
echo "Installing clamav..."
sudo apt-get install clamav clamav-daemon -y

echo "Starting and enabling ClamAV daemon..."
sudo systemctl start clamav-daemon
sudo systemctl enable clamav-daemon

echo "Updating virus definitions..."
sudo systemctl stop clamav-freshclam
sudo -u clamav freshclam
sudo systemctl start clamav-freshclam

echo "All done!"