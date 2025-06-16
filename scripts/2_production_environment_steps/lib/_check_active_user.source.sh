
#
check_active_user_is_root() {

    if [[ $EUID -eq 0 ]]; then
        return 0    
    fi   
    
    return 1

}


# Check sudo access capabilities
check_active_user_has_sudo_access() {
    # Check if sudo exists
    # "check_active_user_has_sudo_access"
    if ! check_command "sudo"; then
        log WARN "sudo not found - operations will be limited"
        return 1
    fi
    
    # "call sudo -n -v to test if already authenticated"
    # First try to check if we already have a valid sudo timestamp (non-interactive)
    if sudo -n -v 2>/dev/null; then
        log INFO "Sudo access available (already authenticated)"
        return 0
    fi
    
    # "check if user is in sudo/wheel groups"
    # Check if user is in sudo or wheel group (common sudo groups)
    if groups 2>/dev/null | grep -qE "(sudo|wheel|admin)"; then
        log INFO "User is in sudo group - sudo access likely available"
        log WARN "You may be prompted for your sudo password during execution"
        return 0
    fi
    
    log WARN "Cannot verify sudo access - user not in common sudo groups"
    return 1
}