#!/bin/bash
# _cmd_list_service_rules.source.sh - List firewall rules for specific services
# This shows all firewall rules related to a service across all hosts
#
# Parameters:
#   --service <service>   Service name to filter by (optional, shows all if not specified)
#   --format <format>     Output format: simple, detailed, csv, json (default: simple)
#   --include-ports      Include port information in output
#   --verbose            Show detailed information

# Source the common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../_sources.sh"

# Initialize script name for logging
SCRIPT_NAME="list_service_rules"

# Default values
SERVICE=""
FORMAT="simple"
INCLUDE_PORTS=false
VERBOSE=false

# Service definitions (matching other commands)
declare -A SERVICE_DEFINITIONS
SERVICE_DEFINITIONS["ssh"]="22/tcp"
SERVICE_DEFINITIONS["http"]="80,443/tcp"
SERVICE_DEFINITIONS["https"]="443/tcp"
SERVICE_DEFINITIONS["samba"]="139,445/tcp,137,138/udp"
SERVICE_DEFINITIONS["smb"]="139,445/tcp"
SERVICE_DEFINITIONS["netbios"]="137,138/udp,139/tcp"
SERVICE_DEFINITIONS["ftp"]="21/tcp"
SERVICE_DEFINITIONS["telnet"]="23/tcp"
SERVICE_DEFINITIONS["smtp"]="25/tcp"
SERVICE_DEFINITIONS["dns"]="53/tcp,53/udp"
SERVICE_DEFINITIONS["dhcp"]="67,68/udp"
SERVICE_DEFINITIONS["tftp"]="69/udp"
SERVICE_DEFINITIONS["mysql"]="3306/tcp"
SERVICE_DEFINITIONS["postgresql"]="5432/tcp"
SERVICE_DEFINITIONS["mongodb"]="27017/tcp"
SERVICE_DEFINITIONS["redis"]="6379/tcp"
SERVICE_DEFINITIONS["elasticsearch"]="9200,9300/tcp"
SERVICE_DEFINITIONS["nfs"]="2049/tcp,111/tcp,111/udp"
SERVICE_DEFINITIONS["rsync"]="873/tcp"
SERVICE_DEFINITIONS["vnc"]="5900-5999/tcp"
SERVICE_DEFINITIONS["rdp"]="3389/tcp"

# Function to show usage
show_usage() {
    cat << EOF
List firewall rules for specific services

Usage: $(basename "${BASH_SOURCE[0]}") [options]

Parameters:
  --service <service>  Service name to filter by (optional)
                       If not specified, shows all service rules
  --format <format>    Output format (default: simple)
                       Options: simple, detailed, csv, json
  --include-ports      Include port information in output
  --verbose           Show detailed information
  --help              Show this help message

Examples:
  # List all service rules
  $(basename "${BASH_SOURCE[0]}")

  # List rules for Samba service
  $(basename "${BASH_SOURCE[0]}") --service samba

  # Show detailed Samba rules with ports
  $(basename "${BASH_SOURCE[0]}") --service samba --format detailed --include-ports

  # Export all rules as CSV
  $(basename "${BASH_SOURCE[0]}") --format csv

Available Services:
EOF
    
    # Show available service definitions
    echo "  Predefined services:"
    for svc in "${!SERVICE_DEFINITIONS[@]}"; do
        echo "    $svc: ${SERVICE_DEFINITIONS[$svc]}"
    done | sort
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --service)
                SERVICE="$2"
                shift 2
                ;;
            --format)
                FORMAT="$2"
                shift 2
                ;;
            --include-ports)
                INCLUDE_PORTS=true
                shift
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
    
    # Validate service if specified
    if [[ -n "$SERVICE" ]] && [[ -z "${SERVICE_DEFINITIONS[$SERVICE]}" ]]; then
        echo "Warning: Service '$SERVICE' is not predefined. Will search by name/port." >&2
    fi
}

# Get ports for a service
get_service_ports() {
    local service="$1"
    
    if [[ -n "${SERVICE_DEFINITIONS[$service]}" ]]; then
        echo "${SERVICE_DEFINITIONS[$service]}"
    else
        echo ""
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

# Parse UFW rules
parse_ufw_rules() {
    local service_filter="$1"
    local -a rules=()
    
    # Get UFW rules
    local rules_output=$(ufw status verbose 2>/dev/null)
    
    # Get service ports if filtering by service
    local service_ports=""
    if [[ -n "$service_filter" ]]; then
        service_ports=$(get_service_ports "$service_filter")
    fi
    
    while IFS= read -r line; do
        # Skip empty lines and headers
        [[ -z "$line" ]] && continue
        [[ "$line" =~ ^Status: ]] && continue
        [[ "$line" =~ ^To ]] && continue
        [[ "$line" =~ ^-- ]] && continue
        
        # Parse rule components
        local action=""
        local from=""
        local to=""
        local port=""
        local proto=""
        local service_name=""
        
        # UFW format: "Port Proto From"
        if [[ "$line" =~ ^([0-9]+(/[a-z]+)?|[a-zA-Z]+)[[:space:]]+(ALLOW|DENY|REJECT)[[:space:]]+(IN|OUT)?[[:space:]]*(.*)$ ]]; then
            local port_or_service="${BASH_REMATCH[1]}"
            action="${BASH_REMATCH[2]}"
            from="${BASH_REMATCH[4]}"
            
            # Determine if it's a port or service
            if [[ "$port_or_service" =~ ^[0-9]+(/[a-z]+)?$ ]]; then
                port="$port_or_service"
                # Try to identify service by port
                for svc in "${!SERVICE_DEFINITIONS[@]}"; do
                    if [[ "${SERVICE_DEFINITIONS[$svc]}" =~ $port ]]; then
                        service_name="$svc"
                        break
                    fi
                done
            else
                service_name="$port_or_service"
                port="${SERVICE_DEFINITIONS[$service_name]:-unknown}"
            fi
            
            # Apply filter if specified
            if [[ -n "$service_filter" ]]; then
                # Check if this rule matches the service
                if [[ "$service_name" != "$service_filter" ]]; then
                    # Check by port
                    local match=false
                    if [[ -n "$service_ports" ]]; then
                        IFS=',' read -ra PORT_ARRAY <<< "${service_ports//[\/a-z]/,}"
                        for p in "${PORT_ARRAY[@]}"; do
                            [[ -z "$p" ]] && continue
                            if [[ "$port" =~ $p ]]; then
                                match=true
                                break
                            fi
                        done
                    fi
                    [[ "$match" == "false" ]] && continue
                fi
            fi
            
            # Store rule
            rules+=("ufw|$service_name|$action|$from|any|$port|$line")
        fi
    done <<< "$rules_output"
    
    # Output rules
    printf "%s\n" "${rules[@]}"
}

# Parse firewalld rules
parse_firewalld_rules() {
    local service_filter="$1"
    local -a rules=()
    
    # Get rich rules
    local rules_output=$(firewall-cmd --list-rich-rules 2>/dev/null)
    
    while IFS= read -r rule; do
        [[ -z "$rule" ]] && continue
        
        local action="ALLOW"
        local from="any"
        local to="any"
        local port=""
        local service_name=""
        
        # Parse action
        if [[ "$rule" =~ (reject|drop) ]]; then
            action="DENY"
        fi
        
        # Parse source
        if [[ "$rule" =~ source[[:space:]]+address=\"([^\"]+)\" ]]; then
            from="${BASH_REMATCH[1]}"
        fi
        
        # Parse service
        if [[ "$rule" =~ service[[:space:]]+name=\"([^\"]+)\" ]]; then
            service_name="${BASH_REMATCH[1]}"
            port="${SERVICE_DEFINITIONS[$service_name]:-unknown}"
        fi
        
        # Parse port
        if [[ "$rule" =~ port[[:space:]]+port=\"([^\"]+)\"[[:space:]]+protocol=\"([^\"]+)\" ]]; then
            port="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
            # Try to identify service by port
            if [[ -z "$service_name" ]]; then
                for svc in "${!SERVICE_DEFINITIONS[@]}"; do
                    if [[ "${SERVICE_DEFINITIONS[$svc]}" =~ ${BASH_REMATCH[1]} ]]; then
                        service_name="$svc"
                        break
                    fi
                done
            fi
        fi
        
        # Apply filter
        if [[ -n "$service_filter" ]] && [[ "$service_name" != "$service_filter" ]]; then
            continue
        fi
        
        # Store rule
        if [[ -n "$service_name" ]] || [[ -n "$port" ]]; then
            rules+=("firewalld|${service_name:-custom}|$action|$from|$to|$port|$rule")
        fi
    done <<< "$rules_output"
    
    # Also check standard services
    local services_output=$(firewall-cmd --list-services 2>/dev/null)
    for svc in $services_output; do
        if [[ -n "$service_filter" ]] && [[ "$svc" != "$service_filter" ]]; then
            continue
        fi
        
        port="${SERVICE_DEFINITIONS[$svc]:-unknown}"
        rules+=("firewalld|$svc|ALLOW|any|any|$port|service: $svc")
    done
    
    # Output rules
    printf "%s\n" "${rules[@]}"
}

# Parse iptables rules
parse_iptables_rules() {
    local service_filter="$1"
    local -a rules=()
    
    # Get INPUT rules
    local rules_output=$(iptables -L INPUT -n -v --line-numbers 2>/dev/null)
    
    while IFS= read -r line; do
        # Skip headers
        [[ "$line" =~ ^Chain ]] && continue
        [[ "$line" =~ ^num ]] && continue
        [[ -z "$line" ]] && continue
        
        # Parse iptables line
        if [[ "$line" =~ ^[[:space:]]*([0-9]+)[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+(ACCEPT|DROP|REJECT)[[:space:]]+([a-z]+)[[:space:]]+--[[:space:]]+([^[:space:]]+)[[:space:]]+([^[:space:]]+)[[:space:]]+(.*) ]]; then
            local rule_num="${BASH_REMATCH[1]}"
            local action="${BASH_REMATCH[2]}"
            local proto="${BASH_REMATCH[3]}"
            local source="${BASH_REMATCH[5]}"
            local dest="${BASH_REMATCH[6]}"
            local details="${BASH_REMATCH[7]}"
            
            [[ "$action" == "ACCEPT" ]] && action="ALLOW"
            [[ "$action" =~ (DROP|REJECT) ]] && action="DENY"
            
            # Parse port from details
            local port=""
            local service_name=""
            
            if [[ "$details" =~ dpt:([0-9]+) ]]; then
                port="${BASH_REMATCH[1]}/$proto"
                
                # Try to identify service by port
                for svc in "${!SERVICE_DEFINITIONS[@]}"; do
                    if [[ "${SERVICE_DEFINITIONS[$svc]}" =~ ${BASH_REMATCH[1]} ]]; then
                        service_name="$svc"
                        break
                    fi
                done
            fi
            
            # Apply filter
            if [[ -n "$service_filter" ]]; then
                if [[ "$service_name" != "$service_filter" ]]; then
                    # Check if port matches service definition
                    local service_ports=$(get_service_ports "$service_filter")
                    if [[ -n "$service_ports" ]] && [[ -n "$port" ]]; then
                        if ! [[ "$service_ports" =~ ${port%/*} ]]; then
                            continue
                        fi
                        service_name="$service_filter"
                    else
                        continue
                    fi
                fi
            fi
            
            # Store rule if it has a service or port
            if [[ -n "$service_name" ]] || [[ -n "$port" ]]; then
                rules+=("iptables|${service_name:-custom}|$action|$source|$dest|$port|$line")
            fi
        fi
    done <<< "$rules_output"
    
    # Output rules
    printf "%s\n" "${rules[@]}"
}

# Format output
format_output() {
    local format="$1"
    local -a rules=()
    
    # Read rules from stdin
    while IFS= read -r rule; do
        [[ -n "$rule" ]] && rules+=("$rule")
    done
    
    case "$format" in
        simple)
            for rule in "${rules[@]}"; do
                IFS='|' read -r fw service action from to port details <<< "$rule"
                echo "$service: $action from $from"
            done | sort -u
            ;;
            
        detailed)
            local current_service=""
            for rule in "${rules[@]}"; do
                IFS='|' read -r fw service action from to port details <<< "$rule"
                
                if [[ "$service" != "$current_service" ]]; then
                    [[ -n "$current_service" ]] && echo ""
                    echo "=== Service: $service ==="
                    current_service="$service"
                fi
                
                echo "  Firewall: $fw"
                echo "  Action: $action"
                echo "  From: $from"
                echo "  To: $to"
                [[ "$INCLUDE_PORTS" == "true" ]] && [[ -n "$port" ]] && echo "  Ports: $port"
                echo "  Rule: ${details:0:80}..."
                echo ""
            done
            ;;
            
        csv)
            echo "firewall,service,action,from,to,ports,rule"
            for rule in "${rules[@]}"; do
                IFS='|' read -r fw service action from to port details <<< "$rule"
                # Escape quotes in details
                details="${details//\"/\"\"}"
                if [[ "$INCLUDE_PORTS" == "true" ]]; then
                    echo "$fw,$service,$action,$from,$to,$port,\"$details\""
                else
                    echo "$fw,$service,$action,$from,$to,\"$details\""
                fi
            done
            ;;
            
        json)
            echo "["
            local first=true
            for rule in "${rules[@]}"; do
                IFS='|' read -r fw service action from to port details <<< "$rule"
                
                [[ "$first" == "true" ]] && first=false || echo ","
                
                echo -n "  {"
                echo -n "\"firewall\": \"$fw\", "
                echo -n "\"service\": \"$service\", "
                echo -n "\"action\": \"$action\", "
                echo -n "\"from\": \"$from\", "
                echo -n "\"to\": \"$to\""
                
                if [[ "$INCLUDE_PORTS" == "true" ]] && [[ -n "$port" ]]; then
                    echo -n ", \"ports\": \"$port\""
                fi
                
                # Escape JSON special characters
                details="${details//\\/\\\\}"
                details="${details//\"/\\\"}"
                echo -n ", \"rule\": \"$details\""
                echo -n "}"
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
        [[ -n "$SERVICE" ]] && echo "Filtering for service: $SERVICE" >&2
        echo "" >&2
    fi
    
    # Collect rules based on firewall type
    local all_rules=""
    case "$firewall_type" in
        ufw)
            all_rules=$(parse_ufw_rules "$SERVICE")
            ;;
        firewalld)
            all_rules=$(parse_firewalld_rules "$SERVICE")
            ;;
        iptables)
            all_rules=$(parse_iptables_rules "$SERVICE")
            ;;
    esac
    
    # Format and output
    if [[ -n "$all_rules" ]]; then
        echo "$all_rules" | format_output "$FORMAT"
    else
        if [[ -n "$SERVICE" ]]; then
            echo "No firewall rules found for service: $SERVICE"
        else
            echo "No service-specific firewall rules found"
        fi
    fi
}

# Execute main function
main "$@"