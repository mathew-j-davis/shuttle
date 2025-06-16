# Command-specific help functions
show_help_enable_samba_user() {
    cat << EOF
Usage: $SCRIPT_NAME enable-samba-user --user <username> [options]

Enable a disabled Samba user account.

Required Parameters:
  --user <username>     Username to enable in Samba

Optional Parameters:
  --dry-run             Show what would be done without making changes

Examples:
  # Enable a disabled Samba user
  $SCRIPT_NAME enable-samba-user --user alice

Notes:
  - User must exist in Samba database
  - Removes the 'D' (disabled) flag from user account
  - User will be able to authenticate to Samba again
  - Use list-samba-users to check current status
  - Password remains unchanged
EOF
}

cmd_enable_samba_user() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local username=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_value "$1" "${2:-}" "Username required after --user" "show_help_enable_samba_user")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_enable_samba_user
                return 0
                ;;
            *)
                show_help_enable_samba_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_enable_samba_user
        error_exit "Username is required"
    fi
    
    echo "enable-samba-user command called with parameters: $original_params"
    
    # Call the core function
    enable_samba_user_core "$username"
    
    return 0
}

# Core function to enable Samba user
enable_samba_user_core() {
    local username="$1"
    
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
    
    if [[ "$current_status" == "enabled" ]]; then
        log INFO "Samba user '$username' is already enabled"
        return 0
    fi
    
    log INFO "Enabling Samba user '$username'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would enable Samba user '$username'"
        log INFO "[DRY RUN] Current flags: $account_flags"
        return 0
    fi
    
    # Enable user
    if sudo smbpasswd -e "$username" >/dev/null 2>&1; then
        log INFO "Successfully enabled Samba user '$username'"
    else
        error_exit "Failed to enable Samba user '$username'"
    fi
    
    # Verify user is now enabled
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
    
    if [[ "$new_status" == "enabled" ]]; then
        log INFO "User '$username' is now enabled for Samba access"
    else
        error_exit "User '$username' appears to still be disabled after enable attempt"
    fi
    
    return 0
}