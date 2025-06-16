# Command-specific help functions
show_help_show_status() {
    cat << EOF
Usage: $SCRIPT_NAME show-status [options]

Show firewall status and active rules overview.

Optional Parameters:
  --verbose             Show detailed firewall information
  --rules               Include detailed rule listings
  --samba-only          Show only Samba-related rules
  --dry-run             Show what would be done without making changes

Examples:
  # Show basic firewall status
  $SCRIPT_NAME show-status
  
  # Show detailed status with all rules
  $SCRIPT_NAME show-status --verbose --rules
  
  # Show only Samba rules in the status
  $SCRIPT_NAME show-status --samba-only
  
  # Show detailed Samba status
  $SCRIPT_NAME show-status --verbose --samba-only

Information Displayed:
  - Firewall type and status (active/inactive)
  - Service status and version
  - Rule summary and counts
  - Default policy settings
  - Active zones (firewalld)
  - Interface assignments
  - Recent rule additions

Notes:
  - Auto-detects firewall type
  - Shows combined status from all firewall components
  - Includes health check information
  - Use --samba-only for focused Samba security status
  - --verbose provides comprehensive system overview
EOF
}

cmd_show_status() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local verbose=false
    local rules=false
    local samba_only=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --verbose)
                verbose=true
                shift
                ;;
            --rules)
                rules=true
                shift
                ;;
            --samba-only)
                samba_only=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_show_status
                return 0
                ;;
            *)
                show_help_show_status
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    echo "show-status command called with parameters: $original_params"
    
    # Call the core function
    show_status_core "$verbose" "$rules" "$samba_only"
    
    return 0
}

# Core function to show firewall status
show_status_core() {
    local verbose="$1"
    local rules="$2"
    local samba_only="$3"
    
    # Auto-detect firewall if not already detected
    if [[ -z "${DETECTED_FIREWALL:-}" ]]; then
        log INFO "Auto-detecting firewall type..."
        detect_firewall_core false >/dev/null 2>&1
    fi
    
    local firewall_type="${DETECTED_FIREWALL:-none}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        echo "[DRY RUN] Would show firewall status:"
        echo "  Firewall type: $firewall_type"
        echo "  Verbose mode: $verbose"
        echo "  Include rules: $rules"
        echo "  Samba only: $samba_only"
        return 0
    fi
    
    echo ""
    echo "========================================"
    echo "       FIREWALL STATUS OVERVIEW"
    echo "========================================"
    echo "Generated: $(date)"
    echo ""
    
    # Show firewall detection summary
    echo "=== Firewall Detection ==="
    if [[ "$firewall_type" == "none" ]]; then
        echo "⚠️  No active firewall detected"
        echo "Status: UNPROTECTED"
        echo ""
        echo "Recommendations:"
        echo "• Install and enable ufw: sudo apt install ufw && sudo ufw enable"
        echo "• Or install firewalld: sudo apt install firewalld && sudo systemctl enable --now firewalld"
        echo "• Or configure iptables with custom rules"
        return 0
    else
        echo "✓ Active firewall: $firewall_type"
        echo "Status: PROTECTED"
    fi
    
    echo ""
    
    # Get status based on firewall type
    case "$firewall_type" in
        "ufw")
            show_ufw_status "$verbose" "$rules" "$samba_only"
            ;;
        "firewalld")
            show_firewalld_status "$verbose" "$rules" "$samba_only"
            ;;
        "iptables")
            show_iptables_status "$verbose" "$rules" "$samba_only"
            ;;
        *)
            echo "⚠️  Unsupported firewall type: $firewall_type"
            return 1
            ;;
    esac
    
    # Show Samba-specific summary if requested or always for samba-only
    if [[ "$samba_only" == "true" || "$verbose" == "true" ]]; then
        echo ""
        echo "=== Samba Security Summary ==="
        show_samba_security_summary "$firewall_type"
    fi
    
    echo ""
    echo "========================================"
    log INFO "Firewall status display completed"
    
    return 0
}

# Show UFW status
show_ufw_status() {
    local verbose="$1"
    local rules="$2"
    local samba_only="$3"
    
    echo "=== UFW Firewall Status ==="
    
    # Get UFW status
    local ufw_status=$(ufw status 2>/dev/null)
    local ufw_status_line=$(echo "$ufw_status" | head -1)
    
    echo "Service: $ufw_status_line"
    
    if echo "$ufw_status_line" | grep -q "Status: active"; then
        echo "State: ✓ ACTIVE"
        
        # Get rule count
        local rule_count=$(echo "$ufw_status" | grep -E "^[0-9]" | wc -l)
        echo "Active rules: $rule_count"
        
        # Get default policies
        if [[ "$verbose" == "true" ]]; then
            echo ""
            echo "Default Policies:"
            ufw status verbose 2>/dev/null | grep "Default:" | sed 's/^/  /'
        fi
        
        # Show rules if requested
        if [[ "$rules" == "true" ]]; then
            echo ""
            if [[ "$samba_only" == "true" ]]; then
                echo "Samba Rules:"
                ufw status numbered 2>/dev/null | grep -E "(445|139|137|138)" | sed 's/^/  /' || echo "  No Samba rules found"
            else
                echo "All Rules:"
                ufw status numbered 2>/dev/null | tail -n +4 | sed 's/^/  /'
            fi
        fi
        
        if [[ "$verbose" == "true" ]]; then
            echo ""
            echo "Logging: $(ufw status verbose 2>/dev/null | grep "Logging:" | cut -d: -f2 | xargs)"
        fi
        
    else
        echo "State: ⚠️  INACTIVE"
        echo "Recommendation: Enable with 'sudo ufw enable'"
    fi
}

# Show Firewalld status
show_firewalld_status() {
    local verbose="$1"
    local rules="$2"
    local samba_only="$3"
    
    echo "=== Firewalld Status ==="
    
    # Check service status
    if systemctl is-active firewalld >/dev/null 2>&1; then
        echo "Service: ✓ ACTIVE"
        echo "State: ✓ RUNNING"
        
        # Get version
        local version=$(firewall-cmd --version 2>/dev/null)
        echo "Version: $version"
        
        # Get default zone
        local default_zone=$(firewall-cmd --get-default-zone 2>/dev/null)
        echo "Default zone: $default_zone"
        
        # Get active zones
        local active_zones=$(firewall-cmd --get-active-zones 2>/dev/null | grep -v "interfaces:" | grep -v "sources:" | tr '\n' ' ')
        echo "Active zones: $active_zones"
        
        if [[ "$verbose" == "true" ]]; then
            echo ""
            echo "Zone Details:"
            firewall-cmd --list-all 2>/dev/null | sed 's/^/  /'
        fi
        
        # Show rules if requested
        if [[ "$rules" == "true" ]]; then
            echo ""
            if [[ "$samba_only" == "true" ]]; then
                echo "Samba Rules:"
                local samba_rules=$(firewall-cmd --list-rich-rules 2>/dev/null | grep -E "(445|139|137|138)")
                if [[ -n "$samba_rules" ]]; then
                    echo "$samba_rules" | sed 's/^/  /'
                else
                    echo "  No Samba-specific rich rules found"
                    # Check for Samba service
                    if firewall-cmd --list-services 2>/dev/null | grep -q samba; then
                        echo "  ✓ Samba service enabled in zone"
                    fi
                fi
            else
                echo "Rich Rules:"
                local rich_rules=$(firewall-cmd --list-rich-rules 2>/dev/null)
                if [[ -n "$rich_rules" ]]; then
                    echo "$rich_rules" | sed 's/^/  /'
                else
                    echo "  No rich rules configured"
                fi
                
                echo ""
                echo "Enabled Services:"
                firewall-cmd --list-services 2>/dev/null | sed 's/^/  /'
                
                echo ""
                echo "Open Ports:"
                firewall-cmd --list-ports 2>/dev/null | sed 's/^/  /' || echo "  No additional ports open"
            fi
        fi
        
    else
        echo "Service: ⚠️  INACTIVE"
        echo "State: ⚠️  STOPPED"
        echo "Recommendation: Start with 'sudo systemctl enable --now firewalld'"
    fi
}

# Show Iptables status
show_iptables_status() {
    local verbose="$1"
    local rules="$2"
    local samba_only="$3"
    
    echo "=== Iptables Status ==="
    
    if command -v iptables >/dev/null 2>&1; then
        echo "Service: ✓ AVAILABLE"
        
        # Count rules
        local input_rules=$(iptables -L INPUT 2>/dev/null | grep -v "^Chain\|^target" | wc -l)
        local forward_rules=$(iptables -L FORWARD 2>/dev/null | grep -v "^Chain\|^target" | wc -l)
        local output_rules=$(iptables -L OUTPUT 2>/dev/null | grep -v "^Chain\|^target" | wc -l)
        
        echo "INPUT rules: $input_rules"
        echo "FORWARD rules: $forward_rules"
        echo "OUTPUT rules: $output_rules"
        
        # Get default policies
        echo ""
        echo "Default Policies:"
        iptables -L 2>/dev/null | grep "^Chain" | sed 's/^/  /'
        
        # Show rules if requested
        if [[ "$rules" == "true" ]]; then
            echo ""
            if [[ "$samba_only" == "true" ]]; then
                echo "Samba Rules:"
                local samba_rules=$(iptables -L INPUT -n --line-numbers 2>/dev/null | grep -E "(445|139|137|138)")
                if [[ -n "$samba_rules" ]]; then
                    echo "$samba_rules" | sed 's/^/  /'
                else
                    echo "  No Samba-specific rules found"
                fi
            else
                echo "INPUT Chain Rules:"
                iptables -L INPUT -n --line-numbers 2>/dev/null | sed 's/^/  /'
                
                if [[ "$verbose" == "true" ]]; then
                    echo ""
                    echo "FORWARD Chain Rules:"
                    iptables -L FORWARD -n --line-numbers 2>/dev/null | sed 's/^/  /'
                    
                    echo ""
                    echo "OUTPUT Chain Rules:"
                    iptables -L OUTPUT -n --line-numbers 2>/dev/null | sed 's/^/  /'
                fi
            fi
        fi
        
        if [[ "$verbose" == "true" ]]; then
            echo ""
            echo "NAT Table Rules:"
            local nat_rules=$(iptables -t nat -L 2>/dev/null | grep -v "^Chain\|^target" | wc -l)
            echo "NAT rules: $nat_rules"
            
            echo ""
            echo "Persistence:"
            if [[ -f /etc/iptables/rules.v4 ]]; then
                echo "  ✓ Rules file exists: /etc/iptables/rules.v4"
                echo "  Modified: $(stat -c%y /etc/iptables/rules.v4 2>/dev/null | cut -d. -f1)"
            else
                echo "  ⚠️  No persistent rules file found"
                echo "  Recommendation: Save rules with 'iptables-save > /etc/iptables/rules.v4'"
            fi
        fi
        
    else
        echo "Service: ⚠️  NOT AVAILABLE"
        echo "State: ⚠️  NOT INSTALLED"
        echo "Recommendation: Install iptables package"
    fi
}

# Show Samba security summary
show_samba_security_summary() {
    local firewall_type="$1"
    
    echo "Firewall: $firewall_type"
    
    # Collect Samba rule information
    local samba_allow_rules=0
    local samba_deny_rules=0
    local samba_ports_covered=()
    
    case "$firewall_type" in
        "ufw")
            # Count UFW Samba rules
            local ufw_rules=$(ufw status 2>/dev/null | grep -E "(445|139|137|138)")
            samba_allow_rules=$(echo "$ufw_rules" | grep -c "ALLOW" 2>/dev/null || echo "0")
            samba_deny_rules=$(echo "$ufw_rules" | grep -c "DENY" 2>/dev/null || echo "0")
            
            # Check covered ports
            echo "$ufw_rules" | grep -o -E "(445|139|137|138)" | sort -u | while read port; do
                samba_ports_covered+=("$port")
            done
            ;;
        "firewalld")
            # Check firewalld Samba configuration
            if firewall-cmd --list-services 2>/dev/null | grep -q samba; then
                samba_allow_rules=1
                samba_ports_covered=("445" "139" "137" "138")
            fi
            
            # Count rich rules
            local rich_rules=$(firewall-cmd --list-rich-rules 2>/dev/null | grep -E "(445|139|137|138)")
            if [[ -n "$rich_rules" ]]; then
                local allow_count=$(echo "$rich_rules" | grep -c "accept" 2>/dev/null || echo "0")
                local deny_count=$(echo "$rich_rules" | grep -c -E "(drop|reject)" 2>/dev/null || echo "0")
                samba_allow_rules=$((samba_allow_rules + allow_count))
                samba_deny_rules=$deny_count
            fi
            ;;
        "iptables")
            # Count iptables Samba rules
            local ipt_rules=$(iptables -L INPUT 2>/dev/null | grep -E "(445|139|137|138)")
            samba_allow_rules=$(echo "$ipt_rules" | grep -c "ACCEPT" 2>/dev/null || echo "0")
            samba_deny_rules=$(echo "$ipt_rules" | grep -c -E "(DROP|REJECT)" 2>/dev/null || echo "0")
            ;;
    esac
    
    echo "Samba rules: $samba_allow_rules allow, $samba_deny_rules deny"
    
    # Security assessment
    echo ""
    echo "Security Assessment:"
    
    if [[ $samba_allow_rules -eq 0 && $samba_deny_rules -eq 0 ]]; then
        echo "  ⚠️  No Samba-specific firewall rules found"
        echo "  → Samba may be blocked by default policy (SECURE)"
        echo "  → Or allowed by permissive rules (RISK)"
        echo "  Recommendation: Add explicit Samba rules"
    elif [[ $samba_allow_rules -gt 0 && $samba_deny_rules -eq 0 ]]; then
        echo "  ✓ Samba access explicitly allowed ($samba_allow_rules rules)"
        echo "  → Check source restrictions for security"
        echo "  Recommendation: Verify source IP restrictions"
    elif [[ $samba_allow_rules -eq 0 && $samba_deny_rules -gt 0 ]]; then
        echo "  🔒 Samba access explicitly denied ($samba_deny_rules rules)"
        echo "  → High security configuration"
        echo "  Note: May need allow rules for legitimate access"
    else
        echo "  ⚡ Mixed Samba rules: $samba_allow_rules allow, $samba_deny_rules deny"
        echo "  → Complex configuration - verify rule order"
        echo "  Recommendation: Review rule priorities and conflicts"
    fi
    
    echo ""
    echo "Quick Actions:"
    echo "  • List Samba rules: $SCRIPT_NAME list-samba-rules"
    echo "  • Allow from network: $SCRIPT_NAME allow-samba-from --source \"192.168.1.0/24\""
    echo "  • Block external access: $SCRIPT_NAME deny-samba-from --source \"0.0.0.0/0\""
}