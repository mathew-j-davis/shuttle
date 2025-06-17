# Input validation library will be loaded by the main script's setup lib loader

# Command-specific help functions
show_help_add_samba_user() {
    cat << EOF
Usage: $SCRIPT_NAME add-samba-user --user <username> [options]

Add a user to Samba and set their password.

Required Parameters:
  --user <username>     Username to add to Samba

Optional Parameters:
  --password <password> Set specific password (interactive prompt if not provided)
  --force               Add user even if already exists in Samba (reset password)
  --dry-run             Show what would be done without making changes

Examples:
  # Add user with interactive password prompt
  $SCRIPT_NAME add-samba-user --user alice
  
  # Add user with specified password
  $SCRIPT_NAME add-samba-user --user bob --password "secure123"
  
  # Force reset existing user password
  $SCRIPT_NAME add-samba-user --user charlie --password "newpass" --force

Security Notes:
  - User must already exist in system (use add-user first if needed)
  - Passwords specified on command line may be visible in process lists
  - Interactive password prompt is more secure
  - Use strong passwords for Samba access
  - Samba passwords are separate from system passwords

Notes:
  - Uses smbpasswd command to manage Samba user database
  - User will be enabled for Samba access after addition
  - Check existing users with list-samba-users command
EOF
}

cmd_add_samba_user() {
    local username=""
    local password=""
    local force=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_user "$1" "${2:-}" "show_help_add_samba_user")
                shift 2
                ;;
            --password)
                password=$(validate_parameter_password "$1" "${2:-}" "show_help_add_samba_user")
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
                show_help_add_samba_user
                return 0
                ;;
            *)
                show_help_add_samba_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_add_samba_user
        error_exit "Username is required"
    fi
    
    # Note: Input validation is already performed during parameter parsing
    # using validate_parameter_user() and validate_parameter_password()
    
    # Call the core function
    add_samba_user_core "$username" "$password" "$force"
    
    return 0
}

# Core function to add Samba user
add_samba_user_core() {
    local username="$1"
    local password="$2"
    local force="$3"
    
    # Check tool availability
    check_tool_permission_or_error_exit "smbpasswd" "manage Samba users" "Samba tools not available"
    
    # Check if user exists in system
    if ! getent passwd "$username" >/dev/null 2>&1; then
        error_exit "System user '$username' does not exist. Create the user first with add-user command."
    fi
    
    # Check if user already exists in Samba
    local user_exists=false
    local escaped_username
    escaped_username=$(sanitize_for_regex "$username")
    if sudo pdbedit -L 2>/dev/null | grep -q "^$escaped_username:"; then
        user_exists=true
        if [[ "$force" != "true" ]]; then
            error_exit "Samba user '$username' already exists. Use --force to reset password."
        fi
    fi
    
    log INFO "Adding user '$username' to Samba"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        if [[ "$user_exists" == "true" ]]; then
            log INFO "[DRY RUN] Would reset password for existing Samba user '$username'"
        else
            log INFO "[DRY RUN] Would add new Samba user '$username'"
        fi
        if [[ -n "$password" ]]; then
            log INFO "[DRY RUN] Would set password from command line parameter"
        else
            log INFO "[DRY RUN] Would prompt for password interactively"
        fi
        return 0
    fi
    
    # Add or update user in Samba
    if [[ -n "$password" ]]; then
        # Use provided password with secure handling (supports ALL characters)
        log INFO "Setting Samba password for user '$username' from parameter (secure method)"
        execute_smbpasswd_with_password "$username" "$password" "-a -s" \
            "Add user to Samba database with provided password using secure stdin method" || error_exit "Failed to set Samba password for '$username'"
    else
        # Interactive password prompt
        log INFO "Setting Samba password for user '$username' (interactive prompt)"
        local smbpasswd_interactive_cmd="sudo smbpasswd -a '$username'"
        execute_or_dryrun "$smbpasswd_interactive_cmd" "Successfully set Samba password for '$username'" "Failed to set Samba password for '$username'" \
                         "Add user to Samba database with interactive password prompt for administrator input" || error_exit "Failed to set Samba password for '$username'"
    fi
    
    # Ensure user is enabled
    local enable_cmd="sudo smbpasswd -e '$username' >/dev/null 2>&1"
    if ! execute_or_dryrun "$enable_cmd" "Enabled Samba user '$username'" "Failed to enable Samba user '$username'" \
                           "Enable Samba user account to allow authentication and file sharing access"; then
        log WARN "Failed to enable Samba user '$username' (may already be enabled)"
    fi
    
    # Verify user was added
    if sudo pdbedit -L 2>/dev/null | grep -q "^$username:"; then
        log INFO "Successfully added Samba user '$username'"
    else
        error_exit "User '$username' not found in Samba database after addition"
    fi
    
    return 0
}