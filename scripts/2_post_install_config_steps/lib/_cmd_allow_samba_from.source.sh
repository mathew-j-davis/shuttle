# Command-specific help functions
show_help_allow_samba_from() {
    cat << EOF
Usage: $SCRIPT_NAME allow-samba-from --source <ip/network> [options]

Allow Samba access from specific IP addresses or networks.

Required Parameters:
  --source <ip/network>   Source IP or network (supports CIDR, comma-separated)

Optional Parameters:
  --comment <text>        Comment/description for the rule
  --ports <ports>         Specific Samba ports (default: all Samba ports)
  --protocol <protocol>   Protocol restriction (tcp, udp, both - default: both)
  --dry-run               Show what would be done without making changes

Examples:
  # Allow from internal network
  $SCRIPT_NAME allow-samba-from --source "192.168.1.0/24" --comment "Internal LAN"
  
  # Allow from multiple specific IPs
  $SCRIPT_NAME allow-samba-from --source "10.10.5.50,10.10.5.51,10.10.5.52" --comment "File servers"
  
  # Allow from management VLAN
  $SCRIPT_NAME allow-samba-from --source "172.16.100.0/24" --comment "Management VLAN"
  
  # Allow only SMB/CIFS (TCP 445)
  $SCRIPT_NAME allow-samba-from --source "192.168.0.0/16" --ports "445" --protocol "tcp"
  
  # Complex network with multiple ranges
  $SCRIPT_NAME allow-samba-from --source "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" --comment "RFC1918 networks"

Source Format:
  - Single IP: 192.168.1.100
  - CIDR network: 192.168.1.0/24
  - IP range: 192.168.1.10-192.168.1.20 (converted to individual rules)
  - Multiple sources: Comma-separated list
  - Any: 0.0.0.0/0 (not recommended for production)

Default Samba Ports:
  - TCP 445 (SMB/CIFS)
  - TCP 139 (NetBIOS Session)
  - UDP 137 (NetBIOS Name)
  - UDP 138 (NetBIOS Datagram)

Notes:
  - Rules are automatically made persistent
  - Firewall type is auto-detected (ufw/firewalld/iptables)
  - Use list-samba-rules to verify configuration
  - Multiple IP ranges help with complex network topologies
  - Test connectivity after applying rules
EOF
}

cmd_allow_samba_from() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local source=""
    local comment=""
    local ports="all"
    local protocol="both"
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --source)
                source=$(validate_parameter_value "$1" "${2:-}" "Source IP/network required after --source" "show_help_allow_samba_from")
                shift 2
                ;;
            --comment)
                comment=$(validate_parameter_value "$1" "${2:-}" "Comment required after --comment" "show_help_allow_samba_from")
                shift 2
                ;;
            --ports)
                ports=$(validate_parameter_value "$1" "${2:-}" "Ports required after --ports" "show_help_allow_samba_from")
                shift 2
                ;;
            --protocol)
                protocol=$(validate_parameter_value "$1" "${2:-}" "Protocol required after --protocol" "show_help_allow_samba_from")
                if [[ "$protocol" != "tcp" && "$protocol" != "udp" && "$protocol" != "both" ]]; then
                    show_help_allow_samba_from
                    error_exit "Invalid protocol: $protocol. Must be 'tcp', 'udp', or 'both'"
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
                show_help_allow_samba_from
                return 0
                ;;
            *)
                show_help_allow_samba_from
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$source" ]]; then
        show_help_allow_samba_from
        error_exit "Source IP/network is required"
    fi
    
    log_command_call "allow-samba-from" "$original_params"
    
    # Call the core function
    allow_samba_from_core "$source" "$comment" "$ports" "$protocol"
    
    return 0
}

# Core function to allow Samba access from source
allow_samba_from_core() {
    local source="$1"
    local comment="$2"
    local ports="$3"
    local protocol="$4"
    
    # Auto-detect firewall if not already detected
    if [[ -z "${DETECTED_FIREWALL:-}" ]]; then
        log INFO "Auto-detecting firewall type..."
        detect_firewall_core false >/dev/null
    fi
    
    local firewall_type="${DETECTED_FIREWALL:-none}"
    if [[ "$firewall_type" == "none" ]]; then
        error_exit "No active firewall detected. Run 'detect-firewall' first or enable a firewall."
    fi
    
    log INFO "Using firewall type: $firewall_type"
    
    # Parse source IPs/networks (handle comma-separated)
    local sources=()
    IFS=',' read -ra source_list <<< "$source"
    for src in "${source_list[@]}"; do
        src=$(echo "$src" | xargs)  # Trim whitespace
        if [[ -n "$src" ]]; then
            sources+=("$src")
        fi
    done
    
    # Define Samba ports
    local samba_ports_tcp=("445" "139")
    local samba_ports_udp=("137" "138")
    local selected_ports=()
    
    if [[ "$ports" == "all" ]]; then
        if [[ "$protocol" == "both" || "$protocol" == "tcp" ]]; then
            for port in "${samba_ports_tcp[@]}"; do
                selected_ports+=("tcp:$port")
            done
        fi
        if [[ "$protocol" == "both" || "$protocol" == "udp" ]]; then
            for port in "${samba_ports_udp[@]}"; do
                selected_ports+=("udp:$port")
            done
        fi
    else
        # Parse custom ports
        IFS=',' read -ra port_list <<< "$ports"
        for port in "${port_list[@]}"; do
            port=$(echo "$port" | xargs)
            if [[ "$protocol" == "both" ]]; then
                selected_ports+=("tcp:$port" "udp:$port")
            else
                selected_ports+=("$protocol:$port")
            fi
        done
    fi
    
    log INFO "Allowing Samba access from ${#sources[@]} source(s) on ${#selected_ports[@]} port(s)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        echo "[DRY RUN] Would add the following firewall rules:"
        for src in "${sources[@]}"; do
            echo "  Source: $src"
            for port_proto in "${selected_ports[@]}"; do
                local proto="${port_proto%:*}"
                local port="${port_proto#*:}"
                echo "    Allow $proto/$port from $src"
            done
        done
        if [[ -n "$comment" ]]; then
            echo "  Comment: $comment"
        fi
        return 0
    fi
    
    # Apply rules based on firewall type
    case "$firewall_type" in
        "ufw")
            apply_ufw_samba_rules_allow "$sources" "$selected_ports" "$comment"
            ;;
        "firewalld")
            apply_firewalld_samba_rules_allow "$sources" "$selected_ports" "$comment"
            ;;
        "iptables")
            apply_iptables_samba_rules_allow "$sources" "$selected_ports" "$comment"
            ;;
        *)
            error_exit "Unsupported firewall type: $firewall_type"
            ;;
    esac
    
    log INFO "Successfully added Samba access rules for ${#sources[@]} source(s)"
    log INFO "Use 'list-samba-rules' to verify the configuration"
    
    return 0
}

# UFW rule application
apply_ufw_samba_rules_allow() {
    local sources=("${!1}")
    local selected_ports=("${!2}")
    local comment="$3"
    
    for src in "${sources[@]}"; do
        for port_proto in "${selected_ports[@]}"; do
            local proto="${port_proto%:*}"
            local port="${port_proto#*:}"
            
            local rule_comment=""
            if [[ -n "$comment" ]]; then
                rule_comment=" comment '$comment'"
            fi
            
            local ufw_cmd="sudo ufw allow from $src to any port $port proto $proto$rule_comment"
            execute_or_dryrun "$ufw_cmd" "Added UFW rule: $proto/$port from $src" "Failed to add UFW rule: $proto/$port from $src" \
                             "Configure UFW firewall to allow Samba traffic from specific source address"
        done
    done
}

# Firewalld rule application
apply_firewalld_samba_rules_allow() {
    local sources=("${!1}")
    local selected_ports=("${!2}")
    local comment="$3"
    
    for src in "${sources[@]}"; do
        for port_proto in "${selected_ports[@]}"; do
            local proto="${port_proto%:*}"
            local port="${port_proto#*:}"
            
            # Create rich rule for firewalld
            local rule_desc="$comment Samba $proto/$port"
            local rich_rule="rule family=\"ipv4\" source address=\"$src\" port protocol=\"$proto\" port=\"$port\" accept"
            
            log INFO "Adding firewalld rich rule from $src for $proto/$port"
            
            local firewalld_cmd="sudo firewall-cmd --add-rich-rule=\"$rich_rule\" --permanent"
            execute_or_dryrun "$firewalld_cmd" "Added firewalld rule: $proto/$port from $src" "Failed to add firewalld rule: $proto/$port from $src" \
                             "Add firewalld rich rule to allow Samba traffic from specific source address permanently"
        done
    done
    
    # Reload firewalld to apply permanent rules
    local reload_cmd="sudo firewall-cmd --reload"
    execute_or_dryrun "$reload_cmd" "Firewalld rules reloaded successfully" "Failed to reload firewalld rules" \
                     "Reload firewalld configuration to activate newly added permanent rules"
}

# Iptables rule application
apply_iptables_samba_rules_allow() {
    local sources=("${!1}")
    local selected_ports=("${!2}")
    local comment="$3"
    
    for src in "${sources[@]}"; do
        for port_proto in "${selected_ports[@]}"; do
            local proto="${port_proto%:*}"
            local port="${port_proto#*:}"
            
            local rule_comment=""
            if [[ -n "$comment" ]]; then
                rule_comment="-m comment --comment \"$comment\""
            fi
            
            local iptables_cmd="sudo iptables -A INPUT -s $src -p $proto --dport $port $rule_comment -j ACCEPT"
            execute_or_dryrun "$iptables_cmd" "Added iptables rule: $proto/$port from $src" "Failed to add iptables rule: $proto/$port from $src" \
                             "Add iptables INPUT rule to allow Samba traffic from specific source address"
        done
    done
    
    # Save iptables rules
    if execute "command -v iptables-save >/dev/null 2>&1" \
              "Iptables-save command available" \
              "Iptables-save command not available" \
              "Check if iptables-save utility is installed for rule persistence"; then
        local save_cmd="sudo iptables-save > /etc/iptables/rules.v4"
        execute_or_dryrun "$save_cmd" "Iptables rules saved" "Could not save iptables rules to /etc/iptables/rules.v4" \
                         "Save current iptables rules to persistent configuration file for reboot survival"
    fi
}