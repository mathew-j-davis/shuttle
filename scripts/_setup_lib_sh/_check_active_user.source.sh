
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
    if execute "sudo -n -v 2>/dev/null" \
              "Sudo access available (already authenticated)" \
              "Sudo authentication required" \
              "Check if user has active sudo authentication timestamp"; then
        return 0
    fi
    
    # "check if user is in sudo/wheel groups"
    # Check if user is in sudo or wheel group (common sudo groups)
    if execute "groups 2>/dev/null | grep -qE \"(sudo|wheel|admin)\"" \
              "User is in sudo group - sudo access likely available" \
              "User is not in sudo groups" \
              "Check if current user belongs to administrative groups (sudo/wheel/admin)"; then
        log WARN "You may be prompted for your sudo password during execution"
        return 0
    fi
    
    log WARN "Cannot verify sudo access - user not in common sudo groups"
    return 1
}