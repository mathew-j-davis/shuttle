# Command-specific help functions
show_help_show_group() {
    cat << EOF
Usage: $SCRIPT_NAME show-group --group <groupname> [options]

Display detailed information about a group.

Required Parameters:
  --group <groupname>   Group name to show information for

Optional Parameters:
  --members             Show group members
  --verbose             Show additional details
  --dry-run             Show what would be done without making changes

Examples:
  # Show basic group information
  $SCRIPT_NAME show-group --group developers
  
  # Show group with members
  $SCRIPT_NAME show-group --group sudo --members
  
  # Show verbose group information
  $SCRIPT_NAME show-group --group docker --verbose --members

Information Displayed:
  - Group name and GID
  - Group type (system vs user group)
  - Member count
  - Group members (if --members specified)
  - Primary group users (users who have this as their primary group)
  - Group description (if available)

Notes:
  - Uses getent to query group information
  - Shows both direct members and users with this as primary group
  - System groups typically have GID < 1000
EOF
}

cmd_show_group() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local groupname=""
    local show_members=false
    local verbose=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --group)
                groupname=$(validate_parameter_value "$1" "${2:-}" "Group name required after --group" "show_help_show_group")
                shift 2
                ;;
            --members)
                show_members=true
                shift
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_show_group
                return 0
                ;;
            *)
                show_help_show_group
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$groupname" ]]; then
        show_help_show_group
        error_exit "Group name is required"
    fi
    
    echo "show-group command called with parameters: $original_params"
    
    # Check if group exists
    if ! group_exists "$groupname"; then
        error_exit "Group '$groupname' does not exist"
    fi
    
    # Call the core function
    show_group_info_core "$groupname" "$show_members" "$verbose"
    
    return 0
}

# Core function to display group information
show_group_info_core() {
    local groupname="$1"
    local show_members="$2"
    local verbose="$3"
    
    # Get group information
    local group_info=""
    if ! group_info=$(getent group "$groupname" 2>/dev/null); then
        log ERROR "Failed to get group information for '$groupname'"
        return 1
    fi
    
    # Parse group information (format: groupname:password:gid:members)
    local group_name=$(echo "$group_info" | cut -d: -f1)
    local group_gid=$(echo "$group_info" | cut -d: -f3)
    local group_members_raw=$(echo "$group_info" | cut -d: -f4)
    
    # Convert comma-separated members to array
    local group_members=()
    if [[ -n "$group_members_raw" ]]; then
        IFS=',' read -ra group_members <<< "$group_members_raw"
    fi
    
    # Determine group type
    local group_type="User Group"
    if [[ "$group_gid" -lt 1000 ]]; then
        group_type="System Group"
    fi
    
    # Display basic group information
    echo ""
    echo "=== Group Information ==="
    echo "Group Name:       $group_name"
    echo "Group ID (GID):   $group_gid"
    echo "Group Type:       $group_type"
    echo "Direct Members:   ${#group_members[@]}"
    
    # Find users who have this group as their primary group
    local primary_users=()
    while IFS=: read -r username _ uid gid _ _ _; do
        if [[ "$gid" == "$group_gid" ]]; then
            primary_users+=("$username")
        fi
    done < <(getent passwd)
    
    echo "Primary Users:    ${#primary_users[@]} (users with this as primary group)"
    
    if [[ "$verbose" == "true" ]]; then
        echo ""
        echo "=== Detailed Information ==="
        
        # Show group line from /etc/group or getent
        echo "Group Entry:      $group_info"
        
        # Show if group is referenced in any special files
        if [[ -f /etc/sudoers ]] && sudo grep -q "^%$groupname" /etc/sudoers 2>/dev/null; then
            echo "Sudo Access:      Yes (group has sudo privileges)"
        elif [[ -f /etc/sudoers.d ]] && sudo find /etc/sudoers.d -type f -exec grep -l "^%$groupname" {} \; 2>/dev/null | head -1 >/dev/null; then
            echo "Sudo Access:      Yes (group has sudo privileges)"
        else
            echo "Sudo Access:      No"
        fi
        
        # Check if group owns any important directories
        local owned_dirs=""
        if owned_dirs=$(find /home /var /opt /usr/local -maxdepth 2 -group "$groupname" -type d 2>/dev/null | head -5); then
            if [[ -n "$owned_dirs" ]]; then
                echo "Owned Directories: (showing first 5)"
                echo "$owned_dirs" | sed 's/^/                  /'
            fi
        fi
    fi
    
    if [[ "$show_members" == "true" ]]; then
        echo ""
        echo "=== Group Membership ==="
        
        if [[ ${#group_members[@]} -gt 0 ]]; then
            echo "Direct Members:"
            for member in "${group_members[@]}"; do
                member=$(echo "$member" | xargs)  # Trim whitespace
                if [[ -n "$member" ]]; then
                    # Check if user exists and get additional info
                    if user_info=$(getent passwd "$member" 2>/dev/null); then
                        local user_uid=$(echo "$user_info" | cut -d: -f3)
                        local user_home=$(echo "$user_info" | cut -d: -f6)
                        local user_shell=$(echo "$user_info" | cut -d: -f7)
                        echo "  - $member (UID: $user_uid, Home: $user_home, Shell: $user_shell)"
                    else
                        echo "  - $member (user not found - may be deleted)"
                    fi
                fi
            done
        else
            echo "Direct Members:   None"
        fi
        
        if [[ ${#primary_users[@]} -gt 0 ]]; then
            echo ""
            echo "Primary Group Users:"
            for user in "${primary_users[@]}"; do
                if user_info=$(getent passwd "$user" 2>/dev/null); then
                    local user_uid=$(echo "$user_info" | cut -d: -f3)
                    local user_home=$(echo "$user_info" | cut -d: -f6)
                    echo "  - $user (UID: $user_uid, Home: $user_home)"
                fi
            done
        else
            echo "Primary Group Users: None"
        fi
        
        # Show total unique users with access to this group
        local all_users=()
        all_users+=("${group_members[@]}")
        all_users+=("${primary_users[@]}")
        
        # Remove duplicates and count
        local unique_users=()
        for user in "${all_users[@]}"; do
            user=$(echo "$user" | xargs)  # Trim whitespace
            if [[ -n "$user" ]] && [[ ! " ${unique_users[*]} " =~ " $user " ]]; then
                unique_users+=("$user")
            fi
        done
        
        echo ""
        echo "Total Users with Group Access: ${#unique_users[@]}"
    fi
    
    echo ""
    return 0
}