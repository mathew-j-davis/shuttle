# Command-specific help functions
show_help_list_shares() {
    cat << EOF
Usage: $SCRIPT_NAME list-shares [options]

List all configured Samba shares.

Optional Parameters:
  --format <format>     Output format: simple, detailed, csv, json
  --include-defaults    Include default shares (homes, printers, etc.)
  --sort <field>        Sort by: name, path, status (default: name)
  --reverse             Reverse sort order
  --dry-run             Show what would be done without making changes

Output Formats:
  simple    - Just share names, one per line (default)
  detailed  - Share name, path, status, comment, key settings
  csv       - Comma-separated values with headers
  json      - JSON array of share objects

Examples:
  # List all shares (simple format)
  $SCRIPT_NAME list-shares
  
  # List with detailed information
  $SCRIPT_NAME list-shares --format detailed
  
  # Include default system shares
  $SCRIPT_NAME list-shares --format detailed --include-defaults
  
  # CSV output sorted by path
  $SCRIPT_NAME list-shares --format csv --sort path
  
  # JSON output for automation
  $SCRIPT_NAME list-shares --format json

Notes:
  - Default shares like [homes] and [printers] are hidden unless --include-defaults is used
  - Status shows if share is available/commented out
  - Uses testparm to parse configuration
  - Only shows shares from /etc/samba/smb.conf
EOF
}

cmd_list_shares() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local format="simple"
    local include_defaults=false
    local sort_field="name"
    local reverse_sort=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_list_shares")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "csv" && "$format" != "json" ]]; then
                    show_help_list_shares
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', 'csv', or 'json'"
                fi
                shift 2
                ;;
            --include-defaults)
                include_defaults=true
                shift
                ;;
            --sort)
                sort_field=$(validate_parameter_value "$1" "${2:-}" "Sort field required after --sort" "show_help_list_shares")
                if [[ "$sort_field" != "name" && "$sort_field" != "path" && "$sort_field" != "status" ]]; then
                    show_help_list_shares
                    error_exit "Invalid sort field: $sort_field. Must be 'name', 'path', or 'status'"
                fi
                shift 2
                ;;
            --reverse)
                reverse_sort=true
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
                show_help_list_shares
                return 0
                ;;
            *)
                show_help_list_shares
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    log_command_call "list-shares" "$original_params"
    
    # Call the core function
    list_shares_core "$format" "$include_defaults" "$sort_field" "$reverse_sort"
    
    return 0
}

# Core function to list Samba shares
list_shares_core() {
    local format="$1"
    local include_defaults="$2"
    local sort_field="$3"
    local reverse_sort="$4"
    
    # Check tool availability
    check_tool_permission_or_error_exit "testparm" "read Samba configuration" "Samba tools not available"
    
    # Create array of share objects
    declare -a share_objects=()
    
    # Get shares from testparm output
    local current_share=""
    local share_path=""
    local share_comment=""
    local share_browseable=""
    local share_readonly=""
    local share_guestok=""
    local share_validusers=""
    
    while IFS= read -r line; do
        # Remove leading/trailing whitespace
        line=$(echo "$line" | xargs)
        
        # Check for share section start
        if [[ "$line" =~ ^\[([^\]]+)\]$ ]]; then
            # Process previous share if exists
            if [[ -n "$current_share" ]]; then
                # Skip default shares unless requested
                if [[ "$include_defaults" == "true" ]] || [[ ! "$current_share" =~ ^(global|homes|printers|print\$|netlogon|sysvol)$ ]]; then
                    # Determine status (enabled/disabled)
                    local status="enabled"
                    if grep -q "^[[:space:]]*#.*\[$current_share\]" /etc/samba/smb.conf 2>/dev/null; then
                        status="disabled"
                    fi
                    
                    # Set defaults for missing values
                    [[ -z "$share_path" ]] && share_path="(not set)"
                    [[ -z "$share_comment" ]] && share_comment=""
                    [[ -z "$share_browseable" ]] && share_browseable="yes"
                    [[ -z "$share_readonly" ]] && share_readonly="no"
                    [[ -z "$share_guestok" ]] && share_guestok="no"
                    [[ -z "$share_validusers" ]] && share_validusers=""
                    
                    share_objects+=("$current_share:$share_path:$status:$share_comment:$share_browseable:$share_readonly:$share_guestok:$share_validusers")
                fi
            fi
            
            # Start new share
            current_share="${BASH_REMATCH[1]}"
            share_path=""
            share_comment=""
            share_browseable=""
            share_readonly=""
            share_guestok=""
            share_validusers=""
            
        elif [[ -n "$current_share" && "$current_share" != "global" ]]; then
            # Parse share parameters
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
            fi
        fi
    done < <(testparm -s 2>/dev/null)
    
    # Process last share
    if [[ -n "$current_share" ]]; then
        if [[ "$include_defaults" == "true" ]] || [[ ! "$current_share" =~ ^(global|homes|printers|print\$|netlogon|sysvol)$ ]]; then
            local status="enabled"
            if grep -q "^[[:space:]]*#.*\[$current_share\]" /etc/samba/smb.conf 2>/dev/null; then
                status="disabled"
            fi
            
            [[ -z "$share_path" ]] && share_path="(not set)"
            [[ -z "$share_comment" ]] && share_comment=""
            [[ -z "$share_browseable" ]] && share_browseable="yes"
            [[ -z "$share_readonly" ]] && share_readonly="no"
            [[ -z "$share_guestok" ]] && share_guestok="no"
            [[ -z "$share_validusers" ]] && share_validusers=""
            
            share_objects+=("$current_share:$share_path:$status:$share_comment:$share_browseable:$share_readonly:$share_guestok:$share_validusers")
        fi
    fi
    
    # Sort share objects
    local sort_cmd="sort"
    case "$sort_field" in
        "name")
            sort_cmd="sort -t: -k1,1"
            ;;
        "path")
            sort_cmd="sort -t: -k2,2"
            ;;
        "status")
            sort_cmd="sort -t: -k3,3"
            ;;
    esac
    
    if [[ "$reverse_sort" == "true" ]]; then
        sort_cmd="$sort_cmd -r"
    fi
    
    # Sort the share objects
    local sorted_shares=()
    while IFS= read -r line; do
        sorted_shares+=("$line")
    done < <(printf '%s\n' "${share_objects[@]}" | eval "$sort_cmd")
    
    # Output based on format
    case "$format" in
        "simple")
            for share_obj in "${sorted_shares[@]}"; do
                echo "$(echo "$share_obj" | cut -d: -f1)"
            done
            ;;
        "detailed")
            printf "%-20s %-30s %-10s %-15s %-15s %s\n" "SHARE_NAME" "PATH" "STATUS" "READ_ONLY" "GUEST_OK" "COMMENT"
            printf "%-20s %-30s %-10s %-15s %-15s %s\n" "----------" "----" "------" "---------" "--------" "-------"
            for share_obj in "${sorted_shares[@]}"; do
                IFS=: read -r sharename path status comment browseable readonly guestok validusers <<< "$share_obj"
                
                # Truncate long paths
                local display_path="$path"
                if [[ ${#path} -gt 28 ]]; then
                    display_path="${path:0:25}..."
                fi
                
                printf "%-20s %-30s %-10s %-15s %-15s %s\n" "$sharename" "$display_path" "$status" "$readonly" "$guestok" "$comment"
            done
            ;;
        "csv")
            echo "share_name,path,status,comment,browseable,read_only,guest_ok,valid_users"
            for share_obj in "${sorted_shares[@]}"; do
                IFS=: read -r sharename path status comment browseable readonly guestok validusers <<< "$share_obj"
                echo "\"$sharename\",\"$path\",\"$status\",\"$comment\",\"$browseable\",\"$readonly\",\"$guestok\",\"$validusers\""
            done
            ;;
        "json")
            echo "["
            local first=true
            for share_obj in "${sorted_shares[@]}"; do
                IFS=: read -r sharename path status comment browseable readonly guestok validusers <<< "$share_obj"
                
                if [[ "$first" == "true" ]]; then
                    first=false
                else
                    echo ","
                fi
                
                echo -n "  {"
                echo -n "\"share_name\":\"$sharename\","
                echo -n "\"path\":\"$path\","
                echo -n "\"status\":\"$status\","
                echo -n "\"comment\":\"$comment\","
                echo -n "\"browseable\":\"$browseable\","
                echo -n "\"read_only\":\"$readonly\","
                echo -n "\"guest_ok\":\"$guestok\","
                echo -n "\"valid_users\":\"$validusers\""
                echo -n "}"
            done
            echo ""
            echo "]"
            ;;
    esac
    
    # Show summary in non-simple formats
    if [[ "$format" != "simple" && "$format" != "json" && "$format" != "csv" ]]; then
        echo ""
        echo "Total shares: ${#sorted_shares[@]}"
        
        # Count by status
        local enabled_count=0
        local disabled_count=0
        
        for share_obj in "${sorted_shares[@]}"; do
            local status=$(echo "$share_obj" | cut -d: -f3)
            case "$status" in
                "enabled") ((enabled_count++)) ;;
                "disabled") ((disabled_count++)) ;;
            esac
        done
        
        echo "Enabled shares: $enabled_count"
        echo "Disabled shares: $disabled_count"
    fi
    
    return 0
}