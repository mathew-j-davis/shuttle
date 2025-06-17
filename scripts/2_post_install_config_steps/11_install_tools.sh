#!/bin/bash

# Tool Installation Script
# Installs Samba (winbind) and ACL tools required for user/group management
# Usage: ./11_install_tools.sh [options]

set -euo pipefail

# Script directory and common functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
SCRIPT_NAME="$(basename "$0")"

# Source common functions if available
if [[ -f "$SCRIPT_DIR/lib/_common_.source.sh" ]]; then
    source "$SCRIPT_DIR/lib/_common_.source.sh"
fi

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
  Samba/Winbind:        samba, winbind, libnss-winbind, libpam-winbind
  ACL Tools:            acl, attr

Examples:
  # Install all default tools
  $SCRIPT_NAME
  
  # Install only ACL tools
  $SCRIPT_NAME --no-samba
  
  # Dry run to see what would be installed
  $SCRIPT_NAME --dry-run

Notes:
  - Requires sudo privileges for package installation
  - Will update package cache unless --no-update specified
  - ACL tools are required for show-acl-on-path, add-acl-to-path, delete-acl-from-path commands
EOF
}

# Function to detect package manager
detect_package_manager() {
    if execute "command -v apt-get >/dev/null 2>&1" \
              "APT package manager found" \
              "APT package manager not found" \
              "Check if APT package manager is available for Debian/Ubuntu systems"; then
        echo "apt"
    elif execute "command -v dnf >/dev/null 2>&1" \
                "DNF package manager found" \
                "DNF package manager not found" \
                "Check if DNF package manager is available for modern RPM systems"; then
        echo "dnf"
    elif execute "command -v yum >/dev/null 2>&1" \
                "YUM package manager found" \
                "YUM package manager not found" \
                "Check if YUM package manager is available for older RPM systems"; then
        echo "yum"
    else
        echo "unknown"
    fi
}

# Function to update package cache
update_package_cache() {
    local pkg_manager="$1"
    
    if [[ "$UPDATE_PACKAGE_CACHE" != "true" ]]; then
        log INFO "Skipping package cache update (--no-update specified)"
        return 0
    fi
    
    log INFO "Updating package cache..."
    
    case "$pkg_manager" in
        "apt")
            execute_or_dryrun "sudo apt-get update" "Package cache updated" "Failed to update package cache"
            ;;
        "dnf")
            execute_or_dryrun "sudo dnf makecache" "Package cache updated" "Failed to update package cache"
            ;;
        "yum")
            execute_or_dryrun "sudo yum makecache" "Package cache updated" "Failed to update package cache"
            ;;
        *)
            log WARN "Unknown package manager, skipping cache update"
            ;;
    esac
}

# Function to install packages
install_packages() {
    local pkg_manager="$1"
    shift
    local packages=("$@")
    
    if [[ ${#packages[@]} -eq 0 ]]; then
        log INFO "No packages to install"
        return 0
    fi
    
    local package_list="${packages[*]}"
    log INFO "Installing packages: $package_list"
    
    local install_cmd=""
    case "$pkg_manager" in
        "apt")
            install_cmd="sudo apt-get install -y $package_list"
            ;;
        "dnf")
            install_cmd="sudo dnf install -y $package_list"
            ;;
        "yum")
            install_cmd="sudo yum install -y $package_list"
            ;;
        *)
            log ERROR "Unsupported package manager: $pkg_manager"
            return 1
            ;;
    esac
    
    if [[ "$VERBOSE" == "true" ]]; then
        execute_or_dryrun "$install_cmd" \
                         "Installed packages: $package_list" \
                         "Failed to install packages: $package_list" \
                         "Installing system packages for Shuttle file sharing and permissions management"
    else
        # Only redirect stdout, keep stderr visible for sudo password prompts
        execute_or_dryrun "$install_cmd >/dev/null" \
                         "Installed packages: $package_list" \
                         "Failed to install packages: $package_list" \
                         "Installing system packages for Shuttle file sharing and permissions management"
    fi
}

# Function to get Samba packages for different distributions
get_samba_packages() {
    local pkg_manager="$1"
    
    case "$pkg_manager" in
        "apt")
            echo "samba winbind libnss-winbind libpam-winbind"
            ;;
        "dnf"|"yum")
            echo "samba samba-winbind samba-winbind-clients"
            ;;
        *)
            echo "samba"
            ;;
    esac
}

# Function to get ACL packages for different distributions
get_acl_packages() {
    local pkg_manager="$1"
    
    case "$pkg_manager" in
        "apt")
            echo "acl attr"
            ;;
        "dnf"|"yum")
            echo "acl attr"
            ;;
        *)
            echo "acl"
            ;;
    esac
}

# Function to check if packages are already installed
check_package_installed() {
    local pkg_manager="$1"
    local package="$2"
    
    case "$pkg_manager" in
        "apt")
            execute "dpkg -l \"$package\" >/dev/null 2>&1" \
                   "Package $package is installed" \
                   "Package $package is not installed" \
                   "Check if package is installed on Debian/Ubuntu system using dpkg"
            ;;
        "dnf"|"yum")
            execute "rpm -q \"$package\" >/dev/null 2>&1" \
                   "Package $package is installed" \
                   "Package $package is not installed" \
                   "Check if package is installed on RPM-based system using rpm"
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to filter already installed packages
filter_uninstalled_packages() {
    local pkg_manager="$1"
    shift
    local packages=("$@")
    local uninstalled=()
    
    for package in "${packages[@]}"; do
        if check_package_installed "$pkg_manager" "$package"; then
            log INFO "Package already installed: $package" >&2
        else
            uninstalled+=("$package")
        fi
    done
    
    echo "${uninstalled[@]}"
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
    
    log INFO "Starting tool installation script"
    
    # Detect package manager
    local pkg_manager
    pkg_manager=$(detect_package_manager)
    
    if [[ "$pkg_manager" == "unknown" ]]; then
        log ERROR "Could not detect supported package manager"
        log ERROR "Supported: apt-get (Debian/Ubuntu), dnf/yum (RHEL/Fedora)"
        exit 1
    fi
    
    log INFO "Detected package manager: $pkg_manager"
    
    # Check if running as root or can sudo
    if [[ $EUID -eq 0 ]]; then
        log INFO "Running as root"
    elif command -v sudo >/dev/null 2>&1; then
        log INFO "Will use sudo for package installation"
    else
        log ERROR "Neither running as root nor sudo available"
        exit 1
    fi
    
    # Update package cache
    update_package_cache "$pkg_manager"
    
    # Install Samba packages
    if [[ "$INSTALL_SAMBA" == "true" ]]; then
        local samba_packages
        samba_packages=$(get_samba_packages "$pkg_manager")
        read -ra samba_array <<< "$samba_packages"
        
        local uninstalled_samba
        uninstalled_samba=$(filter_uninstalled_packages "$pkg_manager" "${samba_array[@]}")
        read -ra uninstalled_samba_array <<< "$uninstalled_samba"
        
        if [[ ${#uninstalled_samba_array[@]} -gt 0 && -n "${uninstalled_samba_array[0]}" ]]; then
            log INFO "Installing Samba/Winbind packages..."
            install_packages "$pkg_manager" "${uninstalled_samba_array[@]}"
        else
            log INFO "All Samba/Winbind packages already installed"
        fi
    else
        log INFO "Skipping Samba/Winbind installation (--no-samba specified)"
    fi
    
    # Install ACL packages
    if [[ "$INSTALL_ACL" == "true" ]]; then
        local acl_packages
        acl_packages=$(get_acl_packages "$pkg_manager")
        read -ra acl_array <<< "$acl_packages"
        
        local uninstalled_acl
        uninstalled_acl=$(filter_uninstalled_packages "$pkg_manager" "${acl_array[@]}")
        read -ra uninstalled_acl_array <<< "$uninstalled_acl"
        
        if [[ ${#uninstalled_acl_array[@]} -gt 0 && -n "${uninstalled_acl_array[0]}" ]]; then
            log INFO "Installing ACL packages..."
            install_packages "$pkg_manager" "${uninstalled_acl_array[@]}"
        else
            log INFO "All ACL packages already installed"
        fi
    else
        log INFO "Skipping ACL tools installation (--no-acl specified)"
    fi
    
    log INFO "Tool installation completed successfully"
    
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

# Default log function if not available from common functions
if ! command -v log >/dev/null 2>&1; then
    log() {
        local level="$1"
        shift
        echo "[$level] $*"
    }
fi

# Default execute_or_dryrun function if not available from common functions
if ! command -v execute_or_dryrun >/dev/null 2>&1; then
    execute_or_dryrun() {
        local cmd="$1"
        local success_msg="$2"
        local error_msg="$3"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would execute: $cmd"
            return 0
        else
            if eval "$cmd"; then
                echo "$success_msg"
                return 0
            else
                echo "$error_msg"
                return 1
            fi
        fi
    }
fi

# Execute main function
main "$@"