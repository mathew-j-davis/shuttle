#!/bin/bash

# List Firewall Rules Command
# Display UFW firewall rules in various formats

# Show usage for list-firewall-rules command
show_list_firewall_rules_usage() {
    cat << EOF
Usage: $SCRIPT_NAME list-firewall-rules [OPTIONS]

Display UFW firewall rules and status information.

OPTIONS:
  --format FORMAT            Output format: simple, numbered, verbose, status [simple]
  --filter TYPE              Filter rules by type: allow, deny, reject, all [all]
  --service SERVICE          Show rules for specific service (ssh, samba, http, etc.)
  --port PORT                Show rules for specific port number
  --protocol PROTOCOL        Show rules for protocol: tcp, udp, both [both]
  --direction DIRECTION      Show rules for direction: in, out, both [both]
  --show-inactive            Include inactive/commented rules
  --export                   Export rules in UFW command format
  --help                     Show this help message

EXAMPLES:
  # Show all rules (simple format)
  $SCRIPT_NAME list-firewall-rules

  # Show detailed rule information
  $SCRIPT_NAME list-firewall-rules --format verbose

  # Show numbered rules (useful for deletion)
  $SCRIPT_NAME list-firewall-rules --format numbered

  # Show only allow rules
  $SCRIPT_NAME list-firewall-rules --filter allow

  # Show SSH-related rules
  $SCRIPT_NAME list-firewall-rules --service ssh

  # Show rules for specific port
  $SCRIPT_NAME list-firewall-rules --port 445

  # Export rules as commands
  $SCRIPT_NAME list-firewall-rules --export

OUTPUT FORMATS:
  • simple:    Basic rule listing (default)
  • numbered:  Rules with numbers for deletion
  • verbose:   Detailed rule information
  • status:    Firewall status and summary
  • export:    UFW commands to recreate rules

FILTERS:
  Combine multiple filters to narrow results (AND logic)
EOF
}

# List UFW firewall rules
list_firewall_rules() {
    local format="simple"
    local filter="all"
    local service=""
    local port=""
    local protocol="both"
    local direction="both"
    local show_inactive=false
    local export_mode=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --format)
                format="$2"
                if [[ "$format" != "simple" && "$format" != "numbered" && "$format" != "verbose" && "$format" != "status" ]]; then
                    error_exit "Invalid format: $format. Use 'simple', 'numbered', 'verbose', or 'status'"
                fi
                shift 2
                ;;
            --filter)
                filter="$2"
                if [[ "$filter" != "allow" && "$filter" != "deny" && "$filter" != "reject" && "$filter" != "all" ]]; then
                    error_exit "Invalid filter: $filter. Use 'allow', 'deny', 'reject', or 'all'"
                fi
                shift 2
                ;;
            --service)
                service="$2"
                shift 2
                ;;
            --port)
                port="$2"
                if ! [[ "$port" =~ ^[0-9]+$ ]] || [[ "$port" -lt 1 ]] || [[ "$port" -gt 65535 ]]; then
                    error_exit "Invalid port: $port. Must be a number between 1 and 65535"
                fi
                shift 2
                ;;
            --protocol)
                protocol="$2"
                if [[ "$protocol" != "tcp" && "$protocol" != "udp" && "$protocol" != "both" ]]; then
                    error_exit "Invalid protocol: $protocol. Use 'tcp', 'udp', or 'both'"
                fi
                shift 2
                ;;
            --direction)
                direction="$2"
                if [[ "$direction" != "in" && "$direction" != "out" && "$direction" != "both" ]]; then
                    error_exit "Invalid direction: $direction. Use 'in', 'out', or 'both'"
                fi
                shift 2
                ;;
            --show-inactive)
                show_inactive=true
                shift
                ;;
            --export)
                export_mode=true
                shift
                ;;
            --help)
                show_list_firewall_rules_usage
                return 0
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
    
    # Check if UFW is installed
    if ! command -v ufw >/dev/null 2>&1; then
        error_exit "UFW is not installed. Install with: sudo apt-get install ufw"
    fi
    
    # Get UFW status
    local ufw_status
    if ! ufw_status=$(sudo ufw status 2>/dev/null); then
        error_exit "Could not get UFW status. Check permissions."
    fi
    
    # Check if UFW is active
    local is_active=false
    if echo "$ufw_status" | grep -q "Status: active"; then
        is_active=true
    fi
    
    # Display based on format
    case "$format" in
        "status")
            show_firewall_status "$is_active"
            ;;
        "verbose")
            show_firewall_verbose "$is_active"
            ;;
        "numbered")
            show_firewall_numbered "$is_active" "$filter" "$service" "$port" "$protocol" "$direction"
            ;;
        "simple")
            show_firewall_simple "$is_active" "$filter" "$service" "$port" "$protocol" "$direction"
            ;;
    esac
    
    # Export mode
    if [[ "$export_mode" == "true" ]]; then
        echo ""
        echo "=== UFW Commands to Recreate Rules ==="
        export_firewall_rules
    fi
}

# Show firewall status summary
show_firewall_status() {
    local is_active="$1"
    
    echo "=== UFW Firewall Status ==="
    if [[ "$is_active" == "true" ]]; then
        echo "Status: 🟢 ACTIVE"
    else
        echo "Status: 🔴 INACTIVE"
    fi
    
    sudo ufw status verbose 2>/dev/null || echo "Could not get detailed status"
}

# Show verbose firewall information
show_firewall_verbose() {
    local is_active="$1"
    
    echo "=== UFW Firewall Detailed Status ==="
    if [[ "$is_active" == "true" ]]; then
        echo "Status: 🟢 ACTIVE"
        echo ""
        sudo ufw status verbose 2>/dev/null || echo "Could not get detailed status"
    else
        echo "Status: 🔴 INACTIVE"
        echo ""
        echo "Rules (inactive):"
        sudo ufw status 2>/dev/null || echo "Could not get rules"
    fi
    
    # Show default policies
    echo ""
    echo "=== Default Policies ==="
    if command -v iptables >/dev/null 2>&1; then
        echo "Current iptables default policies:"
        sudo iptables -L | grep "policy" 2>/dev/null || echo "Could not get iptables policies"
    fi
}

# Show numbered firewall rules
show_firewall_numbered() {
    local is_active="$1"
    local filter="$2"
    local service="$3"
    local port="$4"
    local protocol="$5"
    local direction="$6"
    
    echo "=== UFW Firewall Rules (Numbered) ==="
    if [[ "$is_active" == "true" ]]; then
        echo "Status: 🟢 ACTIVE"
    else
        echo "Status: 🔴 INACTIVE"
    fi
    echo ""
    
    local rules_output
    if rules_output=$(sudo ufw status numbered 2>/dev/null); then
        # Apply filters if specified
        local filtered_output="$rules_output"
        
        if [[ "$filter" != "all" ]]; then
            filtered_output=$(echo "$filtered_output" | grep -i "$filter" || echo "No rules match filter: $filter")
        fi
        
        if [[ -n "$service" ]]; then
            filtered_output=$(echo "$filtered_output" | grep -i "$service" || echo "No rules match service: $service")
        fi
        
        if [[ -n "$port" ]]; then
            filtered_output=$(echo "$filtered_output" | grep "$port" || echo "No rules match port: $port")
        fi
        
        echo "$filtered_output"
    else
        echo "Could not get numbered rules"
    fi
}

# Show simple firewall rules
show_firewall_simple() {
    local is_active="$1"
    local filter="$2"
    local service="$3"
    local port="$4"
    local protocol="$5"
    local direction="$6"
    
    echo "=== UFW Firewall Rules ==="
    if [[ "$is_active" == "true" ]]; then
        echo "Status: 🟢 ACTIVE"
    else
        echo "Status: 🔴 INACTIVE"
    fi
    echo ""
    
    local rules_output
    if rules_output=$(sudo ufw status 2>/dev/null); then
        # Apply filters if specified
        local filtered_output="$rules_output"
        
        if [[ "$filter" != "all" ]]; then
            filtered_output=$(echo "$filtered_output" | grep -i "$filter" || echo "No rules match filter: $filter")
        fi
        
        if [[ -n "$service" ]]; then
            filtered_output=$(echo "$filtered_output" | grep -i "$service" || echo "No rules match service: $service")
        fi
        
        if [[ -n "$port" ]]; then
            filtered_output=$(echo "$filtered_output" | grep "$port" || echo "No rules match port: $port")
        fi
        
        echo "$filtered_output"
    else
        echo "Could not get firewall rules"
    fi
    
    # Show rule count
    local rule_count
    if rule_count=$(sudo ufw status numbered 2>/dev/null | grep -c "^\["); then
        echo ""
        echo "Total rules: $rule_count"
    fi
}

# Export firewall rules as UFW commands
export_firewall_rules() {
    echo "# UFW Firewall Rules Export"
    echo "# Generated on $(date)"
    echo ""
    
    # Get current default policies
    local status_output
    if status_output=$(sudo ufw status verbose 2>/dev/null); then
        echo "# Default policies"
        echo "$status_output" | grep "Default:" | while read -r line; do
            if [[ "$line" =~ Default:\ ([^,]+),\ ([^,]+),\ (.+) ]]; then
                echo "sudo ufw default ${BASH_REMATCH[1]// /} incoming"
                echo "sudo ufw default ${BASH_REMATCH[2]// /} outgoing"
            fi
        done
        echo ""
    fi
    
    # Get numbered rules and convert to commands
    echo "# Firewall rules"
    local rules_output
    if rules_output=$(sudo ufw status numbered 2>/dev/null); then
        echo "$rules_output" | grep "^\[" | while read -r line; do
            # Parse rule line and convert to UFW command
            # This is a simplified conversion - complex rules may need manual review
            if [[ "$line" =~ \]\ +([A-Z]+)\ +([^\ ]+)\ +([^\ ]+)\ +(.+) ]]; then
                local action="${BASH_REMATCH[1],,}"  # Convert to lowercase
                local to="${BASH_REMATCH[2]}"
                local from="${BASH_REMATCH[3]}"
                local details="${BASH_REMATCH[4]}"
                
                echo "# $line"
                echo "sudo ufw $action $to"
            fi
        done
    fi
    
    echo ""
    echo "# Enable firewall"
    echo "sudo ufw enable"
}

# Main function for list-firewall-rules command
cmd_list_firewall_rules() {
    list_firewall_rules "$@"
}

# Export functions for use by other scripts
export -f cmd_list_firewall_rules
export -f show_list_firewall_rules_usage
export -f list_firewall_rules
export -f show_firewall_status
export -f show_firewall_verbose
export -f show_firewall_numbered
export -f show_firewall_simple
export -f export_firewall_rules