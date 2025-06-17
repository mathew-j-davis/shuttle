# Command-specific help functions
show_help_reload_samba() {
    cat << EOF
Usage: $SCRIPT_NAME reload-samba [options]

Reload Samba configuration without stopping services.

Optional Parameters:
  --dry-run             Show what would be done without making changes

Examples:
  # Reload Samba configuration
  $SCRIPT_NAME reload-samba

Notes:
  - Reloads configuration without terminating connections
  - Uses systemctl reload or SIGHUP signal
  - Automatically tests configuration before reload
  - Preferred over restart when possible
  - Some configuration changes may still require full restart
EOF
}

cmd_reload_samba() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_reload_samba
                return 0
                ;;
            *)
                show_help_reload_samba
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    echo "reload-samba command called with parameters: $original_params"
    
    # Call the core function
    reload_samba_core
    
    return 0
}

# Core function to reload Samba configuration
reload_samba_core() {
    # Check tool availability
    check_tool_permission_or_error_exit "systemctl" "manage services" "systemctl not available"
    check_tool_permission_or_error_exit "testparm" "test configuration" "Samba tools not available"
    
    log INFO "Reloading Samba configuration"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would test Samba configuration"
        log INFO "[DRY RUN] Would reload smbd service configuration"
        log INFO "[DRY RUN] Would reload nmbd service configuration"
        return 0
    fi
    
    # Test configuration before reload
    log INFO "Testing Samba configuration before reload..."
    if ! sudo testparm -s >/dev/null 2>&1; then
        error_exit "Samba configuration test failed - not reloading services"
    fi
    log INFO "Configuration test passed"
    
    # Check if services are running
    local smbd_running=false
    local nmbd_running=false
    
    if systemctl is-active smbd >/dev/null 2>&1; then
        smbd_running=true
    fi
    
    if systemctl is-active nmbd >/dev/null 2>&1; then
        nmbd_running=true
    fi
    
    if [[ "$smbd_running" != "true" && "$nmbd_running" != "true" ]]; then
        log WARN "Samba services are not running - cannot reload configuration"
        log INFO "Use start-samba or restart-samba to start services"
        return 1
    fi
    
    # Reload smbd service
    if [[ "$smbd_running" == "true" ]]; then
        log INFO "Reloading smbd configuration..."
        local cmd="sudo systemctl reload smbd 2>/dev/null || sudo systemctl reload-or-restart smbd"
        if ! execute_or_dryrun "$cmd" "smbd configuration reloaded successfully" "Failed to reload smbd via systemctl"; then
            # Fallback to sending SIGHUP signal
            log INFO "Attempting to reload smbd via SIGHUP signal..."
            local fallback_cmd="sudo pkill -HUP smbd 2>/dev/null"
            if ! execute_or_dryrun "$fallback_cmd" "smbd configuration reloaded via signal" "Failed to reload smbd via signal"; then
                log WARN "Failed to reload smbd configuration"
            fi
        fi
    fi
    
    # Reload nmbd service
    if [[ "$nmbd_running" == "true" ]]; then
        log INFO "Reloading nmbd configuration..."
        local cmd="sudo systemctl reload nmbd 2>/dev/null || sudo systemctl reload-or-restart nmbd"
        if ! execute_or_dryrun "$cmd" "nmbd configuration reloaded successfully" "Failed to reload nmbd via systemctl"; then
            # Fallback to sending SIGHUP signal
            log INFO "Attempting to reload nmbd via SIGHUP signal..."
            local fallback_cmd="sudo pkill -HUP nmbd 2>/dev/null"
            if ! execute_or_dryrun "$fallback_cmd" "nmbd configuration reloaded via signal" "Failed to reload nmbd via signal"; then
                log WARN "Failed to reload nmbd configuration"
            fi
        fi
    fi
    
    # Verify services are still running
    sleep 1
    local smbd_status=""
    local nmbd_status=""
    
    if systemctl is-active smbd >/dev/null 2>&1; then
        smbd_status="running"
    else
        smbd_status="not running"
    fi
    
    if systemctl is-active nmbd >/dev/null 2>&1; then
        nmbd_status="running"
    else
        nmbd_status="not running"
    fi
    
    log INFO "Service status after reload: smbd ($smbd_status), nmbd ($nmbd_status)"
    
    if [[ "$smbd_status" == "running" ]]; then
        log INFO "Samba configuration reloaded successfully"
        log INFO "Note: Some configuration changes may require a full restart"
    else
        log WARN "smbd service not running after reload attempt"
    fi
    
    return 0
}