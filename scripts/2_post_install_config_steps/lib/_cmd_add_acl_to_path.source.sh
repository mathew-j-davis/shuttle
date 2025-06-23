# Command-specific help functions
show_help_add_acl_to_path() {
    cat << EOF
Usage: $SCRIPT_NAME add-acl-to-path --path <path> --acl <acl_entry> [options]

Add an Access Control List (ACL) entry to a file or directory.

Required Parameters:
  --path <path>         Path to add ACL to
  --acl <acl_entry>     ACL entry to add (format: [d:][user|group|other]:name:permissions)

Optional Parameters:
  --recursive           Apply ACL recursively to directories
  --default             Set as default ACL (directories only)
  --dry-run             Show what would be done without making changes

ACL Entry Format:
  user:username:rwx     - User permissions
  group:groupname:r-x   - Group permissions  
  other::r--            - Other permissions
  mask::rwx             - Maximum permissions mask
  d:user:username:rwx   - Default user permissions (directories only)
  d:group:groupname:r-x - Default group permissions (directories only)

Permission Symbols:
  r = read, w = write, x = execute, - = no permission

Examples:
  # Give user read/write access to file
  $SCRIPT_NAME add-acl-to-path --path /home/project/file.txt --acl "user:john:rw-"
  
  # Give group execute access to directory recursively
  $SCRIPT_NAME add-acl-to-path --path /opt/app --acl "group:developers:r-x" --recursive
  
  # Set default ACL for new files in directory
  $SCRIPT_NAME add-acl-to-path --path /shared/data --acl "user:backup:r--" --default
  
  # Multiple operations
  $SCRIPT_NAME add-acl-to-path --path /var/log/app --acl "group:loggers:rw-"
  $SCRIPT_NAME add-acl-to-path --path /var/log/app --acl "user:monitor:r--"

Notes:
  - Requires setfacl command (part of acl package)
  - Path must exist and be accessible
  - Default ACLs only apply to directories
  - ACL entries are additive - existing entries remain unless overridden
EOF
}

cmd_add_acl_to_path() {
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
                path=$(validate_parameter_value "$1" "${2:-}" "Path required after --path" "show_help_add_acl_to_path")
                shift 2
                ;;
            --acl)
                acl_entry=$(validate_parameter_value "$1" "${2:-}" "ACL entry required after --acl" "show_help_add_acl_to_path")
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
                show_help_add_acl_to_path
                return 0
                ;;
            *)
                show_help_add_acl_to_path
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$path" ]]; then
        show_help_add_acl_to_path
        error_exit "Path is required"
    fi
    
    if [[ -z "$acl_entry" ]]; then
        show_help_add_acl_to_path
        error_exit "ACL entry is required"
    fi
    
    log_command_call "add-acl-to-path" "$original_params"
    
    # Check tool availability
    check_tool_permission_or_error_exit "setfacl" "modify ACLs" "setfacl not available - install acl package"
    
    # Validate path exists
    if [[ ! -e "$path" ]]; then
        error_exit "Path does not exist: $path"
    fi
    
    # Basic ACL entry format validation
    if [[ ! "$acl_entry" =~ ^(d:)?(user|group|other|mask):[^:]*:[rwx-]+$ ]]; then
        log WARN "ACL entry format may be invalid: $acl_entry"
        log WARN "Expected format: [d:][user|group|other|mask]:name:permissions"
        log WARN "Example: user:john:rw- or d:group:staff:r-x"
    fi
    
    # Call the core function
    add_acl_to_path_core "$path" "$acl_entry" "$recursive" "$default_acl" || error_exit "Failed to add ACL"
    
    return 0
}