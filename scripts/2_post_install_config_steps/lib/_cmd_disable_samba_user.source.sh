# Command-specific help functions
show_help_disable_samba_user() {
    cat << EOF
Usage: $SCRIPT_NAME disable-samba-user --user <username> [options]

Disable a Samba user account temporarily.

Required Parameters:
  --user <username>     Username to disable in Samba

Optional Parameters:
  --force               Disable without confirmation prompt
  --dry-run             Show what would be done without making changes

Examples:
  # Disable a Samba user with confirmation
  $SCRIPT_NAME disable-samba-user --user alice
  
  # Disable user without confirmation
  $SCRIPT_NAME disable-samba-user --user bob --force

Notes:
  - User must exist in Samba database
  - Adds the 'D' (disabled) flag to user account
  - User will not be able to authenticate to Samba
  - User account and password are preserved
  - Can be re-enabled later with enable-samba-user command
  - Use list-samba-users to check current status
EOF
}

cmd_disable_samba_user() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local username=""
    local force=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_value "$1" "${2:-}" "Username required after --user" "show_help_disable_samba_user")
                shift 2
                ;;
            --force)
                force=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_disable_samba_user
                return 0
                ;;
            *)
                show_help_disable_samba_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_disable_samba_user
        error_exit "Username is required"
    fi
    
    log_command_call "disable-samba-user" "$original_params"
    
    # Call the core function
    disable_samba_user_core "$username" "$force"
    
    return 0
}

# Core function to disable Samba user
disable_samba_user_core() {
    local username="$1"
    local force="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "smbpasswd" "manage Samba users" "Samba tools not available"
    
    # Check if user exists in Samba
    if ! sudo pdbedit -L 2>/dev/null | grep -q "^$username:"; then
        error_exit "Samba user '$username' does not exist"
    fi
    
    # Check current user status
    local user_details=""
    local account_flags=""
    local current_status="unknown"
    
    if user_details=$(sudo pdbedit -v "$username" 2>/dev/null); then
        if [[ "$user_details" =~ Account\ Flags:[[:space:]]*\[([^\]]*)\] ]]; then
            account_flags="${BASH_REMATCH[1]}"
        fi
        
        # Determine current status
        if [[ "$account_flags" =~ D ]]; then
            current_status="disabled"
        else
            current_status="enabled"
        fi
    fi
    
    if [[ "$current_status" == "disabled" ]]; then
        log INFO "Samba user '$username' is already disabled"
        return 0
    fi
    
    # Confirmation prompt (unless force or dry-run)
    if [[ "$force" != "true" && "$DRY_RUN" != "true" ]]; then
        echo "Are you sure you want to disable Samba user '$username'? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log INFO "Samba user disable cancelled by user"
            return 0
        fi
    fi
    
    log INFO "Disabling Samba user '$username'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would disable Samba user '$username'"
        log INFO "[DRY RUN] Current flags: $account_flags"
        log INFO "[DRY RUN] User would not be able to authenticate but account would be preserved"
        return 0
    fi
    
    # Disable user
    local cmd="sudo smbpasswd -d \"$username\" >/dev/null 2>&1"
    execute_or_dryrun "$cmd" "Successfully disabled Samba user '$username'" "Failed to disable Samba user '$username'" || error_exit "Failed to disable Samba user '$username'"
    
    # Verify user is now disabled
    local new_status=""
    if user_details=$(sudo pdbedit -v "$username" 2>/dev/null); then
        if [[ "$user_details" =~ Account\ Flags:[[:space:]]*\[([^\]]*)\] ]]; then
            local new_flags="${BASH_REMATCH[1]}"
            if [[ "$new_flags" =~ D ]]; then
                new_status="disabled"
            else
                new_status="enabled"
            fi
        fi
    fi
    
    if [[ "$new_status" == "disabled" ]]; then
        log INFO "User '$username' is now disabled for Samba access"
        log INFO "Note: User account and password are preserved"
        log INFO "Note: Use enable-samba-user to re-enable access"
    else
        error_exit "User '$username' appears to still be enabled after disable attempt"
    fi
    
    return 0
}