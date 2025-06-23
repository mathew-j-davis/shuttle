# Command-specific help functions
show_help_add_share() {
    cat << EOF
Usage: $SCRIPT_NAME add-share --name <sharename> --path <directory> [options]

Create a new Samba share.

Required Parameters:
  --name <sharename>    Name of the share (as seen by clients)
  --path <directory>    Local directory path to share

Optional Parameters:
  --comment <text>      Description of the share
  --browseable          Make share visible in network browsing (default: yes)
  --read-only           Make share read-only (default: no)
  --guest-ok            Allow guest access (default: no)
  --valid-users <list>  Comma-separated list of users with access
  --admin-users <list>  Comma-separated list of admin users
  --create-mask <mask>  Default permissions for new files (default: 0644)
  --directory-mask <mask>  Default permissions for new directories (default: 0755)
  --force-user <user>   Force all access as this user
  --force-group <group> Force all access as this group
  --dry-run             Show what would be done without making changes

Examples:
  # Basic share
  $SCRIPT_NAME add-share --name "data" --path "/var/data"
  
  # Read-only share with comment
  $SCRIPT_NAME add-share --name "readonly" --path "/var/readonly" --comment "Read only files" --read-only
  
  # Share with specific users
  $SCRIPT_NAME add-share --name "private" --path "/var/private" --valid-users "alice,bob"
  
  # Share with custom permissions
  $SCRIPT_NAME add-share --name "upload" --path "/var/upload" --create-mask 0664 --directory-mask 0775
  
  # Guest accessible share
  $SCRIPT_NAME add-share --name "public" --path "/var/public" --guest-ok --comment "Public files"

Notes:
  - Share name must be unique
  - Directory path must exist and be accessible
  - User lists should contain existing system users
  - Permissions are in octal format (e.g., 0644, 0755)
  - Configuration is added to /etc/samba/smb.conf
EOF
}

cmd_add_share() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local sharename=""
    local path=""
    local comment=""
    local browseable="yes"
    local read_only="no"
    local guest_ok="no"
    local valid_users=""
    local admin_users=""
    local create_mask="0644"
    local directory_mask="0755"
    local force_user=""
    local force_group=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)
                sharename=$(validate_parameter_value "$1" "${2:-}" "Share name required after --name" "show_help_add_share")
                shift 2
                ;;
            --path)
                path=$(validate_parameter_value "$1" "${2:-}" "Directory path required after --path" "show_help_add_share")
                shift 2
                ;;
            --comment)
                comment=$(validate_parameter_value "$1" "${2:-}" "Comment text required after --comment" "show_help_add_share")
                shift 2
                ;;
            --browseable)
                browseable="yes"
                shift
                ;;
            --read-only)
                read_only="yes"
                shift
                ;;
            --guest-ok)
                guest_ok="yes"
                shift
                ;;
            --valid-users)
                valid_users=$(validate_parameter_value "$1" "${2:-}" "User list required after --valid-users" "show_help_add_share")
                shift 2
                ;;
            --admin-users)
                admin_users=$(validate_parameter_value "$1" "${2:-}" "Admin user list required after --admin-users" "show_help_add_share")
                shift 2
                ;;
            --create-mask)
                create_mask=$(validate_parameter_value "$1" "${2:-}" "Create mask required after --create-mask" "show_help_add_share")
                shift 2
                ;;
            --directory-mask)
                directory_mask=$(validate_parameter_value "$1" "${2:-}" "Directory mask required after --directory-mask" "show_help_add_share")
                shift 2
                ;;
            --force-user)
                force_user=$(validate_parameter_value "$1" "${2:-}" "User name required after --force-user" "show_help_add_share")
                shift 2
                ;;
            --force-group)
                force_group=$(validate_parameter_value "$1" "${2:-}" "Group name required after --force-group" "show_help_add_share")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_add_share
                return 0
                ;;
            *)
                show_help_add_share
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$sharename" ]]; then
        show_help_add_share
        error_exit "Share name is required"
    fi
    
    if [[ -z "$path" ]]; then
        show_help_add_share
        error_exit "Directory path is required"
    fi
    
    log_command_call "add-share" "$original_params"
    
    # Call the core function
    add_share_core "$sharename" "$path" "$comment" "$browseable" "$read_only" "$guest_ok" "$valid_users" "$admin_users" "$create_mask" "$directory_mask" "$force_user" "$force_group"
    
    return 0
}

# Core function to add Samba share
add_share_core() {
    local sharename="$1"
    local path="$2"
    local comment="$3"
    local browseable="$4"
    local read_only="$5"
    local guest_ok="$6"
    local valid_users="$7"
    local admin_users="$8"
    local create_mask="$9"
    local directory_mask="${10}"
    local force_user="${11}"
    local force_group="${12}"
    
    # Check tool availability
    check_tool_permission_or_error_exit "testparm" "manage Samba configuration" "Samba tools not available"
    
    # Validate directory exists
    if [[ ! -d "$path" ]]; then
        error_exit "Directory '$path' does not exist"
    fi
    
    # Check if share already exists
    if [[ "$DRY_RUN" != "true" ]]; then
        if testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
            error_exit "Share '$sharename' already exists"
        fi
    fi
    
    # Validate permissions format
    if [[ ! "$create_mask" =~ ^0[0-7]{3,4}$ ]]; then
        error_exit "Invalid create mask format: $create_mask (should be octal like 0644)"
    fi
    
    if [[ ! "$directory_mask" =~ ^0[0-7]{3,4}$ ]]; then
        error_exit "Invalid directory mask format: $directory_mask (should be octal like 0755)"
    fi
    
    # Build share configuration
    local share_config=""
    share_config="[$sharename]"
    share_config="$share_config\n   path = $path"
    share_config="$share_config\n   browseable = $browseable"
    share_config="$share_config\n   read only = $read_only"
    share_config="$share_config\n   guest ok = $guest_ok"
    share_config="$share_config\n   create mask = $create_mask"
    share_config="$share_config\n   directory mask = $directory_mask"
    
    if [[ -n "$comment" ]]; then
        share_config="$share_config\n   comment = $comment"
    fi
    
    if [[ -n "$valid_users" ]]; then
        share_config="$share_config\n   valid users = $valid_users"
    fi
    
    if [[ -n "$admin_users" ]]; then
        share_config="$share_config\n   admin users = $admin_users"
    fi
    
    if [[ -n "$force_user" ]]; then
        share_config="$share_config\n   force user = $force_user"
    fi
    
    if [[ -n "$force_group" ]]; then
        share_config="$share_config\n   force group = $force_group"
    fi
    
    # Add share to smb.conf
    log INFO "Adding Samba share '$sharename' at path '$path'"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would add the following to /etc/samba/smb.conf:"
        echo -e "$share_config"
    else
        # Backup smb.conf
        local backup_file="/etc/samba/smb.conf.backup.$(date +%Y%m%d_%H%M%S)"
        if ! execute_or_dryrun "sudo cp /etc/samba/smb.conf '$backup_file'" "Backed up smb.conf to $backup_file" "Failed to backup smb.conf"; then
            error_exit "Failed to backup smb.conf"
        fi
        
        # Add share configuration
        if ! execute_or_dryrun "echo -e '\\n$share_config' | sudo tee -a /etc/samba/smb.conf >/dev/null" "Added share configuration to smb.conf" "Failed to add share configuration to smb.conf"; then
            error_exit "Failed to add share configuration to smb.conf"
        fi
        
        # Test configuration
        if sudo testparm -s >/dev/null 2>&1; then
            log INFO "Samba configuration test passed"
        else
            log ERROR "Samba configuration test failed, restoring backup"
            execute_or_dryrun "sudo cp '$backup_file' /etc/samba/smb.conf" "Restored backup configuration" "Failed to restore backup"
            error_exit "Invalid Samba configuration, backup restored"
        fi
        
        log INFO "Successfully added Samba share '$sharename'"
        log INFO "Note: Restart Samba services to activate the new share"
    fi
    
    return 0
}