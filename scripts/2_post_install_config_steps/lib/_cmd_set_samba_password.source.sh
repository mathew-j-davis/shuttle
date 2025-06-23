# Command-specific help functions
show_help_set_samba_password() {
    cat << EOF
Usage: $SCRIPT_NAME set-samba-password --user <username> [options]

Set or change a Samba user's password.

Required Parameters:
  --user <username>     Username to set password for

Optional Parameters:
  --password <password> Set specific password (interactive prompt if not provided)
  --dry-run             Show what would be done without making changes

Examples:
  # Set password with interactive prompt
  $SCRIPT_NAME set-samba-password --user alice
  
  # Set password from command line
  $SCRIPT_NAME set-samba-password --user bob --password "newsecure123"

Security Notes:
  - User must already exist in Samba user database
  - Passwords specified on command line may be visible in process lists
  - Interactive password prompt is more secure
  - Use strong passwords for Samba access
  - Samba passwords are separate from system passwords

Notes:
  - Uses smbpasswd command to change password
  - User must already be added to Samba (use add-samba-user first)
  - Password change takes effect immediately
EOF
}

cmd_set_samba_password() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local username=""
    local password=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_value "$1" "${2:-}" "Username required after --user" "show_help_set_samba_password")
                shift 2
                ;;
            --password)
                password=$(validate_parameter_value "$1" "${2:-}" "Password required after --password" "show_help_set_samba_password")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_set_samba_password
                return 0
                ;;
            *)
                show_help_set_samba_password
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_set_samba_password
        error_exit "Username is required"
    fi
    
    log_command_call "set-samba-password" "$original_params"
    
    # Call the core function
    set_samba_password_core "$username" "$password"
    
    return 0
}

# Core function to set Samba password
set_samba_password_core() {
    local username="$1"
    local password="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "smbpasswd" "manage Samba users" "Samba tools not available"
    
    # Check if user exists in Samba
    if ! sudo pdbedit -L 2>/dev/null | grep -q "^$username:"; then
        error_exit "Samba user '$username' does not exist. Use add-samba-user command first."
    fi
    
    log INFO "Setting Samba password for user '$username'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        if [[ -n "$password" ]]; then
            log INFO "[DRY RUN] Would set password from command line parameter"
        else
            log INFO "[DRY RUN] Would prompt for password interactively"
        fi
        return 0
    fi
    
    # Set password
    if [[ -n "$password" ]]; then
        # Use provided password
        log INFO "Setting Samba password for user '$username' from parameter"
        local cmd="printf '%s\\n%s\\n' \"$password\" \"$password\" | sudo smbpasswd -s \"$username\" >/dev/null 2>&1"
        execute_or_dryrun "$cmd" "Successfully updated Samba password for '$username'" "Failed to update Samba password for '$username'" || error_exit "Failed to update Samba password for '$username'"
    else
        # Interactive password prompt
        log INFO "Setting Samba password for user '$username' (interactive prompt)"
        local cmd="sudo smbpasswd \"$username\""
        execute_or_dryrun "$cmd" "Successfully updated Samba password for '$username'" "Failed to update Samba password for '$username'" || error_exit "Failed to update Samba password for '$username'"
    fi
    
    return 0
}