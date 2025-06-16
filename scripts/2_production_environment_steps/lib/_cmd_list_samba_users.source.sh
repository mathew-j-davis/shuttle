# Command-specific help functions
show_help_list_samba_users() {
    cat << EOF
Usage: $SCRIPT_NAME list-samba-users [options]

List all Samba users in the database.

Optional Parameters:
  --format <format>     Output format: simple, detailed, csv, json
  --filter <filter>     Filter users: all, enabled, disabled
  --sort <field>        Sort by: name, uid, status (default: name)
  --reverse             Reverse sort order
  --dry-run             Show what would be done without making changes

Output Formats:
  simple    - Just usernames, one per line (default)
  detailed  - Username, UID, status, last password change
  csv       - Comma-separated values with headers
  json      - JSON array of user objects

Filter Options:
  all       - All Samba users (default)
  enabled   - Only enabled users
  disabled  - Only disabled users

Examples:
  # List all Samba users (simple format)
  $SCRIPT_NAME list-samba-users
  
  # List with detailed information
  $SCRIPT_NAME list-samba-users --format detailed
  
  # List only enabled users
  $SCRIPT_NAME list-samba-users --filter enabled --format detailed
  
  # CSV output sorted by UID
  $SCRIPT_NAME list-samba-users --format csv --sort uid
  
  # JSON output for automation
  $SCRIPT_NAME list-samba-users --format json

Notes:
  - Uses pdbedit to query Samba user database
  - Shows user status (enabled/disabled)
  - Includes system UID when available
  - Status indicates if user can currently authenticate
EOF
}

cmd_list_samba_users() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local format="simple"
    local filter="all"
    local sort_field="name"
    local reverse_sort=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_list_samba_users")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "csv" && "$format" != "json" ]]; then
                    show_help_list_samba_users
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', 'csv', or 'json'"
                fi
                shift 2
                ;;
            --filter)
                filter=$(validate_parameter_value "$1" "${2:-}" "Filter required after --filter" "show_help_list_samba_users")
                if [[ "$filter" != "all" && "$filter" != "enabled" && "$filter" != "disabled" ]]; then
                    show_help_list_samba_users
                    error_exit "Invalid filter: $filter. Must be 'all', 'enabled', or 'disabled'"
                fi
                shift 2
                ;;
            --sort)
                sort_field=$(validate_parameter_value "$1" "${2:-}" "Sort field required after --sort" "show_help_list_samba_users")
                if [[ "$sort_field" != "name" && "$sort_field" != "uid" && "$sort_field" != "status" ]]; then
                    show_help_list_samba_users
                    error_exit "Invalid sort field: $sort_field. Must be 'name', 'uid', or 'status'"
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
                show_help_list_samba_users
                return 0
                ;;
            *)
                show_help_list_samba_users
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    echo "list-samba-users command called with parameters: $original_params"
    
    # Call the core function
    list_samba_users_core "$format" "$filter" "$sort_field" "$reverse_sort"
    
    return 0
}

# Core function to list Samba users
list_samba_users_core() {
    local format="$1"
    local filter="$2"
    local sort_field="$3"
    local reverse_sort="$4"
    
    # Check tool availability
    check_tool_permission_or_error_exit "pdbedit" "read Samba user database" "Samba tools not available"
    
    # Create array of user objects
    declare -a user_objects=()
    
    # Get users from pdbedit
    while IFS=: read -r username uid_info; do
        # Extract username if it has extra info
        local clean_username="$username"
        
        # Get detailed user info
        local user_details=""
        if user_details=$(sudo pdbedit -v "$clean_username" 2>/dev/null); then
            # Parse user details
            local unix_uid=""
            local account_flags=""
            local last_changed=""
            
            # Extract information from pdbedit verbose output
            if [[ "$user_details" =~ Unix\ username:[[:space:]]*([^[:space:]]*) ]]; then
                clean_username="${BASH_REMATCH[1]}"
            fi
            
            if [[ "$user_details" =~ Unix\ userid:[[:space:]]*([0-9]+) ]]; then
                unix_uid="${BASH_REMATCH[1]}"
            fi
            
            if [[ "$user_details" =~ Account\ Flags:[[:space:]]*\[([^\]]*)\] ]]; then
                account_flags="${BASH_REMATCH[1]}"
            fi
            
            if [[ "$user_details" =~ Password\ last\ set:[[:space:]]*(.+) ]]; then
                last_changed="${BASH_REMATCH[1]}"
            fi
            
            # Determine status from account flags
            local status="enabled"
            if [[ "$account_flags" =~ D ]]; then
                status="disabled"
            fi
            
            # Get system UID if not found in Samba info
            if [[ -z "$unix_uid" ]]; then
                if user_info=$(getent passwd "$clean_username" 2>/dev/null); then
                    unix_uid=$(echo "$user_info" | cut -d: -f3)
                else
                    unix_uid="unknown"
                fi
            fi
            
            # Apply filter
            case "$filter" in
                "enabled")
                    if [[ "$status" != "enabled" ]]; then
                        continue
                    fi
                    ;;
                "disabled")
                    if [[ "$status" != "disabled" ]]; then
                        continue
                    fi
                    ;;
                "all")
                    # No filtering
                    ;;
            esac
            
            # Clean up last changed date
            [[ -z "$last_changed" ]] && last_changed="unknown"
            
            user_objects+=("$clean_username:$unix_uid:$status:$last_changed:$account_flags")
        fi
    done < <(sudo pdbedit -L 2>/dev/null)
    
    # Sort user objects
    local sort_cmd="sort"
    case "$sort_field" in
        "name")
            sort_cmd="sort -t: -k1,1"
            ;;
        "uid")
            sort_cmd="sort -t: -k2,2n"
            ;;
        "status")
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
            printf "%-20s %-8s %-10s %-25s %s\n" "USERNAME" "UID" "STATUS" "LAST_CHANGED" "FLAGS"
            printf "%-20s %-8s %-10s %-25s %s\n" "--------" "---" "------" "------------" "-----"
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username unix_uid status last_changed account_flags <<< "$user_obj"
                
                # Truncate long dates
                local display_date="$last_changed"
                if [[ ${#last_changed} -gt 23 ]]; then
                    display_date="${last_changed:0:20}..."
                fi
                
                printf "%-20s %-8s %-10s %-25s %s\n" "$username" "$unix_uid" "$status" "$display_date" "$account_flags"
            done
            ;;
        "csv")
            echo "username,uid,status,last_changed,account_flags"
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username unix_uid status last_changed account_flags <<< "$user_obj"
                echo "\"$username\",\"$unix_uid\",\"$status\",\"$last_changed\",\"$account_flags\""
            done
            ;;
        "json")
            echo "["
            local first=true
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username unix_uid status last_changed account_flags <<< "$user_obj"
                
                if [[ "$first" == "true" ]]; then
                    first=false
                else
                    echo ","
                fi
                
                echo -n "  {"
                echo -n "\"username\":\"$username\","
                echo -n "\"uid\":\"$unix_uid\","
                echo -n "\"status\":\"$status\","
                echo -n "\"last_changed\":\"$last_changed\","
                echo -n "\"account_flags\":\"$account_flags\""
                echo -n "}"
            done
            echo ""
            echo "]"
            ;;
    esac
    
    # Show summary in non-simple formats
    if [[ "$format" != "simple" && "$format" != "json" && "$format" != "csv" ]]; then
        echo ""
        echo "Total Samba users: ${#sorted_users[@]}"
        
        # Count by status
        local enabled_count=0
        local disabled_count=0
        
        for user_obj in "${sorted_users[@]}"; do
            local status=$(echo "$user_obj" | cut -d: -f3)
            case "$status" in
                "enabled") ((enabled_count++)) ;;
                "disabled") ((disabled_count++)) ;;
            esac
        done
        
        echo "Enabled users: $enabled_count"
        echo "Disabled users: $disabled_count"
    fi
    
    return 0
}