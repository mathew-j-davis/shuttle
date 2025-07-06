#!/bin/bash
# _cmd_list_isolated_hosts.source.sh - List hosts that have been isolated
# This analyzes firewall rules to identify hosts with isolation patterns
#
# Parameters:
#   --format <format>     Output format: simple, detailed, csv, json (default: simple)
#   --verbose            Show detailed information

# Source the common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../_sources.sh"

# Initialize script name for logging
SCRIPT_NAME="list_isolated_hosts"

# Default values
FORMAT="simple"
VERBOSE=false

# Function to show usage
show_usage() {
    cat << EOF
List hosts that have been isolated with firewall rules

Usage: $(basename "${BASH_SOURCE[0]}") [options]

Parameters:
  --format <format>   Output format (default: simple)
                      Options: simple, detailed, csv, json
  --verbose          Show detailed information
  --help             Show this help message

Examples:
  # List isolated hosts in simple format
  $(basename "${BASH_SOURCE[0]}")

  # Show detailed information about isolated hosts
  $(basename "${BASH_SOURCE[0]}") --format detailed

  # Export as CSV
  $(basename "${BASH_SOURCE[0]}") --format csv

Output Formats:
  simple:   Basic list of isolated hosts
  detailed: Full information including allowed services and rules
  csv:      Comma-separated values for spreadsheet import
  json:     JSON format for programmatic use
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --format)
                FORMAT="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                show_usage
                exit 1
                ;;
        esac
    done
}

# Validate parameters
validate_parameters() {
    # Validate format
    if [[ ! "$FORMAT" =~ ^(simple|detailed|csv|json)$ ]]; then
        echo "Error: Invalid format '$FORMAT'. Must be simple, detailed, csv, or json" >&2
        exit 1
    fi
}

# Detect firewall type
detect_firewall() {
    if command -v ufw >/dev/null 2>&1 && ufw status >/dev/null 2>&1; then
        echo "ufw"
    elif command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
        echo "firewalld"
    elif command -v iptables >/dev/null 2>&1; then
        echo "iptables"
    else
        echo "none"
    fi
}

# Analyze UFW rules for isolated hosts
analyze_ufw_rules() {
    local -A host_rules
    local -A host_allow_rules
    local -A host_deny_rules
    
    # Get all UFW rules
    local rules_output=$(ufw status verbose 2>/dev/null | grep -E "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+|^[a-fA-F0-9:]+|ALLOW|DENY|REJECT")
    
    while IFS= read -r line; do
        # Parse UFW output to find host-specific rules
        if [[ "$line" =~ from[[:space:]]+([^[:space:]]+) ]]; then
            local host="${BASH_REMATCH[1]}"
            
            if [[ "$line" =~ ALLOW ]]; then
                host_allow_rules["$host"]=$((${host_allow_rules["$host"]:-0} + 1))
            elif [[ "$line" =~ (DENY|REJECT) ]]; then
                host_deny_rules["$host"]=$((${host_deny_rules["$host"]:-0} + 1))
            fi
            
            # Extract service/port information
            if [[ "$line" =~ to[[:space:]]+any[[:space:]]+port[[:space:]]+([^[:space:]]+) ]]; then
                local port="${BASH_REMATCH[1]}"
                host_rules["$host"]+="port:$port "
            fi
        fi
    done <<< "$rules_output"
    
    # Identify isolated hosts (those with both allow and deny rules)
    local isolated_hosts=()
    for host in "${!host_allow_rules[@]}"; do
        if [[ -n "${host_deny_rules[$host]}" ]]; then
            isolated_hosts+=("$host")
        fi
    done
    
    # Output based on format
    case "$FORMAT" in
        simple)
            for host in "${isolated_hosts[@]}"; do
                echo "$host"
            done
            ;;
        detailed)
            echo "=== UFW Isolated Hosts ==="
            for host in "${isolated_hosts[@]}"; do
                echo ""
                echo "Host: $host"
                echo "  Allow rules: ${host_allow_rules[$host]}"
                echo "  Deny rules: ${host_deny_rules[$host]}"
                echo "  Services: ${host_rules[$host]}"
            done
            ;;
        csv)
            echo "host,firewall,allow_rules,deny_rules"
            for host in "${isolated_hosts[@]}"; do
                echo "$host,ufw,${host_allow_rules[$host]},${host_deny_rules[$host]}"
            done
            ;;
        json)
            echo "["
            local first=true
            for host in "${isolated_hosts[@]}"; do
                [[ "$first" == "true" ]] && first=false || echo ","
                echo -n "  {\"host\": \"$host\", \"firewall\": \"ufw\", \"allow_rules\": ${host_allow_rules[$host]}, \"deny_rules\": ${host_deny_rules[$host]}}"
            done
            echo ""
            echo "]"
            ;;
    esac
}

# Analyze firewalld rules for isolated hosts
analyze_firewalld_rules() {
    local -A host_rules
    local -A host_allow_rules
    local -A host_deny_rules
    
    # Get all rich rules
    local rules_output=$(firewall-cmd --list-rich-rules 2>/dev/null)
    
    while IFS= read -r rule; do
        # Parse firewalld rich rules
        if [[ "$rule" =~ source[[:space:]]+address=\"([^\"]+)\" ]]; then
            local host="${BASH_REMATCH[1]}"
            
            if [[ "$rule" =~ accept ]]; then
                host_allow_rules["$host"]=$((${host_allow_rules["$host"]:-0} + 1))
                
                # Extract service or port
                if [[ "$rule" =~ service[[:space:]]+name=\"([^\"]+)\" ]]; then
                    host_rules["$host"]+="service:${BASH_REMATCH[1]} "
                elif [[ "$rule" =~ port[[:space:]]+port=\"([^\"]+)\" ]]; then
                    host_rules["$host"]+="port:${BASH_REMATCH[1]} "
                fi
            elif [[ "$rule" =~ (reject|drop) ]]; then
                host_deny_rules["$host"]=$((${host_deny_rules["$host"]:-0} + 1))
            fi
        fi
    done <<< "$rules_output"
    
    # Identify isolated hosts
    local isolated_hosts=()
    for host in "${!host_allow_rules[@]}"; do
        if [[ -n "${host_deny_rules[$host]}" ]]; then
            isolated_hosts+=("$host")
        fi
    done
    
    # Output based on format
    case "$FORMAT" in
        simple)
            for host in "${isolated_hosts[@]}"; do
                echo "$host"
            done
            ;;
        detailed)
            echo "=== Firewalld Isolated Hosts ==="
            for host in "${isolated_hosts[@]}"; do
                echo ""
                echo "Host: $host"
                echo "  Allow rules: ${host_allow_rules[$host]}"
                echo "  Deny rules: ${host_deny_rules[$host]}"
                echo "  Services: ${host_rules[$host]}"
            done
            ;;
        csv)
            echo "host,firewall,allow_rules,deny_rules"
            for host in "${isolated_hosts[@]}"; do
                echo "$host,firewalld,${host_allow_rules[$host]},${host_deny_rules[$host]}"
            done
            ;;
        json)
            echo "["
            local first=true
            for host in "${isolated_hosts[@]}"; do
                [[ "$first" == "true" ]] && first=false || echo ","
                echo -n "  {\"host\": \"$host\", \"firewall\": \"firewalld\", \"allow_rules\": ${host_allow_rules[$host]}, \"deny_rules\": ${host_deny_rules[$host]}}"
            done
            echo ""
            echo "]"
            ;;
    esac
}

# Analyze iptables rules for isolated hosts
analyze_iptables_rules() {
    local -A host_rules
    local -A host_allow_rules
    local -A host_deny_rules
    
    # Get all INPUT rules
    local rules_output=$(iptables -L INPUT -n -v 2>/dev/null)
    
    while IFS= read -r line; do
        # Skip headers
        if [[ "$line" =~ ^Chain ]] || [[ "$line" =~ ^[[:space:]]*pkts ]]; then
            continue
        fi
        
        # Parse iptables output
        if [[ "$line" =~ [[:space:]]([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(/[0-9]{1,2})?)[[:space:]] ]]; then
            local host="${BASH_REMATCH[1]}"
            
            if [[ "$line" =~ ACCEPT ]]; then
                host_allow_rules["$host"]=$((${host_allow_rules["$host"]:-0} + 1))
                
                # Extract port
                if [[ "$line" =~ dpt:([0-9]+) ]]; then
                    host_rules["$host"]+="port:${BASH_REMATCH[1]} "
                fi
            elif [[ "$line" =~ (REJECT|DROP) ]]; then
                host_deny_rules["$host"]=$((${host_deny_rules["$host"]:-0} + 1))
            fi
        fi
    done <<< "$rules_output"
    
    # Identify isolated hosts
    local isolated_hosts=()
    for host in "${!host_allow_rules[@]}"; do
        if [[ -n "${host_deny_rules[$host]}" ]]; then
            isolated_hosts+=("$host")
        fi
    done
    
    # Output based on format
    case "$FORMAT" in
        simple)
            for host in "${isolated_hosts[@]}"; do
                echo "$host"
            done
            ;;
        detailed)
            echo "=== Iptables Isolated Hosts ==="
            for host in "${isolated_hosts[@]}"; do
                echo ""
                echo "Host: $host"
                echo "  Allow rules: ${host_allow_rules[$host]}"
                echo "  Deny rules: ${host_deny_rules[$host]}"
                echo "  Services: ${host_rules[$host]}"
            done
            ;;
        csv)
            echo "host,firewall,allow_rules,deny_rules"
            for host in "${isolated_hosts[@]}"; do
                echo "$host,iptables,${host_allow_rules[$host]},${host_deny_rules[$host]}"
            done
            ;;
        json)
            echo "["
            local first=true
            for host in "${isolated_hosts[@]}"; do
                [[ "$first" == "true" ]] && first=false || echo ","
                echo -n "  {\"host\": \"$host\", \"firewall\": \"iptables\", \"allow_rules\": ${host_allow_rules[$host]}, \"deny_rules\": ${host_deny_rules[$host]}}"
            done
            echo ""
            echo "]"
            ;;
    esac
}

# Main function
main() {
    # Parse arguments
    parse_arguments "$@"
    
    # Initialize logging
    init_command_history
    
    # Log command
    log_command_call "${BASH_SOURCE[0]}" "$@"
    
    # Validate parameters
    validate_parameters
    
    # Export VERBOSE for use in functions
    export VERBOSE
    
    # Detect firewall type
    local firewall_type=$(detect_firewall)
    
    if [[ "$firewall_type" == "none" ]]; then
        echo "Error: No supported firewall detected (ufw, firewalld, or iptables)" >&2
        exit 1
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo "Detected firewall: $firewall_type" >&2
        echo "Analyzing firewall rules for isolated hosts..." >&2
        echo "" >&2
    fi
    
    # Analyze rules based on firewall type
    case "$firewall_type" in
        ufw)
            analyze_ufw_rules
            ;;
        firewalld)
            analyze_firewalld_rules
            ;;
        iptables)
            analyze_iptables_rules
            ;;
    esac
}

# Execute main function
main "$@"