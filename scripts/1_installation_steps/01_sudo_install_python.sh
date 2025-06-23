#!/bin/bash
# 01_sudo_install_python.sh - Install Python3 and development tools
# Refactored to use centralized package management library

set -euo pipefail

# Script identification
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

# Global variables
DRY_RUN=false
VERBOSE=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME [options]

Install Python3 and development tools using the appropriate package manager.

Options:
  --dry-run             Show what would be installed without making changes
  --verbose            Show detailed command execution information
  --help, -h            Show this help message

Packages Installed:
  - Python 3 interpreter
  - Python package manager (pip)
  - Python virtual environment support
  - Python development headers (for building packages)

Examples:
  # Install Python3 and tools
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
            --verbose)
                VERBOSE=true
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
    
    log INFO "Installing Python3 and Development Tools"
    
    # Show package manager info
    show_package_manager_info
    
    # Define package mapping for Python3 and development tools
    declare -A python_packages
    python_packages[apt]="python3 python3-pip python3-venv python3-dev"
    python_packages[dnf]="python3 python3-pip python3-devel"
    python_packages[yum]="python3 python3-pip python3-devel"
    python_packages[pacman]="python python-pip"
    python_packages[zypper]="python3 python3-pip python3-devel"
    python_packages[brew]="python3"
    python_packages[default]="python3"  # Fallback for unknown package managers
    
    install_packages_from_map "Python3 installation" python_packages
    
    # Verify installation using standardized tool checking
    if check_tools_installation "Python installation" "python3" "pip3"; then
        log INFO "Python3 installation completed successfully!"
    else
        log WARN "Some Python tools may not be available in PATH"
    fi
    
    return 0
}


# Execute main function
main "$@"