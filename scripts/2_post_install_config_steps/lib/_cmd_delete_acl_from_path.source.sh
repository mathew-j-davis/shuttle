# Command-specific help functions
show_help_delete_acl_from_path() {
    cat << EOF
Usage: $SCRIPT_NAME delete-acl-from-path --path <path> --acl <acl_entry> [options]

Remove an Access Control List (ACL) entry from a file or directory.

Required Parameters:
  --path <path>         Path to remove ACL from
  --acl <acl_entry>     ACL entry to remove (format: [d:][user|group|other]:name)

Optional Parameters:
  --recursive           Remove ACL recursively from directories
  --default             Remove from default ACL (directories only)
  --dry-run             Show what would be done without making changes

ACL Entry Format (for removal):
  user:username         - Remove user permissions
  group:groupname       - Remove group permissions  
  other                 - Remove other permissions
  mask                  - Remove mask permissions
  d:user:username       - Remove default user permissions (directories only)
  d:group:groupname     - Remove default group permissions (directories only)

Examples:
  # Remove user access from file
  $SCRIPT_NAME delete-acl-from-path --path /home/project/file.txt --acl "user:john"
  
  # Remove group access from directory recursively
  $SCRIPT_NAME delete-acl-from-path --path /opt/app --acl "group:developers" --recursive
  
  # Remove default ACL for directory
  $SCRIPT_NAME delete-acl-from-path --path /shared/data --acl "user:backup" --default
  
  # Remove all ACLs (use with caution)
  $SCRIPT_NAME delete-acl-from-path --path /tmp/test --acl "user:testuser"
  $SCRIPT_NAME delete-acl-from-path --path /tmp/test --acl "group:testgroup"

Notes:
  - Requires setfacl command (part of acl package)
  - Path must exist and be accessible
  - Only removes specified ACL entries, other entries remain
  - Default ACLs only apply to directories
  - Permissions are not specified when removing (only user/group names)
EOF
}

cmd_delete_acl_from_path() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local path=""
    local acl_entry=""
    local recursive=false
    local default_acl=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                path=$(validate_parameter_value "$1" "${2:-}" "Path required after --path" "show_help_delete_acl_from_path")
                shift 2
                ;;
            --acl)
                acl_entry=$(validate_parameter_value "$1" "${2:-}" "ACL entry required after --acl" "show_help_delete_acl_from_path")
                shift 2
                ;;
            --recursive)
                recursive=true
                shift
                ;;
            --default)
                default_acl=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_delete_acl_from_path
                return 0
                ;;
            *)
                show_help_delete_acl_from_path
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$path" ]]; then
        show_help_delete_acl_from_path
        error_exit "Path is required"
    fi
    
    if [[ -z "$acl_entry" ]]; then
        show_help_delete_acl_from_path
        error_exit "ACL entry is required"
    fi
    
    log_command_call "delete-acl-from-path" "$original_params"
    
    # Check tool availability
    check_tool_permission_or_error_exit "setfacl" "modify ACLs" "setfacl not available - install acl package"
    
    # Validate path exists
    if [[ ! -e "$path" ]]; then
        error_exit "Path does not exist: $path"
    fi
    
    # Basic ACL entry format validation for removal (no permissions needed)
    if [[ ! "$acl_entry" =~ ^(d:)?(user|group|other|mask):[^:]*$ ]]; then
        log WARN "ACL entry format may be invalid for removal: $acl_entry"
        log WARN "Expected format: [d:][user|group|other|mask]:name"
        log WARN "Example: user:john or d:group:staff"
    fi
    
    # Call the core function
    remove_acl_from_path_core "$path" "$acl_entry" "$recursive" "$default_acl" || error_exit "Failed to remove ACL"
    
    return 0
}