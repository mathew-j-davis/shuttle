#!/bin/bash

# Samba Configuration Script
# Tool for managing Samba shares, users, and access
# Usage: configure_samba.sh <command> [parameters...]

set -euo pipefail

# Script directory for sourcing libraries
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
LIB_DIR="$SCRIPT_DIR/lib"

# Source shared setup libraries using clean import pattern
SETUP_LIB_DIR="$(dirname "$SCRIPT_DIR")/__setup_lib_sh"
if [[ -f "$SETUP_LIB_DIR/_setup_lib_loader.source.sh" ]]; then
    source "$SETUP_LIB_DIR/_setup_lib_loader.source.sh"
    load_common_libs || {
        echo "ERROR: Failed to load required setup libraries" >&2
        exit 1
    }
else
    echo "ERROR: Setup library loader not found at $SETUP_LIB_DIR/_setup_lib_loader.source.sh" >&2
    exit 1
fi
source "$LIB_DIR/_cmd_add_share.source.sh"
source "$LIB_DIR/_cmd_remove_share.source.sh"
source "$LIB_DIR/_cmd_list_shares.source.sh"
source "$LIB_DIR/_cmd_show_share.source.sh"
source "$LIB_DIR/_cmd_enable_share.source.sh"
source "$LIB_DIR/_cmd_disable_share.source.sh"
source "$LIB_DIR/_cmd_add_samba_user.source.sh"
source "$LIB_DIR/_cmd_remove_samba_user.source.sh"
source "$LIB_DIR/_cmd_list_samba_users.source.sh"
source "$LIB_DIR/_cmd_enable_samba_user.source.sh"
source "$LIB_DIR/_cmd_disable_samba_user.source.sh"
source "$LIB_DIR/_cmd_set_samba_password.source.sh"
source "$LIB_DIR/_cmd_start_samba.source.sh"
source "$LIB_DIR/_cmd_stop_samba.source.sh"
source "$LIB_DIR/_cmd_restart_samba.source.sh"
source "$LIB_DIR/_cmd_reload_samba.source.sh"
source "$LIB_DIR/_cmd_status_samba.source.sh"
source "$LIB_DIR/_cmd_test_config.source.sh"

# Global variables
SCRIPT_NAME="$(basename "$0")"
COMMAND=""
DRY_RUN=false

# Show usage information
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME <command> [options]

Samba Configuration Tool
Tool for managing Samba shares, users, and access control.

COMMANDS:

Share Management:
  add-share                   Create a new Samba share
  remove-share                Remove an existing Samba share
  list-shares                 List all configured Samba shares
  show-share                  Display details of a specific share
  enable-share                Enable a disabled share
  disable-share               Disable a share temporarily

User Management:
  add-samba-user              Add user to Samba (set password)
  remove-samba-user           Remove user from Samba
  set-samba-password          Set/change Samba password for user
  list-samba-users            List all Samba users
  enable-samba-user           Enable a disabled Samba user
  disable-samba-user          Disable a Samba user temporarily

Service Management:
  start-samba                 Start Samba services
  stop-samba                  Stop Samba services
  restart-samba               Restart Samba services
  reload-samba                Reload Samba configuration
  status-samba                Show Samba service status
  test-config                 Test Samba configuration syntax

GLOBAL OPTIONS:
  --dry-run                   Show what would be done without making changes
  --help, -h                  Show help for specific command

EXAMPLES:
  # Get help for a specific command
  $SCRIPT_NAME add-share --help
  $SCRIPT_NAME add-samba-user --help
  
  # Create a new share
  $SCRIPT_NAME add-share --name "shuttle-incoming" --path "/var/shuttle/incoming" --comment "Shuttle file intake"
  
  # Add a user to Samba
  $SCRIPT_NAME add-samba-user --user alice --password "secure123"
  
  # List all shares
  $SCRIPT_NAME list-shares --format detailed
  
  # Test configuration
  $SCRIPT_NAME test-config
  
  # Restart Samba services
  $SCRIPT_NAME restart-samba

FEATURES:
  " Share creation and management
  " User access control
  " Password management
  " Service lifecycle management
  " Configuration validation
  " Detailed status reporting
  " Dry-run mode for safe testing

NOTES:
  " Most commands require root privileges or sudo access
  " Use --dry-run to preview changes before applying them
  " Samba configuration is stored in /etc/samba/smb.conf
  " Users must exist in system before adding to Samba
  " Always test configuration after changes

For detailed help on any command, use:
  $SCRIPT_NAME <command> --help

Examples:
  $SCRIPT_NAME add-share --help
  $SCRIPT_NAME set-samba-password --help
  $SCRIPT_NAME list-shares --help
EOF
}

# Main command dispatcher
main() {
    # Check if any arguments provided
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    # Extract command from first parameter
    COMMAND="$1"
    shift # Remove command from parameters, leaving only command arguments
    
    # Check for --dry-run flag in remaining parameters
    for arg in "$@"; do
        if [[ "$arg" == "--dry-run" ]]; then
            DRY_RUN=true
            break
        fi
    done
    
    # Dispatch to appropriate command function
    case "$COMMAND" in
        "add-share")
            cmd_add_share "$@"
            ;;
        "remove-share")
            cmd_remove_share "$@"
            ;;
        "list-shares")
            cmd_list_shares "$@"
            ;;
        "show-share")
            cmd_show_share "$@"
            ;;
        "enable-share")
            cmd_enable_share "$@"
            ;;
        "disable-share")
            cmd_disable_share "$@"
            ;;
        "add-samba-user")
            cmd_add_samba_user "$@"
            ;;
        "remove-samba-user")
            cmd_remove_samba_user "$@"
            ;;
        "set-samba-password")
            cmd_set_samba_password "$@"
            ;;
        "list-samba-users")
            cmd_list_samba_users "$@"
            ;;
        "enable-samba-user")
            cmd_enable_samba_user "$@"
            ;;
        "disable-samba-user")
            cmd_disable_samba_user "$@"
            ;;
        "start-samba")
            cmd_start_samba "$@"
            ;;
        "stop-samba")
            cmd_stop_samba "$@"
            ;;
        "restart-samba")
            cmd_restart_samba "$@"
            ;;
        "reload-samba")
            cmd_reload_samba "$@"
            ;;
        "status-samba")
            cmd_status_samba "$@"
            ;;
        "test-config")
            cmd_test_config "$@"
            ;;
        "--help" | "-h" | "help")
            show_usage
            ;;
        *)
            show_usage
            error_exit "Unknown command: $COMMAND"
            ;;
    esac
}

# Execute main function with all script arguments
main "$@"