# Input validation library will be loaded by the main script's setup lib loader

# Command-specific help functions
show_help_add_user_to_group() {
    cat << EOF
Usage: $SCRIPT_NAME add-user-to-group --user <username> --group <groupname> [options]

Add a user to a group.

Required Parameters:
  --user <username>     Username to add to group
  --group <groupname>   Group to add the user to

Optional Parameters:
  --domain              User is a domain user (auto-detects domain)
  --dry-run             Show what would be done without making changes

Examples:
  # Add local user to group
  $SCRIPT_NAME add-user-to-group --user john --group developers
  
  # Add domain user to group
  $SCRIPT_NAME add-user-to-group --user jsmith --group sudo --domain
  
  # Add multiple users to a group
  for user in alice bob charlie; do
    $SCRIPT_NAME add-user-to-group --user \$user --group project-team
  done
EOF
}

cmd_add_user_to_group() {
    local username=""
    local groupname=""
    local is_domain=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_user "$1" "${2:-}" "show_help_add_user_to_group")
                shift 2
                ;;
            --group)
                groupname=$(validate_parameter_group "$1" "${2:-}" "show_help_add_user_to_group")
                shift 2
                ;;
            --domain)
                is_domain=true
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
                show_help_add_user_to_group
                return 0
                ;;
            *)
                show_help_add_user_to_group
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_add_user_to_group
        error_exit "Username is required"
    fi
    
    if [[ -z "$groupname" ]]; then
        show_help_add_user_to_group
        error_exit "Group name is required"
    fi
    
    # Note: Input validation is already performed during parameter parsing
    # using validate_parameter_user() and validate_parameter_group()
    
    # Check tool availability
    check_tool_permission_or_error_exit "gpasswd" "modify group membership" "gpasswd not available - cannot add users to groups"
    
    # For domain users, detect format
    local domain_user=""
    if [[ "$is_domain" == "true" ]]; then
        # Validate username contains no domain markers
        if [[ "$username" =~ [@\\] ]]; then
            error_exit "Username must not contain domain. Use plain username with --domain flag"
        fi
        
        # Detect domain and format
        detect_machine_domain || error_exit "Could not detect domain membership"
        local domain="$DETECTED_DOMAIN"
        
        # Check if domain user exists in passwd
        if check_domain_user_exists_locally_in_passwd "$username" "$domain"; then
            domain_user="$DETECTED_DOMAIN_USER_FORMAT"
            log INFO "Using domain user format: $domain_user"
        else
            error_exit "Domain user '$username' not found. Ensure domain user is set up locally first."
        fi
    else
        # For local users, check if user exists
        if ! user_exists_in_passwd "$username"; then
            error_exit "User '$username' does not exist"
        fi
    fi
    
    # Call the core function
    add_user_to_group_core "$username" "$domain_user" "$groupname" || error_exit "Failed to add user to group"
    
    return 0
}