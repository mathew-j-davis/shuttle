#!/bin/bash
# 03_sudo_install_dependencies.sh - Install basic system dependencies

set -e  # Exit on error

# Parse command line arguments for dry-run
DRY_RUN=false
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=true
  fi
done

echo "=== Installing System Dependencies ==="
echo ""

# Check if we're on a Debian-based system
if ! command -v apt-get >/dev/null 2>&1; then
    echo "❌ This script requires apt-get (Debian/Ubuntu)"
    echo "For other distributions, please install these packages manually:"
    echo "  - lsof"
    echo "  - gnupg"

    exit 1
fi

# Function to check if package is installed
is_installed() {
    dpkg -l "$1" 2>/dev/null | grep -q "^ii"
}

# List of packages to install
PACKAGES=(
    "lsof"      # For checking open files
    "gnupg"     # For GPG encryption
)

# Check which packages need installation
TO_INSTALL=()
for pkg in "${PACKAGES[@]}"; do
    if ! is_installed "$pkg"; then
        TO_INSTALL+=("$pkg")
    fi
done

if [[ ${#TO_INSTALL[@]} -eq 0 ]]; then
    echo "✅ All required packages are already installed"
    exit 0
fi

echo "📦 Need to install: ${TO_INSTALL[*]}"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would update package lists:"
    echo "[DRY RUN]   sudo apt-get update"
    echo ""
    echo "[DRY RUN] Would install packages:"
    echo "[DRY RUN]   sudo apt-get install -y ${TO_INSTALL[*]}"
else
    # Update package lists
    echo "Updating package lists..."
    if ! sudo apt-get update; then
        echo "❌ Failed to update package lists"
        echo "Please check your internet connection and apt sources"
        exit 1
    fi

    # Install packages
    echo ""
    echo "Installing packages..."
    if ! sudo apt-get install -y "${TO_INSTALL[@]}"; then
        echo "❌ Failed to install some packages"
        exit 1
    fi
fi

echo ""
echo "✅ All system dependencies installed successfully!"

# Verify installations
echo ""
echo "Verifying installations:"
for pkg in "${PACKAGES[@]}"; do
    if command -v "$pkg" >/dev/null 2>&1 || is_installed "$pkg"; then
        echo "  ✓ $pkg"
    else
        echo "  ✗ $pkg (warning: command not found in PATH)"
    fi
done