# Command-specific help functions
show_help_show_acl_on_path() {
    cat << EOF
Usage: $SCRIPT_NAME show-acl-on-path --path <path> [options]

Display Access Control Lists (ACLs) for a file or directory.

Required Parameters:
  --path <path>         Path to show ACLs for

Optional Parameters:
  --recursive           Show ACLs recursively for directories
  --effective           Show effective permissions
  --numeric             Show numeric IDs instead of names
  --default             Show default ACLs (directories only)
  --dry-run             Show what would be done without making changes

Examples:
  # Show ACLs for a file
  $SCRIPT_NAME show-acl-on-path --path /home/user/document.txt
  
  # Show ACLs recursively for a directory
  $SCRIPT_NAME show-acl-on-path --path /home/project --recursive
  
  # Show effective permissions
  $SCRIPT_NAME show-acl-on-path --path /var/log --effective
  
  # Show numeric UIDs/GIDs
  $SCRIPT_NAME show-acl-on-path --path /opt/app --numeric

Notes:
  - Requires getfacl command (part of acl package)
  - Path must exist and be accessible
  - Default ACLs only apply to directories
EOF
}

cmd_show_acl_on_path() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local path=""
    local recursive=false
    local effective=false
    local numeric=false
    local show_default=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                path=$(validate_parameter_value "$1" "${2:-}" "Path required after --path" "show_help_show_acl_on_path")
                shift 2
                ;;
            --recursive)
                recursive=true
                shift
                ;;
            --effective)
                effective=true
                shift
                ;;
            --numeric)
                numeric=true
                shift
                ;;
            --default)
                show_default=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help_show_acl_on_path
                return 0
                ;;
            *)
                show_help_show_acl_on_path
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$path" ]]; then
        show_help_show_acl_on_path
        error_exit "Path is required"
    fi
    
    log_command_call "show-acl-on-path" "$original_params"
    
    # Check tool availability
    check_tool_permission_or_error_exit "getfacl" "read ACLs" "getfacl not available - install acl package"
    
    # Validate path exists
    if [[ ! -e "$path" ]]; then
        error_exit "Path does not exist: $path"
    fi
    
    # Call the core function
    show_acl_on_path_core "$path" "$recursive" "$effective" "$numeric" "$show_default" || error_exit "Failed to show ACLs"
    
    return 0
}