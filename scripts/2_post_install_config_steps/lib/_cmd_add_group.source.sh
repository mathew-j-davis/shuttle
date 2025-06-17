# Input validation library will be loaded by the main script's setup lib loader

# Command-specific help functions
show_help_add_group() {
    cat << EOF
Usage: $SCRIPT_NAME add-group --group <groupname> [options]

Create a new group.

Required Parameters:
  --group <groupname>   Name for the group

Optional Parameters:
  --gid <number>        Specific group ID
  --system              Create system group (GID < 1000)
  --dry-run             Show what would be done without making changes

Examples:
  # Regular group
  $SCRIPT_NAME add-group --group developers
  
  # System group with specific GID
  $SCRIPT_NAME add-group --group docker --system --gid 999
  
  # Application group
  $SCRIPT_NAME add-group --group app-users
EOF
}

cmd_add_group() {
    local groupname=""
    local gid=""
    local system_group=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --group)
                groupname=$(validate_parameter_group "$1" "${2:-}" "show_help_add_group")
                shift 2
                ;;
            --gid)
                gid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_add_group")
                shift 2
                ;;
            --system)
                system_group=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_add_group
                return 0
                ;;
            *)
                show_help_add_group
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$groupname" ]]; then
        show_help_add_group
        error_exit "Group name is required"
    fi
    
    # Note: Input validation is already performed during parameter parsing
    # using validate_parameter_group() and validate_parameter_numeric()
    
    # Check tool availability
    check_tool_permission_or_error_exit "groupadd" "create groups" "groupadd not available - cannot create groups"
    
    # Check if group already exists
    if group_exists "$groupname"; then
        error_exit "Group '$groupname' already exists"
    fi
    
    # Build groupadd command
    local groupadd_cmd="groupadd"
    
    # Add sudo prefix if running as non-root
    groupadd_cmd=$(prefix_if "! check_active_user_is_root" "$groupadd_cmd" "sudo ")
    
    # --system: Create system group (GID < 1000)
    groupadd_cmd=$(append_if_true "$system_group" "$groupadd_cmd" " --system")
    
    # --gid: Specify group ID (quoted for security)
    groupadd_cmd=$(append_if_set "$gid" "$groupadd_cmd" " --gid '$gid'")
    
    # Add groupname as final argument (quoted for security)
    groupadd_cmd="$groupadd_cmd '$groupname'"
    
    # Execute groupadd
    execute_or_dryrun "$groupadd_cmd" "Group '$groupname' created successfully" "Failed to create group '$groupname'" || error_exit "Failed to create group '$groupname'"
    
    return 0
}