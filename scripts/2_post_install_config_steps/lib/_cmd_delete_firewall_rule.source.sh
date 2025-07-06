#!/bin/bash

# Delete Firewall Rule Command
# Remove specific UFW firewall rules

# Show usage for delete-firewall-rule command
show_delete_firewall_rule_usage() {
    cat << EOF
Usage: $SCRIPT_NAME delete-firewall-rule [OPTIONS]

Delete specific UFW firewall rules by number, rule specification, or pattern.

OPTIONS:
  --number NUMBER            Delete rule by number (use list-firewall-rules --format numbered)
  --rule RULE               Delete rule by exact specification
  --service SERVICE         Delete all rules for service (ssh, samba, http, etc.)
  --port PORT               Delete all rules for specific port
  --from FROM               Delete rules from specific source (IP or range)
  --action ACTION           Delete rules with specific action (allow, deny, reject)
  --all                     Delete all firewall rules (with confirmation)
  --force                   Skip confirmation prompts
  --dry-run                 Show what would be deleted without making changes
  --verbose                 Show detailed output
  --help                    Show this help message

EXAMPLES:
  # Delete rule by number (get numbers with list-firewall-rules --format numbered)
  $SCRIPT_NAME delete-firewall-rule --number 3

  # Delete specific rule
  $SCRIPT_NAME delete-firewall-rule --rule "allow 22/tcp"

  # Delete all SSH rules
  $SCRIPT_NAME delete-firewall-rule --service ssh

  # Delete all rules for port 445
  $SCRIPT_NAME delete-firewall-rule --port 445

  # Delete rules from specific source
  $SCRIPT_NAME delete-firewall-rule --from 192.168.1.100

  # Delete all deny rules
  $SCRIPT_NAME delete-firewall-rule --action deny

  # Delete all rules (dangerous!)
  $SCRIPT_NAME delete-firewall-rule --all

  # Test what would be deleted
  $SCRIPT_NAME delete-firewall-rule --service samba --dry-run --verbose

SAFETY:
  • Use --dry-run to preview changes before applying
  • Rules are deleted permanently and cannot be easily restored
  • Deleting all rules may lock you out if SSH is blocked
  • Consider disabling specific rules instead of deleting

RULE NUMBERS:
  Rule numbers change after each deletion. Always check current
  numbers with list-firewall-rules --format numbered before deleting.
EOF
}

# Delete UFW firewall rules
delete_firewall_rule() {
    local rule_number=""
    local rule_spec=""
    local service=""
    local port=""
    local from_source=""
    local action=""
    local delete_all=false
    local force=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --number)
                rule_number="$2"
                if ! [[ "$rule_number" =~ ^[0-9]+$ ]]; then
                    error_exit "Invalid rule number: $rule_number. Must be a positive integer"
                fi
                shift 2
                ;;
            --rule)
                rule_spec="$2"
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
            --from)
                from_source="$2"
                shift 2
                ;;
            --action)
                action="$2"
                if [[ "$action" != "allow" && "$action" != "deny" && "$action" != "reject" ]]; then
                    error_exit "Invalid action: $action. Use 'allow', 'deny', or 'reject'"
                fi
                shift 2
                ;;
            --all)
                delete_all=true
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
                show_delete_firewall_rule_usage
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
    
    # Validate that at least one deletion criteria is specified
    if [[ -z "$rule_number" && -z "$rule_spec" && -z "$service" && -z "$port" && -z "$from_source" && -z "$action" && "$delete_all" == "false" ]]; then
        error_exit "Must specify deletion criteria. Use --help for usage information."
    fi
    
    # Get current rules for validation and preview
    local current_rules
    if ! current_rules=$(sudo ufw status numbered 2>/dev/null); then
        error_exit "Could not get UFW rules. Check permissions."
    fi
    
    # Check if there are any rules to delete
    if ! echo "$current_rules" | grep -q "^\["; then
        log INFO "No firewall rules found to delete"
        return 0
    fi
    
    log INFO "Analyzing firewall rules for deletion..."
    if [[ "$VERBOSE" == "true" ]]; then
        if [[ -n "$rule_number" ]]; then
            log INFO "  Target rule number: $rule_number"
        fi
        if [[ -n "$rule_spec" ]]; then
            log INFO "  Target rule spec: $rule_spec"
        fi
        if [[ -n "$service" ]]; then
            log INFO "  Target service: $service"
        fi
        if [[ -n "$port" ]]; then
            log INFO "  Target port: $port"
        fi
        if [[ -n "$from_source" ]]; then
            log INFO "  Target source: $from_source"
        fi
        if [[ -n "$action" ]]; then
            log INFO "  Target action: $action"
        fi
        if [[ "$delete_all" == "true" ]]; then
            log INFO "  Target: ALL RULES"
        fi
    fi
    
    # Handle specific deletion methods
    if [[ -n "$rule_number" ]]; then
        delete_rule_by_number "$rule_number" "$force"
    elif [[ -n "$rule_spec" ]]; then
        delete_rule_by_spec "$rule_spec" "$force"
    elif [[ "$delete_all" == "true" ]]; then
        delete_all_rules "$force"
    else
        delete_rules_by_criteria "$service" "$port" "$from_source" "$action" "$force"
    fi
}

# Delete rule by number
delete_rule_by_number() {
    local rule_number="$1"
    local force="$2"
    
    # Validate rule number exists
    local current_rules
    current_rules=$(sudo ufw status numbered 2>/dev/null)
    local rule_line
    rule_line=$(echo "$current_rules" | grep "^\[$rule_number\]")
    
    if [[ -z "$rule_line" ]]; then
        error_exit "Rule number $rule_number not found. Use list-firewall-rules --format numbered to see current rules."
    fi
    
    log INFO "Found rule to delete:"
    echo "  $rule_line"
    
    # Confirmation
    if [[ "$force" == "false" ]]; then
        if ! confirm_action "Delete this rule?"; then
            log INFO "Rule deletion cancelled"
            return 0
        fi
    fi
    
    # Delete rule
    log INFO "Deleting rule number $rule_number..."
    execute_or_execute_dryrun "sudo ufw --force delete $rule_number" "Delete firewall rule $rule_number"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log INFO "✅ Rule $rule_number deleted successfully"
    fi
}

# Delete rule by exact specification
delete_rule_by_spec() {
    local rule_spec="$1"
    local force="$2"
    
    log INFO "Deleting rule: $rule_spec"
    
    # Confirmation
    if [[ "$force" == "false" ]]; then
        if ! confirm_action "Delete rule '$rule_spec'?"; then
            log INFO "Rule deletion cancelled"
            return 0
        fi
    fi
    
    # Delete rule
    execute_or_execute_dryrun "sudo ufw delete $rule_spec" "Delete firewall rule: $rule_spec"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log INFO "✅ Rule deleted successfully"
    fi
}

# Delete all rules
delete_all_rules() {
    local force="$1"
    
    log WARN "⚠️  WARNING: This will delete ALL firewall rules!"
    log WARN "   This may lock you out if SSH rules are deleted"
    
    # Extra confirmation for delete all
    if [[ "$force" == "false" ]]; then
        echo ""
        log WARN "This action will permanently delete all firewall rules."
        if ! confirm_action "Are you ABSOLUTELY sure you want to delete ALL firewall rules?"; then
            log INFO "Delete all rules cancelled"
            return 0
        fi
        
        # Second confirmation
        if ! confirm_action "Final confirmation: Delete ALL firewall rules? (This cannot be undone)"; then
            log INFO "Delete all rules cancelled"
            return 0
        fi
    fi
    
    # Reset UFW to delete all rules
    log INFO "Deleting all firewall rules..."
    execute_or_execute_dryrun "sudo ufw --force reset" "Reset UFW (delete all rules)"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log INFO "✅ All firewall rules deleted"
        log WARN "🔓 Firewall is now inactive with no rules"
        log INFO "   Consider re-enabling with: $SCRIPT_NAME enable-firewall"
    fi
}

# Delete rules by criteria (service, port, source, action)
delete_rules_by_criteria() {
    local service="$1"
    local port="$2"
    local from_source="$3"
    local action="$4"
    local force="$5"
    
    # Get current numbered rules
    local current_rules
    current_rules=$(sudo ufw status numbered 2>/dev/null)
    
    # Find matching rules
    local matching_rules=()
    local rule_numbers=()
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^\[([0-9]+)\].*$ ]]; then
            local rule_num="${BASH_REMATCH[1]}"
            local matches=true
            
            # Check each criteria
            if [[ -n "$service" && ! "$line" =~ $service ]]; then
                matches=false
            fi
            if [[ -n "$port" && ! "$line" =~ $port ]]; then
                matches=false
            fi
            if [[ -n "$from_source" && ! "$line" =~ $from_source ]]; then
                matches=false
            fi
            if [[ -n "$action" && ! "$line" =~ $action ]]; then
                matches=false
            fi
            
            if [[ "$matches" == "true" ]]; then
                matching_rules+=("$line")
                rule_numbers+=("$rule_num")
            fi
        fi
    done <<< "$current_rules"
    
    # Check if any rules match
    if [[ ${#matching_rules[@]} -eq 0 ]]; then
        log INFO "No rules match the specified criteria"
        return 0
    fi
    
    # Show matching rules
    log INFO "Found ${#matching_rules[@]} matching rules:"
    for rule in "${matching_rules[@]}"; do
        echo "  $rule"
    done
    
    # Confirmation
    if [[ "$force" == "false" ]]; then
        if ! confirm_action "Delete these ${#matching_rules[@]} rules?"; then
            log INFO "Rule deletion cancelled"
            return 0
        fi
    fi
    
    # Delete rules in reverse order (highest number first) to maintain numbering
    log INFO "Deleting matching rules..."
    local sorted_numbers
    IFS=$'\n' sorted_numbers=($(sort -nr <<< "${rule_numbers[*]}")); unset IFS
    
    for rule_num in "${sorted_numbers[@]}"; do
        if [[ "$DRY_RUN" == "false" ]]; then
            sudo ufw --force delete "$rule_num" 2>/dev/null || log WARN "Failed to delete rule $rule_num"
            log INFO "  Deleted rule $rule_num"
        else
            log INFO "[DRY RUN]   Would delete rule $rule_num"
        fi
    done
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log INFO "✅ Deleted ${#matching_rules[@]} firewall rules"
    fi
}

# Main function for delete-firewall-rule command
cmd_delete_firewall_rule() {
    delete_firewall_rule "$@"
}

# Export functions for use by other scripts
export -f cmd_delete_firewall_rule
export -f show_delete_firewall_rule_usage
export -f delete_firewall_rule
export -f delete_rule_by_number
export -f delete_rule_by_spec
export -f delete_all_rules
export -f delete_rules_by_criteria