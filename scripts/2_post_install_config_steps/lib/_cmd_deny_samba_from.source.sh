# Command-specific help functions
show_help_deny_samba_from() {
    cat << EOF
Usage: $SCRIPT_NAME deny-samba-from --source <ip/network> [options]

Deny Samba access from specific IP addresses or networks.

Required Parameters:
  --source <ip/network>   Source IP or network to block (supports CIDR, comma-separated)

Optional Parameters:
  --comment <text>        Comment/description for the rule
  --ports <ports>         Specific Samba ports (default: all Samba ports)
  --protocol <protocol>   Protocol restriction (tcp, udp, both - default: both)
  --priority <number>     Rule priority/position (firewall-specific)
  --dry-run               Show what would be done without making changes

Examples:
  # Block from suspicious network
  $SCRIPT_NAME deny-samba-from --source "203.0.113.0/24" --comment "Blocked malicious network"
  
  # Block specific IPs
  $SCRIPT_NAME deny-samba-from --source "198.51.100.10,198.51.100.11" --comment "Blocked attackers"
  
  # Block from external networks (allow only internal)
  $SCRIPT_NAME deny-samba-from --source "0.0.0.0/0" --comment "Block external access"
  
  # Block only SMB/CIFS access
  $SCRIPT_NAME deny-samba-from --source "192.0.2.0/24" --ports "445" --protocol "tcp"
  
  # High priority block rule
  $SCRIPT_NAME deny-samba-from --source "198.51.100.0/24" --priority 1 --comment "High priority block"

Source Format:
  - Single IP: 192.168.1.100
  - CIDR network: 192.168.1.0/24
  - IP range: 192.168.1.10-192.168.1.20 (converted to individual rules)
  - Multiple sources: Comma-separated list
  - All external: 0.0.0.0/0 (blocks everything - use with caution)

Default Samba Ports:
  - TCP 445 (SMB/CIFS)
  - TCP 139 (NetBIOS Session)
  - UDP 137 (NetBIOS Name)
  - UDP 138 (NetBIOS Datagram)

Rule Priority:
  - Lower numbers = higher priority (processed first)
  - Firewall-specific behavior:
    - UFW: Rules are processed in order
    - Firewalld: Rich rules processed before zone rules
    - Iptables: Rules processed in chain order

Notes:
  - Deny rules typically take precedence over allow rules
  - Rules are automatically made persistent
  - Firewall type is auto-detected (ufw/firewalld/iptables)
  - Use list-samba-rules to verify configuration
  - Test carefully - deny rules can block legitimate access
  - Consider logging for blocked connections

SECURITY WARNING:
  Using --source "0.0.0.0/0" will block ALL Samba access from any source.
  This effectively disables Samba networking. Use with extreme caution.
EOF
}

cmd_deny_samba_from() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local source=""
    local comment=""
    local ports="all"
    local protocol="both"
    local priority=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --source)
                source=$(validate_parameter_value "$1" "${2:-}" "Source IP/network required after --source" "show_help_deny_samba_from")
                shift 2
                ;;
            --comment)
                comment=$(validate_parameter_value "$1" "${2:-}" "Comment required after --comment" "show_help_deny_samba_from")
                shift 2
                ;;
            --ports)
                ports=$(validate_parameter_value "$1" "${2:-}" "Ports required after --ports" "show_help_deny_samba_from")
                shift 2
                ;;
            --protocol)
                protocol=$(validate_parameter_value "$1" "${2:-}" "Protocol required after --protocol" "show_help_deny_samba_from")
                if [[ "$protocol" != "tcp" && "$protocol" != "udp" && "$protocol" != "both" ]]; then
                    show_help_deny_samba_from
                    error_exit "Invalid protocol: $protocol. Must be 'tcp', 'udp', or 'both'"
                fi
                shift 2
                ;;
            --priority)
                priority=$(validate_parameter_value "$1" "${2:-}" "Priority required after --priority" "show_help_deny_samba_from")
                if ! [[ "$priority" =~ ^[0-9]+$ ]]; then
                    show_help_deny_samba_from
                    error_exit "Invalid priority: $priority. Must be a positive integer"
                fi
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_deny_samba_from
                return 0
                ;;
            *)
                show_help_deny_samba_from
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$source" ]]; then
        show_help_deny_samba_from
        error_exit "Source IP/network is required"
    fi
    
    # Security warning for blocking all access
    if [[ "$source" == "0.0.0.0/0" ]]; then
        echo ""
        echo "⚠️  WARNING: You are about to block Samba access from ALL sources!"
        echo "   This will effectively disable Samba networking completely."
        echo "   Are you sure you want to continue?"
        echo ""
        
        if [[ "$DRY_RUN" != "true" ]]; then
            read -p "Type 'yes' to confirm blocking all Samba access: " confirm
            if [[ "$confirm" != "yes" ]]; then
                echo "Operation cancelled by user"
                return 1
            fi
        else
            echo "[DRY RUN] Would prompt for confirmation to block all access"
        fi
    fi
    
    log_command_call "deny-samba-from" "$original_params"
    
    # Call the core function
    deny_samba_from_core "$source" "$comment" "$ports" "$protocol" "$priority"
    
    return 0
}

# Core function to deny Samba access from source
deny_samba_from_core() {
    local source="$1"
    local comment="$2"
    local ports="$3"
    local protocol="$4"
    local priority="$5"
    
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
    
    log INFO "Denying Samba access from ${#sources[@]} source(s) on ${#selected_ports[@]} port(s)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        echo "[DRY RUN] Would add the following firewall DENY rules:"
        for src in "${sources[@]}"; do
            echo "  Source: $src"
            for port_proto in "${selected_ports[@]}"; do
                local proto="${port_proto%:*}"
                local port="${port_proto#*:}"
                echo "    DENY $proto/$port from $src"
            done
        done
        if [[ -n "$comment" ]]; then
            echo "  Comment: $comment"
        fi
        if [[ -n "$priority" ]]; then
            echo "  Priority: $priority"
        fi
        return 0
    fi
    
    # Apply rules based on firewall type
    case "$firewall_type" in
        "ufw")
            apply_ufw_samba_rules_deny sources selected_ports "$comment" "$priority"
            ;;
        "firewalld")
            apply_firewalld_samba_rules_deny sources selected_ports "$comment" "$priority"
            ;;
        "iptables")
            apply_iptables_samba_rules_deny sources selected_ports "$comment" "$priority"
            ;;
        *)
            error_exit "Unsupported firewall type: $firewall_type"
            ;;
    esac
    
    log INFO "Successfully added Samba DENY rules for ${#sources[@]} source(s)"
    log INFO "Use 'list-samba-rules' to verify the configuration"
    
    return 0
}

# UFW rule application for deny  
apply_ufw_samba_rules_deny() {
    local sources_ref=$1
    local selected_ports_ref=$2
    local comment="$3"
    local priority="$4"
    
    # Use nameref to access arrays
    local -n sources=$sources_ref
    local -n selected_ports=$selected_ports_ref
    
    for src in "${sources[@]}"; do
        for port_proto in "${selected_ports[@]}"; do
            local proto="${port_proto%:*}"
            local port="${port_proto#*:}"
            
            local rule_comment=""
            if [[ -n "$comment" ]]; then
                rule_comment=" comment '$comment'"
            fi
            
            local insert_option=""
            if [[ -n "$priority" ]]; then
                insert_option="--insert $priority"
            fi
            
            local cmd="sudo ufw $insert_option deny from $src to any port $port proto $proto$rule_comment"
            execute_or_dryrun "$cmd" "Added UFW DENY rule: $proto/$port from $src" "Failed to add UFW DENY rule: $proto/$port from $src"
        done
    done
}


# Firewalld rule application for deny
apply_firewalld_samba_rules_deny() {
    local sources_ref=$1
    local selected_ports_ref=$2
    local comment="$3"
    local priority="$4"
    
    # Use nameref to access arrays
    local -n sources=$sources_ref
    local -n selected_ports=$selected_ports_ref
    
    for src in "${sources[@]}"; do
        for port_proto in "${selected_ports[@]}"; do
            local proto="${port_proto%:*}"
            local port="${port_proto#*:}"
            
            # Create rich rule for firewalld (deny)
            local rule_desc="DENY Samba $proto/$port"
            if [[ -n "$comment" ]]; then
                rule_desc="$comment - DENY Samba $proto/$port"
            fi
            
            local rich_rule="rule family=\"ipv4\" source address=\"$src\" port protocol=\"$proto\" port=\"$port\" drop"
            
            log INFO "Adding firewalld DENY rich rule from $src for $proto/$port"
            
            local cmd="sudo firewall-cmd --add-rich-rule='$rich_rule' --permanent"
            execute_or_dryrun "$cmd" "Added firewalld DENY rule: $proto/$port from $src" "Failed to add firewalld DENY rule: $proto/$port from $src"
        done
    done
    
    # Reload firewalld to apply permanent rules
    local cmd="sudo firewall-cmd --reload"
    execute_or_dryrun "$cmd" "Firewalld rules reloaded successfully" "Failed to reload firewalld rules"
}

# Iptables rule application for deny
apply_iptables_samba_rules_deny() {
    local sources_ref=$1
    local selected_ports_ref=$2
    local comment="$3"
    local priority="$4"
    
    # Use nameref to access arrays
    local -n sources=$sources_ref
    local -n selected_ports=$selected_ports_ref
    
    for src in "${sources[@]}"; do
        for port_proto in "${selected_ports[@]}"; do
            local proto="${port_proto%:*}"
            local port="${port_proto#*:}"
            
            local rule_comment=""
            if [[ -n "$comment" ]]; then
                rule_comment="-m comment --comment \"$comment\""
            fi
            
            local insert_option="-A INPUT"
            if [[ -n "$priority" ]]; then
                insert_option="-I INPUT $priority"
            fi
            
            local cmd="sudo iptables $insert_option -s $src -p $proto --dport $port $rule_comment -j DROP"
            execute_or_dryrun "$cmd" "Added iptables DENY rule: $proto/$port from $src" "Failed to add iptables DENY rule: $proto/$port from $src"
        done
    done
    
    # Save iptables rules
    if command -v iptables-save >/dev/null 2>&1; then
        local cmd="sudo iptables-save > /etc/iptables/rules.v4 2>/dev/null"
        execute_or_dryrun "$cmd" "Iptables rules saved" "Could not save iptables rules to /etc/iptables/rules.v4"
    fi
}