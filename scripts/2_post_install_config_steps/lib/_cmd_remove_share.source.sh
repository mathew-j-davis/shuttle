# Command-specific help functions
show_help_remove_share() {
    cat << EOF
Usage: $SCRIPT_NAME remove-share --name <sharename> [options]

Remove an existing Samba share from configuration.

Required Parameters:
  --name <sharename>    Name of the share to remove

Optional Parameters:
  --force               Remove without confirmation prompt
  --dry-run             Show what would be done without making changes

Examples:
  # Remove share with confirmation
  $SCRIPT_NAME remove-share --name "old-data"
  
  # Remove share without confirmation
  $SCRIPT_NAME remove-share --name "temp-share" --force

Notes:
  - Share configuration is removed from /etc/samba/smb.conf
  - Directory contents are not deleted
  - Samba service restart may be required
  - Backup of smb.conf is created before modification
  - Use list-shares to see available shares
EOF
}

cmd_remove_share() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local sharename=""
    local force=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)
                sharename=$(validate_parameter_value "$1" "${2:-}" "Share name required after --name" "show_help_remove_share")
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
                show_help_remove_share
                return 0
                ;;
            *)
                show_help_remove_share
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$sharename" ]]; then
        show_help_remove_share
        error_exit "Share name is required"
    fi
    
    log_command_call "remove-share" "$original_params"
    
    # Call the core function
    remove_share_core "$sharename" "$force"
    
    return 0
}

# Core function to remove Samba share
remove_share_core() {
    local sharename="$1"
    local force="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "testparm" "manage Samba configuration" "Samba tools not available"
    
    # Check if share exists
    if ! testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
        error_exit "Share '$sharename' does not exist"
    fi
    
    # Get share path for display
    local share_path=""
    if share_path=$(testparm -s 2>/dev/null | sed -n "/^\[$sharename\]/,/^\[/p" | grep "path = " | head -1 | sed 's/.*path = //'); then
        log INFO "Found share '$sharename' at path: $share_path"
    fi
    
    # Confirmation prompt (unless force or dry-run)
    if [[ "$force" != "true" && "$DRY_RUN" != "true" ]]; then
        echo "Are you sure you want to remove share '$sharename'? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log INFO "Share removal cancelled by user"
            return 0
        fi
    fi
    
    log INFO "Removing Samba share '$sharename'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would remove share '$sharename' from /etc/samba/smb.conf"
        if [[ -n "$share_path" ]]; then
            log INFO "[DRY RUN] Directory '$share_path' would remain untouched"
        fi
        return 0
    fi
    
    # Backup smb.conf
    local backup_file="/etc/samba/smb.conf.backup.$(date +%Y%m%d_%H%M%S)"
    if ! execute_or_dryrun "sudo cp /etc/samba/smb.conf '$backup_file'" "Backed up smb.conf to $backup_file" "Failed to backup smb.conf"; then
        error_exit "Failed to backup smb.conf"
    fi
    
    # Remove share section from smb.conf
    # Create temporary file with share section removed
    local temp_file="/tmp/smb.conf.temp.$$"
    if execute_or_dryrun "sudo awk '/^\\[$sharename\\]/ { skip=1; next } /^\\[/ && skip { skip=0 } !skip { print }' /etc/samba/smb.conf > '$temp_file'" "Created temporary file with share removed" "Failed to process smb.conf"; then
        # Replace original file
        if execute_or_dryrun "sudo cp '$temp_file' /etc/samba/smb.conf" "Updated smb.conf with share removed" "Failed to update smb.conf"; then
            execute_or_dryrun "sudo rm -f '$temp_file'" "Cleaned up temporary file" "Failed to clean up temporary file"
            log INFO "Removed share configuration from smb.conf"
        else
            execute_or_dryrun "sudo rm -f '$temp_file'" "Cleaned up temporary file" "Failed to clean up temporary file"
            error_exit "Failed to update smb.conf"
        fi
    else
        execute_or_dryrun "sudo rm -f '$temp_file'" "Cleaned up temporary file" "Failed to clean up temporary file"
        error_exit "Failed to process smb.conf"
    fi
    
    # Test configuration
    if sudo testparm -s >/dev/null 2>&1; then
        log INFO "Samba configuration test passed"
    else
        log ERROR "Samba configuration test failed, restoring backup"
        execute_or_dryrun "sudo cp '$backup_file' /etc/samba/smb.conf" "Restored backup configuration" "Failed to restore backup"
        error_exit "Invalid Samba configuration, backup restored"
    fi
    
    # Verify share was removed
    if testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
        error_exit "Share '$sharename' still exists after removal attempt"
    fi
    
    log INFO "Successfully removed Samba share '$sharename'"
    if [[ -n "$share_path" ]]; then
        log INFO "Note: Directory '$share_path' was not deleted"
    fi
    log INFO "Note: Restart Samba services to deactivate the removed share"
    
    return 0
}