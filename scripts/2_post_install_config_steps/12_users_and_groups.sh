#!/bin/bash

# User and Group Management Script
# Generic command-based tool for managing users, groups, and permissions
# Usage: user_group_manager.sh <command> [parameters...]

set -euo pipefail

# Script directory for sourcing libraries
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
LIB_DIR="$SCRIPT_DIR/lib"

# Source shared setup libraries
SETUP_LIB_DIR="$(dirname "$SCRIPT_DIR")/__setup_lib_sh"
if [[ -f "$SETUP_LIB_DIR/_setup_lib_loader.source.sh" ]]; then
    source "$SETUP_LIB_DIR/_setup_lib_loader.source.sh"
    load_all_setup_libs || {
        echo "ERROR: Failed to load required setup libraries" >&2
        exit 1
    }
else
    echo "ERROR: Setup library loader not found at $SETUP_LIB_DIR/_setup_lib_loader.source.sh" >&2
    exit 1
fi
source "$LIB_DIR/_cmd_show_user.source.sh"
source "$LIB_DIR/_cmd_list_users.source.sh"
source "$LIB_DIR/_cmd_list_user_groups.source.sh"
source "$LIB_DIR/_cmd_add_user.source.sh"
source "$LIB_DIR/_cmd_delete_user.source.sh"
source "$LIB_DIR/_cmd_modify_user.source.sh"
source "$LIB_DIR/_cmd_add_group.source.sh"
source "$LIB_DIR/_cmd_delete_group.source.sh"
source "$LIB_DIR/_cmd_modify_group.source.sh"
source "$LIB_DIR/_cmd_show_group.source.sh"
source "$LIB_DIR/_cmd_list_groups.source.sh"
source "$LIB_DIR/_cmd_list_group_users.source.sh"
source "$LIB_DIR/_cmd_count_group_users.source.sh"
source "$LIB_DIR/_cmd_add_user_to_group.source.sh"
source "$LIB_DIR/_cmd_delete_user_from_group.source.sh"
source "$LIB_DIR/_cmd_show_acl_on_path.source.sh"
source "$LIB_DIR/_cmd_add_acl_to_path.source.sh"
source "$LIB_DIR/_cmd_delete_acl_from_path.source.sh"
source "$LIB_DIR/_cmd_show_path_owner_permissions_and_acl.source.sh"
source "$LIB_DIR/_cmd_set_path_owner.source.sh"
source "$LIB_DIR/_cmd_set_path_permissions.source.sh"



# Global variables
SCRIPT_NAME="$(basename "$0")"
COMMAND=""
DRY_RUN=false

# Show usage information
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME <command> [options]

User and Group Management Tool
Generic command-based tool for managing users, groups, and permissions on Linux systems.

COMMANDS:

User Management:
  add-user                    Create a new user account
  delete-user                 Remove a user account
  modify-user                 Modify existing user account
  list-users                  List users with filtering and formatting options
  show-user                   Display detailed information about a specific user
  list-user-groups            List all groups that a specific user belongs to

Group Management:
  add-group                   Create a new group
  delete-group                Remove a group
  modify-group                Modify existing group
  list-groups                 List groups with filtering and formatting options
  show-group                  Display detailed information about a specific group
  list-group-users            List all users that belong to a specific group
  count-group-users           Count users in a specific group

User-Group Membership:
  add-user-to-group           Add a user to a group
  delete-user-from-group      Remove a user from a group

Path Ownership and Permissions:
  set-path-owner              Set owner and group for files/directories
  set-path-permissions        Set permissions for files/directories
  show-path-owner-permissions-and-acl    Display ownership, permissions, and ACLs

Access Control Lists (ACL):
  show-acl-on-path            Display ACLs for files/directories
  add-acl-to-path             Add ACL entries to files/directories
  delete-acl-from-path        Remove ACL entries from files/directories

GLOBAL OPTIONS:
  --dry-run                   Show what would be done without making changes
  --help, -h                  Show help for specific command

EXAMPLES:
  # Get help for a specific command
  $SCRIPT_NAME add-user --help
  $SCRIPT_NAME list-users --help
  
  # Create a new user
  $SCRIPT_NAME add-user --user alice --home /home/alice
  
  # List all regular users
  $SCRIPT_NAME list-users --filter regular --format detailed
  
  # Show user information
  $SCRIPT_NAME show-user --user bob --groups --files
  
  # Create a group and add users
  $SCRIPT_NAME add-group --group developers
  $SCRIPT_NAME add-user-to-group --user alice --group developers
  
  # List group members
  $SCRIPT_NAME list-group-users --group sudo --format detailed
  
  # Set permissions with ACLs
  $SCRIPT_NAME set-path-permissions --path /var/data --mode 750
  $SCRIPT_NAME add-acl-to-path --path /var/data --acl "u:alice:rwx"

FEATURES:
  • Domain user support (Active Directory, LDAP)
  • Multiple output formats (simple, detailed, CSV, JSON)
  • Comprehensive filtering and sorting options
  • Dry-run mode for safe testing
  • Detailed error messages with command-specific help
  • ACL (Access Control List) management
  • System and regular user/group distinction

NOTES:
  • Most commands require root privileges or sudo access
  • Use --dry-run to preview changes before applying them
  • System users/groups typically have UID/GID < 1000
  • Domain users may require --check-domain flag
  • All commands support --help for detailed usage information

For detailed help on any command, use:
  $SCRIPT_NAME <command> --help

Examples:
  $SCRIPT_NAME add-user --help
  $SCRIPT_NAME list-groups --help
  $SCRIPT_NAME set-path-permissions --help
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
        "add-user")
            cmd_add_user "$@"
            ;;
        "delete-user")
            cmd_delete_user "$@"
            ;;
        "modify-user")
            cmd_modify_user "$@"
            ;;
        "list-users")
            cmd_list_users "$@"
            ;;
        "show-user")
            cmd_show_user_info "$@"
            ;;
        "list-user-groups")
            cmd_list_user_groups "$@"
            ;;
        "add-group")
            cmd_add_group "$@"
            ;;
        "delete-group")
            cmd_delete_group "$@"
            ;;
        "modify-group")
            cmd_modify_group "$@"
            ;;
        "list-groups")
            cmd_list_groups "$@"
            ;;
        "show-group")
            cmd_show_group "$@"
            ;;
        "list-group-users")
            cmd_list_group_users "$@"
            ;;
        "count-group-users")
            cmd_count_group_users "$@"
            ;;
        "add-user-to-group")
            cmd_add_user_to_group "$@"
            ;;
        "delete-user-from-group")
            cmd_delete_user_from_group "$@"
            ;;
        "set-path-owner")
            cmd_set_path_owner "$@"
            ;;
        "set-path-permissions")
            cmd_set_path_permissions "$@"
            ;;
        "show-path-owner-permissions-and-acl")
            cmd_show_path_owner_permissions_and_acl "$@"
            ;;
        "show-acl-on-path")
            cmd_show_acl_on_path "$@"
            ;;
        "add-acl-to-path")
            cmd_add_acl_to_path "$@"
            ;;
        "delete-acl-from-path")
            cmd_delete_acl_from_path "$@"
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