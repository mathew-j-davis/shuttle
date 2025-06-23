# Source input validation library for security
SCRIPT_DIR_FOR_VALIDATION="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")}")"
if [[ -f "$SCRIPT_DIR_FOR_VALIDATION/_input_validation.source.sh" ]]; then
    source "$SCRIPT_DIR_FOR_VALIDATION/_input_validation.source.sh"
fi

# Command-specific help functions
show_help_modify_group() {
    cat << EOF
Usage: $SCRIPT_NAME modify-group --group <groupname> [options]

Modify an existing group.

Required Parameters:
  --group <groupname>   Name of the group to modify

Optional Parameters:
  --new-name <name>     Rename the group
  --gid <number>        Change the group ID
  --dry-run             Show what would be done without making changes

Notes:
  - At least one modification option must be specified
  - Renaming a group does not affect file ownership (files keep the same GID)
  - Changing GID will update file ownership automatically

Examples:
  # Rename a group
  $SCRIPT_NAME modify-group --group oldname --new-name newname
  
  # Change group ID
  $SCRIPT_NAME modify-group --group developers --gid 2000
  
  # Rename and change GID
  $SCRIPT_NAME modify-group --group temp-group --new-name app-group --gid 2001
EOF
}

cmd_modify_group() {
    
    local groupname=""
    local new_name=""
    local gid=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --group)
                groupname=$(validate_parameter_group "$1" "${2:-}" "show_help_modify_group")
                shift 2
                ;;
            --new-name)
                new_name=$(validate_parameter_group "$1" "${2:-}" "show_help_modify_group")
                shift 2
                ;;
            --gid)
                gid=$(validate_parameter_numeric "$1" "${2:-}" "show_help_modify_group")
                shift 2
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
                show_help_modify_group
                return 0
                ;;
            *)
                show_help_modify_group
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$groupname" ]]; then
        show_help_modify_group
        error_exit "Group name is required"
    fi
    
    # Ensure at least one modification is requested
    if [[ -z "$new_name" && -z "$gid" ]]; then
        show_help_modify_group
        error_exit "At least one modification option (--new-name or --gid) must be specified"
    fi
    
    # Note: Input validation is already performed during parameter parsing using:
    # - validate_parameter_group() for group name and new name
    # - validate_parameter_numeric() for GID
    
    # Check tool availability
    check_tool_permission_or_error_exit "groupmod" "modify groups" "groupmod not available - cannot modify groups"
    
    # Check if group exists
    if ! group_exists "$groupname"; then
        error_exit "Group '$groupname' does not exist"
    fi
    
    # Check if new name already exists (if renaming)
    if [[ -n "$new_name" ]] && group_exists "$new_name"; then
        error_exit "Group '$new_name' already exists"
    fi
    
    # Build groupmod command
    local groupmod_cmd="groupmod"
    
    # Add sudo prefix if running as non-root
    groupmod_cmd=$(prefix_if "! check_active_user_is_root" "$groupmod_cmd" "sudo ")
    
    # --new-name: Rename the group
    groupmod_cmd=$(append_if_set "$new_name" "$groupmod_cmd" " --new-name $new_name")
    
    # --gid: Change group ID
    groupmod_cmd=$(append_if_set "$gid" "$groupmod_cmd" " --gid $gid")
    
    # Add groupname as final argument
    groupmod_cmd="$groupmod_cmd $groupname"
    
    # Execute groupmod
    execute_or_dryrun "$groupmod_cmd" "Group '$groupname' modified successfully" "Failed to modify group '$groupname'" || error_exit "Failed to modify group '$groupname'"
    
    return 0
}