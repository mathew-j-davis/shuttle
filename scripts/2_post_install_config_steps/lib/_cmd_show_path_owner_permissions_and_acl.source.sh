# Command-specific help functions
show_help_show_path_owner_permissions_and_acl() {
    cat << EOF
Usage: $SCRIPT_NAME show-path-owner-permissions-and-acl --path <path> [options]

Display comprehensive ownership, permissions, and ACL information for a file or directory.

Required Parameters:
  --path <path>         Path to analyze

Optional Parameters:
  --recursive           Show information recursively for directories
  --numeric             Show numeric UIDs/GIDs instead of names
  --detailed            Show additional detailed information
  --format <format>     Output format: table, json, csv (default: table)
  --dry-run             Show what would be done without making changes

Examples:
  # Show comprehensive info for a file
  $SCRIPT_NAME show-path-owner-permissions-and-acl --path /home/user/document.txt
  
  # Show info recursively for a directory
  $SCRIPT_NAME show-path-owner-permissions-and-acl --path /var/log --recursive
  
  # Show detailed info with numeric IDs
  $SCRIPT_NAME show-path-owner-permissions-and-acl --path /opt/app --detailed --numeric
  
  # JSON output for automation
  $SCRIPT_NAME show-path-owner-permissions-and-acl --path /etc/passwd --format json

Information Displayed:
  - File/directory path and type
  - Owner (user) and group
  - Traditional Unix permissions (rwx)
  - Octal permission mode
  - Access Control Lists (ACLs) if present
  - Special permission bits (setuid, setgid, sticky)
  - File size and modification time
  - SELinux context (if available)

Notes:
  - Requires getfacl command for ACL information
  - Shows both traditional permissions and extended ACLs
  - Recursive mode processes all files and subdirectories
  - JSON/CSV formats are useful for automation and reporting
EOF
}

cmd_show_path_owner_permissions_and_acl() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local path=""
    local recursive=false
    local numeric=false
    local detailed=false
    local format="table"
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                path=$(validate_parameter_value "$1" "${2:-}" "Path required after --path" "show_help_show_path_owner_permissions_and_acl")
                shift 2
                ;;
            --recursive)
                recursive=true
                shift
                ;;
            --numeric)
                numeric=true
                shift
                ;;
            --detailed)
                detailed=true
                shift
                ;;
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_show_path_owner_permissions_and_acl")
                if [[ "$format" != "table" && "$format" != "json" && "$format" != "csv" ]]; then
                    show_help_show_path_owner_permissions_and_acl
                    error_exit "Invalid format: $format. Must be 'table', 'json', or 'csv'"
                fi
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
                show_help_show_path_owner_permissions_and_acl
                return 0
                ;;
            *)
                show_help_show_path_owner_permissions_and_acl
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$path" ]]; then
        show_help_show_path_owner_permissions_and_acl
        error_exit "Path is required"
    fi
    
    log_command_call "show-path-owner-permissions-and-acl" "$original_params"
    
    # Check tool availability for ACLs
    check_tool_permission_or_error_exit "getfacl" "read ACLs" "getfacl not available - install acl package (ACL information will be skipped)"
    
    # Validate path exists
    if [[ ! -e "$path" ]]; then
        error_exit "Path does not exist: $path"
    fi
    
    # Call the core function
    show_path_owner_permissions_and_acl_core "$path" "$recursive" "$numeric" "$detailed" "$format"
    
    return 0
}

# Core function to display comprehensive path information
show_path_owner_permissions_and_acl_core() {
    local path="$1"
    local recursive="$2"
    local numeric="$3"
    local detailed="$4"
    local format="$5"
    
    # Collect all paths to analyze
    local paths_to_analyze=()
    
    if [[ "$recursive" == "true" && -d "$path" ]]; then
        # Get all files and directories recursively
        while IFS= read -r -d '' file; do
            paths_to_analyze+=("$file")
        done < <(find "$path" -print0 2>/dev/null | sort -z)
    else
        # Just the single path
        paths_to_analyze=("$path")
    fi
    
    # Analyze each path and collect data
    local path_data=()
    
    for current_path in "${paths_to_analyze[@]}"; do
        local path_info=""
        if path_info=$(analyze_single_path "$current_path" "$numeric" "$detailed"); then
            path_data+=("$path_info")
        fi
    done
    
    # Output based on format
    case "$format" in
        "table")
            display_table_format "${path_data[@]}"
            ;;
        "json")
            display_json_format "${path_data[@]}"
            ;;
        "csv")
            display_csv_format "${path_data[@]}"
            ;;
    esac
    
    return 0
}

# Function to analyze a single path and return structured data
analyze_single_path() {
    local path="$1"
    local numeric="$2"
    local detailed="$3"
    
    # Get basic file information
    local stat_info=""
    if ! stat_info=$(stat -c "%n|%F|%U|%G|%u|%g|%a|%A|%s|%Y" "$path" 2>/dev/null); then
        log WARN "Could not get stat information for: $path"
        return 1
    fi
    
    # Parse stat output
    IFS='|' read -r file_path file_type owner_name group_name owner_uid group_gid octal_perms symbolic_perms size mtime <<< "$stat_info"
    
    # Use numeric IDs if requested
    local display_owner="$owner_name"
    local display_group="$group_name"
    if [[ "$numeric" == "true" ]]; then
        display_owner="$owner_uid"
        display_group="$group_gid"
    fi
    
    # Get ACL information if available
    local has_acl="false"
    local acl_entries=""
    if command -v getfacl >/dev/null 2>&1; then
        local acl_output=""
        if acl_output=$(getfacl --omit-header "$path" 2>/dev/null); then
            # Check if there are extended ACLs (more than just owner/group/other)
            local acl_line_count=$(echo "$acl_output" | wc -l)
            if [[ $acl_line_count -gt 3 ]]; then
                has_acl="true"
                # Get non-standard ACL entries
                acl_entries=$(echo "$acl_output" | grep -v "^user::.*\|^group::.*\|^other::.*" | tr '\n' ';' | sed 's/;$//')
            fi
        fi
    fi
    
    # Get SELinux context if available
    local selinux_context=""
    if command -v ls >/dev/null 2>&1 && ls -Z "$path" >/dev/null 2>&1; then
        selinux_context=$(ls -dZ "$path" 2>/dev/null | awk '{print $1}' | grep -v "^?")
    fi
    
    # Format modification time
    local formatted_mtime=""
    if [[ -n "$mtime" ]]; then
        formatted_mtime=$(date -d "@$mtime" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$mtime")
    fi
    
    # Analyze special permissions
    local special_perms=""
    if [[ "$symbolic_perms" =~ s.*s.*t ]]; then
        special_perms="setuid,setgid,sticky"
    elif [[ "$symbolic_perms" =~ s.*s ]]; then
        special_perms="setuid,setgid"
    elif [[ "$symbolic_perms" =~ s ]]; then
        special_perms="setuid"
    elif [[ "$symbolic_perms" =~ S ]]; then
        special_perms="setgid"
    elif [[ "$symbolic_perms" =~ t ]]; then
        special_perms="sticky"
    fi
    
    # Create structured data string (pipe-separated for easy parsing)
    echo "$file_path|$file_type|$display_owner|$display_group|$owner_uid|$group_gid|$octal_perms|$symbolic_perms|$size|$formatted_mtime|$has_acl|$acl_entries|$selinux_context|$special_perms"
}

# Function to display data in table format
display_table_format() {
    local path_data=("$@")
    
    if [[ ${#path_data[@]} -eq 0 ]]; then
        echo "No data to display"
        return
    fi
    
    echo ""
    echo "=== Path Ownership, Permissions, and ACL Information ==="
    echo ""
    
    # Header
    printf "%-40s %-10s %-12s %-12s %-6s %-12s %-6s %-8s %-19s %-6s\n" \
        "PATH" "TYPE" "OWNER" "GROUP" "OCTAL" "PERMISSIONS" "SIZE" "HAS_ACL" "MODIFIED" "SPECIAL"
    printf "%-40s %-10s %-12s %-12s %-6s %-12s %-6s %-8s %-19s %-6s\n" \
        "----" "----" "-----" "-----" "-----" "-----------" "----" "-------" "--------" "-------"
    
    # Data rows
    for data in "${path_data[@]}"; do
        IFS='|' read -r file_path file_type owner group owner_uid group_gid octal_perms symbolic_perms size mtime has_acl acl_entries selinux_context special_perms <<< "$data"
        
        # Truncate long paths for display
        local display_path="$file_path"
        if [[ ${#display_path} -gt 38 ]]; then
            display_path="...${display_path: -35}"
        fi
        
        # Truncate long usernames/groups
        if [[ ${#owner} -gt 10 ]]; then
            owner="${owner:0:9}+"
        fi
        if [[ ${#group} -gt 10 ]]; then
            group="${group:0:9}+"
        fi
        
        # Format file size
        local display_size="$size"
        if [[ "$size" -gt 1048576 ]]; then
            display_size="$((size / 1048576))M"
        elif [[ "$size" -gt 1024 ]]; then
            display_size="$((size / 1024))K"
        fi
        
        printf "%-40s %-10s %-12s %-12s %-6s %-12s %-6s %-8s %-19s %-6s\n" \
            "$display_path" "$file_type" "$owner" "$group" "$octal_perms" "$symbolic_perms" "$display_size" "$has_acl" "$mtime" "$special_perms"
        
        # Show ACL details if present
        if [[ "$has_acl" == "true" && -n "$acl_entries" ]]; then
            echo "  ACLs: $(echo "$acl_entries" | tr ';' ' ')"
        fi
        
        # Show SELinux context if present
        if [[ -n "$selinux_context" ]]; then
            echo "  SELinux: $selinux_context"
        fi
    done
    
    echo ""
    echo "Total items: ${#path_data[@]}"
}

# Function to display data in JSON format
display_json_format() {
    local path_data=("$@")
    
    echo "["
    local first=true
    
    for data in "${path_data[@]}"; do
        IFS='|' read -r file_path file_type owner group owner_uid group_gid octal_perms symbolic_perms size mtime has_acl acl_entries selinux_context special_perms <<< "$data"
        
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        
        echo -n "  {"
        echo -n "\"path\":\"$file_path\","
        echo -n "\"type\":\"$file_type\","
        echo -n "\"owner\":\"$owner\","
        echo -n "\"group\":\"$group\","
        echo -n "\"owner_uid\":$owner_uid,"
        echo -n "\"group_gid\":$group_gid,"
        echo -n "\"octal_permissions\":\"$octal_perms\","
        echo -n "\"symbolic_permissions\":\"$symbolic_perms\","
        echo -n "\"size\":$size,"
        echo -n "\"modified\":\"$mtime\","
        echo -n "\"has_acl\":$has_acl,"
        
        if [[ -n "$acl_entries" ]]; then
            local acl_json="["
            local acl_first=true
            IFS=';' read -ra acl_array <<< "$acl_entries"
            for acl_entry in "${acl_array[@]}"; do
                if [[ "$acl_first" == "true" ]]; then
                    acl_first=false
                else
                    acl_json+=","
                fi
                acl_json+="\"$acl_entry\""
            done
            acl_json+="]"
            echo -n "\"acl_entries\":$acl_json,"
        else
            echo -n "\"acl_entries\":[],"
        fi
        
        echo -n "\"selinux_context\":\"$selinux_context\","
        echo -n "\"special_permissions\":\"$special_perms\""
        echo -n "}"
    done
    
    echo ""
    echo "]"
}

# Function to display data in CSV format
display_csv_format() {
    local path_data=("$@")
    
    # Header
    echo "path,type,owner,group,owner_uid,group_gid,octal_permissions,symbolic_permissions,size,modified,has_acl,acl_entries,selinux_context,special_permissions"
    
    # Data rows
    for data in "${path_data[@]}"; do
        IFS='|' read -r file_path file_type owner group owner_uid group_gid octal_perms symbolic_perms size mtime has_acl acl_entries selinux_context special_perms <<< "$data"
        
        # Escape commas and quotes in CSV
        file_path=$(echo "$file_path" | sed 's/"/\\""/g')
        acl_entries=$(echo "$acl_entries" | sed 's/"/\\""/g')
        
        echo "\"$file_path\",\"$file_type\",\"$owner\",\"$group\",$owner_uid,$group_gid,\"$octal_perms\",\"$symbolic_perms\",$size,\"$mtime\",$has_acl,\"$acl_entries\",\"$selinux_context\",\"$special_perms\""
    done
}