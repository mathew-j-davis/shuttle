# Command-specific help functions
show_help_detect_firewall() {
    cat << EOF
Usage: $SCRIPT_NAME detect-firewall [options]

Detect the installed and active firewall type on the system.

Optional Parameters:
  --verbose             Show detailed firewall information
  --dry-run             Show what would be done without making changes

Examples:
  # Detect firewall type
  $SCRIPT_NAME detect-firewall
  
  # Show detailed information
  $SCRIPT_NAME detect-firewall --verbose

Information Displayed:
  - Firewall type (ufw, firewalld, iptables, none)
  - Service status (active/inactive/disabled)
  - Version information
  - Available features
  - Recommended usage

Notes:
  - Checks for ufw, firewalld, and iptables
  - Shows which firewall is currently active
  - Provides recommendations for configuration
  - Required before using other firewall commands
EOF
}

cmd_detect_firewall() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local verbose=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --verbose)
                verbose=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_detect_firewall
                return 0
                ;;
            *)
                show_help_detect_firewall
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    echo "detect-firewall command called with parameters: $original_params"
    
    # Call the core function
    detect_firewall_core "$verbose"
    
    return 0
}

# Core function to detect firewall type
detect_firewall_core() {
    local verbose="$1"
    
    local detected_firewall="none"
    local firewall_status="unknown"
    local firewall_version=""
    local primary_firewall=""
    
    echo ""
    echo "=== Firewall Detection ==="
    
    # Check for ufw
    local ufw_available=false
    local ufw_active=false
    if command -v ufw >/dev/null 2>&1; then
        ufw_available=true
        echo "UFW: Available"
        
        if ufw --version >/dev/null 2>&1; then
            local ufw_ver=$(ufw --version 2>/dev/null | head -1)
            echo "UFW Version: $ufw_ver"
        fi
        
        # Check if ufw is active
        if ufw status 2>/dev/null | grep -q "Status: active"; then
            ufw_active=true
            detected_firewall="ufw"
            firewall_status="active"
            echo "UFW Status: Active"
        else
            echo "UFW Status: Inactive"
        fi
    else
        echo "UFW: Not installed"
    fi
    
    # Check for firewalld
    local firewalld_available=false
    local firewalld_active=false
    if command -v firewall-cmd >/dev/null 2>&1; then
        firewalld_available=true
        echo "Firewalld: Available"
        
        if firewall-cmd --version >/dev/null 2>&1; then
            local firewalld_ver=$(firewall-cmd --version 2>/dev/null)
            echo "Firewalld Version: $firewalld_ver"
        fi
        
        # Check if firewalld is active
        if systemctl is-active firewalld >/dev/null 2>&1; then
            firewalld_active=true
            if [[ "$detected_firewall" == "none" ]]; then
                detected_firewall="firewalld"
                firewall_status="active"
            fi
            echo "Firewalld Status: Active"
        else
            echo "Firewalld Status: Inactive"
        fi
    else
        echo "Firewalld: Not installed"
    fi
    
    # Check for iptables
    local iptables_available=false
    local iptables_rules=false
    if command -v iptables >/dev/null 2>&1; then
        iptables_available=true
        echo "Iptables: Available"
        
        # Check if iptables has custom rules
        local rule_count=$(iptables -L 2>/dev/null | grep -c "^Chain\|^target" || echo "0")
        if [[ "$rule_count" -gt 6 ]]; then  # More than default chains
            iptables_rules=true
            if [[ "$detected_firewall" == "none" ]]; then
                detected_firewall="iptables"
                firewall_status="active"
            fi
            echo "Iptables Status: Has custom rules"
        else
            echo "Iptables Status: Default rules only"
        fi
    else
        echo "Iptables: Not available"
    fi
    
    echo ""
    echo "=== Detection Summary ==="
    echo "Primary Firewall: $detected_firewall"
    echo "Status: $firewall_status"
    
    # Provide recommendations
    echo ""
    echo "=== Recommendations ==="
    
    if [[ "$detected_firewall" == "ufw" ]]; then
        echo "✓ UFW is active and recommended for this system"
        echo "  Use UFW commands for firewall management"
        primary_firewall="ufw"
    elif [[ "$detected_firewall" == "firewalld" ]]; then
        echo "✓ Firewalld is active and recommended for this system"
        echo "  Use firewall-cmd commands for firewall management"
        primary_firewall="firewalld"
    elif [[ "$detected_firewall" == "iptables" ]]; then
        echo "⚠ Iptables has custom rules but no high-level manager detected"
        echo "  Consider installing ufw or firewalld for easier management"
        primary_firewall="iptables"
    else
        echo "⚠ No active firewall detected"
        if [[ "$ufw_available" == "true" ]]; then
            echo "  Recommendation: Enable UFW with 'enable-firewall' command"
            primary_firewall="ufw"
        elif [[ "$firewalld_available" == "true" ]]; then
            echo "  Recommendation: Enable Firewalld with 'enable-firewall' command"
            primary_firewall="firewalld"
        else
            echo "  Recommendation: Install ufw or firewalld first"
        fi
    fi
    
    # Store detected firewall for other commands
    export DETECTED_FIREWALL="$primary_firewall"
    export FIREWALL_STATUS="$firewall_status"
    
    if [[ "$verbose" == "true" ]]; then
        echo ""
        echo "=== Detailed Information ==="
        
        if [[ "$ufw_available" == "true" ]]; then
            echo ""
            echo "UFW Details:"
            if [[ "$ufw_active" == "true" ]]; then
                ufw status verbose 2>/dev/null | sed 's/^/  /' || echo "  Could not get detailed status"
            else
                echo "  UFW is installed but not active"
                echo "  To activate: sudo ufw enable"
            fi
        fi
        
        if [[ "$firewalld_available" == "true" ]]; then
            echo ""
            echo "Firewalld Details:"
            if [[ "$firewalld_active" == "true" ]]; then
                firewall-cmd --list-all 2>/dev/null | sed 's/^/  /' || echo "  Could not get detailed status"
            else
                echo "  Firewalld is installed but not active"
                echo "  To activate: sudo systemctl enable --now firewalld"
            fi
        fi
        
        if [[ "$iptables_available" == "true" ]]; then
            echo ""
            echo "Iptables Details:"
            echo "  Filter table rules:"
            iptables -L -n --line-numbers 2>/dev/null | sed 's/^/    /' || echo "    Could not list rules"
        fi
    fi
    
    echo ""
    log INFO "Firewall detection completed. Primary firewall: $primary_firewall"
    
    return 0
}