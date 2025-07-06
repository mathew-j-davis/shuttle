#!/bin/bash

# Domain User Import Command
# Configurable command for importing domain users into local passwd
# Supports workplace-specific import tools via configuration

# Show usage for import-domain-user command
show_import_domain_user_usage() {
    cat << EOF
Usage: $SCRIPT_NAME import-domain-user [OPTIONS]

Import a domain user into local passwd using configured workplace-specific tool.

OPTIONS:
  --username USERNAME      Domain username to import (required)
  --uid UID               Specific UID to assign (optional, domain is source of truth)
  --home HOME_DIR         Home directory path (optional, uses configured default)
  --shell SHELL           Login shell (optional, uses configured default)
  --primary-group GROUP   Primary group for user (optional)
  --groups GROUPS         Additional secondary groups (comma-separated, optional)
  --custom-args ARGS      Additional arguments to pass to import command
  --command-config FILE   Path to domain import config file
  --command CMD           Override import command
  --args-template TEMPLATE Override command arguments template
  --force                 Force import even if user exists
  --dry-run               Show what would be done without executing
  --verbose               Show detailed output
  --help                  Show this help message

EXAMPLES:
  # Import user with defaults
  $SCRIPT_NAME import-domain-user --username alice.domain
  
  # Import with specific settings
  $SCRIPT_NAME import-domain-user --username alice.domain --uid 70001 --home /home/corp/alice
  
  # Import with primary and secondary groups
  $SCRIPT_NAME import-domain-user --username bob.domain --primary-group "engineering" --groups "developers,sudo"
  
  # Import with custom arguments for workplace-specific options
  $SCRIPT_NAME import-domain-user --username charlie.domain --custom-args "--department IT --cost-center 1234"
  
  # Simple import (domain determines UID, uses defaults for everything else)
  $SCRIPT_NAME import-domain-user --username simple.user
  
  # Use specific config file
  $SCRIPT_NAME import-domain-user --username alice.domain --command-config /etc/shuttle/domain_import.conf
  
  # Override command and template on command line
  $SCRIPT_NAME import-domain-user --username alice.domain \\
    --command 'sudo /opt/corporate/bin/import-domain-user' \\
    --args-template '--username {username} --home {home} --shell {shell} --primary-group {primary_group}'

CONFIGURATION:
  This command requires configuration in shuttle_config.yaml:
  
  user_management:
    domain_user_import:
      enabled: true
      command: "/path/to/your/import-command"
      command_args_template: "--username {username} --home {home} --shell {shell}"
      default_shell: "/bin/bash"
      default_home_pattern: "/home/{username}"
      uid_range_start: 70000        # Optional - only used if UID generation needed
      uid_range_end: 99999          # Optional - only used if UID generation needed

TEMPLATE VARIABLES:
  {username}      - The username being imported
  {uid}           - The UID (if specified, empty if not provided)
  {home}          - The home directory path
  {shell}         - The login shell
  {primary_group} - The primary group (if specified, empty if not provided)
  {groups}        - Additional secondary groups (if specified, empty if not provided)

NOTES:
  • Requires configuration of workplace-specific import command
  • All parameters except username are optional
  • Domain is typically the source of truth for UID assignment
  • Uses configured defaults for home directory and shell when not specified
  • Supports custom arguments for workplace-specific requirements
  • Validates user doesn't already exist (unless --force used)
  • All operations support --dry-run mode
EOF
}

# Main function for importing domain users
cmd_import_domain_user() {
    local username=""
    local uid=""
    local home=""
    local shell=""
    local primary_group=""
    local groups=""
    local custom_args=""
    local force=false
    local command_config_file=""
    local override_command=""
    local override_args_template=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --username)
                username="$2"
                shift 2
                ;;
            --uid)
                uid="$2"
                shift 2
                ;;
            --home)
                home="$2"
                shift 2
                ;;
            --shell)
                shell="$2"
                shift 2
                ;;
            --primary-group)
                primary_group="$2"
                shift 2
                ;;
            --groups)
                groups="$2"
                shift 2
                ;;
            --custom-args)
                custom_args="$2"
                shift 2
                ;;
            --command-config)
                command_config_file="$2"
                shift 2
                ;;
            --command)
                override_command="$2"
                shift 2
                ;;
            --args-template)
                override_args_template="$2"
                shift 2
                ;;
            --force)
                force=true
                shift
                ;;
            --dry-run)
                # Already handled globally
                shift
                ;;
            --verbose)
                # Already handled globally
                shift
                ;;
            --help)
                show_import_domain_user_usage
                return 0
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
    
    # Validate required arguments
    if [[ -z "$username" ]]; then
        error_exit "Username is required. Use --username to specify."
    fi
    
    # Load configuration
    local import_enabled
    local import_command
    local args_template
    local default_shell
    local default_home_pattern
    local uid_range_start
    local uid_range_end
    
    # Priority 1: Command-line overrides
    if [[ -n "$override_command" ]]; then
        import_command="$override_command"
        args_template="${override_args_template:-"--username {username} --home {home} --shell {shell} --primary-group {primary_group}"}"
        default_shell="/bin/bash"
        default_home_pattern="/home/{username}"
        
        if [[ "$VERBOSE" == "true" ]]; then
            log INFO "Using command-line overrides:"
            log INFO "  Command: $import_command"
            log INFO "  Args template: $args_template"
        fi
    
    # Priority 2: Specific config file from command line
    elif [[ -n "$command_config_file" ]]; then
        if [[ ! -f "$command_config_file" ]]; then
            error_exit "Specified config file not found: $command_config_file"
        fi
        
        log INFO "Using specified config file: $command_config_file"
        if ! load_domain_config "$command_config_file"; then
            log WARN "Failed to load domain configuration from: $command_config_file"
            log INFO "Skipping domain user import for: $username"
            return 0
        fi
    
    # Priority 3: Auto-discover domain config files
    else
        local domain_config_file=""
        for config_path in "/etc/shuttle/domain_config.yaml" "$HOME/.config/shuttle/domain_config.yaml" "/etc/shuttle/domain_import.conf"; do
            if [[ -f "$config_path" ]]; then
                domain_config_file="$config_path"
                break
            fi
        done
        
        if [[ -n "$domain_config_file" ]]; then
            log INFO "Using domain config file: $domain_config_file"
            # Load domain-specific configuration
            if ! load_domain_config "$domain_config_file"; then
                log WARN "Failed to load domain configuration from: $domain_config_file"
                log INFO "Skipping domain user import for: $username"
                return 0
            fi
        else
            # Priority 4: Fallback to main shuttle config (for backward compatibility)
            import_enabled=$(get_config_value "user_management.domain_user_import.enabled" "false")
            if [[ "$import_enabled" != "true" ]]; then
                log WARN "Domain user import not configured"
                log INFO "Use --command-config FILE or --command CMD to specify import command"
                log INFO "Or create domain config file at /etc/shuttle/domain_config.yaml"
                log INFO "Or set user_management.domain_user_import.enabled=true in shuttle config"
                log INFO "Skipping domain user import for: $username"
                return 0
            fi
            
            # Get import command from main config
            import_command=$(get_config_value "user_management.domain_user_import.command" "")
            if [[ -z "$import_command" ]]; then
                log WARN "Domain user import command not configured"
                log INFO "Use --command-config FILE or --command CMD to specify import command"
                log INFO "Set user_management.domain_user_import.command in config or create domain config file"
                log INFO "Skipping domain user import for: $username"
                return 0
            fi
            
            # Get other values from main config
            args_template=$(get_config_value "user_management.domain_user_import.command_args_template" "--username {username} --home {home} --shell {shell}")
            default_shell=$(get_config_value "user_management.domain_user_import.default_shell" "/bin/bash")
            default_home_pattern=$(get_config_value "user_management.domain_user_import.default_home_pattern" "/home/{username}")
            uid_range_start=$(get_config_value "user_management.domain_user_import.uid_range_start" "")
            uid_range_end=$(get_config_value "user_management.domain_user_import.uid_range_end" "")
        fi
    fi
    
    # Check if import command exists
    if [[ ! -f "$import_command" ]] && ! command -v "$import_command" >/dev/null 2>&1; then
        error_exit "Import command not found: $import_command"
    fi
    
    # Check if command is executable
    if [[ ! -x "$import_command" ]] && ! command -v "$import_command" >/dev/null 2>&1; then
        error_exit "Import command is not executable: $import_command"
    fi
    
    # Configuration values are now loaded above based on priority
    
    # Apply defaults
    if [[ -z "$shell" ]]; then
        shell="$default_shell"
    fi
    
    if [[ -z "$home" ]]; then
        home="${default_home_pattern//\{username\}/$username}"
    fi
    
    # Generate UID if not provided and range is configured
    if [[ -z "$uid" ]] && [[ -n "$uid_range_start" ]] && [[ -n "$uid_range_end" ]]; then
        uid=$(generate_next_uid "$uid_range_start" "$uid_range_end")
        if [[ -z "$uid" ]]; then
            error_exit "Unable to generate UID in range $uid_range_start-$uid_range_end"
        fi
        
        if [[ "$VERBOSE" == "true" ]]; then
            log INFO "Generated UID: $uid"
        fi
    fi
    
    # Validate UID is in allowed range (only if range is configured and UID is provided)
    if [[ -n "$uid" ]] && [[ -n "$uid_range_start" ]] && [[ -n "$uid_range_end" ]]; then
        if [[ "$uid" -lt "$uid_range_start" ]] || [[ "$uid" -gt "$uid_range_end" ]]; then
            error_exit "UID $uid is outside allowed range $uid_range_start-$uid_range_end"
        fi
    fi
    
    # Check if user needs importing
    local import_needed=true
    local existing_status=""
    
    if id "$username" >/dev/null 2>&1; then
        # User exists in passwd
        existing_status="User $username exists in local passwd"
        
        if [[ "$force" == "false" ]]; then
            log INFO "$existing_status - skipping import (use --force to override)"
            import_needed=false
        else
            log WARN "$existing_status - but --force specified, will attempt import"
        fi
    else
        # User doesn't exist in passwd - import needed
        existing_status="User $username not found in local passwd - import needed"
        log INFO "$existing_status"
        
        # Note: Could add domain authentication check here in the future
        # if check_domain_user_authentication "$username"; then
        #     existing_status="User $username can authenticate but not in local passwd - import needed"
        # else
        #     existing_status="User $username not found in domain or local passwd - import needed"  
        # fi
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        log INFO "Import assessment: $existing_status"
    fi
    
    # Skip import if not needed and not forced
    if [[ "$import_needed" == "false" ]]; then
        log INFO "Import skipped for $username"
        return 0
    fi
    
    # Build final command arguments
    local final_args="$args_template"
    final_args="${final_args//\{username\}/$username}"
    final_args="${final_args//\{uid\}/$uid}"
    final_args="${final_args//\{home\}/$home}"
    final_args="${final_args//\{shell\}/$shell}"
    final_args="${final_args//\{primary_group\}/$primary_group}"
    final_args="${final_args//\{groups\}/$groups}"
    
    # Add custom arguments if provided
    if [[ -n "$custom_args" ]]; then
        final_args="$final_args $custom_args"
    fi
    
    # Log what we're about to do
    log INFO "Importing domain user: $username"
    if [[ "$VERBOSE" == "true" ]]; then
        if [[ -n "$uid" ]]; then
            log INFO "  UID: $uid"
        else
            log INFO "  UID: (determined by domain)"
        fi
        log INFO "  Home: $home"
        log INFO "  Shell: $shell"
        if [[ -n "$primary_group" ]]; then
            log INFO "  Primary group: $primary_group"
        fi
        if [[ -n "$groups" ]]; then
            log INFO "  Secondary groups: $groups"
        fi
        if [[ -n "$custom_args" ]]; then
            log INFO "  Custom args: $custom_args"
        fi
    fi
    
    # Execute the import command
    local full_command="$import_command $final_args"
    
    # Check if we need sudo (if not running as root and command doesn't already include sudo)
    if [[ $EUID -ne 0 ]] && [[ "$import_command" != *"sudo"* ]]; then
        full_command="sudo $full_command"
        if [[ "$VERBOSE" == "true" ]]; then
            log INFO "Adding sudo (not running as root): $full_command"
        fi
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        log INFO "Executing: $full_command"
    fi
    
    execute_or_execute_dryrun "$full_command"
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log INFO "Successfully imported domain user: $username"
        
        # Verify user was created (only if not dry run)
        if [[ "$DRY_RUN" == "false" ]]; then
            if id "$username" >/dev/null 2>&1; then
                log INFO "User $username confirmed in system"
                if [[ "$VERBOSE" == "true" ]]; then
                    log INFO "User details: $(id "$username")"
                fi
            else
                log WARN "User $username not found in system after import"
            fi
        fi
    else
        error_exit "Failed to import domain user: $username (exit code: $exit_code)"
    fi
}

# Helper function to generate next available UID in range
generate_next_uid() {
    local start_uid="$1"
    local end_uid="$2"
    
    # Get list of existing UIDs in range
    local existing_uids
    existing_uids=$(getent passwd | awk -F: "\$3 >= $start_uid && \$3 <= $end_uid {print \$3}" | sort -n)
    
    # Find first available UID
    local current_uid="$start_uid"
    for existing_uid in $existing_uids; do
        if [[ "$current_uid" -lt "$existing_uid" ]]; then
            echo "$current_uid"
            return 0
        fi
        current_uid=$((existing_uid + 1))
    done
    
    # If we get here, use current_uid if it's in range
    if [[ "$current_uid" -le "$end_uid" ]]; then
        echo "$current_uid"
        return 0
    fi
    
    # No available UID found
    return 1
}

# Load domain-specific configuration from separate config file
load_domain_config() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        return 1
    fi
    
    # Simple key=value parser for domain config
    # Supports both YAML-style and shell-style config
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        
        # Clean up key and value
        key=$(echo "$key" | tr -d '[:space:]' | sed 's/://g')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/^["'\'']*//;s/["'\'']*$//')
        
        case "$key" in
            "command"|"import_command")
                import_command="$value"
                ;;
            "args_template"|"command_args_template")
                args_template="$value"
                ;;
            "default_shell")
                default_shell="$value"
                ;;
            "default_home_pattern")
                default_home_pattern="$value"
                ;;
            "uid_range_start")
                uid_range_start="$value"
                ;;
            "uid_range_end")
                uid_range_end="$value"
                ;;
        esac
    done < "$config_file"
    
    # Check required fields
    if [[ -z "$import_command" ]]; then
        log ERROR "Domain config missing required 'command' field"
        return 1
    fi
    
    # Set defaults for optional fields
    [[ -z "$args_template" ]] && args_template="--username {username} --home {home} --shell {shell} --primary-group {primary_group}"
    [[ -z "$default_shell" ]] && default_shell="/bin/bash"
    [[ -z "$default_home_pattern" ]] && default_home_pattern="/home/{username}"
    
    if [[ "$VERBOSE" == "true" ]]; then
        log INFO "Domain config loaded:"
        log INFO "  Command: $import_command"
        log INFO "  Args template: $args_template"
        log INFO "  Default shell: $default_shell"
        log INFO "  Default home pattern: $default_home_pattern"
    fi
    
    return 0
}

# Helper function to check if a domain user can authenticate
# NOTE: Currently disabled - only passwd check is used for reliability
# Uncomment and test these methods when ready to implement domain checking
check_domain_user_authentication() {
    local username="$1"
    
    # For now, always return false - only passwd check is reliable
    # This means script will always attempt import for users not in passwd
    return 1
    
    # FUTURE IMPLEMENTATION OPTIONS (currently commented out):
    
    # Method 1: Check if user has Kerberos principal
    # if command -v kinit >/dev/null 2>&1; then
    #     # Try to get info about the user's principal (non-interactive)
    #     if klist -kt /etc/krb5.keytab 2>/dev/null | grep -q "$username" 2>/dev/null; then
    #         return 0
    #     fi
    # fi
    
    # Method 2: Check with domain-specific tools if available
    # if command -v wbinfo >/dev/null 2>&1; then
    #     if wbinfo -u 2>/dev/null | grep -q "^$username$" 2>/dev/null; then
    #         return 0
    #     fi
    # fi
    
    # Method 3: Check LDAP if configured
    # if command -v ldapsearch >/dev/null 2>&1 && [[ -f /etc/ldap/ldap.conf ]]; then
    #     # This would need to be configured for your specific environment
    #     # ldapsearch -x "(sAMAccountName=$username)" >/dev/null 2>&1 && return 0
    #     :
    # fi
    
    # Method 4: Use configured check command if available
    # local check_command
    # check_command=$(get_config_value "user_management.domain_user_import.commands.check" "")
    # if [[ -n "$check_command" ]]; then
    #     if [[ "$VERBOSE" == "true" ]]; then
    #         log INFO "Using configured check command: $check_command $username"
    #     fi
    #     if $check_command "$username" >/dev/null 2>&1; then
    #         return 0
    #     fi
    # fi
    
    # User not found or can't authenticate
    # return 1
}

# Export functions for use by other scripts
export -f cmd_import_domain_user
export -f show_import_domain_user_usage
export -f generate_next_uid
export -f check_domain_user_authentication
export -f load_domain_config