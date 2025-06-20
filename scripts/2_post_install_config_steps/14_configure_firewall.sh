#!/bin/bash

# Firewall Configuration Script
# Tool for managing host-based firewall rules for Samba and other services
# Usage: configure_firewall.sh <command> [parameters...]

set -euo pipefail

# Script directory for sourcing libraries
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
LIB_DIR="$SCRIPT_DIR/lib"

# Source shared setup libraries using clean import pattern
SETUP_LIB_DIR="$(dirname "$SCRIPT_DIR")/__setup_lib_sh"
if [[ -f "$SETUP_LIB_DIR/_setup_lib_loader.source.sh" ]]; then
    source "$SETUP_LIB_DIR/_setup_lib_loader.source.sh"
    load_common_libs || {
        echo "ERROR: Failed to load required setup libraries" >&2
        exit 1
    }
else
    echo "ERROR: Setup library loader not found at $SETUP_LIB_DIR/_setup_lib_loader.source.sh" >&2
    exit 1
fi
source "$LIB_DIR/_cmd_detect_firewall.source.sh"
source "$LIB_DIR/_cmd_allow_samba_from.source.sh"
source "$LIB_DIR/_cmd_deny_samba_from.source.sh"
source "$LIB_DIR/_cmd_list_samba_rules.source.sh"
source "$LIB_DIR/_cmd_show_status.source.sh"

# Global variables
SCRIPT_NAME="$(basename "$0")"
COMMAND=""
DRY_RUN=false

# Show usage information
show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME <command> [options]

Firewall Configuration Tool
Tool for managing host-based firewall rules, focusing on Samba access control.

COMMANDS:

Samba Access Control:
  allow-samba-from           Allow Samba access from specific IP/network
  deny-samba-from            Deny Samba access from specific IP/network
  list-samba-rules           List current Samba firewall rules
  clear-samba-rules          Remove all Samba firewall rules

General Firewall:
  detect-firewall            Detect installed firewall type
  show-status                Show firewall status and active rules
  enable-firewall            Enable firewall service
  disable-firewall           Disable firewall service (use with caution)

Rule Management:
  allow-port                 Allow access to specific port/service
  deny-port                  Deny access to specific port/service
  list-rules                 List all firewall rules
  save-rules                 Save current rules (make persistent)

GLOBAL OPTIONS:
  --dry-run                  Show what would be done without making changes
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
    
    # Check for --dry-run flag in remaining parameters
    for arg in "$@"; do
        if [[ "$arg" == "--dry-run" ]]; then
            DRY_RUN=true
            break
        fi
    done
    
    # Dispatch to appropriate command function
    case "$COMMAND" in
        "allow-samba-from")
            cmd_allow_samba_from "$@"
            ;;
        "deny-samba-from")
            cmd_deny_samba_from "$@"
            ;;
        "list-samba-rules")
            cmd_list_samba_rules "$@"
            ;;
        "clear-samba-rules")
            cmd_clear_samba_rules "$@"
            ;;
        "detect-firewall")
            cmd_detect_firewall "$@"
            ;;
        "show-status")
            cmd_show_status "$@"
            ;;
        "enable-firewall")
            cmd_enable_firewall "$@"
            ;;
        "disable-firewall")
            cmd_disable_firewall "$@"
            ;;
        "allow-port")
            cmd_allow_port "$@"
            ;;
        "deny-port")
            cmd_deny_port "$@"
            ;;
        "list-rules")
            cmd_list_rules "$@"
            ;;
        "save-rules")
            cmd_save_rules "$@"
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