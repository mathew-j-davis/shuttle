# Command-specific help functions
show_help_remove_samba_user() {
    cat << EOF
Usage: $SCRIPT_NAME remove-samba-user --user <username> [options]

Remove a user from Samba user database.

Required Parameters:
  --user <username>     Username to remove from Samba

Optional Parameters:
  --force               Remove without confirmation prompt
  --dry-run             Show what would be done without making changes

Examples:
  # Remove user with confirmation
  $SCRIPT_NAME remove-samba-user --user alice
  
  # Remove user without confirmation
  $SCRIPT_NAME remove-samba-user --user bob --force

Notes:
  - User is removed from Samba database only
  - System user account is not affected
  - User will no longer be able to access Samba shares
  - Use list-samba-users to see current Samba users
  - User can be re-added later with add-samba-user command
EOF
}

cmd_remove_samba_user() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local username=""
    local force=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_value "$1" "${2:-}" "Username required after --user" "show_help_remove_samba_user")
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
                show_help_remove_samba_user
                return 0
                ;;
            *)
                show_help_remove_samba_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_remove_samba_user
        error_exit "Username is required"
    fi
    
    echo "remove-samba-user command called with parameters: $original_params"
    
    # Call the core function
    remove_samba_user_core "$username" "$force"
    
    return 0
}

# Core function to remove Samba user
remove_samba_user_core() {
    local username="$1"
    local force="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "smbpasswd" "manage Samba users" "Samba tools not available"
    
    # Check if user exists in Samba
    if ! sudo pdbedit -L 2>/dev/null | grep -q "^$username:"; then
        error_exit "Samba user '$username' does not exist"
    fi
    
    # Confirmation prompt (unless force or dry-run)
    if [[ "$force" != "true" && "$DRY_RUN" != "true" ]]; then
        echo "Are you sure you want to remove Samba user '$username'? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log INFO "Samba user removal cancelled by user"
            return 0
        fi
    fi
    
    log INFO "Removing Samba user '$username'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would remove Samba user '$username' from database"
        log INFO "[DRY RUN] System user account would remain untouched"
        return 0
    fi
    
    # Remove user from Samba
    if sudo smbpasswd -x "$username" >/dev/null 2>&1; then
        log INFO "Successfully removed Samba user '$username'"
    else
        error_exit "Failed to remove Samba user '$username'"
    fi
    
    # Verify user was removed
    if sudo pdbedit -L 2>/dev/null | grep -q "^$username:"; then
        error_exit "User '$username' still exists in Samba database after removal"
    fi
    
    log INFO "User '$username' no longer has Samba access"
    log INFO "Note: System user account was not affected"
    
    return 0
}