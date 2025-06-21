#!/bin/bash

# Tool Installation Script
# Installs Samba (winbind) and ACL tools required for user/group management
# Refactored to use centralized package management library

set -euo pipefail

# Script identification
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

# Global variables
DRY_RUN=false
INSTALL_SAMBA=true
INSTALL_ACL=true
UPDATE_PACKAGE_CACHE=true
VERBOSE=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME [options]

Install tools required for user/group management and domain integration.

Options:
  --dry-run             Show what would be installed without making changes
  --no-samba            Skip Samba/Winbind installation
  --no-acl              Skip ACL tools installation
  --no-update           Skip package cache update
  --verbose             Show detailed output
  --help, -h            Show this help message

Default Packages:
  Samba/Winbind:        samba, winbind, libnss-winbind, libpam-winbind (Debian/Ubuntu)
                        samba, samba-winbind, samba-winbind-clients (RHEL/Fedora)
  ACL Tools:            acl, attr

Examples:
  # Install all default tools
  $SCRIPT_NAME
  
  # Install only ACL tools
  $SCRIPT_NAME --no-samba
  
  # Dry run to see what would be installed
  $SCRIPT_NAME --dry-run

Notes:
  - Automatically detects package manager (apt, dnf, yum, pacman, zypper, brew)
  - Requires sudo privileges on most systems (except macOS with Homebrew)
  - Will update package cache unless --no-update specified
  - ACL tools are required for show-acl-on-path, add-acl-to-path, delete-acl-from-path commands
EOF
}

# Main installation function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-samba)
                INSTALL_SAMBA=false
                shift
                ;;
            --no-acl)
                INSTALL_ACL=false
                shift
                ;;
            --no-update)
                UPDATE_PACKAGE_CACHE=false
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
    
    log INFO "Installing Tools for User/Group Management"
    
    # Show package manager info using standardized function
    show_package_manager_info
    
    # Update package cache using standardized function
    if [[ "$UPDATE_PACKAGE_CACHE" == "true" ]]; then
        update_package_cache
    else
        log INFO "Skipping package cache update (--no-update specified)"
    fi
    
    # Install Samba packages using standardized library
    if [[ "$INSTALL_SAMBA" == "true" ]]; then
        log INFO "Installing Samba/Winbind packages..."
        
        # Define package mapping for Samba tools
        declare -A samba_packages
        samba_packages[apt]="samba winbind libnss-winbind libpam-winbind"
        samba_packages[dnf]="samba samba-winbind samba-winbind-clients"
        samba_packages[yum]="samba samba-winbind samba-winbind-clients"
        samba_packages[pacman]="samba"
        samba_packages[zypper]="samba samba-winbind"
        samba_packages[brew]="samba"
        samba_packages[default]="samba"  # Fallback
        
        if [[ "$VERBOSE" == "true" ]]; then
            install_packages_from_map "Samba/Winbind" samba_packages
        else
            install_packages_from_map "Samba/Winbind" samba_packages >/dev/null
        fi
    else
        log INFO "Skipping Samba/Winbind installation (--no-samba specified)"
    fi
    
    # Install ACL packages using standardized library
    if [[ "$INSTALL_ACL" == "true" ]]; then
        log INFO "Installing ACL packages..."
        
        # Define package mapping for ACL tools
        declare -A acl_packages
        acl_packages[apt]="acl attr"
        acl_packages[dnf]="acl attr"
        acl_packages[yum]="acl attr"
        acl_packages[pacman]="acl attr"
        acl_packages[zypper]="acl attr"
        acl_packages[brew]="acl"  # attr not available on macOS
        acl_packages[default]="acl"  # Fallback
        
        if [[ "$VERBOSE" == "true" ]]; then
            install_packages_from_map "ACL tools" acl_packages
        else
            install_packages_from_map "ACL tools" acl_packages >/dev/null
        fi
    else
        log INFO "Skipping ACL tools installation (--no-acl specified)"
    fi
    
    # Verify installations using direct tool checking
    local all_tools_ok=true
    
    if [[ "$INSTALL_SAMBA" == "true" ]]; then
        log INFO "Verifying Samba tools installation..."
        if ! check_tool_with_version "smbpasswd" "none" "Samba password tool"; then
            all_tools_ok=false
        fi
        if ! check_tool_with_version "smbd" "smbd -V" "Samba daemon"; then
            all_tools_ok=false
        fi
        if ! check_tool_with_version "net" "net --version" "Samba net tool"; then
            all_tools_ok=false
        fi
        if ! check_tool_with_version "winbindd" "winbindd -V" "Winbind daemon"; then
            all_tools_ok=false
        fi
    fi
    
    if [[ "$INSTALL_ACL" == "true" ]]; then
        log INFO "Verifying ACL tools installation..."
        if ! check_tool_with_version "getfacl" "getfacl --version" "Get file ACL tool"; then
            all_tools_ok=false
        fi
        if ! check_tool_with_version "setfacl" "setfacl --version" "Set file ACL tool"; then
            all_tools_ok=false
        fi
        if ! check_tool_with_version "getfattr" "getfattr --version" "Get file attributes tool"; then
            all_tools_ok=false
        fi
    fi
    
    if [[ "$all_tools_ok" == "true" ]]; then
        log INFO "All requested tools installed and verified successfully!"
    else
        log WARN "Some tools may not be available in PATH or have version check issues"
        log INFO "This might be normal if they're installed in system locations"
    fi
    
    # Show next steps
    echo ""
    log INFO "Next steps:"
    if [[ "$INSTALL_SAMBA" == "true" ]]; then
        log INFO "  - Configure Samba/Winbind for domain integration"
        log INFO "  - Edit /etc/samba/smb.conf for your domain"
        log INFO "  - Join domain with: net ads join -U Administrator"
    fi
    if [[ "$INSTALL_ACL" == "true" ]]; then
        log INFO "  - ACL tools are ready for use with show-acl-on-path, add-acl-to-path, delete-acl-from-path commands"
    fi
    echo ""
    
    return 0
}

# Execute main function
main "$@"