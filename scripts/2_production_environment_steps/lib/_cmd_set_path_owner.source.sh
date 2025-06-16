# Command-specific help functions
show_help_set_path_owner() {
    cat << EOF
Usage: $SCRIPT_NAME set-path-owner --path <path> [--user <user>] [--group <group>] [options]

Change ownership (user and/or group) of files and directories.

Required Parameters:
  --path <path>         Path to change ownership for

Ownership Parameters (at least one required):
  --user <user>         New owner username or UID
  --group <group>       New group name or GID
  --user-group <user:group>  Set both user and group (format: user:group)

Optional Parameters:
  --recursive           Apply changes recursively to directories
  --preserve-root       Prevent changes to root directory (/)
  --reference <file>    Copy ownership from reference file
  --from <user:group>   Only change files currently owned by this user:group
  --dry-run             Show what would be done without making changes

Examples:
  # Change owner only
  $SCRIPT_NAME set-path-owner --path /home/project --user alice
  
  # Change group only
  $SCRIPT_NAME set-path-owner --path /var/log/app --group developers
  
  # Change both user and group
  $SCRIPT_NAME set-path-owner --path /opt/app --user-group alice:developers
  
  # Change recursively
  $SCRIPT_NAME set-path-owner --path /home/project --user alice --recursive
  
  # Copy ownership from reference file
  $SCRIPT_NAME set-path-owner --path /new/file --reference /existing/file
  
  # Change only files currently owned by specific user
  $SCRIPT_NAME set-path-owner --path /shared --user bob --from alice:users --recursive

Notes:
  - Requires appropriate permissions (usually root/sudo)
  - Use numeric IDs when usernames/groups don't exist
  - --preserve-root prevents accidental changes to system root
  - --from option is useful for bulk ownership transfers
  - --reference copies both user and group from another file
EOF
}

cmd_set_path_owner() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local path=""
    local new_user=""
    local new_group=""
    local user_group=""
    local recursive=false
    local preserve_root=true
    local reference_file=""
    local from_owner=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                path=$(validate_parameter_value "$1" "${2:-}" "Path required after --path" "show_help_set_path_owner")
                shift 2
                ;;
            --user)
                new_user=$(validate_parameter_value "$1" "${2:-}" "User required after --user" "show_help_set_path_owner")
                shift 2
                ;;
            --group)
                new_group=$(validate_parameter_value "$1" "${2:-}" "Group required after --group" "show_help_set_path_owner")
                shift 2
                ;;
            --user-group)
                user_group=$(validate_parameter_value "$1" "${2:-}" "User:group required after --user-group" "show_help_set_path_owner")
                shift 2
                ;;
            --recursive)
                recursive=true
                shift
                ;;
            --preserve-root)
                preserve_root=true
                shift
                ;;
            --no-preserve-root)
                preserve_root=false
                shift
                ;;
            --reference)
                reference_file=$(validate_parameter_value "$1" "${2:-}" "Reference file required after --reference" "show_help_set_path_owner")
                shift 2
                ;;
            --from)
                from_owner=$(validate_parameter_value "$1" "${2:-}" "Current owner required after --from" "show_help_set_path_owner")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_set_path_owner
                return 0
                ;;
            *)
                show_help_set_path_owner
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$path" ]]; then
        show_help_set_path_owner
        error_exit "Path is required"
    fi
    
    # Parse user_group if provided
    if [[ -n "$user_group" ]]; then
        if [[ "$user_group" =~ ^([^:]+):([^:]+)$ ]]; then
            new_user="${BASH_REMATCH[1]}"
            new_group="${BASH_REMATCH[2]}"
        else
            show_help_set_path_owner
            error_exit "Invalid user:group format: $user_group. Use format 'user:group'"
        fi
    fi
    
    # Validate that at least one ownership change is specified
    if [[ -z "$new_user" && -z "$new_group" && -z "$reference_file" ]]; then
        show_help_set_path_owner
        error_exit "Must specify at least one of: --user, --group, --user-group, or --reference"
    fi
    
    # Validate conflicting options
    if [[ -n "$reference_file" && (-n "$new_user" || -n "$new_group") ]]; then
        show_help_set_path_owner
        error_exit "Cannot specify both --reference and --user/--group options"
    fi
    
    echo "set-path-owner command called with parameters: $original_params"
    
    # Check tool availability
    check_tool_permission_or_error_exit "chown" "change ownership" "chown not available - cannot change file ownership"
    
    # Validate path exists
    if [[ ! -e "$path" ]]; then
        error_exit "Path does not exist: $path"
    fi
    
    # Protect root directory
    if [[ "$preserve_root" == "true" && "$path" == "/" ]]; then
        error_exit "Refusing to change ownership of root directory (/). Use --no-preserve-root if you really want this"
    fi
    
    # Call the core function
    set_path_owner_core "$path" "$new_user" "$new_group" "$recursive" "$reference_file" "$from_owner"
    
    return 0
}

# Core function to set path ownership
set_path_owner_core() {
    local path="$1"
    local new_user="$2"
    local new_group="$3"
    local recursive="$4"
    local reference_file="$5"
    local from_owner="$6"
    
    # Handle reference file
    if [[ -n "$reference_file" ]]; then
        if [[ ! -e "$reference_file" ]]; then
            log ERROR "Reference file does not exist: $reference_file"
            return 1
        fi
        
        # Get ownership from reference file
        local ref_stat=""
        if ! ref_stat=$(stat -c "%U:%G" "$reference_file" 2>/dev/null); then
            log ERROR "Could not get ownership information from reference file: $reference_file"
            return 1
        fi
        
        IFS=':' read -r new_user new_group <<< "$ref_stat"
        log INFO "Using ownership from reference file '$reference_file': $new_user:$new_group"
    fi
    
    # Build ownership string for chown
    local ownership_string=""
    if [[ -n "$new_user" && -n "$new_group" ]]; then
        ownership_string="$new_user:$new_group"
    elif [[ -n "$new_user" ]]; then
        ownership_string="$new_user"
    elif [[ -n "$new_group" ]]; then
        ownership_string=":$new_group"
    else
        log ERROR "No ownership changes specified"
        return 1
    fi
    
    # Validate user exists (if not numeric)
    if [[ -n "$new_user" && ! "$new_user" =~ ^[0-9]+$ ]]; then
        if ! getent passwd "$new_user" >/dev/null 2>&1; then
            log WARN "User '$new_user' does not exist in the system"
            log INFO "Proceeding anyway - chown will fail if user is invalid"
        fi
    fi
    
    # Validate group exists (if not numeric)
    if [[ -n "$new_group" && ! "$new_group" =~ ^[0-9]+$ ]]; then
        if ! getent group "$new_group" >/dev/null 2>&1; then
            log WARN "Group '$new_group' does not exist in the system"
            log INFO "Proceeding anyway - chown will fail if group is invalid"
        fi
    fi
    
    # Build chown command
    local chown_cmd="chown"
    
    # Add sudo if not root
    if ! check_active_user_is_root; then
        chown_cmd="sudo $chown_cmd"
    fi
    
    # Add flags
    if [[ "$recursive" == "true" ]]; then
        chown_cmd="$chown_cmd --recursive"
    fi
    
    # Add from option if specified
    if [[ -n "$from_owner" ]]; then
        # Validate from_owner format
        if [[ ! "$from_owner" =~ ^[^:]+:[^:]+$ ]]; then
            log ERROR "Invalid --from format: $from_owner. Use format 'user:group'"
            return 1
        fi
        chown_cmd="$chown_cmd --from='$from_owner'"
    fi
    
    # Add ownership and path
    chown_cmd="$chown_cmd '$ownership_string' '$path'"
    
    # Show what will be changed
    log INFO "Changing ownership of '$path' to '$ownership_string'"
    if [[ "$recursive" == "true" ]]; then
        log INFO "Applying changes recursively"
    fi
    if [[ -n "$from_owner" ]]; then
        log INFO "Only changing files currently owned by: $from_owner"
    fi
    
    # Execute chown command
    execute_or_dryrun "$chown_cmd" "Changed ownership of '$path' to '$ownership_string'" "Failed to change ownership of '$path'" || return 1
    
    # Show summary of changes if not dry run
    if [[ "$DRY_RUN" != "true" ]]; then
        log INFO "Ownership change completed successfully"
        
        # Show current ownership for verification
        local current_ownership=""
        if current_ownership=$(stat -c "%U:%G" "$path" 2>/dev/null); then
            log INFO "Current ownership of '$path': $current_ownership"
        fi
        
        # For recursive changes, show count of affected files
        if [[ "$recursive" == "true" && -d "$path" ]]; then
            local file_count=0
            if file_count=$(find "$path" -print 2>/dev/null | wc -l); then
                log INFO "Total files/directories processed: $file_count"
            fi
        fi
    fi
    
    return 0
}

# Function to validate ownership format (helper)
validate_ownership_format() {
    local ownership="$1"
    
    # Check for valid formats:
    # user
    # :group
    # user:group
    # numeric variations
    if [[ "$ownership" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_-]*$ ]] ||           # user only
       [[ "$ownership" =~ ^:[a-zA-Z0-9_][a-zA-Z0-9_-]*$ ]] ||          # :group only  
       [[ "$ownership" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_-]*:[a-zA-Z0-9_][a-zA-Z0-9_-]*$ ]] || # user:group
       [[ "$ownership" =~ ^[0-9]+$ ]] ||                               # numeric user
       [[ "$ownership" =~ ^:[0-9]+$ ]] ||                              # :numeric group
       [[ "$ownership" =~ ^[0-9]+:[0-9]+$ ]]; then                     # numeric user:group
        return 0
    else
        return 1
    fi
}