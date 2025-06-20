#!/bin/bash

# Parse command line arguments for dry-run
DRY_RUN=false
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=true
  fi
done

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would install ClamAV:"
    echo "[DRY RUN]   sudo apt-get install clamav clamav-daemon -y"
    echo ""
    echo "[DRY RUN] Would start and enable ClamAV daemon:"
    echo "[DRY RUN]   sudo systemctl start clamav-daemon"
    echo "[DRY RUN]   sudo systemctl enable clamav-daemon"
    echo ""
    echo "[DRY RUN] Would update virus definitions:"
    echo "[DRY RUN]   sudo systemctl stop clamav-freshclam"
    echo "[DRY RUN]   sudo -u clamav freshclam"
    echo "[DRY RUN]   sudo systemctl start clamav-freshclam"
else
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
fi

echo "All done!"