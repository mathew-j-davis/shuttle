#!/bin/bash
# 03_sudo_install_dependencies.sh - Install basic system dependencies
# Refactored to use centralized package management library

set -euo pipefail

# Script identification
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

# Global variables
DRY_RUN=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME [options]

Install basic system dependencies required for Shuttle operation.

Options:
  --dry-run             Show what would be installed without making changes
  --help, -h            Show this help message

Dependencies Installed:
  - lsof (for checking open files)
  - gnupg (for GPG encryption/decryption)

Examples:
  # Install all system dependencies
  $SCRIPT_NAME
  
  # Dry run to see what would be installed
  $SCRIPT_NAME --dry-run

Notes:
  - Automatically detects package manager (apt, dnf, yum, pacman, zypper, brew)
  - Requires sudo privileges on most systems (except macOS with Homebrew)
  - Skips packages that are already installed
EOF
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log INFO "Installing System Dependencies"
    
    # Show package manager info
    show_package_manager_info
    
    # Define package mapping for basic system tools
    declare -A system_packages
    system_packages[apt]="lsof gnupg"
    system_packages[dnf]="lsof gnupg2"
    system_packages[yum]="lsof gnupg2"
    system_packages[pacman]="lsof gnupg"
    system_packages[zypper]="lsof gpg2"
    system_packages[brew]="lsof gnupg"
    system_packages[default]="lsof gnupg"  # Fallback
    
    install_packages_from_map "System dependencies" system_packages
    
    # Verify installation using standardized tool checking
    # Use 'none' for tools that don't have --version flag
    if check_tools_installation "system dependencies" "lsof:lsof -v 2>&1" "gpg:gpg --version"; then
        log INFO "All system dependencies installed successfully!"
    else
        log WARN "Some dependencies may not be available in PATH"
        log INFO "This might be normal if they're installed in system locations"
    fi
    
    return 0
}


# Execute main function
main "$@"