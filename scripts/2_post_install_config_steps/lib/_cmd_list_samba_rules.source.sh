# Command-specific help functions
show_help_list_samba_rules() {
    cat << EOF
Usage: $SCRIPT_NAME list-samba-rules [options]

List current firewall rules related to Samba traffic.

Optional Parameters:
  --format <format>     Output format (simple, detailed, json - default: detailed)
  --source <ip/network> Filter by source IP/network
  --port <port>         Filter by specific port
  --protocol <protocol> Filter by protocol (tcp, udp, both - default: both)
  --verbose             Show additional rule details
  --dry-run             Show what would be done without making changes

Examples:
  # List all Samba rules
  $SCRIPT_NAME list-samba-rules
  
  # List rules with simple format
  $SCRIPT_NAME list-samba-rules --format simple
  
  # List rules from specific network
  $SCRIPT_NAME list-samba-rules --source "192.168.1.0/24"
  
  # List rules for specific port
  $SCRIPT_NAME list-samba-rules --port 445
  
  # List TCP rules only
  $SCRIPT_NAME list-samba-rules --protocol tcp
  
  # Export rules as JSON
  $SCRIPT_NAME list-samba-rules --format json

Output Formats:
  simple    - One rule per line with basic info
  detailed  - Formatted table with full details (default)
  json      - Machine-readable JSON format

Information Displayed:
  - Rule number/ID
  - Source IP/network
  - Protocol and port
  - Action (allow/deny)
  - Comment/description
  - Rule status (active/inactive)

Notes:
  - Shows rules for all Samba ports (445, 139, 137, 138)
  - Firewall type is auto-detected
  - Filters are applied after rule collection
  - Use --verbose for additional rule metadata
EOF
}

cmd_list_samba_rules() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local format="detailed"
    local source_filter=""
    local port_filter=""
    local protocol_filter="both"
    local verbose=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_list_samba_rules")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "json" ]]; then
                    show_help_list_samba_rules
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', or 'json'"
                fi
                shift 2
                ;;
            --source)
                source_filter=$(validate_parameter_value "$1" "${2:-}" "Source IP/network required after --source" "show_help_list_samba_rules")
                shift 2
                ;;
            --port)
                port_filter=$(validate_parameter_value "$1" "${2:-}" "Port required after --port" "show_help_list_samba_rules")
                shift 2
                ;;
            --protocol)
                protocol_filter=$(validate_parameter_value "$1" "${2:-}" "Protocol required after --protocol" "show_help_list_samba_rules")
                if [[ "$protocol_filter" != "tcp" && "$protocol_filter" != "udp" && "$protocol_filter" != "both" ]]; then
                    show_help_list_samba_rules
                    error_exit "Invalid protocol: $protocol_filter. Must be 'tcp', 'udp', or 'both'"
                fi
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
                show_help_list_samba_rules
                return 0
                ;;
            *)
                show_help_list_samba_rules
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    log_command_call "list-samba-rules" "$original_params"
    
    # Call the core function
    list_samba_rules_core "$format" "$source_filter" "$port_filter" "$protocol_filter" "$verbose"
    
    return 0
}

# Core function to list Samba firewall rules
list_samba_rules_core() {
    local format="$1"
    local source_filter="$2"
    local port_filter="$3"
    local protocol_filter="$4"
    local verbose="$5"
    
    # Auto-detect firewall if not already detected
    if [[ -z "${DETECTED_FIREWALL:-}" ]]; then
        log INFO "Auto-detecting firewall type..."
        detect_firewall_core false >/dev/null
    fi
    
    local firewall_type="${DETECTED_FIREWALL:-none}"
    if [[ "$firewall_type" == "none" ]]; then
        error_exit "No active firewall detected. Run 'detect-firewall' first or enable a firewall."
    fi
    
    log INFO "Listing Samba rules for firewall type: $firewall_type"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        echo "[DRY RUN] Would list Samba firewall rules:"
        echo "  Firewall type: $firewall_type"
        echo "  Output format: $format"
        [[ -n "$source_filter" ]] && echo "  Source filter: $source_filter"
        [[ -n "$port_filter" ]] && echo "  Port filter: $port_filter"
        echo "  Protocol filter: $protocol_filter"
        echo "  Verbose mode: $verbose"
        return 0
    fi
    
    # Define Samba ports to look for
    local samba_ports=("445" "139" "137" "138")
    
    # Collect rules based on firewall type
    local rules_data=""
    case "$firewall_type" in
        "ufw")
            rules_data=$(collect_ufw_samba_rules "${samba_ports[@]}")
            ;;
        "firewalld")
            rules_data=$(collect_firewalld_samba_rules "${samba_ports[@]}")
            ;;
        "iptables")
            rules_data=$(collect_iptables_samba_rules "${samba_ports[@]}")
            ;;
        *)
            error_exit "Unsupported firewall type: $firewall_type"
            ;;
    esac
    
    # Apply filters
    if [[ -n "$source_filter" || -n "$port_filter" || "$protocol_filter" != "both" ]]; then
        rules_data=$(filter_samba_rules "$rules_data" "$source_filter" "$port_filter" "$protocol_filter")
    fi
    
    # Output results
    if [[ -z "$rules_data" ]]; then
        echo ""
        echo "No Samba firewall rules found"
        if [[ -n "$source_filter" || -n "$port_filter" || "$protocol_filter" != "both" ]]; then
            echo "This may be due to the applied filters:"
            [[ -n "$source_filter" ]] && echo "  Source filter: $source_filter"
            [[ -n "$port_filter" ]] && echo "  Port filter: $port_filter"
            [[ "$protocol_filter" != "both" ]] && echo "  Protocol filter: $protocol_filter"
        fi
        return 0
    fi
    
    # Format and display results
    case "$format" in
        "simple")
            format_samba_rules_simple "$rules_data"
            ;;
        "detailed")
            format_samba_rules_detailed "$rules_data" "$verbose"
            ;;
        "json")
            format_samba_rules_json "$rules_data"
            ;;
    esac
    
    # Count and summary
    local rule_count=$(echo "$rules_data" | wc -l)
    echo ""
    log INFO "Found $rule_count Samba firewall rule(s)"
    
    return 0
}

# Collect UFW Samba rules
collect_ufw_samba_rules() {
    local samba_ports=("$@")
    local rules=""
    
    # Get UFW status with numbered rules
    local ufw_output=$(ufw status numbered 2>/dev/null)
    
    for port in "${samba_ports[@]}"; do
        # Look for rules matching Samba ports
        local port_rules=$(echo "$ufw_output" | grep -E "($port/tcp|$port/udp)" | while read -r line; do
            # Parse UFW rule format: [ 1] 445/tcp ALLOW IN 192.168.1.0/24
            if [[ "$line" =~ ^\[\ *([0-9]+)\]\ +([0-9]+)/(tcp|udp)\ +(ALLOW|DENY)\ +(IN|OUT)\ +(.+)$ ]]; then
                local rule_num="${BASH_REMATCH[1]}"
                local rule_port="${BASH_REMATCH[2]}"
                local rule_proto="${BASH_REMATCH[3]}"
                local rule_action="${BASH_REMATCH[4]}"
                local rule_direction="${BASH_REMATCH[5]}"
                local rule_source="${BASH_REMATCH[6]}"
                
                # Extract comment if present
                local rule_comment=""
                if [[ "$rule_source" =~ (.+)\ +#\ +(.+) ]]; then
                    rule_source="${BASH_REMATCH[1]}"
                    rule_comment="${BASH_REMATCH[2]}"
                fi
                
                echo "ufw|$rule_num|$rule_source|$rule_proto|$rule_port|$rule_action|$rule_comment|active"
            fi
        done)
        
        [[ -n "$port_rules" ]] && rules+="$port_rules"$'\n'
    done
    
    echo "$rules"
}

# Collect Firewalld Samba rules
collect_firewalld_samba_rules() {
    local samba_ports=("$@")
    local rules=""
    
    # Get rich rules that might contain Samba ports
    local rich_rules=$(firewall-cmd --list-rich-rules 2>/dev/null)
    
    local rule_num=1
    while IFS= read -r rule; do
        [[ -z "$rule" ]] && continue
        
        for port in "${samba_ports[@]}"; do
            if echo "$rule" | grep -q "port=\"$port\""; then
                # Parse rich rule: rule family="ipv4" source address="192.168.1.0/24" port protocol="tcp" port="445" accept
                local rule_source=""
                local rule_proto=""
                local rule_port=""
                local rule_action=""
                
                [[ "$rule" =~ source\ address=\"([^\"]+)\" ]] && rule_source="${BASH_REMATCH[1]}"
                [[ "$rule" =~ port\ protocol=\"([^\"]+)\" ]] && rule_proto="${BASH_REMATCH[1]}"
                [[ "$rule" =~ port=\"([^\"]+)\" ]] && rule_port="${BASH_REMATCH[1]}"
                [[ "$rule" =~ (accept|drop|reject)$ ]] && rule_action="${BASH_REMATCH[1]}"
                
                # Convert action to standard format
                [[ "$rule_action" == "accept" ]] && rule_action="ALLOW"
                [[ "$rule_action" == "drop" || "$rule_action" == "reject" ]] && rule_action="DENY"
                
                echo "firewalld|$rule_num|${rule_source:-any}|$rule_proto|$rule_port|$rule_action||active"
                ((rule_num++))
                break
            fi
        done
    done <<< "$rich_rules"
    
    echo "$rules"
}

# Collect Iptables Samba rules
collect_iptables_samba_rules() {
    local samba_ports=("$@")
    local rules=""
    
    # Get iptables rules with line numbers
    local iptables_output=$(iptables -L INPUT -n --line-numbers 2>/dev/null)
    
    local rule_num=1
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        
        for port in "${samba_ports[@]}"; do
            if echo "$line" | grep -q "dpt:$port"; then
                # Parse iptables rule line
                local rule_source=""
                local rule_proto=""
                local rule_port=""
                local rule_action=""
                local rule_comment=""
                
                # Extract components from iptables output
                [[ "$line" =~ ^([0-9]+)\ +([A-Z]+)\ +([a-z]+)\ +([^\ ]+)\ +([^\ ]+)\ +([^\ ]+)\ +(.*)$ ]] && {
                    rule_num="${BASH_REMATCH[1]}"
                    rule_action="${BASH_REMATCH[2]}"
                    rule_proto="${BASH_REMATCH[3]}"
                    rule_source="${BASH_REMATCH[4]}"
                }
                
                # Extract port from additional fields
                [[ "$line" =~ dpt:([0-9]+) ]] && rule_port="${BASH_REMATCH[1]}"
                
                # Extract comment if present
                [[ "$line" =~ /\*\ (.+)\ \*/ ]] && rule_comment="${BASH_REMATCH[1]}"
                
                # Clean up source (0.0.0.0/0 becomes "any")
                [[ "$rule_source" == "0.0.0.0/0" ]] && rule_source="any"
                
                echo "iptables|$rule_num|$rule_source|$rule_proto|$rule_port|$rule_action|$rule_comment|active"
                break
            fi
        done
    done <<< "$iptables_output"
    
    echo "$rules"
}

# Filter rules based on criteria
filter_samba_rules() {
    local rules_data="$1"
    local source_filter="$2"
    local port_filter="$3"
    local protocol_filter="$4"
    
    local filtered_rules=""
    
    while IFS='|' read -r fw_type rule_num source proto port action comment status; do
        [[ -z "$rule_num" ]] && continue
        
        # Apply source filter
        if [[ -n "$source_filter" ]]; then
            if ! echo "$source" | grep -q "$source_filter"; then
                continue
            fi
        fi
        
        # Apply port filter
        if [[ -n "$port_filter" ]]; then
            if [[ "$port" != "$port_filter" ]]; then
                continue
            fi
        fi
        
        # Apply protocol filter
        if [[ "$protocol_filter" != "both" ]]; then
            if [[ "$proto" != "$protocol_filter" ]]; then
                continue
            fi
        fi
        
        filtered_rules+="$fw_type|$rule_num|$source|$proto|$port|$action|$comment|$status"$'\n'
    done <<< "$rules_data"
    
    echo "$filtered_rules"
}

# Format rules in simple format
format_samba_rules_simple() {
    local rules_data="$1"
    
    echo ""
    echo "Samba Firewall Rules (Simple Format):"
    echo "======================================"
    
    while IFS='|' read -r fw_type rule_num source proto port action comment status; do
        [[ -z "$rule_num" ]] && continue
        echo "$action $proto/$port from $source${comment:+ # $comment}"
    done <<< "$rules_data"
}

# Format rules in detailed format
format_samba_rules_detailed() {
    local rules_data="$1"
    local verbose="$2"
    
    echo ""
    echo "Samba Firewall Rules (Detailed Format):"
    echo "========================================"
    
    if [[ "$verbose" == "true" ]]; then
        printf "%-4s %-8s %-18s %-8s %-6s %-6s %-8s %s\n" "NUM" "TYPE" "SOURCE" "PROTOCOL" "PORT" "ACTION" "STATUS" "COMMENT"
        printf "%-4s %-8s %-18s %-8s %-6s %-6s %-8s %s\n" "---" "-------" "-----------------" "--------" "-----" "------" "-------" "-------"
    else
        printf "%-4s %-18s %-8s %-6s %-6s %s\n" "NUM" "SOURCE" "PROTOCOL" "PORT" "ACTION" "COMMENT"
        printf "%-4s %-18s %-8s %-6s %-6s %s\n" "---" "-----------------" "--------" "-----" "------" "-------"
    fi
    
    while IFS='|' read -r fw_type rule_num source proto port action comment status; do
        [[ -z "$rule_num" ]] && continue
        
        if [[ "$verbose" == "true" ]]; then
            printf "%-4s %-8s %-18s %-8s %-6s %-6s %-8s %s\n" "$rule_num" "$fw_type" "$source" "$proto" "$port" "$action" "$status" "$comment"
        else
            printf "%-4s %-18s %-8s %-6s %-6s %s\n" "$rule_num" "$source" "$proto" "$port" "$action" "$comment"
        fi
    done <<< "$rules_data"
}

# Format rules in JSON format
format_samba_rules_json() {
    local rules_data="$1"
    
    echo ""
    echo "{"
    echo "  \"samba_firewall_rules\": ["
    
    local first_rule=true
    while IFS='|' read -r fw_type rule_num source proto port action comment status; do
        [[ -z "$rule_num" ]] && continue
        
        [[ "$first_rule" == "false" ]] && echo ","
        first_rule=false
        
        echo -n "    {"
        echo -n "\"rule_number\": \"$rule_num\", "
        echo -n "\"firewall_type\": \"$fw_type\", "
        echo -n "\"source\": \"$source\", "
        echo -n "\"protocol\": \"$proto\", "
        echo -n "\"port\": \"$port\", "
        echo -n "\"action\": \"$action\", "
        echo -n "\"comment\": \"$comment\", "
        echo -n "\"status\": \"$status\""
        echo -n "}"
    done <<< "$rules_data"
    
    echo ""
    echo "  ],"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"firewall_type\": \"${DETECTED_FIREWALL:-unknown}\""
    echo "}"
}