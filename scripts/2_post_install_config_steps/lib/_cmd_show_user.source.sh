# Command-specific help functions
show_help_show_user() {
    cat << EOF
Usage: $SCRIPT_NAME show-user --user <username> [options]

Display detailed information about a user (local or domain).

Required Parameters:
  --user <username>     Username to show information for

Optional Parameters:
  --groups              Show group memberships
  --files               Show files owned by user (sample)
  --verbose             Show additional details
  --check-domain        Check if user exists in domain
  --dry-run             Show what would be done without making changes

Examples:
  # Show basic user information
  $SCRIPT_NAME show-user --user alice
  
  # Show user with group memberships
  $SCRIPT_NAME show-user --user bob --groups
  
  # Show comprehensive user information
  $SCRIPT_NAME show-user --user carol --groups --files --verbose
  
  # Check domain user existence
  $SCRIPT_NAME show-user --user "DOMAIN\\user" --check-domain

Information Displayed:
  - User ID (UID) and primary group
  - Home directory and shell
  - User type (system vs regular user)
  - Account status and login information
  - Group memberships (if --groups specified)
  - Owned files sample (if --files specified)
  - Domain status (if --check-domain specified)
  - Last login information (if available)

Notes:
  - Uses getent to query user information
  - Works with both local and domain users
  - System users typically have UID < 1000
  - Domain users may use different formats (DOMAIN\\user, user@domain, etc.)
EOF
}

cmd_show_user_info() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local username=""
    local show_groups=false
    local show_files=false
    local verbose=false
    local check_domain=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_value "$1" "${2:-}" "Username required after --user" "show_help_show_user")
                shift 2
                ;;
            --groups)
                show_groups=true
                shift
                ;;
            --files)
                show_files=true
                shift
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            --check-domain)
                check_domain=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_show_user
                return 0
                ;;
            *)
                show_help_show_user
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_show_user
        error_exit "Username is required"
    fi
    
    echo "show-user command called with parameters: $original_params"
    
    # Call the core function
    show_user_info_core "$username" "$show_groups" "$show_files" "$verbose" "$check_domain"
    
    return 0
}

# Core function to display user information
show_user_info_core() {
    local username="$1"
    local show_groups="$2"
    local show_files="$3"
    local verbose="$4"
    local check_domain="$5"
    
    # Check if user exists locally first
    local user_info=""
    local user_exists_locally=false
    
    if user_info=$(getent passwd "$username" 2>/dev/null); then
        user_exists_locally=true
    else
        echo ""
        echo "User '$username' not found in local passwd database"
        
        # If domain checking is requested, try to find domain user
        if [[ "$check_domain" == "true" ]]; then
            echo "Checking for domain user..."
            
            # Detect domain and try different formats
            if detect_machine_domain; then
                local domain="$DETECTED_DOMAIN"
                echo "Detected domain: $domain"
                
                # Try different domain user formats
                if check_domain_user_exists_locally_in_passwd "$username" "$domain"; then
                    local domain_format="$DETECTED_DOMAIN_USER_FORMAT"
                    echo "Found domain user with format: $domain_format"
                    if user_info=$(getent passwd "$domain_format" 2>/dev/null); then
                        user_exists_locally=true
                        username="$domain_format"  # Use the format that worked
                    fi
                fi
            fi
        fi
        
        if [[ "$user_exists_locally" == "false" ]]; then
            if [[ "$check_domain" == "true" ]]; then
                echo "User not found locally or in domain"
            else
                echo "Use --check-domain to search for domain users"
            fi
            return 1
        fi
    fi
    
    # Parse user information (format: username:password:uid:gid:gecos:home:shell)
    local user_name=$(echo "$user_info" | cut -d: -f1)
    local user_uid=$(echo "$user_info" | cut -d: -f3)
    local user_gid=$(echo "$user_info" | cut -d: -f4)
    local user_gecos=$(echo "$user_info" | cut -d: -f5)
    local user_home=$(echo "$user_info" | cut -d: -f6)
    local user_shell=$(echo "$user_info" | cut -d: -f7)
    
    # Get primary group name
    local primary_group=""
    if primary_group_info=$(getent group "$user_gid" 2>/dev/null); then
        primary_group=$(echo "$primary_group_info" | cut -d: -f1)
    else
        primary_group="$user_gid (group not found)"
    fi
    
    # Determine user type
    local user_type="Regular User"
    if [[ "$user_uid" -lt 1000 ]]; then
        user_type="System User"
    fi
    
    # Check if user is locked
    local account_status="Active"
    if getent shadow "$user_name" 2>/dev/null | cut -d: -f2 | grep -q "^!"; then
        account_status="Locked"
    elif getent shadow "$user_name" 2>/dev/null | cut -d: -f2 | grep -q "^\*"; then
        account_status="No Password"
    fi
    
    # Display basic user information
    echo ""
    echo "=== User Information ==="
    echo "Username:         $user_name"
    echo "User ID (UID):    $user_uid"
    echo "Primary Group:    $primary_group (GID: $user_gid)"
    echo "User Type:        $user_type"
    echo "Account Status:   $account_status"
    echo "Home Directory:   $user_home"
    echo "Login Shell:      $user_shell"
    
    if [[ -n "$user_gecos" ]]; then
        echo "Full Name/Info:   $user_gecos"
    fi
    
    # Check home directory status
    if [[ -d "$user_home" ]]; then
        local home_perms=$(stat -c "%a" "$user_home" 2>/dev/null)
        local home_owner=$(stat -c "%U" "$user_home" 2>/dev/null)
        echo "Home Dir Status:  Exists (permissions: $home_perms, owner: $home_owner)"
    else
        echo "Home Dir Status:  Does not exist"
    fi
    
    if [[ "$verbose" == "true" ]]; then
        echo ""
        echo "=== Detailed Information ==="
        
        # Show user entry
        echo "User Entry:       $user_info"
        
        # Check last login
        local last_login=""
        if command -v lastlog >/dev/null 2>&1; then
            last_login=$(lastlog -u "$user_name" 2>/dev/null | tail -1)
            if [[ "$last_login" =~ "Never logged in" ]]; then
                echo "Last Login:       Never"
            else
                echo "Last Login:       $last_login"
            fi
        fi
        
        # Check for sudo access
        if command -v sudo >/dev/null 2>&1; then
            if sudo -l -U "$user_name" >/dev/null 2>&1; then
                echo "Sudo Access:      Yes (user has sudo privileges)"
            else
                echo "Sudo Access:      No"
            fi
        fi
        
        # Check if user has any running processes
        local process_count=0
        if process_count=$(ps -u "$user_name" --no-headers 2>/dev/null | wc -l); then
            echo "Running Processes: $process_count"
        fi
        
        # Check password aging info if available
        if command -v chage >/dev/null 2>&1 && [[ "$user_uid" -ge 1000 ]]; then
            local chage_info=""
            if chage_info=$(sudo chage -l "$user_name" 2>/dev/null); then
                echo "Password Info:"
                echo "$chage_info" | head -5 | sed 's/^/                  /'
            fi
        fi
    fi
    
    if [[ "$show_groups" == "true" ]]; then
        echo ""
        echo "=== Group Memberships ==="
        
        # Get all groups for user
        local user_groups=""
        if user_groups=$(groups "$user_name" 2>/dev/null); then
            # Extract group names (groups command output: "username : group1 group2 group3")
            local group_list=$(echo "$user_groups" | cut -d: -f2 | xargs)
            
            if [[ -n "$group_list" ]]; then
                echo "Groups:           $group_list"
                echo ""
                echo "Group Details:"
                
                # Show details for each group
                for group in $group_list; do
                    if group_info=$(getent group "$group" 2>/dev/null); then
                        local group_gid=$(echo "$group_info" | cut -d: -f3)
                        local is_primary=""
                        if [[ "$group_gid" == "$user_gid" ]]; then
                            is_primary=" (PRIMARY)"
                        fi
                        echo "  - $group (GID: $group_gid)$is_primary"
                    else
                        echo "  - $group (GID: unknown)"
                    fi
                done
            else
                echo "Groups:           None found"
            fi
        else
            echo "Groups:           Could not determine group memberships"
        fi
    fi
    
    if [[ "$show_files" == "true" ]]; then
        echo ""
        echo "=== File Ownership ==="
        
        # Look for files owned by the user in common locations
        local owned_files=""
        echo "Searching for files owned by '$user_name' (this may take a moment)..."
        
        if owned_files=$(find /home /var /opt /usr/local -maxdepth 3 -user "$user_name" 2>/dev/null | head -10); then
            if [[ -n "$owned_files" ]]; then
                local file_count=$(echo "$owned_files" | wc -l)
                echo "Files Owned:      $file_count+ files found (showing first 10):"
                echo "$owned_files" | sed 's/^/                  /'
                
                # Count total files (this might be slow for users with many files)
                if [[ "$verbose" == "true" ]]; then
                    echo "                  Counting total files..."
                    local total_files=$(find /home /var /opt /usr/local -user "$user_name" 2>/dev/null | wc -l)
                    echo "                  Total files owned: $total_files"
                fi
            else
                echo "Files Owned:      No files found in common locations"
            fi
        else
            echo "Files Owned:      Could not search for owned files"
        fi
    fi
    
    if [[ "$check_domain" == "true" ]]; then
        echo ""
        echo "=== Domain Information ==="
        
        # Detect domain integration
        if detect_domain_integration; then
            echo "Domain Integration: $DETECTED_INTEGRATION"
            
            if detect_machine_domain; then
                echo "Machine Domain:     $DETECTED_DOMAIN"
                
                # Check if this is a domain user
                if [[ "$username" =~ \\ ]] || [[ "$username" =~ @ ]] || [[ "$username" =~ \+ ]]; then
                    echo "User Type:          Domain User"
                    
                    # Try to verify with domain tools
                    if [[ "$DETECTED_INTEGRATION" == "winbind" ]]; then
                        if verify_domain_user_winbind "$username"; then
                            echo "Domain Verification: User found in domain (via winbind)"
                        else
                            echo "Domain Verification: User not found in domain (via winbind)"
                        fi
                    fi
                else
                    echo "User Type:          Local User"
                    echo "Domain Status:      Not a domain user format"
                fi
            else
                echo "Machine Domain:     Could not detect"
            fi
        else
            echo "Domain Integration: None or not functional"
        fi
    fi
    
    echo ""
    return 0
}