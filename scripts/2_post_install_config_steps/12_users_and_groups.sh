#!/bin/bash

# User and Group Management Script
# Generic command-based tool for managing users, groups, and permissions
# Usage: user_group_manager.sh <command> [parameters...]

set -euo pipefail

# Script identification
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

source "$SCRIPT_DIR/lib/_cmd_show_user.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_users.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_user_groups.source.sh"
source "$SCRIPT_DIR/lib/_cmd_add_user.source.sh"
source "$SCRIPT_DIR/lib/_cmd_delete_user.source.sh"
source "$SCRIPT_DIR/lib/_cmd_modify_user.source.sh"
source "$SCRIPT_DIR/lib/_cmd_add_group.source.sh"
source "$SCRIPT_DIR/lib/_cmd_delete_group.source.sh"
source "$SCRIPT_DIR/lib/_cmd_modify_group.source.sh"
source "$SCRIPT_DIR/lib/_cmd_show_group.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_groups.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_group_users.source.sh"
source "$SCRIPT_DIR/lib/_cmd_count_group_users.source.sh"
source "$SCRIPT_DIR/lib/_cmd_add_user_to_group.source.sh"
source "$SCRIPT_DIR/lib/_cmd_delete_user_from_group.source.sh"
source "$SCRIPT_DIR/lib/_cmd_show_acl_on_path.source.sh"
source "$SCRIPT_DIR/lib/_cmd_add_acl_to_path.source.sh"
source "$SCRIPT_DIR/lib/_cmd_delete_acl_from_path.source.sh"
source "$SCRIPT_DIR/lib/_cmd_show_path_owner_permissions_and_acl.source.sh"
source "$SCRIPT_DIR/lib/_cmd_set_path_owner.source.sh"
source "$SCRIPT_DIR/lib/_cmd_set_path_permissions.source.sh"
source "$SCRIPT_DIR/lib/_cmd_import_domain_user.source.sh"
source "$SCRIPT_DIR/lib/_cmd_generate_domain_config.source.sh"



# Global variables
SCRIPT_NAME="$(basename "$0")"
COMMAND=""
DRY_RUN=false
VERBOSE=false
RECKLESS=false

# Safety validation arrays
SAFE_PREFIXES=(
    "/var/shuttle/"
    "/etc/shuttle/"
    "/var/log/shuttle/"
    "/opt/shuttle/"
    "/tmp/shuttle/"
    "/usr/local/bin/run-shuttle"
    "/usr/local/bin/run-shuttle-defender-test"
)

DANGEROUS_PATHS=(
    "/etc/passwd" "/etc/shadow" "/etc/group" "/etc/sudoers"
    "/usr/bin/" "/usr/sbin/" "/bin/" "/sbin/" "/lib/" "/boot/"
    "/dev/" "/proc/" "/sys/" "/root/"
    "/etc/systemd/" "/etc/ssh/" "/etc/fstab" "/etc/hosts"
)

DANGEROUS_PREFIXES=(
    "/usr/bin/" "/usr/sbin/" "/bin/" "/sbin/" "/lib/" "/boot/"
    "/dev/" "/proc/" "/sys/" "/etc/systemd/" "/etc/ssh/"
)

# Safety validation functions
validate_path_safety() {
    local path="$1"
    
    # Check if path is dangerous
    for dangerous_path in "${DANGEROUS_PATHS[@]}"; do
        if [[ "$path" == "$dangerous_path" ]]; then
            echo "DANGEROUS:Path '$path' is a critical system path"
            return 1
        fi
    done
    
    for dangerous_prefix in "${DANGEROUS_PREFIXES[@]}"; do
        if [[ "$path" == "$dangerous_prefix"* ]]; then
            echo "DANGEROUS:Path '$path' is in dangerous system area '$dangerous_prefix'"
            return 1
        fi
    done
    
    # Check for SSH and shell configuration dangers
    if [[ "$path" == *"/.ssh/"* ]] || [[ "$path" == *"/.ssh" ]]; then
        echo "DANGEROUS:Path '$path' contains SSH configuration"
        return 1
    fi
    
    if [[ "$path" == *"/.bash"* ]] || [[ "$path" == *"/.zsh"* ]] || [[ "$path" == *"/.profile"* ]]; then
        echo "DANGEROUS:Path '$path' contains shell configuration"
        return 1
    fi
    
    # Check if path is in safe whitelist
    for safe_prefix in "${SAFE_PREFIXES[@]}"; do
        if [[ "$path" == "$safe_prefix"* ]]; then
            echo "SAFE:Path '$path' is in shuttle safe zone"
            return 0
        fi
    done
    
    # Outside whitelist but not dangerous
    echo "WARNING:Path '$path' is outside standard shuttle directories"
    return 0
}

check_path_safety() {
    local path="$1"
    local operation="$2"
    
    if [[ "$RECKLESS" == "true" ]]; then
        if [[ "$VERBOSE" == "true" ]]; then
            echo "⚠️  RECKLESS MODE: Bypassing safety check for $path"
        fi
        return 0
    fi
    
    local safety_result
    safety_result=$(validate_path_safety "$path")
    local validation_exit_code=$?
    
    local status="${safety_result%%:*}"
    local message="${safety_result#*:}"
    
    case "$status" in
        "DANGEROUS")
            echo "🚨 SAFETY CHECK FAILED: $message" >&2
            echo "❌ Refusing to $operation on dangerous path: $path" >&2
            echo "" >&2
            echo "💡 To override this safety check, run with --reckless flag:" >&2
            echo "   $SCRIPT_NAME $COMMAND --reckless [other options]" >&2
            echo "" >&2
            echo "⚠️  WARNING: --reckless mode disables ALL safety checks!" >&2
            echo "   If you know enough to disable this safety check,"
            echo "   perhaps you should be making these changes directly from the command line?" >&2
            return 1
            ;;
        "WARNING")
            if [[ "$VERBOSE" == "true" ]]; then
                echo "⚠️  $message"
            fi
            return 0
            ;;
        "SAFE")
            if [[ "$VERBOSE" == "true" ]]; then
                echo "✅ $message"
            fi
            return 0
            ;;
    esac
    
    return 0
}

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
  import-domain-user          Import domain user into local passwd (configurable)
  generate-domain-config      Generate domain import configuration and setup files

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
  --verbose                   Show detailed output
  --reckless                  Bypass ALL safety checks (DANGEROUS!)
  --help, -h                  Show help for specific command

EXAMPLES:
  # Get help for a specific command
  $SCRIPT_NAME add-user --help
  $SCRIPT_NAME list-users --help
  
  # Create a new user
  $SCRIPT_NAME add-user --user alice --home /home/alice
  
  # Import domain user
  $SCRIPT_NAME import-domain-user --username alice.domain
  
  # Generate domain config templates
  $SCRIPT_NAME generate-domain-config --output-dir /etc/shuttle --interactive
  
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
    
    # Check for --dry-run, --verbose, and --reckless flags in remaining parameters
    for arg in "$@"; do
        if [[ "$arg" == "--dry-run" ]]; then
            DRY_RUN=true
        elif [[ "$arg" == "--verbose" ]]; then
            VERBOSE=true
        elif [[ "$arg" == "--reckless" ]]; then
            RECKLESS=true
            echo "⚠️  RECKLESS MODE ENABLED - ALL SAFETY CHECKS DISABLED!"
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
        "import-domain-user")
            cmd_import_domain_user "$@"
            ;;
        "generate-domain-config")
            cmd_generate_domain_config "$@"
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