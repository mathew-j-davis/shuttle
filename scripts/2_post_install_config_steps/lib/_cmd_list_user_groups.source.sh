# Command-specific help functions
show_help_list_user_groups() {
    cat << EOF
Usage: $SCRIPT_NAME list-user-groups --user <username> [options]

List all groups that a specific user belongs to.

Required Parameters:
  --user <username>     Username to show group memberships for

Optional Parameters:
  --format <format>     Output format: simple, detailed, csv, json
  --primary-only        Show only primary group
  --member-only         Show only groups where user is direct member
  --sort <field>        Sort by: name, gid, type (default: name)
  --reverse             Reverse sort order
  --check-domain        Check if user exists in domain
  --dry-run             Show what would be done without making changes

Output Formats:
  simple    - Just group names, one per line (default)
  detailed  - Group name, GID, membership type, group type
  csv       - Comma-separated values with headers
  json      - JSON array of group objects

Examples:
  # List all groups for user (simple format)
  $SCRIPT_NAME list-user-groups --user alice
  
  # List groups with detailed information
  $SCRIPT_NAME list-user-groups --user bob --format detailed
  
  # List only primary group
  $SCRIPT_NAME list-user-groups --user carol --primary-only
  
  # List only direct memberships
  $SCRIPT_NAME list-user-groups --user dave --member-only
  
  # CSV output sorted by GID
  $SCRIPT_NAME list-user-groups --user eve --format csv --sort gid
  
  # JSON output for automation
  $SCRIPT_NAME list-user-groups --user frank --format json
  
  # Check domain user
  $SCRIPT_NAME list-user-groups --user "DOMAIN\\\\user" --check-domain

Information Displayed:
  - Group name and GID
  - Membership type (primary, member, both)
  - Group type (system vs user group)
  - Total groups and breakdown by type

Notes:
  - Uses getent and groups commands to query memberships
  - Works with both local and domain users
  - Primary group is the user's default group (from /etc/passwd)
  - Member groups are groups the user was explicitly added to
  - System groups typically have GID < 1000
EOF
}

cmd_list_user_groups() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local username=""
    local format="simple"
    local primary_only=false
    local member_only=false
    local sort_field="name"
    local reverse_sort=false
    local check_domain=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --user)
                username=$(validate_parameter_value "$1" "${2:-}" "Username required after --user" "show_help_list_user_groups")
                shift 2
                ;;
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_list_user_groups")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "csv" && "$format" != "json" ]]; then
                    show_help_list_user_groups
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', 'csv', or 'json'"
                fi
                shift 2
                ;;
            --primary-only)
                primary_only=true
                shift
                ;;
            --member-only)
                member_only=true
                shift
                ;;
            --sort)
                sort_field=$(validate_parameter_value "$1" "${2:-}" "Sort field required after --sort" "show_help_list_user_groups")
                if [[ "$sort_field" != "name" && "$sort_field" != "gid" && "$sort_field" != "type" ]]; then
                    show_help_list_user_groups
                    error_exit "Invalid sort field: $sort_field. Must be 'name', 'gid', or 'type'"
                fi
                shift 2
                ;;
            --reverse)
                reverse_sort=true
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
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help_list_user_groups
                return 0
                ;;
            *)
                show_help_list_user_groups
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$username" ]]; then
        show_help_list_user_groups
        error_exit "Username is required"
    fi
    
    # Validate conflicting options
    if [[ "$primary_only" == "true" && "$member_only" == "true" ]]; then
        show_help_list_user_groups
        error_exit "Cannot specify both --primary-only and --member-only"
    fi
    
    log_command_call "list-user-groups" "$original_params"
    
    # Call the core function
    list_user_groups_core "$username" "$format" "$primary_only" "$member_only" "$sort_field" "$reverse_sort" "$check_domain"
    
    return 0
}

# Core function to list user groups
list_user_groups_core() {
    local username="$1"
    local format="$2"
    local primary_only="$3"
    local member_only="$4"
    local sort_field="$5"
    local reverse_sort="$6"
    local check_domain="$7"
    
    # Check if user exists locally first
    local user_info=""
    local user_exists_locally=false
    local effective_username="$username"
    
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
                        effective_username="$domain_format"  # Use the format that worked
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
    
    # Parse user information to get primary group
    local user_gid=$(echo "$user_info" | cut -d: -f4)
    local primary_group_info=""
    local primary_group_name=""
    
    if primary_group_info=$(getent group "$user_gid" 2>/dev/null); then
        primary_group_name=$(echo "$primary_group_info" | cut -d: -f1)
    else
        primary_group_name="$user_gid"
        echo "Warning: Primary group GID $user_gid not found in group database"
    fi
    
    # Get all groups for user using groups command
    local user_groups=""
    local all_group_names=()
    
    if user_groups=$(groups "$effective_username" 2>/dev/null); then
        # Extract group names (groups command output: "username : group1 group2 group3")
        local group_list=$(echo "$user_groups" | cut -d: -f2 | xargs)
        if [[ -n "$group_list" ]]; then
            read -ra all_group_names <<< "$group_list"
        fi
    else
        echo "Warning: Could not determine group memberships for '$effective_username'"
        return 1
    fi
    
    # Create array of group objects with additional info
    declare -a group_objects=()
    
    for group_name in "${all_group_names[@]}"; do
        group_name=$(echo "$group_name" | xargs)  # Trim whitespace
        if [[ -z "$group_name" ]]; then
            continue
        fi
        
        # Get group information
        local group_info=""
        if ! group_info=$(getent group "$group_name" 2>/dev/null); then
            # Group not found, skip
            continue
        fi
        
        # Parse group information
        local group_gid=$(echo "$group_info" | cut -d: -f3)
        local group_members_raw=$(echo "$group_info" | cut -d: -f4)
        
        # Determine membership type
        local membership_type=""
        local is_primary=false
        local is_member=false
        
        # Check if this is the primary group
        if [[ "$group_gid" == "$user_gid" ]]; then
            is_primary=true
        fi
        
        # Check if user is a direct member
        if [[ -n "$group_members_raw" ]]; then
            local group_members=()
            IFS=',' read -ra group_members <<< "$group_members_raw"
            for member in "${group_members[@]}"; do
                member=$(echo "$member" | xargs)
                if [[ "$member" == "$effective_username" ]]; then
                    is_member=true
                    break
                fi
            done
        fi
        
        # Set membership type
        if [[ "$is_primary" == "true" && "$is_member" == "true" ]]; then
            membership_type="both"
        elif [[ "$is_primary" == "true" ]]; then
            membership_type="primary"
        elif [[ "$is_member" == "true" ]]; then
            membership_type="member"
        else
            membership_type="unknown"
        fi
        
        # Apply filters
        if [[ "$primary_only" == "true" && "$is_primary" != "true" ]]; then
            continue
        fi
        
        if [[ "$member_only" == "true" && "$is_member" != "true" ]]; then
            continue
        fi
        
        # Determine group type
        local group_type="user"
        if [[ "$group_gid" -lt 1000 ]]; then
            group_type="system"
        fi
        
        group_objects+=("$group_name:$group_gid:$membership_type:$group_type")
    done
    
    # Sort group objects
    local sort_cmd="sort"
    case "$sort_field" in
        "name")
            sort_cmd="sort -t: -k1,1"
            ;;
        "gid")
            sort_cmd="sort -t: -k2,2n"
            ;;
        "type")
            sort_cmd="sort -t: -k4,4"
            ;;
    esac
    
    if [[ "$reverse_sort" == "true" ]]; then
        sort_cmd="$sort_cmd -r"
    fi
    
    # Sort the group objects
    local sorted_groups=()
    while IFS= read -r line; do
        sorted_groups+=("$line")
    done < <(printf '%s\n' "${group_objects[@]}" | eval "$sort_cmd")
    
    # Output based on format
    case "$format" in
        "simple")
            for group_obj in "${sorted_groups[@]}"; do
                echo "$(echo "$group_obj" | cut -d: -f1)"
            done
            ;;
        "detailed")
            printf "%-20s %-8s %-12s %-10s %s\n" "GROUP_NAME" "GID" "MEMBERSHIP" "TYPE" "NOTES"
            printf "%-20s %-8s %-12s %-10s %s\n" "----------" "---" "----------" "----" "-----"
            for group_obj in "${sorted_groups[@]}"; do
                IFS=: read -r group_name group_gid membership_type group_type <<< "$group_obj"
                
                local notes=""
                if [[ "$group_name" == "$primary_group_name" ]]; then
                    notes="Primary group"
                fi
                
                printf "%-20s %-8s %-12s %-10s %s\n" "$group_name" "$group_gid" "$membership_type" "$group_type" "$notes"
            done
            ;;
        "csv")
            echo "group_name,gid,membership_type,group_type"
            for group_obj in "${sorted_groups[@]}"; do
                IFS=: read -r group_name group_gid membership_type group_type <<< "$group_obj"
                echo "$group_name,$group_gid,$membership_type,$group_type"
            done
            ;;
        "json")
            echo "["
            local first=true
            for group_obj in "${sorted_groups[@]}"; do
                IFS=: read -r group_name group_gid membership_type group_type <<< "$group_obj"
                
                if [[ "$first" == "true" ]]; then
                    first=false
                else
                    echo ","
                fi
                
                local is_primary_json="false"
                if [[ "$group_name" == "$primary_group_name" ]]; then
                    is_primary_json="true"
                fi
                
                echo -n "  {"
                echo -n "\"group_name\":\"$group_name\","
                echo -n "\"gid\":$group_gid,"
                echo -n "\"membership_type\":\"$membership_type\","
                echo -n "\"group_type\":\"$group_type\","
                echo -n "\"is_primary\":$is_primary_json"
                echo -n "}"
            done
            echo ""
            echo "]"
            ;;
    esac
    
    # Show summary in non-simple formats
    if [[ "$format" != "simple" && "$format" != "json" && "$format" != "csv" ]]; then
        echo ""
        echo "Total groups for user '$effective_username': ${#sorted_groups[@]}"
        
        # Count by membership and type
        local primary_count=0
        local member_count=0
        local both_count=0
        local system_count=0
        local user_count=0
        
        for group_obj in "${sorted_groups[@]}"; do
            local membership_type=$(echo "$group_obj" | cut -d: -f3)
            local group_type=$(echo "$group_obj" | cut -d: -f4)
            
            case "$membership_type" in
                "primary") ((primary_count++)) ;;
                "member") ((member_count++)) ;;
                "both") ((both_count++)) ;;
            esac
            
            case "$group_type" in
                "system") ((system_count++)) ;;
                "user") ((user_count++)) ;;
            esac
        done
        
        echo "Primary group only: $primary_count"
        echo "Direct member only: $member_count"
        echo "Both primary and member: $both_count"
        echo "System groups: $system_count"
        echo "User groups: $user_count"
    fi
    
    return 0
}