
# Input validation library will be loaded by the main script's setup lib loader

# Function to validate shell selection
validate_shell() {
    local shell_path="$1"
    
    # Common valid shells
    local valid_shells=(
        "/bin/bash"
        "/bin/sh" 
        "/bin/dash"
        "/bin/zsh"
        "/bin/fish"
        "/bin/tcsh"
        "/bin/csh"
        "/bin/ksh"
        "/sbin/nologin"
        "/bin/false"
        "/usr/sbin/nologin"
    )
    
    # Check if shell is in valid list
    for valid_shell in "${valid_shells[@]}"; do
        if [[ "$shell_path" == "$valid_shell" ]]; then
            return 0
        fi
    done
    
    # Check if shell exists as executable file
    if [[ -x "$shell_path" ]]; then
        return 0
    fi
    
    return 1
}

# Command-specific help functions
show_help_add_user() {
    cat << EOF
Usage: $SCRIPT_NAME add-user --user <username> (--local | --domain [DOMAIN]) [options]

Create a new user account (local or domain).

Required Parameters:
  --user <username>     Username for the account
  --local              Create a local user account
  --domain [DOMAIN]    Setup domain user (optional: specify domain)

Local User Options:
  --group <group>       Primary group for the user
  --groups <g1,g2,...>  Additional groups (comma-separated)
  --home <path>         Home directory path
  --shell <shell>       Login shell (default: /bin/bash)
  --no-login            Set shell to /sbin/nologin (no interactive login)
  --comment <text>      GECOS field/user description
  --uid <number>        Specific user ID
  --no-create-home      Don't create home directory
  --system              Create system account (UID < 1000)
  --password <pass>     Set password (use with caution)

Domain User Options:
  --domain-method <method>  Integration method: winbind, sssd, or auto (default: auto)
  --groups <g1,g2,...>     Additional local groups
  --home <path>            Custom home directory path
  --shell <shell>          Login shell (default: /bin/bash)
  --no-login               Set shell to /sbin/nologin (no interactive login)
  --no-create-home         Don't create home directory (useful for service accounts)

Common Options:
  --dry-run             Show what would be done without making changes

Domain User Requirements:
  - Username must be plain username only (no DOMAIN\\ or @domain)
  - Domain is auto-detected from machine or specified with --domain flag  
  - User must already exist in the domain before local setup

Examples:
  # Local user
  $SCRIPT_NAME add-user --local --user john --group users --groups sudo,docker
  
  # Local service account (no login)
  $SCRIPT_NAME add-user --local --user svc-app --no-login --no-create-home --groups app
  
  # Domain user with auto-detected domain
  $SCRIPT_NAME add-user --domain --user jsmith --groups sudo
  
  # Domain user with explicit domain
  $SCRIPT_NAME add-user --domain CORP --user jsmith --groups docker
  
  # Domain service account (no home directory)
  $SCRIPT_NAME add-user --domain --user svc-backup --no-create-home --groups backup-ops
  
  # Domain service account (no login or home)
  $SCRIPT_NAME add-user --domain --user svc-monitor --no-login --no-create-home --groups monitoring
EOF
}

cmd_add_user() {
    local username=""
    local is_local=false
    local is_domain=false
    local domain_name=""
    local domain_method="auto"
    local primary_group=""
    local additional_groups=""
    local home_dir=""
    local shell="/bin/bash"
    local comment=""
    local uid=""
    local no_create_home=false
    local system_account=false
    local password=""
    local no_login=false
    local shell_explicitly_set=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_user "$1" "${2:-}" "show_help_add_user")
                shift 2
                ;;
            --local)
                is_local=true
                shift
                ;;
            --domain)
                is_domain=true
                # Check for optional domain value
                if [[ -n "${2:-}" ]] && ! [[ "${2:-}" =~ ^-- ]]; then
                    domain_name="$2"
                    shift 2
                else
                    # Domain flag without value - will auto-detect
                    shift
                fi
                ;;
            --domain-method)
                domain_method=$(validate_parameter_value "$1" "${2:-}" "Domain method required after --domain-method" "show_help_add_user")
                if [[ "$domain_method" != "winbind" && "$domain_method" != "sssd" && "$domain_method" != "auto" ]]; then
                    show_help_add_user
                    error_exit "Invalid domain method: $domain_method. Must be 'winbind', 'sssd', or 'auto'"
                fi
                shift 2
                ;;
            --group)
                primary_group=$(validate_parameter_group "$1" "${2:-}" "show_help_add_user")
                shift 2
                ;;
            --groups)
                additional_groups=$(validate_parameter_group_list "$1" "${2:-}" "show_help_add_user")
                shift 2
                ;;
            --home)
                home_dir=$(validate_parameter_path "$1" "${2:-}" "show_help_add_user")
                shift 2
                ;;
            --shell)
                shell=$(validate_parameter_shell "$1" "${2:-}" "show_help_add_user")
                shell_explicitly_set=true
                shift 2
                ;;
            --comment)
                comment=$(validate_parameter_comment "$1" "${2:-}" "show_help_add_user")
                shift 2
                ;;
            --uid)
                uid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_add_user")
                shift 2
                ;;
            --no-create-home)
                no_create_home=true
                shift
                ;;
            --no-login)
                shell="/sbin/nologin"
                no_login=true
                shift
                ;;
            --system)
                system_account=true
                shift
                ;;
            --password)
                password=$(validate_parameter_password "$1" "${2:-}" "show_help_add_user")
                shift 2
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
                show_help_add_user
                return 0
                ;;
            *)
                show_help_add_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_add_user
        error_exit "Username is required"
    fi
    
    if [[ "$is_local" == "false" && "$is_domain" == "false" ]]; then
        show_help_add_user
        error_exit "Must specify either --local or --domain"
    fi
    
    if [[ "$is_local" == "true" && "$is_domain" == "true" ]]; then
        show_help_add_user
        error_exit "Cannot specify both --local and --domain"
    fi
    
    # Validate shell/no-login conflict
    if [[ "$shell_explicitly_set" == "true" && "$no_login" == "true" ]]; then
        show_help_add_user
        error_exit "Cannot specify both --shell and --no-login flags"
    fi
    
    # Validate shell choice
    if ! validate_shell "$shell"; then
        show_help_add_user
        error_exit "Invalid shell: $shell. Shell must be a valid executable or one of the common shells"
    fi
    
    # Branch based on user type
    if [[ "$is_local" == "true" ]]; then
        _create_local_user "$username" "$primary_group" "$additional_groups" \
                          "$home_dir" "$shell" "$comment" "$uid" \
                          "$no_create_home" "$system_account" "$password"
    else
        _setup_domain_user_locally "$username" "$domain_name" "$domain_method" \
                                  "$home_dir" "$shell" "$additional_groups" "$no_create_home"
    fi
}



# Helper function for local user creation (existing logic)
_create_local_user() {
    local username="$1"
    local primary_group="$2"
    local additional_groups="$3"
    local home_dir="$4"
    local shell="$5"
    local comment="$6"
    local uid="$7"
    local no_create_home="$8"
    local system_account="$9"
    local password="${10}"
    
    # Note: Input validation is already performed during parameter parsing using:
    # - validate_parameter_user() for username
    # - validate_parameter_group() for primary group  
    # - validate_parameter_group_list() for additional groups (validates each group individually)
    # - validate_parameter_path() for home directory
    # - validate_parameter_shell() for shell
    # - validate_parameter_comment() for comment
    # - validate_parameter_numeric() for UID
    # - validate_parameter_password() for password
    
    check_tool_permission_or_error_exit "useradd" "create users" "useradd not available - cannot create users"
    
    # Check if user already exists
    if user_exists_in_passwd "$username"; then
        error_exit "User '$username' already exists"
    fi
    
    # Build useradd command using utility functions with long-form flags for readability
    local useradd_cmd="useradd"
    
    # Add sudo prefix if running as non-root
    useradd_cmd=$(prefix_if "! check_active_user_is_root" "$useradd_cmd" "sudo ")
    
    # --system: Create system account (UID < 1000)
    useradd_cmd=$(append_if_true "$system_account" "$useradd_cmd" " --system")
    
    # --uid: Specify user ID
    useradd_cmd=$(append_if_set "$uid" "$useradd_cmd" " --uid '$uid'")
    
    # --gid: Set primary group
    useradd_cmd=$(append_if_set "$primary_group" "$useradd_cmd" " --gid '$primary_group'")
    
    # --groups: Add to supplementary groups
    useradd_cmd=$(append_if_set "$additional_groups" "$useradd_cmd" " --groups '$additional_groups'")
    
    # --home-dir: Set home directory path
    useradd_cmd=$(append_if_set "$home_dir" "$useradd_cmd" " --home-dir '$home_dir'")
    
    # --no-create-home: Don't create home directory if requested
    useradd_cmd=$(append_if_true "$no_create_home" "$useradd_cmd" " --no-create-home")
    
    # --create-home: Create home directory (default behavior unless --no-create-home specified)
    useradd_cmd=$(append_if_false "$no_create_home" "$useradd_cmd" " --create-home")
    
    # --shell: Set login shell
    useradd_cmd=$(append_if_set "$shell" "$useradd_cmd" " --shell '$shell'")
    
    # --comment: Set GECOS field/user description
    useradd_cmd=$(append_if_set "$comment" "$useradd_cmd" " --comment \"$comment\"")
    
    # Add username as final argument (quoted for security)
    useradd_cmd="$useradd_cmd '$username'"
    
    # Execute useradd
    execute_or_dryrun "$useradd_cmd" \
                     "User '$username' created successfully" \
                     "Failed to create user '$username'" \
                     "Create new system user account for Shuttle file operations" \
                     || error_exit "Failed to create user '$username'"
    
    # Set password if provided
    if [[ -n "$password" ]]; then
        log INFO "Setting password for user '$username'..."
        # Use printf to safely handle passwords with special characters
        local passwd_cmd="printf '%s:%s\\n' '$username' '$password' | chpasswd"
        if ! check_active_user_is_root; then
            passwd_cmd="printf '%s:%s\\n' '$username' '$password' | sudo chpasswd"
        fi
        execute_or_dryrun "$passwd_cmd" \
                         "Password set for user '$username'" \
                         "Failed to set password for user '$username'" \
                         "Set initial password for user authentication" \
                         || log WARN "Failed to set password for user '$username'"
    fi
    
    return 0
}


# Helper function to set up local resources for existing domain users
# This does NOT create domain users - it only sets up local resources (home dir, groups, etc)
# for domain users that already exist in the domain
_setup_domain_user_locally() {
    local username="$1"
    local domain_param="$2"     # Domain from --domain flag (or empty)
    local domain_method="$3"
    local home_dir="$4"
    local shell="$5"
    local additional_groups="$6"
    local no_create_home="${7:-false}"
    
    # Validate username contains no domain markers
    if [[ "$username" =~ [@\\] ]]; then
        error_exit "Username must not contain domain. Use plain username with --domain flag if needed"
    fi
    
    # Detect machine domain
    detect_machine_domain
    local machine_domain="$DETECTED_DOMAIN"
    
    # Determine which domain to use
    local domain=""
    if [[ -n "$domain_param" ]]; then
        # Domain explicitly provided
        if [[ -n "$machine_domain" && "$domain_param" != "$machine_domain" ]]; then
            error_exit "Specified domain '$domain_param' does not match machine domain '$machine_domain'"
        fi
        domain="$domain_param"
    elif [[ -n "$machine_domain" ]]; then
        # Use detected domain
        domain="$machine_domain"
        log INFO "Using detected domain: $domain"
    else
        error_exit "Machine not domain-joined. Specify domain with --domain flag"
    fi
    
    log INFO "Setting up local resources for domain user: $username from domain: $domain, determining domain using integration using method: $domain_method"
    
    # Auto-detect domain integration method if requested
    if [[ "$domain_method" == "auto" ]]; then
        log INFO "Auto-detecting domain integration method..."
        
        detect_domain_integration || true # don't exit on error
        domain_method="$DETECTED_INTEGRATION"


        
        if [[ "$domain_method" == "none" ]]; then
            log ERROR "No domain integration detected"
            error_exit "No domain integration detected. Install winbind or sssd"
        fi
        log INFO "Auto-detected domain integration method: $domain_method"
    fi
    
    # Check if domain user already has local resources
    if check_domain_user_exists_locally_in_passwd "$username" "$domain"; then
        error_exit "Domain user '$username' already has local resources set up"
    fi
    
    # Verify domain user exists in domain but not locally configured
    # This checks that the user exists in the domain directory (via NSS)
    # but hasn't been set up with local resources yet
    log INFO "Verifying domain user '$username' exists in domain '$domain'"
    
    local user_found_in_domain=false
    local domain_user=""
    
    case "$domain_method" in
        "winbind")
            # Try winbind format first, then fall back to passwd check
            local winbind_format="${domain}\\${username}"
            if verify_domain_user_winbind "$winbind_format"; then
                user_found_in_domain=true
                domain_user="$winbind_format"
            elif check_domain_user_exists_locally_in_passwd "$username" "$domain"; then
                user_found_in_domain=true
                domain_user="$DETECTED_DOMAIN_USER_FORMAT"
                log DEBUG "Found domain user via getent: $domain_user"
            fi
            ;;
        "sssd")
            # For SSSD, use format checking logic to find the correct format
            # This verifies the user exists in the domain and is accessible via getent
            if check_domain_user_exists_locally_in_passwd "$username" "$domain"; then
                user_found_in_domain=true
                domain_user="$DETECTED_DOMAIN_USER_FORMAT"  # Use the format that worked
                log DEBUG "Found domain user via getent: $domain_user"
            else
                log DEBUG "Domain user not found via getent for any format"
            fi
            ;;
    esac
    
    if [[ "$user_found_in_domain" != "true" ]]; then
        error_exit "Domain user '$username' not found in domain '$domain'"
    fi
    
    log INFO "Domain user '$domain_user' found in domain"

    # Check for ANY existing local resources for this domain user
    log INFO "Checking for any existing local resources for domain user '$domain_user'..."
    
    if check_user_all_local_resources "$username" "$domain_user" "$home_dir"; then
        log ERROR "Domain user '$username' already has local resources configured:"
        for issue in "${DETECTED_USER_RESOURCES[@]}"; do
            log ERROR "  - $issue"
        done
        log ERROR ""
        log ERROR "To proceed, first clean up existing resources:"
        log ERROR "  1. Remove home directories: rm -rf /home/$username"
        if [[ -n "$home_dir" && "$home_dir" != "/home/$username" ]]; then
            log ERROR "     Remove custom home: rm -rf '$home_dir'"
        fi
        log ERROR "  2. Remove from all groups: Check 'groups $domain_user' and use 'gpasswd -d $domain_user <group>'"
        log ERROR "  3. Check file ownership: find / -user '$domain_user' 2>/dev/null"
        log ERROR ""
        error_exit "Cannot setup domain user '$username' - existing local resources must be removed first"
    fi
    
    log INFO "No existing local resources found - safe to proceed with setup"
    
    # Handle home directory creation (unless --no-create-home specified)
    if [[ "$no_create_home" == "true" ]]; then
        log INFO "Skipping home directory creation for service account '$username'"
    else
        modify_user_home_directory "$username" "$domain_user" "$home_dir" || error_exit "Failed to create home directory"
    fi
    
    # Add user to additional groups if specified
    if [[ -n "$additional_groups" ]]; then
        log INFO "Adding user '$domain_user' to groups: $additional_groups"
        # Convert comma-separated list to array
        IFS=',' read -ra group_array <<< "$additional_groups"
        for group in "${group_array[@]}"; do
            group=$(echo "$group" | xargs)  # Trim whitespace
            add_user_to_group_core "$username" "$domain_user" "$group" || log WARN "Failed to add user to group '$group'"
        done
    fi
    
    log INFO "Domain user '$domain_user' setup completed successfully"
    return 0
}