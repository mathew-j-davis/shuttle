# Source input validation library for security
SCRIPT_DIR_FOR_VALIDATION="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")}")"
if [[ -f "$SCRIPT_DIR_FOR_VALIDATION/_input_validation.source.sh" ]]; then
    source "$SCRIPT_DIR_FOR_VALIDATION/_input_validation.source.sh"
fi

# Command-specific help functions
show_help_modify_user() {
    cat << EOF
Usage: $SCRIPT_NAME modify-user --user <username> [options]

Modify an existing user account (local or domain).

Required Parameters:
  --user <username>     Username to modify

Optional Parameters:
  --domain              User is a domain user (auto-detects domain)
  --group <group>       Change primary group
  --add-groups <g1,g2>  Add to additional groups (comma-separated)
  --remove-groups <g1,g2> Remove from groups (comma-separated)
  --home <path>         Change home directory path
  --shell <shell>       Change login shell
  --no-login            Set shell to /sbin/nologin (no interactive login)
  --comment <text>      Change GECOS field/user description
  --uid <number>        Change user ID (use with caution)
  --lock                Lock user account (disable login)
  --unlock              Unlock user account (enable login)
  --expire <date>       Set account expiration date (YYYY-MM-DD)
  --no-expire           Remove account expiration
  --dry-run             Show what would be done without making changes

Local User Options:
  --password <pass>     Change password (use with caution)

Domain User Options:
  --create-home         Create home directory if it doesn't exist
  --remove-home         Remove current home directory

Examples:
  # Change user's shell
  $SCRIPT_NAME modify-user --user john --shell /bin/zsh
  
  # Add user to additional groups
  $SCRIPT_NAME modify-user --user john --add-groups docker,sudo
  
  # Change home directory and move files
  $SCRIPT_NAME modify-user --user john --home /home/john_new
  
  # Lock user account
  $SCRIPT_NAME modify-user --user john --lock
  
  # Modify domain user - add to groups and create home
  $SCRIPT_NAME modify-user --user jsmith --domain --add-groups developers --create-home
  
  # Remove user from groups
  $SCRIPT_NAME modify-user --user john --remove-groups old-project,temp-access

Notes:
  - For local users: Uses usermod command
  - For domain users: Modifies local resources only (groups, home directory, etc.)
  - Domain users remain in the domain unchanged
  - Home directory changes will move existing files unless user is domain user
  - UID changes can break file ownership - use with caution
  - Shell validation ensures only valid shells are set
EOF
}

cmd_modify_user() {
    
    local username=""
    local is_domain=false
    local primary_group=""
    local add_groups=""
    local remove_groups=""
    local home_dir=""
    local shell=""
    local comment=""
    local uid=""
    local lock_account=false
    local unlock_account=false
    local expire_date=""
    local no_expire=false
    local password=""
    local create_home=false
    local remove_home=false
    local no_login=false
    local shell_explicitly_set=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_user "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --domain)
                is_domain=true
                shift
                ;;
            --group)
                primary_group=$(validate_parameter_group "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --add-groups)
                add_groups=$(validate_parameter_group_list "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --remove-groups)
                remove_groups=$(validate_parameter_group_list "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --home)
                home_dir=$(validate_parameter_path "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --shell)
                shell=$(validate_parameter_shell "$1" "${2:-}" "show_help_modify_user")
                shell_explicitly_set=true
                shift 2
                ;;
            --comment)
                comment=$(validate_parameter_comment "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --uid)
                uid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --lock)
                lock_account=true
                shift
                ;;
            --unlock)
                unlock_account=true
                shift
                ;;
            --expire)
                expire_date=$(validate_parameter_value "$1" "${2:-}" "Expiration date required after --expire (YYYY-MM-DD format)" "show_help_modify_user")
                shift 2
                ;;
            --no-expire)
                no_expire=true
                shift
                ;;
            --password)
                password=$(validate_parameter_password "$1" "${2:-}" "show_help_modify_user")
                shift 2
                ;;
            --create-home)
                create_home=true
                shift
                ;;
            --remove-home)
                remove_home=true
                shift
                ;;
            --no-login)
                shell="/sbin/nologin"
                no_login=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_modify_user
                return 0
                ;;
            *)
                show_help_modify_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_modify_user
        error_exit "Username is required"
    fi
    
    # Validate conflicting options
    if [[ "$shell_explicitly_set" == "true" && "$no_login" == "true" ]]; then
        show_help_modify_user
        error_exit "Cannot specify both --shell and --no-login flags"
    fi
    
    if [[ "$lock_account" == "true" && "$unlock_account" == "true" ]]; then
        show_help_modify_user
        error_exit "Cannot specify both --lock and --unlock"
    fi
    
    if [[ "$expire_date" != "" && "$no_expire" == "true" ]]; then
        show_help_modify_user
        error_exit "Cannot specify both --expire and --no-expire"
    fi
    
    if [[ "$create_home" == "true" && "$remove_home" == "true" ]]; then
        show_help_modify_user
        error_exit "Cannot specify both --create-home and --remove-home"
    fi
    
    # Note: Input validation is already performed during parameter parsing using:
    # - validate_parameter_user() for username
    # - validate_parameter_group() for primary group
    # - validate_parameter_group_list() for add/remove groups
    # - validate_parameter_path() for home directory
    # - validate_parameter_shell() for shell
    # - validate_parameter_comment() for comment
    # - validate_parameter_numeric() for UID
    # - validate_parameter_password() for password
    
    # Validate expiration date format if specified
    if [[ -n "$expire_date" ]] && ! [[ "$expire_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        show_help_modify_user
        error_exit "Invalid date format: $expire_date. Use YYYY-MM-DD format"
    fi
    
    
    # Branch based on user type
    if [[ "$is_domain" == "true" ]]; then
        _modify_domain_user_locally "$username" "$primary_group" "$add_groups" "$remove_groups" \
                                   "$home_dir" "$shell" "$comment" "$create_home" "$remove_home"
    else
        _modify_local_user "$username" "$primary_group" "$add_groups" "$remove_groups" \
                          "$home_dir" "$shell" "$comment" "$uid" "$lock_account" "$unlock_account" \
                          "$expire_date" "$no_expire" "$password"
    fi
}

# Helper function for local user modification
_modify_local_user() {
    local username="$1"
    local primary_group="$2"
    local add_groups="$3"
    local remove_groups="$4"
    local home_dir="$5"
    local shell="$6"
    local comment="$7"
    local uid="$8"
    local lock_account="$9"
    local unlock_account="${10}"
    local expire_date="${11}"
    local no_expire="${12}"
    local password="${13}"
    
    check_tool_permission_or_error_exit "usermod" "modify users" "usermod not available - cannot modify users"
    
    # Check if user exists
    if ! user_exists_in_passwd "$username"; then
        error_exit "User '$username' does not exist"
    fi
    
    log INFO "Modifying local user: $username"
    
    # Handle group removals first
    if [[ -n "$remove_groups" ]]; then
        log INFO "Removing user '$username' from groups: $remove_groups"
        IFS=',' read -ra remove_group_array <<< "$remove_groups"
        for group in "${remove_group_array[@]}"; do
            group=$(echo "$group" | xargs)  # Trim whitespace
            remove_user_from_group_core "$username" "" "$group" || log WARN "Failed to remove user from group '$group'"
        done
    fi
    
    # Build usermod command for main modifications
    local usermod_cmd="usermod"
    local has_modifications=false
    
    # Add sudo prefix if running as non-root
    if ! check_active_user_is_root; then
        usermod_cmd="sudo $usermod_cmd"
    fi
    
    # --uid: Change user ID
    if [[ -n "$uid" ]]; then
        usermod_cmd="$usermod_cmd --uid $uid"
        has_modifications=true
        log WARN "Changing UID can break file ownership. Consider running: find / -user $username -exec chown $uid {} \\; after this command"
    fi
    
    # --gid: Change primary group
    if [[ -n "$primary_group" ]]; then
        usermod_cmd="$usermod_cmd --gid $primary_group"
        has_modifications=true
    fi
    
    # --home: Change home directory
    if [[ -n "$home_dir" ]]; then
        usermod_cmd="$usermod_cmd --home $home_dir --move-home"
        has_modifications=true
    fi
    
    # --shell: Change login shell
    if [[ -n "$shell" ]]; then
        usermod_cmd="$usermod_cmd --shell $shell"
        has_modifications=true
    fi
    
    # --comment: Change GECOS field
    if [[ -n "$comment" ]]; then
        usermod_cmd="$usermod_cmd --comment \"$comment\""
        has_modifications=true
    fi
    
    # --lock: Lock account
    if [[ "$lock_account" == "true" ]]; then
        usermod_cmd="$usermod_cmd --lock"
        has_modifications=true
    fi
    
    # --unlock: Unlock account
    if [[ "$unlock_account" == "true" ]]; then
        usermod_cmd="$usermod_cmd --unlock"
        has_modifications=true
    fi
    
    # --expiredate: Set expiration date
    if [[ -n "$expire_date" ]]; then
        usermod_cmd="$usermod_cmd --expiredate $expire_date"
        has_modifications=true
    elif [[ "$no_expire" == "true" ]]; then
        usermod_cmd="$usermod_cmd --expiredate ''"
        has_modifications=true
    fi
    
    # Add username as final argument
    usermod_cmd="$usermod_cmd $username"
    
    # Execute usermod if there are modifications
    if [[ "$has_modifications" == "true" ]]; then
        execute_or_dryrun "$usermod_cmd" "User '$username' modified successfully" "Failed to modify user '$username'" || error_exit "Failed to modify user '$username'"
    fi
    
    # Handle group additions
    if [[ -n "$add_groups" ]]; then
        log INFO "Adding user '$username' to groups: $add_groups"
        IFS=',' read -ra add_group_array <<< "$add_groups"
        for group in "${add_group_array[@]}"; do
            group=$(echo "$group" | xargs)  # Trim whitespace
            add_user_to_group_core "$username" "" "$group" || log WARN "Failed to add user to group '$group'"
        done
    fi
    
    # Set password if provided
    if [[ -n "$password" ]]; then
        log INFO "Setting password for user '$username'..."
        local passwd_cmd="echo '$username:$password' | chpasswd"
        if ! check_active_user_is_root; then
            passwd_cmd="echo '$username:$password' | sudo chpasswd"
        fi
        execute_or_dryrun "$passwd_cmd" "Password set for user '$username'" "Failed to set password for user '$username'" || log WARN "Failed to set password for user '$username'"
    fi
    
    log INFO "Local user '$username' modification completed"
    return 0
}

# Helper function for domain user local resource modification
_modify_domain_user_locally() {
    local username="$1"
    local primary_group="$2"
    local add_groups="$3"
    local remove_groups="$4"
    local home_dir="$5"
    local shell="$6"
    local comment="$7"
    local create_home="$8"
    local remove_home="$9"
    
    # Validate username contains no domain markers
    if [[ "$username" =~ [@\\] ]]; then
        error_exit "Username must not contain domain. Use plain username with --domain flag"
    fi
    
    # Detect domain and find domain user format
    detect_machine_domain || error_exit "Could not detect domain membership"
    local domain="$DETECTED_DOMAIN"
    
    # Check if domain user has local resources
    if ! check_domain_user_exists_locally_in_passwd "$username" "$domain"; then
        error_exit "Domain user '$username' has no local resources set up. Use add-user --domain first"
    fi
    
    local domain_user="$DETECTED_DOMAIN_USER_FORMAT"
    log INFO "Modifying local resources for domain user: $domain_user"
    
    # Handle group removals first
    if [[ -n "$remove_groups" ]]; then
        log INFO "Removing domain user '$domain_user' from groups: $remove_groups"
        IFS=',' read -ra remove_group_array <<< "$remove_groups"
        for group in "${remove_group_array[@]}"; do
            group=$(echo "$group" | xargs)  # Trim whitespace
            remove_user_from_group_core "$username" "$domain_user" "$group" || log WARN "Failed to remove user from group '$group'"
        done
    fi
    
    # Handle home directory operations
    if [[ "$remove_home" == "true" ]]; then
        # Get current home directory
        local current_home=""
        if user_info=$(getent passwd "$domain_user" 2>/dev/null); then
            current_home=$(echo "$user_info" | cut -d: -f6)
            if [[ -d "$current_home" ]]; then
                log INFO "Removing home directory: $current_home"
                local rm_home_cmd="rm -rf '$current_home'"
                if ! check_active_user_is_root; then
                    rm_home_cmd="sudo $rm_home_cmd"
                fi
                execute_or_dryrun "$rm_home_cmd" "Removed home directory '$current_home'" "Failed to remove home directory '$current_home'" || log WARN "Home directory removal failed"
            fi
        fi
    elif [[ "$create_home" == "true" ]] || [[ -n "$home_dir" ]]; then
        # Create or modify home directory
        modify_user_home_directory "$username" "$domain_user" "$home_dir" || log WARN "Failed to modify home directory"
    fi
    
    # Note: We can't modify shell, comment, or primary group for domain users through local tools
    # These are managed by the domain controller
    if [[ -n "$shell" ]] || [[ -n "$comment" ]] || [[ -n "$primary_group" ]]; then
        log WARN "Shell, comment, and primary group changes are not supported for domain users"
        log WARN "These attributes are managed by the domain controller"
    fi
    
    # Handle group additions
    if [[ -n "$add_groups" ]]; then
        log INFO "Adding domain user '$domain_user' to groups: $add_groups"
        IFS=',' read -ra add_group_array <<< "$add_groups"
        for group in "${add_group_array[@]}"; do
            group=$(echo "$group" | xargs)  # Trim whitespace
            add_user_to_group_core "$username" "$domain_user" "$group" || log WARN "Failed to add user to group '$group'"
        done
    fi
    
    log INFO "Domain user '$username' local resource modification completed"
    return 0
}