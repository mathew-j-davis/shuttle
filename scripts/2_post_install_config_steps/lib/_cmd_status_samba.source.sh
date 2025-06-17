# Command-specific help functions
show_help_status_samba() {
    cat << EOF
Usage: $SCRIPT_NAME status-samba [options]

Show Samba service status and information.

Optional Parameters:
  --verbose             Show detailed service information
  --format <format>     Output format: simple, detailed, json
  --dry-run             Show what would be done without making changes

Output Formats:
  simple    - Basic status information (default)
  detailed  - Comprehensive service details
  json      - JSON formatted output for automation

Examples:
  # Show basic status
  $SCRIPT_NAME status-samba
  
  # Show detailed status
  $SCRIPT_NAME status-samba --verbose
  
  # JSON output for monitoring
  $SCRIPT_NAME status-samba --format json

Information Displayed:
  - Service status (running/stopped)
  - Process IDs and uptime
  - Configuration file status
  - Listening ports and connections
  - Recent log entries (verbose mode)
EOF
}

cmd_status_samba() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local verbose=false
    local format="simple"
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --verbose)
                verbose=true
                shift
                ;;
            --format)
                format=$(validate_parameter_value "$1" "${2:-}" "Format required after --format" "show_help_status_samba")
                if [[ "$format" != "simple" && "$format" != "detailed" && "$format" != "json" ]]; then
                    show_help_status_samba
                    error_exit "Invalid format: $format. Must be 'simple', 'detailed', or 'json'"
                fi
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_status_samba
                return 0
                ;;
            *)
                show_help_status_samba
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    echo "status-samba command called with parameters: $original_params"
    
    # Call the core function
    status_samba_core "$verbose" "$format"
    
    return 0
}

# Core function to show Samba service status
status_samba_core() {
    local verbose="$1"
    local format="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "systemctl" "check service status" "systemctl not available"
    
    # Gather service information
    local smbd_status="unknown"
    local nmbd_status="unknown"
    local smbd_pid=""
    local nmbd_pid=""
    local smbd_uptime=""
    local nmbd_uptime=""
    local smbd_enabled="unknown"
    local nmbd_enabled="unknown"
    
    # Check service status
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
    
    # Check if services are enabled
    if systemctl is-enabled smbd >/dev/null 2>&1; then
        smbd_enabled="enabled"
    else
        smbd_enabled="disabled"
    fi
    
    if systemctl is-enabled nmbd >/dev/null 2>&1; then
        nmbd_enabled="enabled"
    else
        nmbd_enabled="disabled"
    fi
    
    # Get process information if running
    if [[ "$smbd_status" == "running" ]]; then
        smbd_pid=$(pgrep -f "smbd" | head -1)
        if [[ -n "$smbd_pid" ]]; then
            smbd_uptime=$(ps -o etime= -p "$smbd_pid" 2>/dev/null | xargs)
        fi
    fi
    
    if [[ "$nmbd_status" == "running" ]]; then
        nmbd_pid=$(pgrep -f "nmbd" | head -1)
        if [[ -n "$nmbd_pid" ]]; then
            nmbd_uptime=$(ps -o etime= -p "$nmbd_pid" 2>/dev/null | xargs)
        fi
    fi
    
    # Check configuration
    local config_status="unknown"
    if [[ -f /etc/samba/smb.conf ]]; then
        if testparm -s >/dev/null 2>&1; then
            config_status="valid"
        else
            config_status="invalid"
        fi
    else
        config_status="missing"
    fi
    
    # Get listening ports
    local smb_ports=""
    local nmb_ports=""
    if command -v netstat >/dev/null 2>&1; then
        smb_ports=$(netstat -tlnp 2>/dev/null | grep ":445\|:139" | grep smbd | awk '{print $4}' | tr '\n' ' ')
        nmb_ports=$(netstat -ulnp 2>/dev/null | grep ":137\|:138" | grep nmbd | awk '{print $4}' | tr '\n' ' ')
    elif command -v ss >/dev/null 2>&1; then
        smb_ports=$(ss -tlnp 2>/dev/null | grep ":445\|:139" | grep smbd | awk '{print $4}' | tr '\n' ' ')
        nmb_ports=$(ss -ulnp 2>/dev/null | grep ":137\|:138" | grep nmbd | awk '{print $4}' | tr '\n' ' ')
    fi
    
    # Output based on format
    case "$format" in
        "simple")
            echo ""
            echo "=== Samba Service Status ==="
            echo "smbd:             $smbd_status ($smbd_enabled)"
            echo "nmbd:             $nmbd_status ($nmbd_enabled)"
            echo "Configuration:    $config_status"
            
            if [[ "$smbd_status" == "running" && -n "$smbd_pid" ]]; then
                echo "smbd PID:         $smbd_pid"
                if [[ -n "$smbd_uptime" ]]; then
                    echo "smbd Uptime:      $smbd_uptime"
                fi
            fi
            
            if [[ "$nmbd_status" == "running" && -n "$nmbd_pid" ]]; then
                echo "nmbd PID:         $nmbd_pid"
                if [[ -n "$nmbd_uptime" ]]; then
                    echo "nmbd Uptime:      $nmbd_uptime"
                fi
            fi
            ;;
            
        "detailed")
            echo ""
            echo "=== Samba Service Status ==="
            echo "smbd Service:     $smbd_status ($smbd_enabled)"
            echo "nmbd Service:     $nmbd_status ($nmbd_enabled)"
            echo "Configuration:    $config_status"
            echo ""
            
            if [[ "$smbd_status" == "running" ]]; then
                echo "=== smbd Process Information ==="
                echo "PID:              $smbd_pid"
                echo "Uptime:           ${smbd_uptime:-unknown}"
                echo "Listening Ports:  ${smb_ports:-none detected}"
                echo ""
            fi
            
            if [[ "$nmbd_status" == "running" ]]; then
                echo "=== nmbd Process Information ==="
                echo "PID:              $nmbd_pid"
                echo "Uptime:           ${nmbd_uptime:-unknown}"
                echo "Listening Ports:  ${nmb_ports:-none detected}"
                echo ""
            fi
            
            echo "=== Configuration Information ==="
            echo "Config File:      /etc/samba/smb.conf"
            if [[ -f /etc/samba/smb.conf ]]; then
                local config_size=$(stat -c%s /etc/samba/smb.conf 2>/dev/null)
                local config_modified=$(stat -c%y /etc/samba/smb.conf 2>/dev/null | cut -d. -f1)
                echo "File Size:        ${config_size:-unknown} bytes"
                echo "Last Modified:    ${config_modified:-unknown}"
            fi
            echo ""
            
            # Show systemctl status if verbose
            if [[ "$verbose" == "true" ]]; then
                echo "=== Service Details ==="
                echo "smbd service status:"
                systemctl status smbd --no-pager -l 2>/dev/null | head -10 | sed 's/^/  /'
                echo ""
                echo "nmbd service status:"
                systemctl status nmbd --no-pager -l 2>/dev/null | head -10 | sed 's/^/  /'
                echo ""
            fi
            ;;
            
        "json")
            cat << EOF
{
  "samba_status": {
    "smbd": {
      "status": "$smbd_status",
      "enabled": "$smbd_enabled",
      "pid": "$smbd_pid",
      "uptime": "$smbd_uptime",
      "listening_ports": "$smb_ports"
    },
    "nmbd": {
      "status": "$nmbd_status",
      "enabled": "$nmbd_enabled",
      "pid": "$nmbd_pid",
      "uptime": "$nmbd_uptime",
      "listening_ports": "$nmb_ports"
    },
    "configuration": {
      "status": "$config_status",
      "file": "/etc/samba/smb.conf"
    },
    "overall_status": "$(if [[ "$smbd_status" == "running" ]]; then echo "operational"; else echo "not_operational"; fi)"
  }
}
EOF
            ;;
    esac
    
    return 0
}