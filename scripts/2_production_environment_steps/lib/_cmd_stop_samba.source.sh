# Command-specific help functions
show_help_stop_samba() {
    cat << EOF
Usage: $SCRIPT_NAME stop-samba [options]

Stop Samba services.

Optional Parameters:
  --force               Stop services without confirmation
  --dry-run             Show what would be done without making changes

Examples:
  # Stop Samba services with confirmation
  $SCRIPT_NAME stop-samba
  
  # Stop services without confirmation
  $SCRIPT_NAME stop-samba --force

Notes:
  - Stops both smbd and nmbd services
  - Uses systemctl to manage services
  - Active connections will be terminated
  - Check status with status-samba command
EOF
}

cmd_stop_samba() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local force=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force)
                force=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_stop_samba
                return 0
                ;;
            *)
                show_help_stop_samba
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    echo "stop-samba command called with parameters: $original_params"
    
    # Call the core function
    stop_samba_core "$force"
    
    return 0
}

# Core function to stop Samba services
stop_samba_core() {
    local force="$1"
    
    # Check tool availability
    check_tool_permission_or_error_exit "systemctl" "manage services" "systemctl not available"
    
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
        log INFO "Samba services are already stopped"
        return 0
    fi
    
    # Confirmation prompt (unless force or dry-run)
    if [[ "$force" != "true" && "$DRY_RUN" != "true" ]]; then
        echo "Are you sure you want to stop Samba services? This will terminate active connections. (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log INFO "Samba service stop cancelled by user"
            return 0
        fi
    fi
    
    log INFO "Stopping Samba services"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        if [[ "$smbd_running" == "true" ]]; then
            log INFO "[DRY RUN] Would stop smbd service"
        fi
        if [[ "$nmbd_running" == "true" ]]; then
            log INFO "[DRY RUN] Would stop nmbd service"
        fi
        return 0
    fi
    
    # Stop smbd service
    if [[ "$smbd_running" == "true" ]]; then
        log INFO "Stopping smbd service..."
        if sudo systemctl stop smbd; then
            log INFO "smbd service stopped successfully"
        else
            log ERROR "Failed to stop smbd service"
        fi
    fi
    
    # Stop nmbd service
    if [[ "$nmbd_running" == "true" ]]; then
        log INFO "Stopping nmbd service..."
        if sudo systemctl stop nmbd; then
            log INFO "nmbd service stopped successfully"
        else
            log ERROR "Failed to stop nmbd service"
        fi
    fi
    
    # Verify services are stopped
    sleep 2
    local smbd_status=""
    local nmbd_status=""
    
    if systemctl is-active smbd >/dev/null 2>&1; then
        smbd_status="running"
    else
        smbd_status="stopped"
    fi
    
    if systemctl is-active nmbd >/dev/null 2>&1; then
        nmbd_status="running"
    else
        nmbd_status="stopped"
    fi
    
    log INFO "Service status: smbd ($smbd_status), nmbd ($nmbd_status)"
    
    if [[ "$smbd_status" == "stopped" ]]; then
        log INFO "Samba services stopped successfully"
    else
        log WARN "Some Samba services may still be running"
    fi
    
    return 0
}