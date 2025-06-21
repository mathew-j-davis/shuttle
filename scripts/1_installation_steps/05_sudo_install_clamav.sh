#!/bin/bash
# 05_sudo_install_clamav.sh - Install ClamAV antivirus software
# Refactored to use centralized package management library

set -euo pipefail

# Script identification
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

# Global variables
DRY_RUN=false
START_SERVICES=true
UPDATE_DEFINITIONS=true

# Function to show usage
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME [options]

Install ClamAV antivirus software and configure services.

Options:
  --dry-run             Show what would be installed without making changes
  --no-services         Skip starting/enabling ClamAV services
  --no-update          Skip updating virus definitions
  --help, -h            Show this help message

Components Installed:
  - ClamAV antivirus engine
  - ClamAV daemon (background scanner)
  - Virus definition database

Services Configured:
  - clamav-daemon (on systemd systems)
  - clamav-freshclam (virus definition updates)

Examples:
  # Install ClamAV with full setup
  $SCRIPT_NAME
  
  # Install packages only, skip service configuration
  $SCRIPT_NAME --no-services --no-update
  
  # Dry run to see what would be done
  $SCRIPT_NAME --dry-run

Notes:
  - Automatically detects package manager (apt, dnf, yum, pacman, zypper)
  - Requires sudo privileges for installation and service management
  - Services are only configured on systemd-based systems
EOF
}

# Function to manage ClamAV services
manage_clamav_services() {
    local context="ClamAV service management"
    
    if [[ "$START_SERVICES" != "true" ]]; then
        log INFO "Skipping service configuration (--no-services specified)"
        return 0
    fi
    
    # Check if systemctl is available
    if ! execute "command -v systemctl >/dev/null 2>&1" \
                "systemctl found - configuring services" \
                "systemctl not found - skipping service configuration" \
                "Check if systemctl is available for service management"; then
        return 0
    fi
    
    log INFO "Configuring ClamAV services"
    
    # Service names vary by distribution
    local pm
    pm=$(get_package_manager "$context") || return 1
    
    local daemon_service=""
    local freshclam_service=""
    
    case "$pm" in
        "apt")
            daemon_service="clamav-daemon"
            freshclam_service="clamav-freshclam"
            ;;
        "dnf"|"yum"|"zypper")
            daemon_service="clamd@scan"  # On RHEL/CentOS
            freshclam_service="clamav-freshclam"
            ;;
        *)
            log ERROR "Unknown service names for package manager: $pm"
            return 1
            ;;
    esac
    
    # Start and enable ClamAV daemon
    if [[ -n "$daemon_service" ]]; then
        local start_cmd="sudo systemctl start $daemon_service"
        local enable_cmd="sudo systemctl enable $daemon_service"
        
        if execute_or_dryrun "$start_cmd" \
                            "$daemon_service started successfully" \
                            "Failed to start $daemon_service (may need manual configuration)" \
                            "Start ClamAV daemon service for background scanning"; then
            execute_or_dryrun "$enable_cmd" \
                            "$daemon_service enabled for automatic startup" \
                            "Failed to enable $daemon_service" \
                            "Enable ClamAV daemon to start automatically on boot"
        fi
    fi
    
    # Configure freshclam service
    if [[ -n "$freshclam_service" && "$UPDATE_DEFINITIONS" == "true" ]]; then
        log INFO "Configuring virus definition updates"
        
        # Stop freshclam to update manually first
        execute_or_dryrun "sudo systemctl stop $freshclam_service" \
                         "Stopped $freshclam_service for manual update" \
                         "Could not stop $freshclam_service (may not be running)" \
                         "Stop freshclam service to perform manual virus definition update"
        
        # Update definitions manually
        execute_or_dryrun "sudo -u clamav freshclam" \
                         "Virus definitions updated successfully" \
                         "Failed to update virus definitions manually" \
                         "Download latest virus definitions from ClamAV database"
        
        # Start and enable automatic updates
        if execute_or_dryrun "sudo systemctl start $freshclam_service" \
                            "$freshclam_service started successfully" \
                            "Failed to start $freshclam_service" \
                            "Start freshclam service for automatic virus definition updates"; then
            execute_or_dryrun "sudo systemctl enable $freshclam_service" \
                            "Automatic virus definition updates enabled" \
                            "Failed to enable automatic updates" \
                            "Enable freshclam service to start automatically on boot"
        fi
    fi
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
            --no-services)
                START_SERVICES=false
                shift
                ;;
            --no-update)
                UPDATE_DEFINITIONS=false
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
    
    log INFO "Installing ClamAV Antivirus"
    
    # Show package manager info
    show_package_manager_info
    
    # Define package mapping for ClamAV
    declare -A clamav_packages
    clamav_packages[apt]="clamav clamav-daemon"
    clamav_packages[dnf]="clamav clamd"
    clamav_packages[yum]="clamav clamd"
    clamav_packages[pacman]="clamav"
    clamav_packages[zypper]="clamav"
    clamav_packages[brew]="clamav"
    clamav_packages[default]="clamav"  # Fallback
    
    install_packages_from_map "ClamAV installation" clamav_packages
    
    # Configure services
    manage_clamav_services
    
    # Verify installation using standardized tool checking
    local all_found=true
    if ! check_tools_installation "ClamAV installation" "clamscan" "clamdscan"; then
        all_found=false
    fi
    
    # Show status if not dry run
    if [[ "${DRY_RUN:-false}" != "true" && "$START_SERVICES" == "true" ]]; then
        if execute "command -v systemctl >/dev/null 2>&1" \
                  "Checking service status" \
                  "systemctl not available for status check" \
                  "Check if systemctl is available for service status"; then
            log INFO "Service status:"
            local pm
            pm=$(get_package_manager) || return 1
            
            case "$pm" in
                "apt")
                    local daemon_status=$(systemctl is-active clamav-daemon 2>/dev/null || echo "unknown")
                    local freshclam_status=$(systemctl is-active clamav-freshclam 2>/dev/null || echo "unknown")
                    log INFO "clamav-daemon: $daemon_status"
                    log INFO "clamav-freshclam: $freshclam_status"
                    ;;
                "dnf"|"yum"|"zypper")
                    local clamd_status=$(systemctl is-active clamd@scan 2>/dev/null || echo "unknown")
                    log INFO "clamd@scan: $clamd_status"
                    ;;
            esac
        fi
    fi
    
    if [[ "$all_found" == "true" ]]; then
        log INFO "ClamAV installation completed successfully!"
    else
        log WARN "Some ClamAV tools may not be available in PATH"
    fi
    
    log INFO "Next steps:"
    log INFO "  - Test scanning: clamscan --version"
    log INFO "  - Scan a file: clamscan /path/to/file"
    log INFO "  - Check service: systemctl status clamav-daemon"
    
    return 0
}


# Execute main function
main "$@"