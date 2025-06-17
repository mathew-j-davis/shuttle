# Input validation library will be loaded by the main script's setup lib loader

# Command-specific help functions
show_help_set_path_owner() {
    cat << EOF
Usage: $SCRIPT_NAME set-path-owner --path <path> [--user <user>] [--group <group>] [options]

Change ownership (user and/or group) of files and directories.

Required Parameters:
  --path <path>         Path to change ownership for

Ownership Parameters (at least one required):
  --user <username>     New owner username
  --uid <uid>          New owner user ID (numeric)
  --group <groupname>   New group name
  --gid <gid>          New group ID (numeric)

Optional Parameters:
  --recursive           Apply changes recursively to directories
  --preserve-root       Prevent changes to root directory (/)
  --reference <file>    Copy ownership from reference file
  --from <user:group>   Only change files currently owned by this user:group
  --dry-run             Show what would be done without making changes

Examples:
  # Change owner by username
  $SCRIPT_NAME set-path-owner --path /home/project --user alice
  
  # Change owner by UID
  $SCRIPT_NAME set-path-owner --path /home/project --uid 1000
  
  # Change group by name
  $SCRIPT_NAME set-path-owner --path /var/log/app --group developers
  
  # Change group by GID
  $SCRIPT_NAME set-path-owner --path /var/log/app --gid 1001
  
  # Change both user and group (mixed name/numeric)
  $SCRIPT_NAME set-path-owner --path /opt/app --user alice --gid 1001
  
  # Change recursively
  $SCRIPT_NAME set-path-owner --path /home/project --user alice --recursive
  
  # Copy ownership from reference file
  $SCRIPT_NAME set-path-owner --path /new/file --reference /existing/file
  
  # Change only files currently owned by specific user
  $SCRIPT_NAME set-path-owner --path /shared --user bob --from alice:users --recursive

Notes:
  - Requires appropriate permissions (usually root/sudo)
  - Use --uid/--gid when usernames/groups don't exist locally
  - Cannot specify both --user and --uid (use one or the other)
  - Cannot specify both --group and --gid (use one or the other)
  - --preserve-root prevents accidental changes to system root
  - --from option is useful for bulk ownership transfers
  - --reference copies both user and group from another file
EOF
}

cmd_set_path_owner() {
    local path=""
    local new_user=""
    local new_uid=""
    local new_group=""
    local new_gid=""
    local recursive=false
    local preserve_root=true
    local reference_file=""
    local from_owner=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                path=$(validate_parameter_path "$1" "${2:-}" "show_help_set_path_owner")
                shift 2
                ;;
            --user)
                new_user=$(validate_parameter_user "$1" "${2:-}" "show_help_set_path_owner")
                shift 2
                ;;
            --group)
                new_group=$(validate_parameter_group "$1" "${2:-}" "show_help_set_path_owner")
                shift 2
                ;;
            --uid)
                new_uid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_set_path_owner")
                shift 2
                ;;
            --gid)
                new_gid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_set_path_owner")
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
                reference_file=$(validate_parameter_path "$1" "${2:-}" "show_help_set_path_owner")
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
    
    # Validate conflicting user specifications
    if [[ -n "$new_user" && -n "$new_uid" ]]; then
        show_help_set_path_owner
        error_exit "Cannot specify both --user and --uid. Use --user for username or --uid for numeric ID"
    fi
    
    # Validate conflicting group specifications
    if [[ -n "$new_group" && -n "$new_gid" ]]; then
        show_help_set_path_owner
        error_exit "Cannot specify both --group and --gid. Use --group for name or --gid for numeric ID"
    fi
    
    # Validate that at least one ownership change is specified
    if [[ -z "$new_user" && -z "$new_uid" && -z "$new_group" && -z "$new_gid" && -z "$reference_file" ]]; then
        show_help_set_path_owner
        error_exit "Must specify at least one of: --user, --uid, --group, --gid, or --reference"
    fi
    
    # Validate conflicting options
    if [[ -n "$reference_file" && (-n "$new_user" || -n "$new_uid" || -n "$new_group" || -n "$new_gid") ]]; then
        show_help_set_path_owner
        error_exit "Cannot specify both --reference and ownership options (--user/--uid/--group/--gid)"
    fi
    
    # Note: Input validation is already performed during parameter parsing using:
    # - validate_parameter_path() for paths
    # - validate_parameter_user() for usernames  
    # - validate_parameter_group() for group names
    # - validate_parameter_numeric() for UID/GID values
    
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
    set_path_owner_core "$path" "$new_user" "$new_uid" "$new_group" "$new_gid" "$recursive" "$reference_file" "$from_owner"
    
    return 0
}

# Core function to set path ownership
set_path_owner_core() {
    local path="$1"
    local new_user="$2"
    local new_uid="$3"
    local new_group="$4"
    local new_gid="$5"
    local recursive="$6"
    local reference_file="$7"
    local from_owner="$8"
    
    # Determine final user and group values
    local final_user=""
    local final_group=""
    
    if [[ -n "$new_user" ]]; then
        final_user="$new_user"
    elif [[ -n "$new_uid" ]]; then
        final_user="$new_uid"
    fi
    
    if [[ -n "$new_group" ]]; then
        final_group="$new_group"
    elif [[ -n "$new_gid" ]]; then
        final_group="$new_gid"
    fi
    
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
        
        IFS=':' read -r final_user final_group <<< "$ref_stat"
        log INFO "Using ownership from reference file '$reference_file': $final_user:$final_group"
    fi
    
    # Build ownership string for chown
    local ownership_string=""
    if [[ -n "$final_user" && -n "$final_group" ]]; then
        ownership_string="$final_user:$final_group"
    elif [[ -n "$final_user" ]]; then
        ownership_string="$final_user"
    elif [[ -n "$final_group" ]]; then
        ownership_string=":$final_group"
    else
        log ERROR "No ownership changes specified"
        return 1
    fi
    
    # Validate user exists (if not numeric)
    if [[ -n "$final_user" && ! "$final_user" =~ ^[0-9]+$ ]]; then
        if ! getent passwd "$final_user" >/dev/null 2>&1; then
            log WARN "User '$final_user' does not exist in the system"
            log INFO "Proceeding anyway - chown will fail if user is invalid"
        fi
    fi
    
    # Validate group exists (if not numeric)
    if [[ -n "$final_group" && ! "$final_group" =~ ^[0-9]+$ ]]; then
        if ! getent group "$final_group" >/dev/null 2>&1; then
            log WARN "Group '$final_group' does not exist in the system"
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
    execute_or_dryrun "$chown_cmd" "Changed ownership of '$path' to '$ownership_string'" "Failed to change ownership of '$path'" \
                     "Change file or directory ownership to control which user and group can access the resource" || return 1
    
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