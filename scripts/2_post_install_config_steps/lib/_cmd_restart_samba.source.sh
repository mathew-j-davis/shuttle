# Command-specific help functions
show_help_restart_samba() {
    cat << EOF
Usage: $SCRIPT_NAME restart-samba [options]

Restart Samba services.

Optional Parameters:
  --dry-run             Show what would be done without making changes

Examples:
  # Restart Samba services
  $SCRIPT_NAME restart-samba

Notes:
  - Restarts both smbd and nmbd services
  - Uses systemctl to manage services
  - Active connections will be terminated briefly
  - Automatically tests configuration before restart
  - Use after configuration changes to apply them
EOF
}

cmd_restart_samba() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help_restart_samba
                return 0
                ;;
            *)
                show_help_restart_samba
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    log_command_call "restart-samba" "$original_params"
    
    # Call the core function
    restart_samba_core
    
    return 0
}

# Core function to restart Samba services
restart_samba_core() {
    # Check tool availability
    check_tool_permission_or_error_exit "systemctl" "manage services" "systemctl not available"
    check_tool_permission_or_error_exit "testparm" "test configuration" "Samba tools not available"
    
    log INFO "Restarting Samba services"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would test Samba configuration"
        log INFO "[DRY RUN] Would restart smbd service"
        log INFO "[DRY RUN] Would restart nmbd service"
        return 0
    fi
    
    # Test configuration before restart
    log INFO "Testing Samba configuration before restart..."
    if ! sudo testparm -s >/dev/null 2>&1; then
        error_exit "Samba configuration test failed - not restarting services"
    fi
    log INFO "Configuration test passed"
    
    # Restart smbd service
    log INFO "Restarting smbd service..."
    local cmd="sudo systemctl restart smbd"
    execute_or_dryrun "$cmd" "smbd service restarted successfully" "Failed to restart smbd service" || error_exit "Failed to restart smbd service"
    
    # Restart nmbd service
    log INFO "Restarting nmbd service..."
    local cmd="sudo systemctl restart nmbd"
    if ! execute_or_dryrun "$cmd" "nmbd service restarted successfully" "Failed to restart nmbd service"; then
        log WARN "Failed to restart nmbd service (may not be critical)"
    fi
    
    # Verify services are running
    sleep 2
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
    
    log INFO "Service status after restart: smbd ($smbd_status), nmbd ($nmbd_status)"
    
    if [[ "$smbd_status" == "running" ]]; then
        log INFO "Samba services restarted successfully"
    else
        error_exit "Samba services failed to start after restart"
    fi
    
    return 0
}