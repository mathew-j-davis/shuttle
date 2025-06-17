
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
        getent|id|groups)
            return 1  # Does not need sudo
            ;;
    esac
    
    # Everything else typically needs root/sudo
    return 0  # Needs sudo
}