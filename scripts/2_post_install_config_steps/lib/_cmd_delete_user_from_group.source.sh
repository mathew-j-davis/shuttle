# Command-specific help functions
show_help_delete_user_from_group() {
    cat << EOF
Usage: $SCRIPT_NAME delete-user-from-group --user <username> --group <groupname> [options]

Remove a user from a group.

Required Parameters:
  --user <username>     Username to remove from group
  --group <groupname>   Group to remove the user from

Optional Parameters:
  --domain              User is a domain user (auto-detects domain)
  --dry-run             Show what would be done without making changes

Notes:
  - User must currently be a member of the group
  - Cannot remove user from their primary group

Examples:
  # Remove local user from group
  $SCRIPT_NAME delete-user-from-group --user john --group developers
  
  # Remove domain user from group
  $SCRIPT_NAME delete-user-from-group --user jsmith --group sudo --domain
EOF
}

cmd_delete_user_from_group() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local username=""
    local groupname=""
    local is_domain=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_value "$1" "${2:-}" "Username required after --user" "show_help_delete_user_from_group")
                shift 2
                ;;
            --group)
                groupname=$(validate_parameter_value "$1" "${2:-}" "Group name required after --group" "show_help_delete_user_from_group")
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
            --help|-h)
                show_help_delete_user_from_group
                return 0
                ;;
            *)
                show_help_delete_user_from_group
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_delete_user_from_group
        error_exit "Username is required"
    fi
    
    if [[ -z "$groupname" ]]; then
        show_help_delete_user_from_group
        error_exit "Group name is required"
    fi
    
    echo "delete-user-from-group command called with parameters: $original_params"
    
    # Check tool availability
    check_tool_permission_or_error_exit "gpasswd" "modify group membership" "gpasswd not available - cannot remove users from groups"
    
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
    remove_user_from_group_core "$username" "$domain_user" "$groupname" || error_exit "Failed to remove user from group"
    
    return 0
}