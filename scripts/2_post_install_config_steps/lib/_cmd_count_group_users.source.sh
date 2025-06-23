# Command-specific help functions
show_help_count_group_users() {
    cat << EOF
Usage: $SCRIPT_NAME count-group-users --group <groupname> [options]

Count users that belong to a specific group.

Required Parameters:
  --group <groupname>   Group name to count users for

Optional Parameters:
  --primary-only        Count only users with this as primary group
  --members-only        Count only direct group members
  --format <format>     Output format: simple, detailed (default: simple)
  --dry-run             Show what would be done without making changes

Output Formats:
  simple    - Just the count number
  detailed  - Count with breakdown by membership type

Examples:
  # Count all users in group
  $SCRIPT_NAME count-group-users --group developers
  
  # Count only direct members
  $SCRIPT_NAME count-group-users --group docker --members-only
  
  # Count only users with this as primary group
  $SCRIPT_NAME count-group-users --group users --primary-only
  
  # Detailed count with breakdown
  $SCRIPT_NAME count-group-users --group sudo --format detailed

Notes:
  - Counts both direct members and users with group as primary group by default
  - Use --members-only or --primary-only to filter specific types
  - Simple format outputs just the number for scripting
  - Detailed format shows breakdown by membership type
EOF
}

cmd_count_group_users() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local groupname=""
    local format="simple"
    local primary_only=false
    local members_only=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --group)
                groupname=$(validate_parameter_value "$1" "${2:-}" "Group name required after --group" "show_help_count_group_users")
                shift 2
                ;;
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_count_group_users")
                if [[ "$format" != "simple" && "$format" != "detailed" ]]; then
                    show_help_count_group_users
                    error_exit "Invalid format: $format. Must be 'simple' or 'detailed'"
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
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help_count_group_users
                return 0
                ;;
            *)
                show_help_count_group_users
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$groupname" ]]; then
        show_help_count_group_users
        error_exit "Group name is required"
    fi
    
    # Validate conflicting options
    if [[ "$primary_only" == "true" && "$members_only" == "true" ]]; then
        show_help_count_group_users
        error_exit "Cannot specify both --primary-only and --members-only"
    fi
    
    log_command_call "count-group-users" "$original_params"
    
    # Check if group exists
    if ! group_exists "$groupname"; then
        error_exit "Group '$groupname' does not exist"
    fi
    
    # Call the core function
    count_group_users_core "$groupname" "$format" "$primary_only" "$members_only"
    
    return 0
}

# Core function to count group users
count_group_users_core() {
    local groupname="$1"
    local format="$2"
    local primary_only="$3"
    local members_only="$4"
    
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
            # Verify user exists in passwd
            if getent passwd "$user" >/dev/null 2>&1; then
                unique_users+=("$user")
            fi
        fi
    done
    
    # Count members by type for detailed output
    local member_count=0
    local primary_count=0
    local both_count=0
    
    if [[ "$format" == "detailed" ]]; then
        for user in "${unique_users[@]}"; do
            local is_member=false
            local is_primary=false
            
            # Check if user is a direct member
            if [[ " ${direct_members[*]} " =~ " $user " ]]; then
                is_member=true
            fi
            
            # Check if user has this as primary group
            if user_info=$(getent passwd "$user" 2>/dev/null); then
                local user_gid=$(echo "$user_info" | cut -d: -f4)
                if [[ "$user_gid" == "$group_gid" ]]; then
                    is_primary=true
                fi
            fi
            
            # Categorize membership
            if [[ "$is_member" == "true" && "$is_primary" == "true" ]]; then
                ((both_count++))
            elif [[ "$is_member" == "true" ]]; then
                ((member_count++))
            elif [[ "$is_primary" == "true" ]]; then
                ((primary_count++))
            fi
        done
    fi
    
    # Output based on format
    case "$format" in
        "simple")
            echo "${#unique_users[@]}"
            ;;
        "detailed")
            echo "Total users in group '$groupname': ${#unique_users[@]}"
            echo ""
            echo "Breakdown by membership type:"
            echo "  Direct members only:     $member_count"
            echo "  Primary group users only: $primary_count"
            echo "  Both member and primary:  $both_count"
            echo ""
            echo "Summary:"
            echo "  Total direct members:     $((member_count + both_count))"
            echo "  Total primary users:      $((primary_count + both_count))"
            echo "  Total unique users:       ${#unique_users[@]}"
            ;;
    esac
    
    return 0
}