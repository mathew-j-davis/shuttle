#!/bin/bash
# _cmd_unisolate_host.source.sh - Remove isolation rules for a host
# This removes firewall rules that were created by isolate_host command
#
# Parameters:
#   --host <host>         Host to unisolate (IP, CIDR, or hostname)
#   --comment-pattern <pattern>  Pattern to match in rule comments (optional)
#   --force              Skip confirmation prompts
#   --dry-run            Show what would be done without making changes
#   --verbose            Show detailed information

# Source the common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../_sources.sh"

# Initialize script name for logging
SCRIPT_NAME="unisolate_host"

# Default values
HOST=""
COMMENT_PATTERN=""
FORCE=false
DRY_RUN=false
VERBOSE=false

# Function to show usage
show_usage() {
    cat << EOF
Remove isolation rules for a host

Usage: $(basename "${BASH_SOURCE[0]}") --host <host> [options]

Parameters:
  --host <host>           Host to unisolate (required)
                          Examples: 192.168.1.100, 192.168.1.0/24
  --comment-pattern <pat> Pattern to match in rule comments
                          Helps identify specific isolation rule sets
  --force                 Skip confirmation prompts
  --dry-run              Show what would be done
  --verbose              Show detailed information
  --help                 Show this help message

Examples:
  # Remove all isolation rules for a host
  $(basename "${BASH_SOURCE[0]}") --host 192.168.1.100

  # Remove specific isolation rules by comment pattern
  $(basename "${BASH_SOURCE[0]}") --host 192.168.1.100 --comment-pattern "File server"

  # Force removal without confirmation
  $(basename "${BASH_SOURCE[0]}") --host 192.168.1.100 --force

Note: This command will remove both allow and deny rules that were created
      for the specified host during isolation.
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                HOST="$2"
                shift 2
                ;;
            --comment-pattern)
                COMMENT_PATTERN="$2"
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
    
    # Validate host format
    if ! validate_network_source "$HOST"; then
        echo "Error: Invalid host specification '$HOST'" >&2
        exit 1
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

# Remove UFW isolation rules
remove_ufw_isolation() {
    local host="$1"
    local comment_pattern="$2"
    
    echo "Removing UFW isolation rules for $host..."
    
    # Get numbered rules
    local rules_output=$(ufw status numbered 2>/dev/null | grep -E "^\[[0-9]+\]")
    
    if [[ -z "$rules_output" ]]; then
        echo "No UFW rules found"
        return
    fi
    
    # Find rules related to the host
    local rules_to_delete=()
    
    while IFS= read -r line; do
        # Check if rule contains the host
        if echo "$line" | grep -q "$host"; then
            # If comment pattern specified, check for it
            if [[ -n "$comment_pattern" ]]; then
                if echo "$line" | grep -q "$comment_pattern"; then
                    local rule_num=$(echo "$line" | sed -n 's/^\[\([0-9]\+\)\].*/\1/p')
                    rules_to_delete+=("$rule_num")
                fi
            else
                local rule_num=$(echo "$line" | sed -n 's/^\[\([0-9]\+\)\].*/\1/p')
                rules_to_delete+=("$rule_num")
            fi
        fi
    done <<< "$rules_output"
    
    # Sort rules in descending order to delete from highest to lowest
    IFS=$'\n' rules_to_delete=($(sort -rn <<<"${rules_to_delete[*]}"))
    unset IFS
    
    # Delete rules
    local deleted_count=0
    for rule_num in "${rules_to_delete[@]}"; do
        if [[ "$VERBOSE" == "true" ]]; then
            echo "  Deleting rule $rule_num"
        fi
        
        execute_or_dryrun "echo y | ufw delete $rule_num" \
            "Deleted UFW rule $rule_num" \
            "Failed to delete UFW rule $rule_num" \
            "Delete UFW rule number $rule_num related to host $host"
            
        ((deleted_count++))
    done
    
    echo "Removed $deleted_count UFW rule(s) for $host"
}

# Remove firewalld isolation rules
remove_firewalld_isolation() {
    local host="$1"
    local comment_pattern="$2"
    
    echo "Removing firewalld isolation rules for $host..."
    
    # Get all rich rules
    local rules_output=$(firewall-cmd --list-rich-rules 2>/dev/null)
    
    if [[ -z "$rules_output" ]]; then
        echo "No firewalld rich rules found"
        return
    fi
    
    # Find rules related to the host
    local deleted_count=0
    
    while IFS= read -r rule; do
        # Check if rule contains the host
        if echo "$rule" | grep -q "source address=\"$host\""; then
            # If comment pattern specified, check for it (firewalld doesn't support comments in rich rules)
            # So we'll just remove all rules for the host
            
            if [[ "$VERBOSE" == "true" ]]; then
                echo "  Removing rule: $rule"
            fi
            
            execute_or_dryrun "firewall-cmd --permanent --remove-rich-rule='$rule'" \
                "Removed firewalld rule" \
                "Failed to remove firewalld rule" \
                "Remove firewalld rich rule for host $host"
                
            ((deleted_count++))
        fi
    done <<< "$rules_output"
    
    # Reload firewalld if any rules were removed
    if [[ $deleted_count -gt 0 ]]; then
        execute_or_dryrun "firewall-cmd --reload" \
            "Reloaded firewalld configuration" \
            "Failed to reload firewalld" \
            "Reload firewalld to apply changes"
    fi
    
    echo "Removed $deleted_count firewalld rule(s) for $host"
}

# Remove iptables isolation rules
remove_iptables_isolation() {
    local host="$1"
    local comment_pattern="$2"
    
    echo "Removing iptables isolation rules for $host..."
    
    # Get all INPUT rules with line numbers
    local rules_output=$(iptables -L INPUT -n --line-numbers -v 2>/dev/null)
    
    if [[ -z "$rules_output" ]]; then
        echo "No iptables rules found"
        return
    fi
    
    # Find rules related to the host
    local rules_to_delete=()
    
    while IFS= read -r line; do
        # Skip header lines
        if [[ "$line" =~ ^Chain ]] || [[ "$line" =~ ^num ]]; then
            continue
        fi
        
        # Check if rule contains the host
        if echo "$line" | grep -q "$host"; then
            # If comment pattern specified, check for it
            if [[ -n "$comment_pattern" ]]; then
                # Get the full rule details to check comment
                local rule_num=$(echo "$line" | awk '{print $1}')
                local rule_detail=$(iptables -L INPUT $rule_num -v -n 2>/dev/null | tail -n 1)
                
                if echo "$rule_detail" | grep -q "$comment_pattern"; then
                    rules_to_delete+=("$rule_num")
                fi
            else
                local rule_num=$(echo "$line" | awk '{print $1}')
                rules_to_delete+=("$rule_num")
            fi
        fi
    done <<< "$rules_output"
    
    # Sort rules in descending order to delete from highest to lowest
    IFS=$'\n' rules_to_delete=($(sort -rn <<<"${rules_to_delete[*]}"))
    unset IFS
    
    # Delete rules
    local deleted_count=0
    for rule_num in "${rules_to_delete[@]}"; do
        if [[ "$VERBOSE" == "true" ]]; then
            echo "  Deleting rule $rule_num"
        fi
        
        execute_or_dryrun "iptables -D INPUT $rule_num" \
            "Deleted iptables rule $rule_num" \
            "Failed to delete iptables rule $rule_num" \
            "Delete iptables INPUT rule number $rule_num related to host $host"
            
        ((deleted_count++))
    done
    
    # Save iptables rules if any were removed
    if [[ $deleted_count -gt 0 ]] && command -v iptables-save >/dev/null 2>&1; then
        execute_or_dryrun "iptables-save > /etc/iptables/rules.v4" \
            "Saved iptables rules" \
            "Failed to save iptables rules" \
            "Save iptables rules for persistence"
    fi
    
    echo "Removed $deleted_count iptables rule(s) for $host"
}

# Show current rules for host
show_current_rules() {
    local host="$1"
    local firewall_type="$2"
    
    echo ""
    echo "=== Current Rules for $host ==="
    
    case "$firewall_type" in
        ufw)
            echo "UFW rules:"
            ufw status numbered 2>/dev/null | grep "$host" || echo "  No rules found"
            ;;
        firewalld)
            echo "Firewalld rich rules:"
            firewall-cmd --list-rich-rules 2>/dev/null | grep "$host" || echo "  No rules found"
            ;;
        iptables)
            echo "Iptables INPUT rules:"
            iptables -L INPUT -n -v --line-numbers 2>/dev/null | grep "$host" || echo "  No rules found"
            ;;
    esac
    
    echo ""
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
    
    # Detect firewall type
    local firewall_type=$(detect_firewall)
    
    if [[ "$firewall_type" == "none" ]]; then
        echo "Error: No supported firewall detected (ufw, firewalld, or iptables)" >&2
        exit 1
    fi
    
    echo "Detected firewall: $firewall_type"
    
    # Show current rules if verbose
    if [[ "$VERBOSE" == "true" ]]; then
        show_current_rules "$HOST" "$firewall_type"
    fi
    
    # Confirm action if not forced
    if [[ "$FORCE" != "true" ]] && [[ "$DRY_RUN" != "true" ]]; then
        echo "Warning: This will remove all isolation rules for $HOST"
        echo "The host will return to normal firewall behavior."
        echo ""
        read -p "Are you sure you want to continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Operation cancelled"
            exit 0
        fi
    fi
    
    # Remove isolation based on firewall type
    case "$firewall_type" in
        ufw)
            remove_ufw_isolation "$HOST" "$COMMENT_PATTERN"
            ;;
        firewalld)
            remove_firewalld_isolation "$HOST" "$COMMENT_PATTERN"
            ;;
        iptables)
            remove_iptables_isolation "$HOST" "$COMMENT_PATTERN"
            ;;
    esac
    
    echo ""
    echo "Host $HOST has been unisolated"
    
    if [[ "$DRY_RUN" != "true" ]]; then
        echo "Note: The host now follows the default firewall rules."
    fi
}

# Execute main function
main "$@"