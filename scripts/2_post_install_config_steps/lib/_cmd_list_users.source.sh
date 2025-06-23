# Command-specific help functions
show_help_list_users() {
    cat << EOF
Usage: $SCRIPT_NAME list-users [options]

List users on the system with various filtering and output options.

Optional Parameters:
  --format <format>        Output format: simple, detailed, csv, json
  --filter <filter>        Filter users: all, system, regular, locked, unlocked
  --sort <field>           Sort by: name, uid, home, shell (default: name)
  --reverse                Reverse sort order
  --min-uid <uid>          Show only users with UID >= value
  --max-uid <uid>          Show only users with UID <= value
  --shell <shell>          Show only users with specific shell
  --home-pattern <pattern> Show only users whose home matches pattern
  --dry-run                Show what would be done without making changes

Output Formats:
  simple    - Just usernames, one per line (default)
  detailed  - Username, UID, GID, home directory, shell, status
  csv       - Comma-separated values with headers
  json      - JSON array of user objects

Filter Options:
  all       - All users (default)
  system    - System users (UID < 1000)
  regular   - Regular users (UID >= 1000)
  locked    - Users with locked accounts
  unlocked  - Users with unlocked accounts

Examples:
  # List all users (simple format)
  $SCRIPT_NAME list-users
  
  # List regular users with detailed information
  $SCRIPT_NAME list-users --filter regular --format detailed
  
  # List users sorted by UID
  $SCRIPT_NAME list-users --sort uid --format detailed
  
  # List users with bash shell
  $SCRIPT_NAME list-users --shell /bin/bash
  
  # List users with UID between 1000 and 2000
  $SCRIPT_NAME list-users --min-uid 1000 --max-uid 2000
  
  # CSV output for spreadsheet import
  $SCRIPT_NAME list-users --format csv --filter regular
  
  # JSON output for automation
  $SCRIPT_NAME list-users --format json --filter system

Notes:
  - System users typically have UID < 1000
  - Regular users typically have UID >= 1000
  - Locked users have '!' or '*' in their password field
  - Home pattern supports shell wildcards (e.g., '/home/*')
EOF
}

cmd_list_users() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local format="simple"
    local filter="all"
    local sort_field="name"
    local reverse_sort=false
    local min_uid=""
    local max_uid=""
    local shell_filter=""
    local home_pattern=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_list_users")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "csv" && "$format" != "json" ]]; then
                    show_help_list_users
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', 'csv', or 'json'"
                fi
                shift 2
                ;;
            --filter)
                filter=$(validate_parameter_value "$1" "${2:-}" "Filter required after --filter" "show_help_list_users")
                if [[ "$filter" != "all" && "$filter" != "system" && "$filter" != "regular" && "$filter" != "locked" && "$filter" != "unlocked" ]]; then
                    show_help_list_users
                    error_exit "Invalid filter: $filter. Must be 'all', 'system', 'regular', 'locked', or 'unlocked'"
                fi
                shift 2
                ;;
            --sort)
                sort_field=$(validate_parameter_value "$1" "${2:-}" "Sort field required after --sort" "show_help_list_users")
                if [[ "$sort_field" != "name" && "$sort_field" != "uid" && "$sort_field" != "home" && "$sort_field" != "shell" ]]; then
                    show_help_list_users
                    error_exit "Invalid sort field: $sort_field. Must be 'name', 'uid', 'home', or 'shell'"
                fi
                shift 2
                ;;
            --reverse)
                reverse_sort=true
                shift
                ;;
            --min-uid)
                min_uid=$(validate_parameter_value "$1" "${2:-}" "UID required after --min-uid" "show_help_list_users")
                if ! [[ "$min_uid" =~ ^[0-9]+$ ]]; then
                    show_help_list_users
                    error_exit "Invalid UID: $min_uid. Must be a number"
                fi
                shift 2
                ;;
            --max-uid)
                max_uid=$(validate_parameter_value "$1" "${2:-}" "UID required after --max-uid" "show_help_list_users")
                if ! [[ "$max_uid" =~ ^[0-9]+$ ]]; then
                    show_help_list_users
                    error_exit "Invalid UID: $max_uid. Must be a number"
                fi
                shift 2
                ;;
            --shell)
                shell_filter=$(validate_parameter_value "$1" "${2:-}" "Shell required after --shell" "show_help_list_users")
                shift 2
                ;;
            --home-pattern)
                home_pattern=$(validate_parameter_value "$1" "${2:-}" "Pattern required after --home-pattern" "show_help_list_users")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_list_users
                return 0
                ;;
            *)
                show_help_list_users
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate UID range if both specified
    if [[ -n "$min_uid" && -n "$max_uid" ]]; then
        if [[ "$min_uid" -gt "$max_uid" ]]; then
            show_help_list_users
            error_exit "min-uid ($min_uid) cannot be greater than max-uid ($max_uid)"
        fi
    fi
    
    log_command_call "list-users" "$original_params"
    
    # Call the core function
    list_users_core "$format" "$filter" "$sort_field" "$reverse_sort" "$min_uid" "$max_uid" "$shell_filter" "$home_pattern"
    
    return 0
}

# Core function to list users
list_users_core() {
    local format="$1"
    local filter="$2"
    local sort_field="$3"
    local reverse_sort="$4"
    local min_uid="$5"
    local max_uid="$6"
    local shell_filter="$7"
    local home_pattern="$8"
    
    # Create array of user objects with additional info
    declare -a user_objects=()
    
    # Read all users from passwd
    while IFS=: read -r username _ uid gid gecos home shell; do
        # Apply UID filters
        if [[ -n "$min_uid" && "$uid" -lt "$min_uid" ]]; then
            continue
        fi
        if [[ -n "$max_uid" && "$uid" -gt "$max_uid" ]]; then
            continue
        fi
        
        # Apply shell filter
        if [[ -n "$shell_filter" && "$shell" != "$shell_filter" ]]; then
            continue
        fi
        
        # Apply home pattern filter
        if [[ -n "$home_pattern" ]]; then
            # Use shell pattern matching
            if ! [[ "$home" == $home_pattern ]]; then
                continue
            fi
        fi
        
        # Determine user type
        local user_type="regular"
        if [[ "$uid" -lt 1000 ]]; then
            user_type="system"
        fi
        
        # Check account status
        local account_status="unlocked"
        if getent shadow "$username" 2>/dev/null | cut -d: -f2 | grep -q "^!"; then
            account_status="locked"
        elif getent shadow "$username" 2>/dev/null | cut -d: -f2 | grep -q "^\\*"; then
            account_status="no_password"
        fi
        
        # Apply filter
        case "$filter" in
            "system")
                if [[ "$user_type" != "system" ]]; then
                    continue
                fi
                ;;
            "regular")
                if [[ "$user_type" != "regular" ]]; then
                    continue
                fi
                ;;
            "locked")
                if [[ "$account_status" != "locked" ]]; then
                    continue
                fi
                ;;
            "unlocked")
                if [[ "$account_status" == "locked" ]]; then
                    continue
                fi
                ;;
            "all")
                # No additional filtering
                ;;
        esac
        
        # Get primary group name
        local primary_group=""
        if group_info=$(getent group "$gid" 2>/dev/null); then
            primary_group=$(echo "$group_info" | cut -d: -f1)
        else
            primary_group="$gid"
        fi
        
        user_objects+=("$username:$uid:$gid:$primary_group:$home:$shell:$user_type:$account_status:$gecos")
    done < <(getent passwd)
    
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
            sort_cmd="sort -t: -k5,5"
            ;;
        "shell")
            sort_cmd="sort -t: -k6,6"
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
            printf "%-20s %-8s %-8s %-15s %-30s %-20s %-10s %s\n" "USERNAME" "UID" "GID" "PRIMARY_GROUP" "HOME" "SHELL" "TYPE" "STATUS"
            printf "%-20s %-8s %-8s %-15s %-30s %-20s %-10s %s\n" "--------" "---" "---" "-------------" "----" "-----" "----" "------"
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username uid gid primary_group home shell user_type account_status gecos <<< "$user_obj"
                printf "%-20s %-8s %-8s %-15s %-30s %-20s %-10s %s\n" "$username" "$uid" "$gid" "$primary_group" "$home" "$shell" "$user_type" "$account_status"
            done
            ;;
        "csv")
            echo "username,uid,gid,primary_group,home,shell,user_type,account_status,gecos"
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username uid gid primary_group home shell user_type account_status gecos <<< "$user_obj"
                echo "$username,$uid,$gid,$primary_group,$home,$shell,$user_type,$account_status,\"$gecos\""
            done
            ;;
        "json")
            echo "["
            local first=true
            for user_obj in "${sorted_users[@]}"; do
                IFS=: read -r username uid gid primary_group home shell user_type account_status gecos <<< "$user_obj"
                
                if [[ "$first" == "true" ]]; then
                    first=false
                else
                    echo ","
                fi
                
                echo -n "  {"
                echo -n "\"username\":\"$username\","
                echo -n "\"uid\":$uid,"
                echo -n "\"gid\":$gid,"
                echo -n "\"primary_group\":\"$primary_group\","
                echo -n "\"home\":\"$home\","
                echo -n "\"shell\":\"$shell\","
                echo -n "\"user_type\":\"$user_type\","
                echo -n "\"account_status\":\"$account_status\","
                echo -n "\"gecos\":\"$gecos\""
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
        
        # Count by type and status
        local system_count=0
        local regular_count=0
        local locked_count=0
        local unlocked_count=0
        
        for user_obj in "${sorted_users[@]}"; do
            local user_type=$(echo "$user_obj" | cut -d: -f7)
            local account_status=$(echo "$user_obj" | cut -d: -f8)
            
            case "$user_type" in
                "system") ((system_count++)) ;;
                "regular") ((regular_count++)) ;;
            esac
            
            case "$account_status" in
                "locked") ((locked_count++)) ;;
                *) ((unlocked_count++)) ;;
            esac
        done
        
        echo "System users: $system_count"
        echo "Regular users: $regular_count"
        echo "Locked accounts: $locked_count"
        echo "Unlocked accounts: $unlocked_count"
    fi
    
    return 0
}