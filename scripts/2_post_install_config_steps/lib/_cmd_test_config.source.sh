# Command-specific help functions
show_help_test_config() {
    cat << EOF
Usage: $SCRIPT_NAME test-config [options]

Test Samba configuration syntax and validity.

Optional Parameters:
  --verbose             Show detailed configuration analysis
  --show-config         Display the effective configuration
  --dry-run             Show what would be done without making changes

Examples:
  # Test configuration syntax
  $SCRIPT_NAME test-config
  
  # Test with detailed output
  $SCRIPT_NAME test-config --verbose
  
  # Test and show effective configuration
  $SCRIPT_NAME test-config --show-config

Information Displayed:
  - Configuration syntax validation
  - Share definitions and parameters
  - Global settings verification
  - Warning and error messages
  - Effective configuration (if requested)

Notes:
  - Uses testparm command to validate configuration
  - Reports syntax errors and warnings
  - Shows effective values after defaults applied
  - Run before restarting Samba services
EOF
}

cmd_test_config() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local verbose=false
    local show_config=false
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --verbose)
                verbose=true
                shift
                ;;
            --show-config)
                show_config=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help_test_config
                return 0
                ;;
            *)
                show_help_test_config
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    echo "test-config command called with parameters: $original_params"
    
    # Call the core function
    test_config_core "$verbose" "$show_config"
    
    return 0
}

# Core function to test Samba configuration
test_config_core() {
    local verbose="$1"
    local show_config="$2"
    
    # Check tool availability
    check_tool_permission_or_error_exit "testparm" "test Samba configuration" "Samba tools not available"
    
    # Check if configuration file exists
    if [[ ! -f /etc/samba/smb.conf ]]; then
        error_exit "Samba configuration file /etc/samba/smb.conf not found"
    fi
    
    log INFO "Testing Samba configuration"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would test /etc/samba/smb.conf with testparm"
        if [[ "$show_config" == "true" ]]; then
            log INFO "[DRY RUN] Would display effective configuration"
        fi
        if [[ "$verbose" == "true" ]]; then
            log INFO "[DRY RUN] Would show detailed analysis"
        fi
        return 0
    fi
    
    echo ""
    echo "=== Samba Configuration Test ==="
    echo "Configuration file: /etc/samba/smb.conf"
    
    # Get file information
    local config_size=$(stat -c%s /etc/samba/smb.conf 2>/dev/null)
    local config_modified=$(stat -c%y /etc/samba/smb.conf 2>/dev/null | cut -d. -f1)
    echo "File size: ${config_size:-unknown} bytes"
    echo "Last modified: ${config_modified:-unknown}"
    echo ""
    
    # Run testparm with different levels of detail
    local testparm_result=""
    local testparm_exit_code=0
    
    if [[ "$verbose" == "true" ]]; then
        echo "=== Detailed Configuration Test ==="
        # Run testparm with verbose output, capture both stdout and stderr
        testparm_result=$(testparm -v /etc/samba/smb.conf 2>&1)
        testparm_exit_code=$?
    else
        echo "=== Basic Configuration Test ==="
        # Run testparm with standard output
        testparm_result=$(testparm /etc/samba/smb.conf 2>&1)
        testparm_exit_code=$?
    fi
    
    # Display results
    echo "$testparm_result"
    echo ""
    
    # Analyze results
    if [[ $testparm_exit_code -eq 0 ]]; then
        echo "=== Test Results ==="
        echo "Status: PASSED"
        echo "Configuration syntax is valid"
        
        # Count shares
        local share_count=$(echo "$testparm_result" | grep -c "^\[.*\]" || echo "0")
        echo "Shares found: $share_count"
        
        # Check for warnings
        local warning_count=$(echo "$testparm_result" | grep -ci "warning\|note" || echo "0")
        if [[ "$warning_count" -gt 0 ]]; then
            echo "Warnings: $warning_count (see output above)"
        else
            echo "Warnings: none"
        fi
        
    else
        echo "=== Test Results ==="
        echo "Status: FAILED"
        echo "Configuration has syntax errors"
        
        # Extract error information
        local error_lines=$(echo "$testparm_result" | grep -i "error\|failed\|invalid" || echo "")
        if [[ -n "$error_lines" ]]; then
            echo ""
            echo "Error details:"
            echo "$error_lines" | sed 's/^/  /'
        fi
        
        echo ""
        error_exit "Configuration test failed - please fix errors before proceeding"
    fi
    
    # Show effective configuration if requested
    if [[ "$show_config" == "true" ]]; then
        echo ""
        echo "=== Effective Configuration ==="
        echo "(This shows the configuration as Samba will interpret it)"
        echo ""
        
        if testparm -s /etc/samba/smb.conf 2>/dev/null; then
            echo ""
            echo "Configuration displayed successfully"
        else
            echo "Failed to display effective configuration"
        fi
    fi
    
    # Additional analysis for verbose mode
    if [[ "$verbose" == "true" ]]; then
        echo ""
        echo "=== Configuration Analysis ==="
        
        # Check for common issues
        local global_section=$(testparm -s 2>/dev/null | sed -n '/^\[global\]/,/^\[/p' | grep -v "^\[")
        
        # Check workgroup
        if echo "$global_section" | grep -q "workgroup = "; then
            local workgroup=$(echo "$global_section" | grep "workgroup = " | cut -d= -f2 | xargs)
            echo "Workgroup: $workgroup"
        fi
        
        # Check security mode
        if echo "$global_section" | grep -q "security = "; then
            local security=$(echo "$global_section" | grep "security = " | cut -d= -f2 | xargs)
            echo "Security mode: $security"
        fi
        
        # Check for password backend
        if echo "$global_section" | grep -q "passdb backend = "; then
            local passdb=$(echo "$global_section" | grep "passdb backend = " | cut -d= -f2 | xargs)
            echo "Password backend: $passdb"
        fi
        
        # List non-global shares
        local custom_shares=$(testparm -s 2>/dev/null | grep "^\[" | grep -v "^\[global\]" | wc -l)
        echo "Custom shares: $custom_shares"
    fi
    
    echo ""
    log INFO "Configuration test completed successfully"
    
    return 0
}