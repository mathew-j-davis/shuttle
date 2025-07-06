#!/bin/bash
# _cmd_deny_service_from.source.sh - Deny specific service access from a source
# This extends the basic Samba allow/deny to support any service definition
#
# Parameters:
#   --service <service>   Service name (e.g., ssh, http, samba, custom)
#   --source <source>     Source IP, CIDR, hostname, or 'any'
#   --ports <ports>       Port specification (optional, uses service defaults)
#   --protocol <proto>    Protocol: tcp, udp, both (default: tcp)
#   --comment <comment>   Rule comment/description
#   --priority <priority> Rule priority (for iptables)
#   --dry-run            Show what would be done without making changes
#   --verbose            Show detailed information

# Source the common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../_sources.sh"

# Initialize script name for logging
SCRIPT_NAME="deny_service_from"

# Default values
SERVICE=""
SOURCE=""
PORTS=""
PROTOCOL="tcp"
COMMENT=""
PRIORITY=""
DRY_RUN=false
VERBOSE=false

# Service definitions (can be extended via configuration)
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
Deny access to a specific service from a source

Usage: $(basename "${BASH_SOURCE[0]}") --service <service> --source <source> [options]

Parameters:
  --service <service>     Service name (required)
                         Predefined: ssh, http, https, samba, ftp, mysql, etc.
                         Custom: specify with --ports
  --source <source>       Source specification (required)
                         Examples: 192.168.1.100, 192.168.1.0/24, any
  --ports <ports>         Override service ports or define custom service
                         Examples: 8080, 8080-8090, 80,443
  --protocol <proto>      Protocol: tcp, udp, both (default: tcp)
  --comment <comment>     Rule description
  --priority <priority>   Rule priority (for iptables)
  --dry-run              Show what would be done
  --verbose              Show detailed information
  --help                 Show this help message

Examples:
  # Deny SSH from specific host
  $(basename "${BASH_SOURCE[0]}") --service ssh --source 192.168.1.100

  # Deny HTTP/HTTPS from subnet
  $(basename "${BASH_SOURCE[0]}") --service http --source 192.168.1.0/24

  # Deny Samba from all except specific hosts (use with allow rules)
  $(basename "${BASH_SOURCE[0]}") --service samba --source any

  # Deny custom service with comment
  $(basename "${BASH_SOURCE[0]}") --service database --ports 3306 --source 10.0.0.0/8 --comment "Block external DB access"

Service Definitions:
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
            --source)
                SOURCE="$2"
                shift 2
                ;;
            --ports)
                PORTS="$2"
                shift 2
                ;;
            --protocol)
                PROTOCOL="$2"
                shift 2
                ;;
            --comment)
                COMMENT="$2"
                shift 2
                ;;
            --priority)
                PRIORITY="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
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
    # Check required parameters
    if [[ -z "$SERVICE" ]]; then
        echo "Error: Service name is required" >&2
        show_usage
        exit 1
    fi
    
    if [[ -z "$SOURCE" ]]; then
        echo "Error: Source specification is required" >&2
        show_usage
        exit 1
    fi
    
    # Validate protocol
    if [[ ! "$PROTOCOL" =~ ^(tcp|udp|both)$ ]]; then
        echo "Error: Invalid protocol '$PROTOCOL'. Must be tcp, udp, or both" >&2
        exit 1
    fi
    
    # Validate source format
    if [[ "$SOURCE" != "any" ]]; then
        # Basic validation for IP/CIDR/hostname
        if ! validate_network_source "$SOURCE"; then
            echo "Error: Invalid source specification '$SOURCE'" >&2
            exit 1
        fi
    fi
    
    # Validate priority if specified
    if [[ -n "$PRIORITY" ]] && ! [[ "$PRIORITY" =~ ^[0-9]+$ ]]; then
        echo "Error: Priority must be a positive number" >&2
        exit 1
    fi
    
    # Warn about denying from 'any'
    if [[ "$SOURCE" == "any" ]]; then
        echo "Warning: Denying service from 'any' will block all access to $SERVICE" >&2
        echo "This is typically used with specific allow rules for exceptions" >&2
        
        if [[ "$DRY_RUN" != "true" ]]; then
            read -p "Are you sure you want to continue? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Operation cancelled"
                exit 0
            fi
        fi
    fi
}

# Validate network source (IP, CIDR, hostname)
validate_network_source() {
    local source="$1"
    
    # Check for IPv4 address
    if [[ "$source" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        return 0
    fi
    
    # Check for IPv4 CIDR
    if [[ "$source" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        return 0
    fi
    
    # Check for IPv6 (simplified check)
    if [[ "$source" =~ : ]]; then
        return 0
    fi
    
    # Check for hostname (basic check)
    if [[ "$source" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$ ]]; then
        return 0
    fi
    
    return 1
}

# Determine ports and protocol for service
determine_service_ports() {
    local service="$1"
    local custom_ports="$2"
    
    # If custom ports specified, use them
    if [[ -n "$custom_ports" ]]; then
        echo "$custom_ports"
        return
    fi
    
    # Check predefined services
    if [[ -n "${SERVICE_DEFINITIONS[$service]}" ]]; then
        # Extract just the ports from the definition
        echo "${SERVICE_DEFINITIONS[$service]}" | cut -d'/' -f1
        return
    fi
    
    # No ports found
    echo ""
}

# Determine protocol for service
determine_service_protocol() {
    local service="$1"
    local custom_protocol="$2"
    
    # If protocol explicitly specified, use it
    if [[ "$custom_protocol" != "tcp" ]] || [[ -n "$PORTS" ]]; then
        echo "$custom_protocol"
        return
    fi
    
    # Check predefined services for protocol
    if [[ -n "${SERVICE_DEFINITIONS[$service]}" ]]; then
        local def="${SERVICE_DEFINITIONS[$service]}"
        if [[ "$def" =~ tcp ]] && [[ "$def" =~ udp ]]; then
            echo "both"
        elif [[ "$def" =~ udp ]]; then
            echo "udp"
        else
            echo "tcp"
        fi
        return
    fi
    
    # Default to tcp
    echo "tcp"
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

# Add UFW deny rules
add_ufw_deny_rules() {
    local service="$1"
    local source="$2"
    local ports="$3"
    local protocol="$4"
    local comment="$5"
    
    # Build UFW command base
    local ufw_cmd="ufw deny"
    
    # Add source
    if [[ "$source" != "any" ]]; then
        ufw_cmd="$ufw_cmd from $source"
    fi
    
    # Add port/service
    if [[ -n "$ports" ]]; then
        # Handle multiple ports
        IFS=',' read -ra PORT_ARRAY <<< "$ports"
        for port in "${PORT_ARRAY[@]}"; do
            local cmd="$ufw_cmd to any port $port"
            
            # Add protocol
            if [[ "$protocol" == "both" ]]; then
                # Add both TCP and UDP rules
                execute_or_dryrun "$cmd proto tcp comment '$comment'" \
                    "Added UFW deny rule: $service TCP port $port from $source" \
                    "Failed to add UFW deny rule" \
                    "Add UFW firewall rule to deny $service TCP access on port $port from $source"
                    
                execute_or_dryrun "$cmd proto udp comment '$comment'" \
                    "Added UFW deny rule: $service UDP port $port from $source" \
                    "Failed to add UFW deny rule" \
                    "Add UFW firewall rule to deny $service UDP access on port $port from $source"
            else
                execute_or_dryrun "$cmd proto $protocol comment '$comment'" \
                    "Added UFW deny rule: $service port $port/$protocol from $source" \
                    "Failed to add UFW deny rule" \
                    "Add UFW firewall rule to deny $service access on port $port/$protocol from $source"
            fi
        done
    else
        # Try to use service name directly if UFW knows it
        local cmd="$ufw_cmd $service"
        if [[ -n "$comment" ]]; then
            cmd="$cmd comment '$comment'"
        fi
        
        execute_or_dryrun "$cmd" \
            "Added UFW deny rule: $service from $source" \
            "Failed to add UFW deny rule" \
            "Add UFW firewall rule to deny $service access from $source"
    fi
}

# Add firewalld deny rules
add_firewalld_deny_rules() {
    local service="$1"
    local source="$2"
    local ports="$3"
    local protocol="$4"
    local comment="$5"
    
    # Check if service is predefined in firewalld
    local service_exists=false
    if firewall-cmd --get-services 2>/dev/null | grep -qw "$service"; then
        service_exists=true
    fi
    
    if [[ "$service_exists" == "true" ]] && [[ -z "$PORTS" ]]; then
        # Use predefined service with reject rule
        local cmd="firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"$source\" service name=\"$service\" reject'"
        
        if [[ "$source" == "any" ]]; then
            # Remove service and add explicit reject rule
            execute_or_dryrun "firewall-cmd --permanent --remove-service=$service 2>/dev/null || true" \
                "Removed $service from allowed services" \
                "Failed to remove service" \
                "Remove $service from allowed services if present"
                
            cmd="firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" service name=\"$service\" reject'"
        fi
        
        execute_or_dryrun "$cmd" \
            "Added firewalld deny rule: $service from $source" \
            "Failed to add firewalld deny rule" \
            "Add firewalld rule to deny $service access from $source"
    else
        # Use port-based rules
        IFS=',' read -ra PORT_ARRAY <<< "$ports"
        for port in "${PORT_ARRAY[@]}"; do
            if [[ "$protocol" == "both" ]]; then
                # Add both TCP and UDP
                for proto in tcp udp; do
                    add_firewalld_deny_port_rule "$service" "$source" "$port" "$proto" "$comment"
                done
            else
                add_firewalld_deny_port_rule "$service" "$source" "$port" "$protocol" "$comment"
            fi
        done
    fi
    
    # Reload firewalld
    execute_or_dryrun "firewall-cmd --reload" \
        "Reloaded firewalld configuration" \
        "Failed to reload firewalld" \
        "Reload firewalld to apply new rules"
}

# Add single firewalld deny port rule
add_firewalld_deny_port_rule() {
    local service="$1"
    local source="$2"
    local port="$3"
    local protocol="$4"
    local comment="$5"
    
    if [[ "$source" == "any" ]]; then
        # Remove port if allowed and add reject rule
        execute_or_dryrun "firewall-cmd --permanent --remove-port=$port/$protocol 2>/dev/null || true" \
            "Removed port $port/$protocol from allowed ports" \
            "Failed to remove port" \
            "Remove port $port/$protocol from allowed ports if present"
            
        local cmd="firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" port port=\"$port\" protocol=\"$protocol\" reject'"
    else
        local cmd="firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"$source\" port port=\"$port\" protocol=\"$protocol\" reject'"
    fi
    
    execute_or_dryrun "$cmd" \
        "Added firewalld deny rule: port $port/$protocol from $source" \
        "Failed to add firewalld deny rule" \
        "Add firewalld rule to deny access on port $port/$protocol from $source"
}

# Add iptables deny rules
add_iptables_deny_rules() {
    local service="$1"
    local source="$2"
    local ports="$3"
    local protocol="$4"
    local comment="$5"
    local priority="$6"
    
    # Determine rule position
    local position_arg=""
    if [[ -n "$priority" ]]; then
        position_arg="-I INPUT $priority"
    else
        position_arg="-A INPUT"
    fi
    
    # Build base command
    local base_cmd="iptables $position_arg"
    
    # Add source
    if [[ "$source" != "any" ]]; then
        base_cmd="$base_cmd -s $source"
    fi
    
    # Add ports and protocol
    IFS=',' read -ra PORT_ARRAY <<< "$ports"
    for port in "${PORT_ARRAY[@]}"; do
        if [[ "$protocol" == "both" ]]; then
            # Add both TCP and UDP rules
            for proto in tcp udp; do
                add_iptables_single_deny_rule "$base_cmd" "$port" "$proto" "$comment" "$service"
            done
        else
            add_iptables_single_deny_rule "$base_cmd" "$port" "$protocol" "$comment" "$service"
        fi
    done
}

# Add single iptables deny rule
add_iptables_single_deny_rule() {
    local base_cmd="$1"
    local port="$2"
    local protocol="$3"
    local comment="$4"
    local service="$5"
    
    local cmd="$base_cmd -p $protocol --dport $port"
    
    # Add comment if provided
    if [[ -n "$comment" ]]; then
        cmd="$cmd -m comment --comment \"$comment\""
    fi
    
    # Use REJECT instead of DROP for better user experience
    cmd="$cmd -j REJECT --reject-with icmp-port-unreachable"
    
    execute_or_dryrun "$cmd" \
        "Added iptables deny rule: $service port $port/$protocol" \
        "Failed to add iptables deny rule" \
        "Add iptables rule to deny $service access on port $port/$protocol"
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
    
    # Export DRY_RUN for use in execute functions
    export DRY_RUN
    export VERBOSE
    
    # Determine actual ports and protocol
    local actual_ports=$(determine_service_ports "$SERVICE" "$PORTS")
    local actual_protocol=$(determine_service_protocol "$SERVICE" "$PROTOCOL")
    
    # Validate that we have ports
    if [[ -z "$actual_ports" ]]; then
        echo "Error: No ports defined for service '$SERVICE' and no --ports specified" >&2
        echo "Use --ports to specify custom ports for this service" >&2
        exit 1
    fi
    
    # Show what will be done
    if [[ "$VERBOSE" == "true" ]]; then
        echo "Service: $SERVICE"
        echo "Source: $SOURCE"
        echo "Ports: $actual_ports"
        echo "Protocol: $actual_protocol"
        [[ -n "$COMMENT" ]] && echo "Comment: $COMMENT"
        [[ -n "$PRIORITY" ]] && echo "Priority: $PRIORITY"
    fi
    
    # Detect firewall type
    local firewall_type=$(detect_firewall)
    
    if [[ "$firewall_type" == "none" ]]; then
        echo "Error: No supported firewall detected (ufw, firewalld, or iptables)" >&2
        exit 1
    fi
    
    echo "Detected firewall: $firewall_type"
    
    # Apply rules based on firewall type
    case "$firewall_type" in
        ufw)
            add_ufw_deny_rules "$SERVICE" "$SOURCE" "$actual_ports" "$actual_protocol" "$COMMENT"
            ;;
        firewalld)
            add_firewalld_deny_rules "$SERVICE" "$SOURCE" "$actual_ports" "$actual_protocol" "$COMMENT"
            ;;
        iptables)
            add_iptables_deny_rules "$SERVICE" "$SOURCE" "$actual_ports" "$actual_protocol" "$COMMENT" "$PRIORITY"
            
            # Save iptables rules
            if command -v iptables-save >/dev/null 2>&1; then
                execute_or_dryrun "iptables-save > /etc/iptables/rules.v4" \
                    "Saved iptables rules" \
                    "Failed to save iptables rules" \
                    "Save iptables rules for persistence"
            fi
            ;;
    esac
    
    echo "Successfully configured firewall deny rules for $SERVICE from $SOURCE"
}

# Execute main function
main "$@"