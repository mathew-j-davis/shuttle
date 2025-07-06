#!/bin/bash
# _cmd_isolate_host.source.sh - Isolate a host to specific services only
# This creates firewall rules to allow only specified services and deny everything else
#
# Parameters:
#   --host <host>         Host to isolate (IP, CIDR, or hostname)
#   --allow-services <services>  Comma-separated list of allowed services
#   --priority <priority> Base rule priority (for iptables)
#   --comment <comment>   Rule comment/description
#   --force              Skip confirmation prompts
#   --dry-run            Show what would be done without making changes
#   --verbose            Show detailed information

# Source the common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../_sources.sh"

# Initialize script name for logging
SCRIPT_NAME="isolate_host"

# Default values
HOST=""
ALLOW_SERVICES=""
PRIORITY=""
COMMENT=""
FORCE=false
DRY_RUN=false
VERBOSE=false

# Service definitions (matching allow/deny service commands)
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
SERVICE_DEFINITIONS["ping"]="icmp"

# Function to show usage
show_usage() {
    cat << EOF
Isolate a host to allow only specific services

Usage: $(basename "${BASH_SOURCE[0]}") --host <host> --allow-services <services> [options]

Parameters:
  --host <host>           Host to isolate (required)
                          Examples: 192.168.1.100, 192.168.1.0/24
  --allow-services <svcs> Comma-separated list of allowed services (required)
                          Examples: samba  or  ssh,http  or  samba,ping
  --priority <priority>   Base rule priority (for iptables)
  --comment <comment>     Rule description
  --force                 Skip confirmation prompts
  --dry-run              Show what would be done
  --verbose              Show detailed information
  --help                 Show this help message

Examples:
  # Isolate host to Samba access only
  $(basename "${BASH_SOURCE[0]}") --host 192.168.1.100 --allow-services samba

  # Isolate subnet to SSH and HTTP only
  $(basename "${BASH_SOURCE[0]}") --host 192.168.1.0/24 --allow-services ssh,http

  # Isolate with comment
  $(basename "${BASH_SOURCE[0]}") --host 192.168.1.100 --allow-services samba,ping --comment "File server - Samba only"

Available Services:
EOF
    
    # Show available service definitions
    echo "  Standard services:"
    for svc in "${!SERVICE_DEFINITIONS[@]}"; do
        echo "    $svc: ${SERVICE_DEFINITIONS[$svc]}"
    done | sort
    
    echo ""
    echo "Note: This command will:"
    echo "  1. Allow the specified services from the host"
    echo "  2. Deny all other traffic from the host"
    echo "  3. Not affect traffic from other hosts"
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                HOST="$2"
                shift 2
                ;;
            --allow-services)
                ALLOW_SERVICES="$2"
                shift 2
                ;;
            --priority)
                PRIORITY="$2"
                shift 2
                ;;
            --comment)
                COMMENT="$2"
                shift 2
                ;;
            --force)
                FORCE=true
                shift
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
    if [[ -z "$HOST" ]]; then
        echo "Error: Host specification is required" >&2
        show_usage
        exit 1
    fi
    
    if [[ -z "$ALLOW_SERVICES" ]]; then
        echo "Error: At least one allowed service must be specified" >&2
        show_usage
        exit 1
    fi
    
    # Validate host format
    if ! validate_network_source "$HOST"; then
        echo "Error: Invalid host specification '$HOST'" >&2
        exit 1
    fi
    
    # Validate priority if specified
    if [[ -n "$PRIORITY" ]] && ! [[ "$PRIORITY" =~ ^[0-9]+$ ]]; then
        echo "Error: Priority must be a positive number" >&2
        exit 1
    fi
    
    # Validate services
    IFS=',' read -ra SERVICE_ARRAY <<< "$ALLOW_SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        if [[ -z "${SERVICE_DEFINITIONS[$service]}" ]]; then
            echo "Warning: Service '$service' is not predefined. You may need to configure it manually." >&2
        fi
    done
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

# Apply UFW isolation rules
apply_ufw_isolation() {
    local host="$1"
    local services="$2"
    local comment="$3"
    
    echo "Applying UFW isolation rules for $host..."
    
    # First, allow each specified service
    IFS=',' read -ra SERVICE_ARRAY <<< "$services"
    local service_count=0
    
    for service in "${SERVICE_ARRAY[@]}"; do
        echo "  Allowing $service..."
        
        # Use the allow_service_from command
        local cmd="${SCRIPT_DIR}/_cmd_allow_service_from.source.sh"
        cmd="$cmd --service $service --source $host"
        
        if [[ -n "$comment" ]]; then
            cmd="$cmd --comment \"$comment - Allow $service\""
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            cmd="$cmd --dry-run"
        fi
        
        if [[ "$VERBOSE" == "true" ]]; then
            cmd="$cmd --verbose"
        fi
        
        execute_or_execute_dryrun "$cmd" \
            "Allowed $service from $host" \
            "Failed to allow $service" \
            "Configure firewall to allow $service access from $host"
            
        ((service_count++))
    done
    
    # Then, deny everything else from this host
    echo "  Denying all other traffic..."
    
    # UFW doesn't have a direct "deny all except" rule, so we need to be creative
    # Add a deny rule for the host with a lower priority
    local deny_cmd="ufw insert 1 deny from $host"
    
    if [[ -n "$comment" ]]; then
        deny_cmd="$deny_cmd comment '$comment - Deny all other traffic'"
    fi
    
    execute_or_dryrun "$deny_cmd" \
        "Added deny rule for all other traffic from $host" \
        "Failed to add deny rule" \
        "Add UFW rule to deny all non-allowed traffic from $host"
    
    echo "Isolation complete: $host can only access $service_count allowed service(s)"
}

# Apply firewalld isolation rules
apply_firewalld_isolation() {
    local host="$1"
    local services="$2"
    local comment="$3"
    
    echo "Applying firewalld isolation rules for $host..."
    
    # First, create a rich rule to reject all traffic from the host
    local reject_rule="firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"$host\" reject'"
    
    execute_or_dryrun "$reject_rule" \
        "Added base reject rule for $host" \
        "Failed to add reject rule" \
        "Add firewalld rule to reject all traffic from $host by default"
    
    # Then, add specific allow rules for each service
    IFS=',' read -ra SERVICE_ARRAY <<< "$services"
    local service_count=0
    
    for service in "${SERVICE_ARRAY[@]}"; do
        echo "  Allowing $service..."
        
        # Check if service is predefined
        if firewall-cmd --get-services 2>/dev/null | grep -qw "$service"; then
            # Use service name
            local allow_rule="firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"$host\" service name=\"$service\" accept'"
        else
            # Need to use port-based rule
            if [[ -n "${SERVICE_DEFINITIONS[$service]}" ]]; then
                local ports="${SERVICE_DEFINITIONS[$service]}"
                # Extract port and protocol
                local port=$(echo "$ports" | cut -d'/' -f1)
                local proto=$(echo "$ports" | cut -d'/' -f2)
                
                local allow_rule="firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"$host\" port port=\"$port\" protocol=\"$proto\" accept'"
            else
                echo "Warning: Unknown service $service, skipping"
                continue
            fi
        fi
        
        execute_or_dryrun "$allow_rule" \
            "Allowed $service from $host" \
            "Failed to allow $service" \
            "Add firewalld rule to allow $service access from $host"
            
        ((service_count++))
    done
    
    # Reload firewalld
    execute_or_dryrun "firewall-cmd --reload" \
        "Reloaded firewalld configuration" \
        "Failed to reload firewalld" \
        "Reload firewalld to apply isolation rules"
    
    echo "Isolation complete: $host can only access $service_count allowed service(s)"
}

# Apply iptables isolation rules
apply_iptables_isolation() {
    local host="$1"
    local services="$2"
    local comment="$3"
    local priority="$4"
    
    echo "Applying iptables isolation rules for $host..."
    
    # Calculate rule positions
    local base_priority=${priority:-100}
    local allow_priority=$base_priority
    local deny_priority=$((base_priority + 50))
    
    # First, add allow rules for each service
    IFS=',' read -ra SERVICE_ARRAY <<< "$services"
    local service_count=0
    
    for service in "${SERVICE_ARRAY[@]}"; do
        echo "  Allowing $service..."
        
        if [[ "$service" == "ping" ]] || [[ "$service" == "icmp" ]]; then
            # Special handling for ICMP
            local icmp_cmd="iptables -I INPUT $allow_priority -s $host -p icmp -j ACCEPT"
            
            if [[ -n "$comment" ]]; then
                icmp_cmd="$icmp_cmd -m comment --comment \"$comment - Allow ICMP\""
            fi
            
            execute_or_dryrun "$icmp_cmd" \
                "Allowed ICMP from $host" \
                "Failed to allow ICMP" \
                "Add iptables rule to allow ICMP from $host"
        else
            # Use the allow_service_from command for other services
            local cmd="${SCRIPT_DIR}/_cmd_allow_service_from.source.sh"
            cmd="$cmd --service $service --source $host --priority $allow_priority"
            
            if [[ -n "$comment" ]]; then
                cmd="$cmd --comment \"$comment - Allow $service\""
            fi
            
            if [[ "$DRY_RUN" == "true" ]]; then
                cmd="$cmd --dry-run"
            fi
            
            if [[ "$VERBOSE" == "true" ]]; then
                cmd="$cmd --verbose"
            fi
            
            execute_or_execute_dryrun "$cmd" \
                "Allowed $service from $host" \
                "Failed to allow $service" \
                "Configure iptables to allow $service access from $host"
        fi
        
        ((service_count++))
        ((allow_priority++))
    done
    
    # Then, add a deny rule for everything else from this host
    echo "  Denying all other traffic..."
    
    local deny_cmd="iptables -I INPUT $deny_priority -s $host -j REJECT --reject-with icmp-port-unreachable"
    
    if [[ -n "$comment" ]]; then
        deny_cmd="$deny_cmd -m comment --comment \"$comment - Deny all other traffic\""
    fi
    
    execute_or_dryrun "$deny_cmd" \
        "Added deny rule for all other traffic from $host" \
        "Failed to add deny rule" \
        "Add iptables rule to deny all non-allowed traffic from $host"
    
    # Save iptables rules
    if command -v iptables-save >/dev/null 2>&1; then
        execute_or_dryrun "iptables-save > /etc/iptables/rules.v4" \
            "Saved iptables rules" \
            "Failed to save iptables rules" \
            "Save iptables rules for persistence"
    fi
    
    echo "Isolation complete: $host can only access $service_count allowed service(s)"
}

# Show isolation summary
show_isolation_summary() {
    local host="$1"
    local services="$2"
    
    echo ""
    echo "=== Host Isolation Summary ==="
    echo "Host: $host"
    echo "Allowed services:"
    
    IFS=',' read -ra SERVICE_ARRAY <<< "$services"
    for service in "${SERVICE_ARRAY[@]}"; do
        if [[ -n "${SERVICE_DEFINITIONS[$service]}" ]]; then
            echo "  - $service (${SERVICE_DEFINITIONS[$service]})"
        else
            echo "  - $service (custom)"
        fi
    done
    
    echo "All other traffic: DENIED"
    echo ""
    
    if [[ "$DRY_RUN" != "true" ]]; then
        echo "Note: The host $host is now isolated to the specified services only."
        echo "To remove isolation, use the 'unisolate_host' command."
    fi
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
    
    # Confirm action if not forced
    if [[ "$FORCE" != "true" ]] && [[ "$DRY_RUN" != "true" ]]; then
        echo "Warning: This will isolate $HOST to only access: $ALLOW_SERVICES"
        echo "All other network traffic from this host will be blocked."
        echo ""
        read -p "Are you sure you want to continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Operation cancelled"
            exit 0
        fi
    fi
    
    # Show what will be done
    if [[ "$VERBOSE" == "true" ]]; then
        echo "Host to isolate: $HOST"
        echo "Allowed services: $ALLOW_SERVICES"
        [[ -n "$COMMENT" ]] && echo "Comment: $COMMENT"
        [[ -n "$PRIORITY" ]] && echo "Base priority: $PRIORITY"
    fi
    
    # Detect firewall type
    local firewall_type=$(detect_firewall)
    
    if [[ "$firewall_type" == "none" ]]; then
        echo "Error: No supported firewall detected (ufw, firewalld, or iptables)" >&2
        exit 1
    fi
    
    echo "Detected firewall: $firewall_type"
    
    # Apply isolation based on firewall type
    case "$firewall_type" in
        ufw)
            apply_ufw_isolation "$HOST" "$ALLOW_SERVICES" "$COMMENT"
            ;;
        firewalld)
            apply_firewalld_isolation "$HOST" "$ALLOW_SERVICES" "$COMMENT"
            ;;
        iptables)
            apply_iptables_isolation "$HOST" "$ALLOW_SERVICES" "$COMMENT" "$PRIORITY"
            ;;
    esac
    
    # Show summary
    show_isolation_summary "$HOST" "$ALLOW_SERVICES"
}

# Execute main function
main "$@"