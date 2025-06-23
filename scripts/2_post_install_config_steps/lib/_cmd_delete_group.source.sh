# Source input validation library for security
SCRIPT_DIR_FOR_VALIDATION="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")}")"
if [[ -f "$SCRIPT_DIR_FOR_VALIDATION/_input_validation.source.sh" ]]; then
    source "$SCRIPT_DIR_FOR_VALIDATION/_input_validation.source.sh"
fi

# Command-specific help functions
show_help_delete_group() {
    cat << EOF
Usage: $SCRIPT_NAME delete-group --group <groupname> [options]

Delete an existing group.

Required Parameters:
  --group <groupname>   Name of the group to delete

Optional Parameters:
  --force               Delete even if group is primary group for users
  --dry-run             Show what would be done without making changes

Notes:
  - By default, will fail if group is a primary group for any user
  - Use --force with caution as it may leave users without a primary group

Examples:
  # Delete a group
  $SCRIPT_NAME delete-group --group developers
  
  # Force delete even if it's a primary group
  $SCRIPT_NAME delete-group --group oldgroup --force
EOF
}

cmd_delete_group() {
    
    local groupname=""
    local force=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --group)
                groupname=$(validate_parameter_group "$1" "${2:-}" "show_help_delete_group")
                shift 2
                ;;
            --force)
                force=true
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
                show_help_delete_group
                return 0
                ;;
            *)
                show_help_delete_group
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$groupname" ]]; then
        show_help_delete_group
        error_exit "Group name is required"
    fi
    
    # Note: Input validation is already performed during parameter parsing
    # using validate_parameter_group() for group name
    
    # Check tool availability
    check_tool_permission_or_error_exit "groupdel" "delete groups" "groupdel not available - cannot delete groups"
    
    # Check if group exists
    if ! group_exists "$groupname"; then
        error_exit "Group '$groupname' does not exist"
    fi
    
    # Build groupdel command
    local groupdel_cmd="groupdel"
    
    # Add sudo prefix if running as non-root
    groupdel_cmd=$(prefix_if "! check_active_user_is_root" "$groupdel_cmd" "sudo ")
    
    # --force: Delete even if it's a primary group
    groupdel_cmd=$(append_if_true "$force" "$groupdel_cmd" " -f")
    
    # Add groupname as final argument
    groupdel_cmd="$groupdel_cmd $groupname"
    
    # Execute groupdel
    execute_or_dryrun "$groupdel_cmd" "Group '$groupname' deleted successfully" "Failed to delete group '$groupname'" || error_exit "Failed to delete group '$groupname'"
    
    return 0
}