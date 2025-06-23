# Command-specific help functions
show_help_enable_share() {
    cat << EOF
Usage: $SCRIPT_NAME enable-share --name <sharename> [options]

Enable a disabled Samba share by uncommenting its configuration.

Required Parameters:
  --name <sharename>    Name of the share to enable

Optional Parameters:
  --dry-run             Show what would be done without making changes

Examples:
  # Enable a disabled share
  $SCRIPT_NAME enable-share --name "temp-data"

Notes:
  - Share must exist in configuration (but be commented out)
  - Removes comment markers (#) from share section
  - Creates backup of smb.conf before modification
  - Tests configuration after changes
  - Restart Samba services to activate changes
  - Use show-share to verify current status
EOF
}

cmd_enable_share() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local sharename=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)
                sharename=$(validate_parameter_value "$1" "${2:-}" "Share name required after --name" "show_help_enable_share")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_enable_share
                return 0
                ;;
            *)
                show_help_enable_share
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$sharename" ]]; then
        show_help_enable_share
        error_exit "Share name is required"
    fi
    
    log_command_call "enable-share" "$original_params"
    
    # Call the core function
    enable_share_core "$sharename"
    
    return 0
}

# Core function to enable Samba share
enable_share_core() {
    local sharename="$1"
    
    # Check tool availability
    check_tool_permission_or_error_exit "testparm" "manage Samba configuration" "Samba tools not available"
    
    # Check if share exists (enabled or disabled)
    local share_exists=false
    local share_enabled=false
    
    # Check if share is in testparm output (enabled)
    if testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
        share_exists=true
        share_enabled=true
    fi
    
    # Check if share is commented out in smb.conf (disabled)
    if grep -q "^[[:space:]]*#.*\[$sharename\]" /etc/samba/smb.conf 2>/dev/null; then
        share_exists=true
        share_enabled=false
    fi
    
    if [[ "$share_exists" != "true" ]]; then
        error_exit "Share '$sharename' does not exist in configuration"
    fi
    
    if [[ "$share_enabled" == "true" ]]; then
        log INFO "Share '$sharename' is already enabled"
        return 0
    fi
    
    log INFO "Enabling Samba share '$sharename'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would uncomment share '$sharename' in /etc/samba/smb.conf"
        
        # Show what would be changed
        echo "Lines that would be uncommented:"
        grep -n "^[[:space:]]*#.*\[$sharename\]" /etc/samba/smb.conf 2>/dev/null | head -5
        local in_share=false
        while IFS= read -r line; do
            if [[ "$line" =~ ^[[:space:]]*#.*\[${sharename}\]$ ]]; then
                in_share=true
                echo "  $line"
            elif [[ "$line" =~ ^[[:space:]]*#.*\[.*\]$ ]] && [[ "$in_share" == "true" ]]; then
                break
            elif [[ "$in_share" == "true" && "$line" =~ ^[[:space:]]*#.* ]]; then
                echo "  $line"
            elif [[ "$in_share" == "true" && ! "$line" =~ ^[[:space:]]*# ]]; then
                in_share=false
            fi
        done < /etc/samba/smb.conf
        
        return 0
    fi
    
    # Backup smb.conf
    local backup_file="/etc/samba/smb.conf.backup.$(date +%Y%m%d_%H%M%S)"
    if ! execute_or_dryrun "sudo cp /etc/samba/smb.conf '$backup_file'" "Backed up smb.conf to $backup_file" "Failed to backup smb.conf"; then
        error_exit "Failed to backup smb.conf"
    fi
    
    # Create temporary file with share enabled
    local temp_file="/tmp/smb.conf.temp.$$"
    local in_share=false
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:space:]]*#.*\[${sharename}\]$ ]]; then
            # Start of disabled share - uncomment it
            in_share=true
            echo "$line" | sed 's/^[[:space:]]*#[[:space:]]*//' >> "$temp_file"
        elif [[ "$line" =~ ^[[:space:]]*#.*\[.*\]$ ]] && [[ "$in_share" == "true" ]]; then
            # Start of different section - stop uncommenting
            in_share=false
            echo "$line" >> "$temp_file"
        elif [[ "$in_share" == "true" ]]; then
            if [[ "$line" =~ ^[[:space:]]*#.* ]]; then
                # Uncomment line in disabled share
                echo "$line" | sed 's/^[[:space:]]*#[[:space:]]*//' >> "$temp_file"
            else
                # Non-commented line in share section (shouldn't happen but handle it)
                echo "$line" >> "$temp_file"
                in_share=false
            fi
        else
            # Regular line outside target share
            echo "$line" >> "$temp_file"
        fi
    done < /etc/samba/smb.conf
    
    # Replace original file
    if execute_or_dryrun "sudo cp '$temp_file' /etc/samba/smb.conf" "Enabled share '$sharename' in smb.conf" "Failed to update smb.conf"; then
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
    
    # Verify share is now enabled
    if testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
        log INFO "Successfully enabled Samba share '$sharename'"
        log INFO "Note: Restart Samba services to activate the enabled share"
    else
        error_exit "Share '$sharename' not found in active configuration after enabling"
    fi
    
    return 0
}