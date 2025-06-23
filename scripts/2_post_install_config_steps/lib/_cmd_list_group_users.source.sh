# Command-specific help functions
show_help_list_group_users() {
    cat << EOF
Usage: $SCRIPT_NAME list-group-users --group <groupname> [options]

List all users that belong to a specific group.

Required Parameters:
  --group <groupname>   Group name to list users for

Optional Parameters:
  --format <format>     Output format: simple, detailed, csv, json
  --primary-only        Show only users with this as primary group
  --members-only        Show only direct group members
  --sort <field>        Sort by: name, uid, home (default: name)
  --reverse             Reverse sort order
  --dry-run             Show what would be done without making changes

Output Formats:
  simple    - Just usernames, one per line (default)
  detailed  - Username, UID, home directory, shell
  csv       - Comma-separated values with headers
  json      - JSON array of user objects

Examples:
  # List all users in group (simple format)
  $SCRIPT_NAME list-group-users --group developers
  
  # List with detailed information
  $SCRIPT_NAME list-group-users --group sudo --format detailed
  
  # List only direct members (not primary group users)
  $SCRIPT_NAME list-group-users --group docker --members-only
  
  # List only users with this as primary group
  $SCRIPT_NAME list-group-users --group users --primary-only
  
  # CSV output sorted by UID
  $SCRIPT_NAME list-group-users --group staff --format csv --sort uid
  
  # JSON output for automation
  $SCRIPT_NAME list-group-users --group admin --format json

Notes:
  - Shows both direct members and users with group as primary group
  - Use --members-only or --primary-only to filter specific types
  - JSON format is useful for scripting and automation
  - CSV format includes headers for spreadsheet import
EOF
}

cmd_list_group_users() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local groupname=""
    local format="simple"
    local primary_only=false
    local members_only=false
    local sort_field="name"
    local reverse_sort=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --group)
                groupname=$(validate_parameter_value "$1" "${2:-}" "Group name required after --group" "show_help_list_group_users")
                shift 2
                ;;
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_list_group_users")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "csv" && "$format" != "json" ]]; then
                    show_help_list_group_users
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', 'csv', or 'json'"
                fi
                shift 2
                ;;
            --primary-only)
                primary_only=true
                shift
                ;;
            --members-only)
                members_only=true
                shift
                ;;
            --sort)
                sort_field=$(validate_parameter_value "$1" "${2:-}" "Sort field required after --sort" "show_help_list_group_users")
                if [[ "$sort_field" != "name" && "$sort_field" != "uid" && "$sort_field" != "home" ]]; then
                    show_help_list_group_users
                    error_exit "Invalid sort field: $sort_field. Must be 'name', 'uid', or 'home'"
                fi
                shift 2
                ;;
            --reverse)
                reverse_sort=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_list_group_users
                return 0
                ;;
            *)
                show_help_list_group_users
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$groupname" ]]; then
        show_help_list_group_users
        error_exit "Group name is required"
    fi
    
    # Validate conflicting options
    if [[ "$primary_only" == "true" && "$members_only" == "true" ]]; then
        show_help_list_group_users
        error_exit "Cannot specify both --primary-only and --members-only"
    fi
    
    log_command_call "list-group-users" "$original_params"
    
    # Check if group exists
    if ! group_exists "$groupname"; then
        error_exit "Group '$groupname' does not exist"
    fi
    
    # Call the core function
    list_group_users_core "$groupname" "$format" "$primary_only" "$members_only" "$sort_field" "$reverse_sort"
    
    return 0
}

# Core function to list group users
list_group_users_core() {
    local groupname="$1"
    local format="$2"
    local primary_only="$3"
    local members_only="$4"
    local sort_field="$5"
    local reverse_sort="$6"
    
    # Get group information
    local group_info=""
    if ! group_info=$(getent group "$groupname" 2>/dev/null); then
        log ERROR "Failed to get group information for '$groupname'"
        return 1
    fi
    
    # Parse group information (format: groupname:password:gid:members)
    local group_gid=$(echo "$group_info" | cut -d: -f3)
    local group_members_raw=$(echo "$group_info" | cut -d: -f4)
    
    # Get direct group members
    local direct_members=()
    if [[ -n "$group_members_raw" ]]; then
        IFS=',' read -ra direct_members <<< "$group_members_raw"
    fi
    
    # Get users who have this group as their primary group
    local primary_users=()
    while IFS=: read -r username _ uid gid _ _ _; do
        if [[ "$gid" == "$group_gid" ]]; then
            primary_users+=("$username")
        fi
    done < <(getent passwd)
    
    # Build the list of users based on filters
    local all_users=()
    
    if [[ "$members_only" == "true" ]]; then
        # Only direct members
        all_users=("${direct_members[@]}")
    elif [[ "$primary_only" == "true" ]]; then
        # Only primary group users
        all_users=("${primary_users[@]}")
    else
        # Both direct members and primary users
        all_users=("${direct_members[@]}" "${primary_users[@]}")
    fi
    
    # Remove duplicates and empty entries
    local unique_users=()
    for user in "${all_users[@]}"; do
        user=$(echo "$user" | xargs)  # Trim whitespace
        if [[ -n "$user" ]] && [[ ! " ${unique_users[*]} " =~ " $user " ]]; then
            unique_users+=("$user")
        fi
    done
    
    # Create array of user objects with additional info
    declare -a user_objects=()
    for user in "${unique_users[@]}"; do
        if user_info=$(getent passwd "$user" 2>/dev/null); then
            local username=$(echo "$user_info" | cut -d: -f1)
            local uid=$(echo "$user_info" | cut -d: -f3)
            local user_gid=$(echo "$user_info" | cut -d: -f4)
            local home=$(echo "$user_info" | cut -d: -f6)
            local shell=$(echo "$user_info" | cut -d: -f7)
            
            # Determine membership type
            local membership_type=""
            if [[ " ${direct_members[*]} " =~ " $user " ]] && [[ "$user_gid" == "$group_gid" ]]; then
                membership_type="both"
            elif [[ " ${direct_members[*]} " =~ " $user " ]]; then
                membership_type="member"
            elif [[ "$user_gid" == "$group_gid" ]]; then
                membership_type="primary"
            else
                membership_type="unknown"
            fi
            
            user_objects+=("$username:$uid:$home:$shell:$membership_type")
        fi
    done
    
    # Sort user objects
    local sort_cmd="sort"
    case "$sort_field" in
        "name")
            sort_cmd="sort -t: -k1,1"
            ;;
        "uid")
            sort_cmd="sort -t: -k2,2n"
            ;;
        "home")
            sort_cmd="sort -t: -k3,3"
            ;;
    esac
    
    if [[ "$reverse_sort" == "true" ]]; then
        sort_cmd="$sort_cmd -r"
    fi
    
    # Sort the user objects
    local sorted_users=()
    while IFS= read -r line; do
        sorted_users+=("$line")
    done < <(printf '%s\n' "${user_objects[@]}" | eval "$sort_cmd")
    
    # Output based on format
    case "$format" in
        "simple")
            for user_obj in "${sorted_users[@]}"; do
                echo "$(echo "$user_obj" | cut -d: -f1)"
            done
            ;;
        "detailed")
            printf "%-20s %-8s %-10s %-30s %-20s %s\n" "USERNAME" "UID" "TYPE" "HOME" "SHELL" "MEMBERSHIP"
            printf "%-20s %-8s %-10s %-30s %-20s %s\n" "--------" "---" "----" "----" "-----" "----------"
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username uid home shell membership_type <<< "$user_obj"
                
                # Determine user type
                local user_type="User"
                if [[ "$uid" -lt 1000 ]]; then
                    user_type="System"
                fi
                
                printf "%-20s %-8s %-10s %-30s %-20s %s\n" "$username" "$uid" "$user_type" "$home" "$shell" "$membership_type"
            done
            ;;
        "csv")
            echo "username,uid,home,shell,membership_type"
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username uid home shell membership_type <<< "$user_obj"
                echo "$username,$uid,$home,$shell,$membership_type"
            done
            ;;
        "json")
            echo "["
            local first=true
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username uid home shell membership_type <<< "$user_obj"
                
                if [[ "$first" == "true" ]]; then
                    first=false
                else
                    echo ","
                fi
                
                echo -n "  {"
                echo -n "\"username\":\"$username\","
                echo -n "\"uid\":$uid,"
                echo -n "\"home\":\"$home\","
                echo -n "\"shell\":\"$shell\","
                echo -n "\"membership_type\":\"$membership_type\""
                echo -n "}"
            done
            echo ""
            echo "]"
            ;;
    esac
    
    # Show summary in non-simple formats
    if [[ "$format" != "simple" && "$format" != "json" && "$format" != "csv" ]]; then
        echo ""
        echo "Total users: ${#sorted_users[@]}"
        
        # Count by membership type
        local member_count=0
        local primary_count=0
        local both_count=0
        
        for user_obj in "${sorted_users[@]}"; do
            local membership_type=$(echo "$user_obj" | cut -d: -f5)
            case "$membership_type" in
                "member") ((member_count++)) ;;
                "primary") ((primary_count++)) ;;
                "both") ((both_count++)) ;;
            esac
        done
        
        echo "Direct members: $member_count"
        echo "Primary group users: $primary_count"
        echo "Both: $both_count"
    fi
    
    return 0
}