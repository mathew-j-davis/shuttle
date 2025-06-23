# Command-specific help functions
show_help_start_samba() {
    cat << EOF
Usage: $SCRIPT_NAME start-samba [options]

Start Samba services.

Optional Parameters:
  --dry-run             Show what would be done without making changes

Examples:
  # Start Samba services
  $SCRIPT_NAME start-samba

Notes:
  - Starts both smbd and nmbd services
  - Uses systemctl to manage services
  - Check status with status-samba command
  - Services must be installed before starting
EOF
}

cmd_start_samba() {
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
                show_help_start_samba
                return 0
                ;;
            *)
                show_help_start_samba
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    log_command_call "start-samba" "$original_params"
    
    # Call the core function
    start_samba_core
    
    return 0
}

# Core function to start Samba services
start_samba_core() {
    # Check tool availability
    check_tool_permission_or_error_exit "systemctl" "manage services" "systemctl not available"
    
    log INFO "Starting Samba services"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would start smbd service"
        log INFO "[DRY RUN] Would start nmbd service"
        return 0
    fi
    
    # Start smbd service
    log INFO "Starting smbd service..."
    local cmd="sudo systemctl start smbd"
    execute_or_dryrun "$cmd" "smbd service started successfully" "Failed to start smbd service" \
                     "Start Samba smbd daemon to enable SMB/CIFS file sharing functionality" || error_exit "Failed to start smbd service"
    
    # Start nmbd service
    log INFO "Starting nmbd service..."
    local cmd="sudo systemctl start nmbd"
    if ! execute_or_dryrun "$cmd" "nmbd service started successfully" "Failed to start nmbd service" \
                        "Start Samba nmbd daemon to provide NetBIOS name resolution and browsing services"; then
        log WARN "Failed to start nmbd service (may not be critical)"
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
    
    log INFO "Service status: smbd ($smbd_status), nmbd ($nmbd_status)"
    
    if [[ "$smbd_status" == "running" ]]; then
        log INFO "Samba services started successfully"
    else
        error_exit "Samba services failed to start properly"
    fi
    
    return 0
}