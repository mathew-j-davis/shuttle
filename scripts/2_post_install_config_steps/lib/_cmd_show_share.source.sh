# Command-specific help functions
show_help_show_share() {
    cat << EOF
Usage: $SCRIPT_NAME show-share --name <sharename> [options]

Display detailed information about a specific Samba share.

Required Parameters:
  --name <sharename>    Name of the share to display

Optional Parameters:
  --verbose             Show additional configuration details
  --dry-run             Show what would be done without making changes

Examples:
  # Show basic share information
  $SCRIPT_NAME show-share --name "data"
  
  # Show detailed configuration
  $SCRIPT_NAME show-share --name "private" --verbose

Information Displayed:
  - Share name and status (enabled/disabled)
  - Directory path and accessibility
  - Access permissions and restrictions
  - User access controls
  - File creation settings
  - Additional configuration options (verbose mode)

Notes:
  - Uses testparm to parse share configuration
  - Shows actual effective configuration
  - Checks directory accessibility
  - Displays both configured and default values
EOF
}

cmd_show_share() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local sharename=""
    local verbose=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)
                sharename=$(validate_parameter_value "$1" "${2:-}" "Share name required after --name" "show_help_show_share")
                shift 2
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
                show_help_show_share
                return 0
                ;;
            *)
                show_help_show_share
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$sharename" ]]; then
        show_help_show_share
        error_exit "Share name is required"
    fi
    
    echo "show-share command called with parameters: $original_params"
    
    # Call the core function
    show_share_core "$sharename" "$verbose"
    
    return 0
}

# Core function to show Samba share details
show_share_core() {
    local sharename="$1"
    local verbose="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "testparm" "read Samba configuration" "Samba tools not available"
    
    # Check if share exists
    if ! testparm -s 2>/dev/null | grep -q "^\[$sharename\]"; then
        error_exit "Share '$sharename' does not exist"
    fi
    
    # Extract share configuration
    local share_config=""
    local in_share=false
    local share_path=""
    local share_comment=""
    local share_browseable=""
    local share_readonly=""
    local share_guestok=""
    local share_validusers=""
    local share_adminusers=""
    local share_createmask=""
    local share_directorymask=""
    local share_forceuser=""
    local share_forcegroup=""
    local share_writelist=""
    local share_readlist=""
    
    while IFS= read -r line; do
        line=$(echo "$line" | xargs)  # Trim whitespace
        
        if [[ "$line" == "[$sharename]" ]]; then
            in_share=true
            continue
        elif [[ "$line" =~ ^\[.*\]$ ]] && [[ "$in_share" == "true" ]]; then
            break
        elif [[ "$in_share" == "true" ]]; then
            # Parse configuration parameters
            if [[ "$line" =~ ^path[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_path="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^comment[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_comment="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^browseable[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_browseable="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^read[[:space:]]+only[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_readonly="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^guest[[:space:]]+ok[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_guestok="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^valid[[:space:]]+users[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_validusers="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^admin[[:space:]]+users[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_adminusers="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^create[[:space:]]+mask[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_createmask="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^directory[[:space:]]+mask[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_directorymask="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^force[[:space:]]+user[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_forceuser="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^force[[:space:]]+group[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_forcegroup="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^write[[:space:]]+list[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_writelist="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^read[[:space:]]+list[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                share_readlist="${BASH_REMATCH[1]}"
            fi
        fi
    done < <(testparm -s 2>/dev/null)
    
    # Check if share is disabled (commented out)
    local share_status="enabled"
    if grep -q "^[[:space:]]*#.*\[$sharename\]" /etc/samba/smb.conf 2>/dev/null; then
        share_status="disabled"
    fi
    
    # Display share information
    echo ""
    echo "=== Share Information ==="
    echo "Share Name:       $sharename"
    echo "Status:           $share_status"
    echo "Path:             ${share_path:-'(not set)'}"
    echo "Comment:          ${share_comment:-'(none)'}"
    echo ""
    
    # Check directory status
    if [[ -n "$share_path" && "$share_path" != "(not set)" ]]; then
        echo "=== Directory Status ==="
        if [[ -d "$share_path" ]]; then
            local dir_perms=$(stat -c "%a" "$share_path" 2>/dev/null)
            local dir_owner=$(stat -c "%U:%G" "$share_path" 2>/dev/null)
            echo "Directory:        Exists"
            echo "Permissions:      $dir_perms"
            echo "Owner:            $dir_owner"
            
            # Check accessibility
            if [[ -r "$share_path" ]]; then
                echo "Readable:         Yes"
            else
                echo "Readable:         No"
            fi
            
            if [[ -w "$share_path" ]]; then
                echo "Writable:         Yes"
            else
                echo "Writable:         No"
            fi
        else
            echo "Directory:        Does not exist"
        fi
        echo ""
    fi
    
    # Display access configuration
    echo "=== Access Configuration ==="
    echo "Browseable:       ${share_browseable:-'yes (default)'}"
    echo "Read Only:        ${share_readonly:-'no (default)'}"
    echo "Guest Access:     ${share_guestok:-'no (default)'}"
    echo "Valid Users:      ${share_validusers:-'(all users)'}"
    echo "Admin Users:      ${share_adminusers:-'(none)'}"
    
    if [[ -n "$share_writelist" ]]; then
        echo "Write List:       $share_writelist"
    fi
    
    if [[ -n "$share_readlist" ]]; then
        echo "Read List:        $share_readlist"
    fi
    echo ""
    
    # Display file creation settings
    echo "=== File Creation Settings ==="
    echo "Create Mask:      ${share_createmask:-'0644 (default)'}"
    echo "Directory Mask:   ${share_directorymask:-'0755 (default)'}"
    
    if [[ -n "$share_forceuser" ]]; then
        echo "Force User:       $share_forceuser"
    fi
    
    if [[ -n "$share_forcegroup" ]]; then
        echo "Force Group:      $share_forcegroup"
    fi
    echo ""
    
    # Verbose information
    if [[ "$verbose" == "true" ]]; then
        echo "=== Additional Configuration ==="
        
        # Get raw configuration section
        echo "Raw Configuration:"
        local config_section=""
        local in_section=false
        
        while IFS= read -r line; do
            if [[ "$line" =~ ^\[${sharename}\]$ ]]; then
                in_section=true
                config_section="$config_section$line\n"
            elif [[ "$line" =~ ^\[.*\]$ ]] && [[ "$in_section" == "true" ]]; then
                break
            elif [[ "$in_section" == "true" ]]; then
                config_section="$config_section$line\n"
            fi
        done < /etc/samba/smb.conf
        
        echo -e "$config_section" | sed 's/^/  /'
        echo ""
        
        # Show effective configuration from testparm
        echo "Effective Configuration (via testparm):"
        testparm -s 2>/dev/null | sed -n "/^\[$sharename\]/,/^\[/p" | head -n -1 | sed 's/^/  /'
        echo ""
    fi
    
    return 0
}