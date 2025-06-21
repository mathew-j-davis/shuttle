
check_tool_permission_or_error_exit() {
    if ! check_generic_tool_permission "$1" "$2"; then
        error_exit "$3"
    fi
}

check_generic_tool_permission() {
    local tool="$1"
    local operation="$2"
    local can_execute=false
    local is_root=false
    local needs_sudo=false
    
    # Step 1: Check if tool exists
    if ! check_command "$tool"; then
        log WARN "Tool '$tool' not found in PATH"
        return 2  # Tool doesn't exist
    fi
    
    # Step 2: Check permissions
    if check_active_user_is_root; then
        is_root=true
        can_execute=true
        needs_sudo=false

    elif ! check_tool_needs_sudo "$tool"; then
        can_execute=true
        needs_sudo=false
    else
        needs_sudo=true
        # Assume we can execute with sudo if we have sudo access
        if check_active_user_has_sudo_access; then
            can_execute=true
        fi
    fi

    # Step 3: Report results
    if [[ "$can_execute" == "true" ]]; then
        if [[ "$needs_sudo" == "true" ]]; then
            log INFO "✓ Can $operation (requires sudo)"
        else
            log INFO "✓ Can $operation"
        fi
        return 0
    else
        log ERROR "✗ Cannot $operation - insufficient permissions for $tool"
        return 1
    fi
}

# Generic helper to check if a tool requires sudo
check_tool_needs_sudo() {
    local tool="$1"
    
    # These tools always work without special permissions
    case "$tool" in
        getent|id|groups|brew)
            return 1  # Does not need sudo
            ;;
    esac
    
    # Everything else typically needs root/sudo
    return 0  # Needs sudo
}

# Add sudo prefix to command if required based on tool and user permissions
# Usage: add_sudo_if_required "tool_name" "command"
# Returns: "command" or "sudo command" depending on requirements
add_sudo_if_required() {
    local tool="$1"
    local command="$2"
    
    # Check if running as root
    if check_active_user_is_root; then
        echo "$command"
        return 0
    fi
    
    # Check if tool needs sudo
    if ! check_tool_needs_sudo "$tool"; then
        echo "$command"
        return 0
    fi
    
    # Tool needs sudo and we're not root
    if check_active_user_has_sudo_access; then
        echo "sudo $command"
        return 0
    else
        echo "ERROR: Command requires root privileges or sudo access: $command" >&2
        echo "Either run as root or ensure user has sudo privileges" >&2
        return 1
    fi
}

# Check if a tool exists and optionally get its version
# Usage: check_tool_with_version "tool" "version_command" "context"
# Returns 0 if tool exists, 1 if not
# Prints version info if available
check_tool_with_version() {
    local tool="$1"
    local version_cmd="${2:-$tool --version}"  # Default to --version flag
    local context="${3:-tool check}"
    
    # First check if tool exists
    if ! check_command "$tool"; then
        log WARN "$tool not found in PATH"
        return 1
    fi
    
    # Try to get version if command provided
    if [[ -n "$version_cmd" && "$version_cmd" != "none" ]]; then
        if execute "$version_cmd 2>&1 | head -1" \
                  "$tool version retrieved" \
                  "$tool version check failed" \
                  "Get $tool version information"; then
            local version_output=$($version_cmd 2>&1 | head -1)
            log INFO "$tool: $version_output"
        else
            log INFO "$tool: found (version unknown)"
        fi
    else
        log INFO "$tool: found"
    fi
    
    return 0
}

# Check multiple tools and report status
# Usage: check_tools_installation "context" tool1 tool2 tool3...
# Returns 0 if all found, 1 if any missing
check_tools_installation() {
    local context="$1"
    shift
    local tools=("$@")
    local all_found=true
    
    log INFO "Verifying $context"
    
    for tool in "${tools[@]}"; do
        local tool_name="$tool"
        local version_cmd=""
        
        # Handle tool:version_cmd syntax
        if [[ "$tool" == *":"* ]]; then
            tool_name="${tool%%:*}"
            version_cmd="${tool#*:}"
        else
            # Default version commands for common tools
            case "$tool_name" in
                "python3")
                    version_cmd="python3 --version"
                    ;;
                "pip3")
                    version_cmd="pip3 --version"
                    ;;
                "clamscan")
                    version_cmd="clamscan --version"
                    ;;
                "clamdscan")
                    version_cmd="none"  # No version flag
                    ;;
                "ufw")
                    version_cmd="ufw --version"
                    ;;
                "firewall-cmd")
                    version_cmd="firewall-cmd --version"
                    ;;
                "iptables")
                    version_cmd="iptables --version"
                    ;;
                "systemctl")
                    version_cmd="systemctl --version"
                    ;;
                *)
                    version_cmd="$tool_name --version"
                    ;;
            esac
        fi
        
        if ! check_tool_with_version "$tool_name" "$version_cmd" "$context"; then
            all_found=false
        fi
    done
    
    return $([ "$all_found" == "true" ] && echo 0 || echo 1)
}