#!/bin/bash

# Firewall Configuration Script
# Tool for managing host-based firewall rules for Samba and other services
# Usage: configure_firewall.sh <command> [parameters...]

set -euo pipefail

# Script identification
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source required libraries - simple and direct
source "$SCRIPT_DIR/_sources.sh"

# Source all firewall command modules
source "$SCRIPT_DIR/lib/_cmd_detect_firewall.source.sh"
source "$SCRIPT_DIR/lib/_cmd_enable_firewall.source.sh"
source "$SCRIPT_DIR/lib/_cmd_disable_firewall.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_firewall_rules.source.sh"
source "$SCRIPT_DIR/lib/_cmd_delete_firewall_rule.source.sh"
source "$SCRIPT_DIR/lib/_cmd_allow_samba_from.source.sh"
source "$SCRIPT_DIR/lib/_cmd_deny_samba_from.source.sh"
source "$SCRIPT_DIR/lib/_cmd_allow_service_from.source.sh"
source "$SCRIPT_DIR/lib/_cmd_deny_service_from.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_samba_rules.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_service_rules.source.sh"
source "$SCRIPT_DIR/lib/_cmd_isolate_host.source.sh"
source "$SCRIPT_DIR/lib/_cmd_unisolate_host.source.sh"
source "$SCRIPT_DIR/lib/_cmd_list_isolated_hosts.source.sh"
source "$SCRIPT_DIR/lib/_cmd_show_status.source.sh"

# Global variables
SCRIPT_NAME="$(basename "$0")"
COMMAND=""
DRY_RUN=false
VERBOSE=false

# Show usage information
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME <command> [options]

Firewall Configuration Tool
Tool for managing host-based firewall rules, focusing on Samba access control.

COMMANDS:

Firewall Management:
  enable-firewall            Enable UFW firewall with security settings
  disable-firewall           Disable UFW firewall (use with caution)
  detect-firewall            Detect installed firewall type
  show-status                Show firewall status and active rules
  list-firewall-rules        List all firewall rules (various formats)
  delete-firewall-rule       Delete specific firewall rules

Samba Access Control:
  allow-samba-from           Allow Samba access from specific IP/network
  deny-samba-from            Deny Samba access from specific IP/network
  list-samba-rules           List current Samba firewall rules

Service Access Control:
  allow-service-from         Allow service access from specific sources
  deny-service-from          Deny service access from specific sources
  list-service-rules         List service-specific firewall rules

Host Isolation:
  isolate-host               Isolate host to specific services only
  unisolate-host             Remove host isolation
  list-isolated-hosts        List currently isolated hosts

GLOBAL OPTIONS:
  --dry-run                  Show what would be done without making changes
  --verbose                  Show detailed output
  --help, -h                 Show help for specific command

EXAMPLES:
  # Detect firewall type
  $SCRIPT_NAME detect-firewall
  
  # Allow Samba from internal network
  $SCRIPT_NAME allow-samba-from --source "192.168.1.0/24" --comment "Internal LAN"
  
  # Allow Samba from specific management network
  $SCRIPT_NAME allow-samba-from --source "10.10.5.0/24" --comment "Management VLAN"
  
  # Allow Samba from multiple specific IPs
  $SCRIPT_NAME allow-samba-from --source "172.16.10.50,172.16.10.51" --comment "File servers"
  
  # List current Samba rules
  $SCRIPT_NAME list-samba-rules
  
  # Allow SSH from management network only
  $SCRIPT_NAME allow-port --port 22 --source "10.10.5.0/24" --comment "SSH management"
  
  # Show firewall status
  $SCRIPT_NAME show-status

SAMBA PORTS:
  - TCP 445 (SMB/CIFS)
  - TCP 139 (NetBIOS Session Service)
  - UDP 137 (NetBIOS Name Service)
  - UDP 138 (NetBIOS Datagram Service)

FEATURES:
  • Auto-detects firewall type (ufw, firewalld, iptables)
  • Supports complex network topologies
  • IP range and CIDR notation support
  • Multiple IP/network specification
  • Rule commenting and organization
  • Persistent rule configuration
  • Dry-run mode for safe testing

NOTES:
  • Requires root privileges or sudo access
  • Rules are made persistent automatically
  • Use --dry-run to preview changes
  • Samba rules apply to all shares (per-share not supported by host firewall)
  • Complex networks can specify multiple source ranges
  • Always test connectivity after firewall changes

For detailed help on any command, use:
  $SCRIPT_NAME <command> --help

Examples:
  $SCRIPT_NAME allow-samba-from --help
  $SCRIPT_NAME list-samba-rules --help
  $SCRIPT_NAME detect-firewall --help
EOF
}

# Main command dispatcher
main() {
    # Check if any arguments provided
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    # Extract command from first parameter
    COMMAND="$1"
    shift # Remove command from parameters, leaving only command arguments
    
    # Check for --dry-run and --verbose flags in remaining parameters
    for arg in "$@"; do
        if [[ "$arg" == "--dry-run" ]]; then
            DRY_RUN=true
        elif [[ "$arg" == "--verbose" ]]; then
            VERBOSE=true
        fi
    done
    
    # Dispatch to appropriate command function
    case "$COMMAND" in
        # Firewall Management
        "enable-firewall")
            cmd_enable_firewall "$@"
            ;;
        "disable-firewall")
            cmd_disable_firewall "$@"
            ;;
        "detect-firewall")
            cmd_detect_firewall "$@"
            ;;
        "show-status")
            cmd_show_status "$@"
            ;;
        "list-firewall-rules")
            cmd_list_firewall_rules "$@"
            ;;
        "delete-firewall-rule")
            cmd_delete_firewall_rule "$@"
            ;;
        # Samba Access Control
        "allow-samba-from")
            cmd_allow_samba_from "$@"
            ;;
        "deny-samba-from")
            cmd_deny_samba_from "$@"
            ;;
        "list-samba-rules")
            cmd_list_samba_rules "$@"
            ;;
        # Service Access Control
        "allow-service-from")
            cmd_allow_service_from "$@"
            ;;
        "deny-service-from")
            cmd_deny_service_from "$@"
            ;;
        "list-service-rules")
            cmd_list_service_rules "$@"
            ;;
        # Host Isolation
        "isolate-host")
            cmd_isolate_host "$@"
            ;;
        "unisolate-host")
            cmd_unisolate_host "$@"
            ;;
        "list-isolated-hosts")
            cmd_list_isolated_hosts "$@"
            ;;
        "--help" | "-h" | "help")
            show_usage
            ;;
        *)
            show_usage
            error_exit "Unknown command: $COMMAND"
            ;;
    esac
}

# Execute main function with all script arguments
main "$@"