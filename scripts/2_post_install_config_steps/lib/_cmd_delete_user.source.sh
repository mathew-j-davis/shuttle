# Input validation library will be loaded by the main script's setup lib loader

# Command-specific help functions
show_help_delete_user() {
    cat << EOF
Usage: $SCRIPT_NAME delete-user --user <username> [options]

Delete a user account and optionally clean up associated resources.

Required Parameters:
  --user <username>     Username to delete

Optional Parameters:
  --domain              User is a domain user (auto-detects domain)
  --remove-home         Remove user's home directory
  --remove-mail         Remove user's mail spool
  --force               Force deletion even if user is logged in
  --backup-home <path>  Backup home directory before deletion
  --dry-run             Show what would be done without making changes

Safety Options:
  --preserve-files      Keep all files owned by user (default behavior)
  --remove-owned-files  Remove all files owned by user (use with extreme caution)

Examples:
  # Delete local user (preserves home directory and files)
  $SCRIPT_NAME delete-user --user john
  
  # Delete local user and remove home directory
  $SCRIPT_NAME delete-user --user john --remove-home
  
  # Delete domain user (removes local resources only)
  $SCRIPT_NAME delete-user --user jsmith --domain
  
  # Delete user with backup of home directory
  $SCRIPT_NAME delete-user --user john --backup-home /backup/users/john --remove-home
  
  # Force delete even if user is logged in
  $SCRIPT_NAME delete-user --user john --force --remove-home

Notes:
  - For local users: Removes user account from /etc/passwd
  - For domain users: Only removes local resources (home dir, group memberships, etc.)
  - Domain users remain in the domain - this only cleans up local setup
  - By default, preserves files owned by user for safety
  - Use --remove-owned-files with extreme caution as it's irreversible
  - User will be removed from all local groups automatically
EOF
}

cmd_delete_user() {
    local username=""
    local is_domain=false
    local remove_home=false
    local remove_mail=false
    local force_delete=false
    local backup_home=""
    local preserve_files=true
    local remove_owned_files=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_user "$1" "${2:-}" "show_help_delete_user")
                shift 2
                ;;
            --domain)
                is_domain=true
                shift
                ;;
            --remove-home)
                remove_home=true
                shift
                ;;
            --remove-mail)
                remove_mail=true
                shift
                ;;
            --force)
                force_delete=true
                shift
                ;;
            --backup-home)
                backup_home=$(validate_parameter_path "$1" "${2:-}" "show_help_delete_user")
                shift 2
                ;;
            --preserve-files)
                preserve_files=true
                remove_owned_files=false
                shift
                ;;
            --remove-owned-files)
                preserve_files=false
                remove_owned_files=true
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
                show_help_delete_user
                return 0
                ;;
            *)
                show_help_delete_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_delete_user
        error_exit "Username is required"
    fi
    
    # Validate conflicting options
    if [[ "$preserve_files" == "false" && "$remove_owned_files" == "false" ]]; then
        preserve_files=true  # Default to safe option
    fi
    
    # Note: Input validation is already performed during parameter parsing
    # using validate_parameter_user() and validate_parameter_path()
    
    # Branch based on user type
    if [[ "$is_domain" == "true" ]]; then
        _delete_domain_user_locally "$username" "$remove_home" "$backup_home" "$remove_owned_files"
    else
        _delete_local_user "$username" "$remove_home" "$remove_mail" "$force_delete" "$backup_home" "$remove_owned_files"
    fi
}

# Helper function for local user deletion
_delete_local_user() {
    local username="$1"
    local remove_home="$2"
    local remove_mail="$3"
    local force_delete="$4"
    local backup_home="$5"
    local remove_owned_files="$6"
    
    # Note: Input validation already performed during parameter parsing
    
    check_tool_permission_or_error_exit "userdel" "delete users" "userdel not available - cannot delete users"
    
    # Check if user exists
    if ! user_exists_in_passwd "$username"; then
        error_exit "User '$username' does not exist"
    fi
    
    log INFO "Deleting local user: $username"
    
    # Check if user is currently logged in (unless force specified)
    if [[ "$force_delete" != "true" ]]; then
        # Use sanitized username for grep to prevent regex injection
        local escaped_username
        escaped_username=$(sanitize_for_regex "$username")
        if who | grep -q "^$escaped_username "; then
            error_exit "User '$username' is currently logged in. Use --force to delete anyway or ask user to log out first"
        fi
    fi
    
    # Get user info before deletion for backup/cleanup purposes
    local user_info=""
    if user_info=$(getent passwd "$username" 2>/dev/null); then
        local user_home=$(echo "$user_info" | cut -d: -f6)
        log INFO "User home directory: $user_home"
        
        # Backup home directory if requested
        if [[ -n "$backup_home" && -d "$user_home" ]]; then
            log INFO "Backing up home directory to: $backup_home"
            local backup_cmd="cp -r '$user_home' '$backup_home'"
            if ! check_active_user_is_root; then
                backup_cmd="sudo $backup_cmd"
            fi
            execute_or_dryrun "$backup_cmd" "Backed up home directory to '$backup_home'" "Failed to backup home directory" || log WARN "Home directory backup failed"
        fi
    fi
    
    # Build userdel command
    local userdel_cmd="userdel"
    
    # Add sudo prefix if running as non-root
    if ! check_active_user_is_root; then
        userdel_cmd="sudo $userdel_cmd"
    fi
    
    # Add flags based on options
    if [[ "$remove_home" == "true" ]]; then
        userdel_cmd="$userdel_cmd --remove"
    fi
    
    if [[ "$remove_mail" == "true" ]]; then
        userdel_cmd="$userdel_cmd --remove-all-files"
    elif [[ "$remove_owned_files" == "true" ]]; then
        userdel_cmd="$userdel_cmd --remove-all-files"
    fi
    
    if [[ "$force_delete" == "true" ]]; then
        userdel_cmd="$userdel_cmd --force"
    fi
    
    # Add username as final argument (quoted for security)
    userdel_cmd="$userdel_cmd '$username'"
    
    # Execute userdel
    execute_or_dryrun "$userdel_cmd" "User '$username' deleted successfully" "Failed to delete user '$username'" || error_exit "Failed to delete user '$username'"
    
    # Clean up any remaining files owned by user if requested and userdel didn't handle it
    if [[ "$remove_owned_files" == "true" && "$remove_mail" != "true" ]]; then
        log INFO "Searching for remaining files owned by '$username'..."
        local remaining_files=""
        if remaining_files=$(find /home /var /opt /usr/local -user "$username" 2>/dev/null | head -10); then
            if [[ -n "$remaining_files" ]]; then
                log WARN "Found files still owned by '$username' (showing first 10):"
                echo "$remaining_files"
                log INFO "Removing remaining files owned by '$username'..."
                local cleanup_cmd="find /home /var /opt /usr/local -user '$username' -delete 2>/dev/null"
                if ! check_active_user_is_root; then
                    cleanup_cmd="sudo $cleanup_cmd"
                fi
                execute_or_dryrun "$cleanup_cmd" "Cleaned up remaining files owned by '$username'" "Failed to clean up some files owned by '$username'" || log WARN "Some file cleanup may have failed"
            fi
        fi
    fi
    
    log INFO "Local user '$username' deletion completed"
    return 0
}

# Helper function for domain user local resource cleanup
_delete_domain_user_locally() {
    local username="$1"
    local remove_home="$2"
    local backup_home="$3"
    local remove_owned_files="$4"
    
    # Validate username contains no domain markers
    if [[ "$username" =~ [@\\] ]]; then
        error_exit "Username must not contain domain. Use plain username with --domain flag"
    fi
    
    # Detect domain and find domain user format
    detect_machine_domain || error_exit "Could not detect domain membership"
    local domain="$DETECTED_DOMAIN"
    
    # Check if domain user has local resources
    if ! check_domain_user_exists_locally_in_passwd "$username" "$domain"; then
        log WARN "Domain user '$username' has no local resources to clean up"
        return 0
    fi
    
    local domain_user="$DETECTED_DOMAIN_USER_FORMAT"
    log INFO "Cleaning up local resources for domain user: $domain_user"
    
    # Get comprehensive list of resources to clean up
    if check_user_all_local_resources "$username" "$domain_user" ""; then
        log INFO "Found local resources to clean up:"
        for resource in "${DETECTED_USER_RESOURCES[@]}"; do
            log INFO "  - $resource"
        done
    else
        log INFO "No local resources found for domain user '$username'"
        return 0
    fi
    
    # Get user home directory for backup if needed
    local user_home=""
    if user_info=$(getent passwd "$domain_user" 2>/dev/null); then
        user_home=$(echo "$user_info" | cut -d: -f6)
        
        # Backup home directory if requested
        if [[ -n "$backup_home" && -d "$user_home" ]]; then
            log INFO "Backing up home directory to: $backup_home"
            local backup_cmd="cp -r '$user_home' '$backup_home'"
            if ! check_active_user_is_root; then
                backup_cmd="sudo $backup_cmd"
            fi
            execute_or_dryrun "$backup_cmd" "Backed up home directory to '$backup_home'" "Failed to backup home directory" || log WARN "Home directory backup failed"
        fi
    fi
    
    # Remove from all groups
    log INFO "Removing domain user '$domain_user' from all local groups..."
    local user_groups=""
    if user_groups=$(groups "$domain_user" 2>/dev/null | cut -d: -f2 | xargs); then
        if [[ -n "$user_groups" ]]; then
            for group in $user_groups; do
                # Skip primary group - it will be handled when we remove the user entry
                if [[ "$group" != "$username" ]]; then
                    remove_user_from_group_core "$username" "$domain_user" "$group" || log WARN "Failed to remove from group '$group'"
                fi
            done
        fi
    fi
    
    # Remove home directory if requested
    if [[ "$remove_home" == "true" && -n "$user_home" && -d "$user_home" ]]; then
        log INFO "Removing home directory: $user_home"
        local rm_home_cmd="rm -rf '$user_home'"
        if ! check_active_user_is_root; then
            rm_home_cmd="sudo $rm_home_cmd"
        fi
        execute_or_dryrun "$rm_home_cmd" "Removed home directory '$user_home'" "Failed to remove home directory '$user_home'" || log WARN "Home directory removal failed"
    fi
    
    # Remove owned files if requested
    if [[ "$remove_owned_files" == "true" ]]; then
        log INFO "Removing all files owned by '$domain_user'..."
        local cleanup_cmd="find /home /var /opt /usr/local -user '$domain_user' -delete 2>/dev/null"
        if ! check_active_user_is_root; then
            cleanup_cmd="sudo $cleanup_cmd"
        fi
        execute_or_dryrun "$cleanup_cmd" "Removed files owned by '$domain_user'" "Failed to remove some files owned by '$domain_user'" || log WARN "Some file cleanup may have failed"
    fi
    
    log INFO "Domain user '$username' local resource cleanup completed"
    log INFO "Note: Domain user still exists in the domain - only local resources were cleaned up"
    return 0
}