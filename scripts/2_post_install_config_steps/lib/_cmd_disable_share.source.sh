# Command-specific help functions
show_help_disable_share() {
    cat << EOF
Usage: $SCRIPT_NAME disable-share --name <sharename> [options]

Disable a Samba share by commenting out its configuration.

Required Parameters:
  --name <sharename>    Name of the share to disable

Optional Parameters:
  --force               Disable without confirmation prompt
  --dry-run             Show what would be done without making changes

Examples:
  # Disable a share with confirmation
  $SCRIPT_NAME disable-share --name "temp-data"
  
  # Disable share without confirmation
  $SCRIPT_NAME disable-share --name "old-share" --force

Notes:
  - Share configuration is commented out (not deleted)
  - Can be re-enabled later with enable-share command
  - Creates backup of smb.conf before modification
  - Tests configuration after changes
  - Restart Samba services to deactivate share
  - Directory contents are not affected
EOF
}

cmd_disable_share() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local sharename=""
    local force=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)
                sharename=$(validate_parameter_value "$1" "${2:-}" "Share name required after --name" "show_help_disable_share")
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
            --help|-h)
                show_help_disable_share
                return 0
                ;;
            *)
                show_help_disable_share
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$sharename" ]]; then
        show_help_disable_share
        error_exit "Share name is required"
    fi
    
    log_command_call "disable-share" "$original_params"
    
    # Call the core function
    disable_share_core "$sharename" "$force"
    
    return 0
}

# Core function to disable Samba share
disable_share_core() {
    local sharename="$1"
    local force="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "testparm" "manage Samba configuration" "Samba tools not available"
    
    # Check if share exists and is enabled
    if ! testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
        # Check if it's already disabled
        if grep -q "^[[:space:]]*#.*\[$sharename\]" /etc/samba/smb.conf 2>/dev/null; then
            log INFO "Share '$sharename' is already disabled"
            return 0
        else
            error_exit "Share '$sharename' does not exist"
        fi
    fi
    
    # Get share path for display
    local share_path=""
    if share_path=$(testparm -s 2>/dev/null | sed -n "/^\[$sharename\]/,/^\[/p" | grep "path = " | head -1 | sed 's/.*path = //'); then
        log INFO "Found share '$sharename' at path: $share_path"
    fi
    
    # Confirmation prompt (unless force or dry-run)
    if [[ "$force" != "true" && "$DRY_RUN" != "true" ]]; then
        echo "Are you sure you want to disable share '$sharename'? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log INFO "Share disable cancelled by user"
            return 0
        fi
    fi
    
    log INFO "Disabling Samba share '$sharename'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would comment out share '$sharename' in /etc/samba/smb.conf"
        
        # Show what would be changed
        echo "Lines that would be commented out:"
        local in_share=false
        while IFS= read -r line; do
            if [[ "$line" =~ ^\[${sharename}\]$ ]]; then
                in_share=true
                echo "  # $line"
            elif [[ "$line" =~ ^\[.*\]$ ]] && [[ "$in_share" == "true" ]]; then
                break
            elif [[ "$in_share" == "true" ]]; then
                echo "  # $line"
            fi
        done < /etc/samba/smb.conf
        
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
    
    # Create temporary file with share disabled
    local temp_file="/tmp/smb.conf.temp.$$"
    local in_share=false
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^\[${sharename}\]$ ]]; then
            # Start of target share - comment it out
            in_share=true
            echo "# $line" >> "$temp_file"
        elif [[ "$line" =~ ^\[.*\]$ ]] && [[ "$in_share" == "true" ]]; then
            # Start of different section - stop commenting
            in_share=false
            echo "$line" >> "$temp_file"
        elif [[ "$in_share" == "true" ]]; then
            # Line in target share - comment it out
            if [[ "$line" =~ ^[[:space:]]*$ ]]; then
                # Empty line in share section
                echo "$line" >> "$temp_file"
            else
                # Content line in share section
                echo "# $line" >> "$temp_file"
            fi
        else
            # Regular line outside target share
            echo "$line" >> "$temp_file"
        fi
    done < /etc/samba/smb.conf
    
    # Replace original file
    if execute_or_dryrun "sudo cp '$temp_file' /etc/samba/smb.conf" "Disabled share '$sharename' in smb.conf" "Failed to update smb.conf"; then
        rm -f "$temp_file"
    else
        rm -f "$temp_file"
        error_exit "Failed to update smb.conf"
    fi
    
    # Test configuration
    if sudo testparm -s >/dev/null 2>&1; then
        log INFO "Samba configuration test passed"
    else
        log ERROR "Samba configuration test failed, restoring backup"
        execute_or_dryrun "sudo cp '$backup_file' /etc/samba/smb.conf" "Restored backup configuration" "Failed to restore backup"
        error_exit "Invalid Samba configuration, backup restored"
    fi
    
    # Verify share is now disabled
    if ! testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
        log INFO "Successfully disabled Samba share '$sharename'"
        if [[ -n "$share_path" ]]; then
            log INFO "Note: Directory '$share_path' was not affected"
        fi
        log INFO "Note: Restart Samba services to deactivate the disabled share"
    else
        error_exit "Share '$sharename' still appears active after disabling"
    fi
    
    return 0
}