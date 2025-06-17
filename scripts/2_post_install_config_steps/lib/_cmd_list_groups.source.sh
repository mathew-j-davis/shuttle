# Command-specific help functions
show_help_list_groups() {
    cat << EOF
Usage: $SCRIPT_NAME list-groups [options]

List groups on the system with various filtering and output options.

Optional Parameters:
  --format <format>        Output format: simple, detailed, csv, json
  --filter <filter>        Filter groups: all, system, user, empty, non-empty
  --sort <field>           Sort by: name, gid, members (default: name)
  --reverse                Reverse sort order
  --min-gid <gid>          Show only groups with GID >= value
  --max-gid <gid>          Show only groups with GID <= value
  --name-pattern <pattern> Show only groups whose name matches pattern
  --dry-run                Show what would be done without making changes

Output Formats:
  simple    - Just group names, one per line (default)
  detailed  - Group name, GID, member count, member list
  csv       - Comma-separated values with headers
  json      - JSON array of group objects

Filter Options:
  all       - All groups (default)
  system    - System groups (GID < 1000)
  user      - User groups (GID >= 1000)
  empty     - Groups with no members
  non-empty - Groups with at least one member

Examples:
  # List all groups (simple format)
  $SCRIPT_NAME list-groups
  
  # List user groups with detailed information
  $SCRIPT_NAME list-groups --filter user --format detailed
  
  # List groups sorted by GID
  $SCRIPT_NAME list-groups --sort gid --format detailed
  
  # List groups with GID between 1000 and 2000
  $SCRIPT_NAME list-groups --min-gid 1000 --max-gid 2000
  
  # List groups matching pattern
  $SCRIPT_NAME list-groups --name-pattern "dev*"
  
  # CSV output for spreadsheet import
  $SCRIPT_NAME list-groups --format csv --filter user
  
  # JSON output for automation
  $SCRIPT_NAME list-groups --format json --filter system

Notes:
  - System groups typically have GID < 1000
  - User groups typically have GID >= 1000
  - Empty groups have no direct members (but may have users with it as primary group)
  - Member count includes both direct members and primary group users
  - Name pattern supports shell wildcards (e.g., 'sudo*', '*admin*')
EOF
}

cmd_list_groups() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local format="simple"
    local filter="all"
    local sort_field="name"
    local reverse_sort=false
    local min_gid=""
    local max_gid=""
    local name_pattern=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_list_groups")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "csv" && "$format" != "json" ]]; then
                    show_help_list_groups
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', 'csv', or 'json'"
                fi
                shift 2
                ;;
            --filter)
                filter=$(validate_parameter_value "$1" "${2:-}" "Filter required after --filter" "show_help_list_groups")
                if [[ "$filter" != "all" && "$filter" != "system" && "$filter" != "user" && "$filter" != "empty" && "$filter" != "non-empty" ]]; then
                    show_help_list_groups
                    error_exit "Invalid filter: $filter. Must be 'all', 'system', 'user', 'empty', or 'non-empty'"
                fi
                shift 2
                ;;
            --sort)
                sort_field=$(validate_parameter_value "$1" "${2:-}" "Sort field required after --sort" "show_help_list_groups")
                if [[ "$sort_field" != "name" && "$sort_field" != "gid" && "$sort_field" != "members" ]]; then
                    show_help_list_groups
                    error_exit "Invalid sort field: $sort_field. Must be 'name', 'gid', or 'members'"
                fi
                shift 2
                ;;
            --reverse)
                reverse_sort=true
                shift
                ;;
            --min-gid)
                min_gid=$(validate_parameter_value "$1" "${2:-}" "GID required after --min-gid" "show_help_list_groups")
                if ! [[ "$min_gid" =~ ^[0-9]+$ ]]; then
                    show_help_list_groups
                    error_exit "Invalid GID: $min_gid. Must be a number"
                fi
                shift 2
                ;;
            --max-gid)
                max_gid=$(validate_parameter_value "$1" "${2:-}" "GID required after --max-gid" "show_help_list_groups")
                if ! [[ "$max_gid" =~ ^[0-9]+$ ]]; then
                    show_help_list_groups
                    error_exit "Invalid GID: $max_gid. Must be a number"
                fi
                shift 2
                ;;
            --name-pattern)
                name_pattern=$(validate_parameter_value "$1" "${2:-}" "Pattern required after --name-pattern" "show_help_list_groups")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_list_groups
                return 0
                ;;
            *)
                show_help_list_groups
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate GID range if both specified
    if [[ -n "$min_gid" && -n "$max_gid" ]]; then
        if [[ "$min_gid" -gt "$max_gid" ]]; then
            show_help_list_groups
            error_exit "min-gid ($min_gid) cannot be greater than max-gid ($max_gid)"
        fi
    fi
    
    echo "list-groups command called with parameters: $original_params"
    
    # Call the core function
    list_groups_core "$format" "$filter" "$sort_field" "$reverse_sort" "$min_gid" "$max_gid" "$name_pattern"
    
    return 0
}

# Core function to list groups
list_groups_core() {
    local format="$1"
    local filter="$2"
    local sort_field="$3"
    local reverse_sort="$4"
    local min_gid="$5"
    local max_gid="$6"
    local name_pattern="$7"
    
    # Create array of group objects with additional info
    declare -a group_objects=()
    
    # Read all groups from group database
    while IFS=: read -r groupname _ gid members_raw; do
        # Apply GID filters
        if [[ -n "$min_gid" && "$gid" -lt "$min_gid" ]]; then
            continue
        fi
        if [[ -n "$max_gid" && "$gid" -gt "$max_gid" ]]; then
            continue
        fi
        
        # Apply name pattern filter
        if [[ -n "$name_pattern" ]]; then
            # Use shell pattern matching
            if ! [[ "$groupname" == $name_pattern ]]; then
                continue
            fi
        fi
        
        # Determine group type
        local group_type="user"
        if [[ "$gid" -lt 1000 ]]; then
            group_type="system"
        fi
        
        # Parse direct members
        local direct_members=()
        if [[ -n "$members_raw" ]]; then
            IFS=',' read -ra direct_members <<< "$members_raw"
        fi
        
        # Find users who have this group as their primary group
        local primary_users=()
        while IFS=: read -r username _ uid user_gid _ _ _; do
            if [[ "$user_gid" == "$gid" ]]; then
                primary_users+=("$username")
            fi
        done < <(getent passwd)
        
        # Combine all users and remove duplicates
        local all_users=()
        all_users+=("${direct_members[@]}")
        all_users+=("${primary_users[@]}")
        
        local unique_users=()
        for user in "${all_users[@]}"; do
            user=$(echo "$user" | xargs)  # Trim whitespace
            if [[ -n "$user" ]] && [[ ! " ${unique_users[*]} " =~ " $user " ]]; then
                # Verify user exists
                if getent passwd "$user" >/dev/null 2>&1; then
                    unique_users+=("$user")
                fi
            fi
        done
        
        local member_count=${#unique_users[@]}
        
        # Apply membership filters
        case "$filter" in
            "system")
                if [[ "$group_type" != "system" ]]; then
                    continue
                fi
                ;;
            "user")
                if [[ "$group_type" != "user" ]]; then
                    continue
                fi
                ;;
            "empty")
                if [[ "$member_count" -gt 0 ]]; then
                    continue
                fi
                ;;
            "non-empty")
                if [[ "$member_count" -eq 0 ]]; then
                    continue
                fi
                ;;
            "all")
                # No additional filtering
                ;;
        esac
        
        # Create member list string for display
        local member_list=""
        if [[ ${#unique_users[@]} -gt 0 ]]; then
            member_list=$(printf "%s," "${unique_users[@]}")
            member_list="${member_list%,}"  # Remove trailing comma
        fi
        
        # Store group object: groupname:gid:group_type:member_count:member_list:direct_count:primary_count
        local direct_count=${#direct_members[@]}
        local primary_count=${#primary_users[@]}
        group_objects+=("$groupname:$gid:$group_type:$member_count:$member_list:$direct_count:$primary_count")
    done < <(getent group)
    
    # Sort group objects
    local sort_cmd="sort"
    case "$sort_field" in
        "name")
            sort_cmd="sort -t: -k1,1"
            ;;
        "gid")
            sort_cmd="sort -t: -k2,2n"
            ;;
        "members")
            sort_cmd="sort -t: -k4,4n"
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
            printf "%-20s %-8s %-10s %-8s %-8s %-8s %s\n" "GROUPNAME" "GID" "TYPE" "TOTAL" "DIRECT" "PRIMARY" "MEMBERS"
            printf "%-20s %-8s %-10s %-8s %-8s %-8s %s\n" "---------" "---" "----" "-----" "------" "-------" "-------"
            for group_obj in "${sorted_groups[@]}"; do
                IFS=: read -r groupname gid group_type member_count member_list direct_count primary_count <<< "$group_obj"
                
                # Truncate member list if too long
                local display_members="$member_list"
                if [[ ${#member_list} -gt 40 ]]; then
                    display_members="${member_list:0:37}..."
                fi
                
                printf "%-20s %-8s %-10s %-8s %-8s %-8s %s\n" "$groupname" "$gid" "$group_type" "$member_count" "$direct_count" "$primary_count" "$display_members"
            done
            ;;
        "csv")
            echo "groupname,gid,group_type,total_members,direct_members,primary_users,member_list"
            for group_obj in "${sorted_groups[@]}"; do
                IFS=: read -r groupname gid group_type member_count member_list direct_count primary_count <<< "$group_obj"
                echo "$groupname,$gid,$group_type,$member_count,$direct_count,$primary_count,\"$member_list\""
            done
            ;;
        "json")
            echo "["
            local first=true
            for group_obj in "${sorted_groups[@]}"; do
                IFS=: read -r groupname gid group_type member_count member_list direct_count primary_count <<< "$group_obj"
                
                if [[ "$first" == "true" ]]; then
                    first=false
                else
                    echo ","
                fi
                
                # Convert member list to JSON array
                local members_json="[]"
                if [[ -n "$member_list" ]]; then
                    members_json="[\"$(echo "$member_list" | sed 's/,/","/g')\"]"
                fi
                
                echo -n "  {"
                echo -n "\"groupname\":\"$groupname\","
                echo -n "\"gid\":$gid,"
                echo -n "\"group_type\":\"$group_type\","
                echo -n "\"total_members\":$member_count,"
                echo -n "\"direct_members\":$direct_count,"
                echo -n "\"primary_users\":$primary_count,"
                echo -n "\"members\":$members_json"
                echo -n "}"
            done
            echo ""
            echo "]"
            ;;
    esac
    
    # Show summary in non-simple formats
    if [[ "$format" != "simple" && "$format" != "json" && "$format" != "csv" ]]; then
        echo ""
        echo "Total groups: ${#sorted_groups[@]}"
        
        # Count by type and membership
        local system_count=0
        local user_count=0
        local empty_count=0
        local non_empty_count=0
        
        for group_obj in "${sorted_groups[@]}"; do
            local group_type=$(echo "$group_obj" | cut -d: -f3)
            local member_count=$(echo "$group_obj" | cut -d: -f4)
            
            case "$group_type" in
                "system") ((system_count++)) ;;
                "user") ((user_count++)) ;;
            esac
            
            if [[ "$member_count" -eq 0 ]]; then
                ((empty_count++))
            else
                ((non_empty_count++))
            fi
        done
        
        echo "System groups: $system_count"
        echo "User groups: $user_count"
        echo "Empty groups: $empty_count"
        echo "Non-empty groups: $non_empty_count"
    fi
    
    return 0
}