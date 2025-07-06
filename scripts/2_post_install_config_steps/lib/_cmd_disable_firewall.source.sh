#!/bin/bash

# Disable Firewall Command
# Disables UFW firewall with safety warnings

# Show usage for disable-firewall command
show_disable_firewall_usage() {
    cat << EOF
Usage: $SCRIPT_NAME disable-firewall [OPTIONS]

Disable UFW firewall. Use with caution in production environments.

OPTIONS:
  --preserve-rules           Keep firewall rules but disable enforcement
  --reset                    Reset all rules and disable firewall
  --force                    Skip confirmation prompts
  --dry-run                  Show what would be done without making changes
  --verbose                  Show detailed output
  --help                     Show this help message

EXAMPLES:
  # Disable firewall (with confirmation)
  $SCRIPT_NAME disable-firewall

  # Disable but keep rules for later re-enabling
  $SCRIPT_NAME disable-firewall --preserve-rules

  # Completely reset firewall configuration
  $SCRIPT_NAME disable-firewall --reset

  # Force disable without confirmation
  $SCRIPT_NAME disable-firewall --force

  # Test what would be disabled
  $SCRIPT_NAME disable-firewall --dry-run --verbose

SECURITY WARNING:
  Disabling the firewall removes network security protection.
  Only disable if you have alternative security measures in place.

MODES:
  • Default: Disable firewall but preserve rules
  • --preserve-rules: Explicitly keep rules (same as default)
  • --reset: Remove all rules and disable firewall

ALTERNATIVE:
  Consider using specific allow/deny rules instead of disabling entirely.
EOF
}

# Disable UFW firewall
disable_firewall() {
    local preserve_rules=true
    local force=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --preserve-rules)
                preserve_rules=true
                shift
                ;;
            --reset)
                preserve_rules=false
                shift
                ;;
            --force)
                force=true
                shift
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
                show_disable_firewall_usage
                return 0
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
    
    log INFO "Disabling UFW firewall..."
    if [[ "$VERBOSE" == "true" ]]; then
        log INFO "  Preserve rules: $preserve_rules"
        log INFO "  Force: $force"
    fi
    
    # Check if UFW is installed
    if ! command -v ufw >/dev/null 2>&1; then
        log WARN "UFW is not installed - nothing to disable"
        return 0
    fi
    
    # Check UFW status
    local ufw_status
    if ufw_status=$(sudo ufw status 2>/dev/null); then
        if echo "$ufw_status" | grep -q "Status: inactive"; then
            log INFO "UFW is already inactive"
            
            if [[ "$preserve_rules" == "false" ]]; then
                log INFO "Checking for existing rules to reset..."
                if sudo ufw status numbered 2>/dev/null | grep -q "\["; then
                    log INFO "Found existing rules that will be reset"
                else
                    log INFO "No existing rules found"
                    return 0
                fi
            else
                return 0
            fi
        fi
    fi
    
    # Show current status if verbose
    if [[ "$VERBOSE" == "true" && "$DRY_RUN" == "false" ]]; then
        log INFO "Current UFW status:"
        sudo ufw status verbose 2>/dev/null || log WARN "Could not get UFW status"
    fi
    
    # Security warning and confirmation
    if [[ "$force" == "false" ]]; then
        echo ""
        log WARN "⚠️  SECURITY WARNING: Disabling firewall removes network protection"
        log WARN "   This exposes all services to network access"
        log WARN "   Only disable if you have alternative security measures"
        echo ""
        
        if [[ "$preserve_rules" == "true" ]]; then
            log INFO "Rules will be preserved and can be re-enabled later"
        else
            log WARN "All firewall rules will be permanently deleted!"
        fi
        
        if ! confirm_action "Are you sure you want to disable the firewall?"; then
            log INFO "Firewall disable cancelled"
            return 0
        fi
    fi
    
    # Disable UFW
    if [[ "$preserve_rules" == "true" ]]; then
        log INFO "Disabling UFW (preserving rules)..."
        execute_or_execute_dryrun "sudo ufw disable" "Disable UFW firewall"
        
        if [[ "$DRY_RUN" == "false" ]]; then
            log INFO "✅ Firewall disabled but rules preserved"
            log INFO "   Re-enable with: sudo ufw enable"
        fi
    else
        log INFO "Resetting and disabling UFW..."
        execute_or_execute_dryrun "sudo ufw --force reset" "Reset and disable UFW firewall"
        
        if [[ "$DRY_RUN" == "false" ]]; then
            log INFO "✅ Firewall completely reset and disabled"
            log INFO "   All rules have been removed"
        fi
    fi
    
    # Show final status
    if [[ "$DRY_RUN" == "false" ]]; then
        echo ""
        log INFO "Current firewall status:"
        sudo ufw status 2>/dev/null || log WARN "Could not get UFW status"
        
        # Additional security reminder
        echo ""
        log WARN "🔓 Firewall is now disabled - network services are exposed"
        log INFO "   Consider using specific firewall rules instead of disabling entirely"
        log INFO "   Re-enable firewall with: $SCRIPT_NAME enable-firewall"
    else
        echo ""
        log INFO "[DRY RUN] Firewall would be disabled"
        if [[ "$preserve_rules" == "true" ]]; then
            log INFO "  Rules would be preserved"
        else
            log INFO "  All rules would be deleted"
        fi
    fi
}

# Main function for disable-firewall command
cmd_disable_firewall() {
    disable_firewall "$@"
}

# Export functions for use by other scripts
export -f cmd_disable_firewall
export -f show_disable_firewall_usage
export -f disable_firewall