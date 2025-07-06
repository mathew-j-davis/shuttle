#!/bin/bash

# Enable Firewall Command
# Enables UFW firewall with basic security settings

# Show usage for enable-firewall command
show_enable_firewall_usage() {
    cat << EOF
Usage: $SCRIPT_NAME enable-firewall [OPTIONS]

Enable UFW firewall with basic security configuration.

OPTIONS:
  --default-policy POLICY    Default policy for incoming connections (deny, allow, reject) [deny]
  --allow-ssh                Allow SSH connections (port 22) [enabled by default]
  --no-ssh                   Don't automatically allow SSH connections
  --logging LEVEL            Set logging level (off, low, medium, high, full) [low]
  --dry-run                  Show what would be done without making changes
  --verbose                  Show detailed output
  --help                     Show this help message

EXAMPLES:
  # Enable firewall with default settings (deny incoming, allow SSH)
  $SCRIPT_NAME enable-firewall

  # Enable firewall without SSH access (be careful!)
  $SCRIPT_NAME enable-firewall --no-ssh

  # Enable with custom logging
  $SCRIPT_NAME enable-firewall --logging medium

  # Test what would be enabled
  $SCRIPT_NAME enable-firewall --dry-run --verbose

SECURITY NOTES:
  • By default, SSH (port 22) is allowed to prevent lockout
  • Use --no-ssh only if you have console access
  • Outgoing connections are allowed by default
  • Default policy denies all incoming connections
  • Enable logging for security monitoring

FIREWALL STATUS:
  After enabling, check status with: sudo ufw status verbose
EOF
}

# Enable UFW firewall
enable_firewall() {
    local default_policy="deny"
    local allow_ssh=true
    local logging_level="low"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --default-policy)
                default_policy="$2"
                if [[ "$default_policy" != "deny" && "$default_policy" != "allow" && "$default_policy" != "reject" ]]; then
                    error_exit "Invalid default policy: $default_policy. Use 'deny', 'allow', or 'reject'"
                fi
                shift 2
                ;;
            --allow-ssh)
                allow_ssh=true
                shift
                ;;
            --no-ssh)
                allow_ssh=false
                shift
                ;;
            --logging)
                logging_level="$2"
                if [[ "$logging_level" != "off" && "$logging_level" != "low" && "$logging_level" != "medium" && "$logging_level" != "high" && "$logging_level" != "full" ]]; then
                    error_exit "Invalid logging level: $logging_level. Use 'off', 'low', 'medium', 'high', or 'full'"
                fi
                shift 2
                ;;
            --dry-run)
                # Already handled globally
                shift
                ;;
            --verbose)
                # Already handled globally
                shift
                ;;
            --help)
                show_enable_firewall_usage
                return 0
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
    
    log INFO "Enabling UFW firewall..."
    if [[ "$VERBOSE" == "true" ]]; then
        log INFO "  Default policy: $default_policy"
        log INFO "  Allow SSH: $allow_ssh"
        log INFO "  Logging level: $logging_level"
    fi
    
    # Check if UFW is installed
    if ! command -v ufw >/dev/null 2>&1; then
        error_exit "UFW is not installed. Install with: sudo apt-get install ufw"
    fi
    
    # Check UFW status
    local ufw_status
    if ufw_status=$(sudo ufw status 2>/dev/null); then
        if echo "$ufw_status" | grep -q "Status: active"; then
            log WARN "UFW is already active"
            if [[ "$VERBOSE" == "true" ]]; then
                log INFO "Current UFW status:"
                sudo ufw status verbose 2>/dev/null || log WARN "Could not get UFW status details"
            fi
            
            if ! confirm_action "UFW is already enabled. Reconfigure anyway?"; then
                log INFO "Firewall configuration cancelled"
                return 0
            fi
        fi
    fi
    
    # Reset UFW to clean state (with confirmation)
    if [[ "$DRY_RUN" == "false" ]]; then
        log INFO "Resetting UFW to clean state..."
        execute_or_execute_dryrun "sudo ufw --force reset" "Reset UFW configuration"
    else
        log INFO "[DRY RUN] Would reset UFW configuration"
    fi
    
    # Set default policies
    log INFO "Setting default policies..."
    execute_or_execute_dryrun "sudo ufw default $default_policy incoming" "Set default incoming policy to $default_policy"
    execute_or_execute_dryrun "sudo ufw default allow outgoing" "Set default outgoing policy to allow"
    
    # Configure SSH access
    if [[ "$allow_ssh" == "true" ]]; then
        log INFO "Allowing SSH connections..."
        execute_or_execute_dryrun "sudo ufw allow ssh" "Allow SSH (port 22)"
    else
        log WARN "SSH access will NOT be allowed - ensure you have console access!"
    fi
    
    # Set logging level
    if [[ "$logging_level" != "low" ]]; then
        log INFO "Setting logging level to $logging_level..."
        execute_or_execute_dryrun "sudo ufw logging $logging_level" "Set UFW logging to $logging_level"
    fi
    
    # Enable UFW
    log INFO "Enabling UFW firewall..."
    if [[ "$DRY_RUN" == "false" ]]; then
        # Use --force to avoid interactive prompt
        execute_or_execute_dryrun "sudo ufw --force enable" "Enable UFW firewall"
    else
        log INFO "[DRY RUN] Would enable UFW firewall"
    fi
    
    # Show final status
    if [[ "$DRY_RUN" == "false" ]]; then
        echo ""
        log INFO "Firewall enabled successfully!"
        log INFO "Current firewall status:"
        sudo ufw status verbose 2>/dev/null || log WARN "Could not get UFW status"
    else
        echo ""
        log INFO "[DRY RUN] Firewall would be enabled with these settings:"
        log INFO "  Default incoming: $default_policy"
        log INFO "  Default outgoing: allow"
        log INFO "  SSH access: $allow_ssh"
        log INFO "  Logging: $logging_level"
    fi
    
    # Security reminders
    if [[ "$allow_ssh" == "false" ]]; then
        echo ""
        log WARN "⚠️  IMPORTANT: SSH access is disabled!"
        log WARN "   Ensure you have console access before disconnecting"
    fi
    
    if [[ "$default_policy" == "allow" ]]; then
        echo ""
        log WARN "⚠️  WARNING: Default policy allows all incoming connections"
        log WARN "   This reduces security - consider using 'deny' instead"
    fi
}

# Main function for enable-firewall command
cmd_enable_firewall() {
    enable_firewall "$@"
}

# Export functions for use by other scripts
export -f cmd_enable_firewall
export -f show_enable_firewall_usage
export -f enable_firewall