# Microsoft Defender Test Design

## Problem Statement

Microsoft Defender's output format lacks a standardized API and relies on parsing stdout text to determine scan results. This creates two primary risks:

1. **Filename Manipulation**: A malicious file with a specially crafted filename could include text that matches our "clean" detection pattern
2. **Output Format Changes**: Microsoft could change the output format without notice, breaking our detection logic

## Test Objectives

1. Create a daily verification test that confirms Microsoft Defender output format remains consistent
2. Use the actual application's scan functionality rather than a separate implementation
3. Test both positive (malware detected) and negative (clean file) scenarios
4. Alert administrators if the output format changes
5. Run reliably in a Linux environment

## Implementation Approach

### 1. Test File Creation

Create two types of test files:
- **Clean file**: Plain text with known safe content
- **EICAR test file**: Standard antivirus test file that all scanners should detect as malicious

```python
def create_test_files(test_dir):
    """Create test files in the specified directory."""
    # Create clean test file
    clean_path = os.path.join(test_dir, "clean_test.txt")
    with open(clean_path, 'w') as f:
        f.write("This is a safe test file.")
    
    # Create EICAR test file
    eicar_path = os.path.join(test_dir, "eicar_test.txt")
    with open(eicar_path, 'w') as f:
        f.write(r'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
    
    return clean_path, eicar_path
```

### 2. Use Existing Application Functionality

Leverage the existing scanning functionality from the Shuttle application:

```python
def test_defender_detection():
    """Test the Defender malware detection using application's actual functions."""
    from shuttle.scanning import scan_for_malware_using_defender, handle_defender_scan_result, scan_result_types
    
    # Create test files
    test_dir = tempfile.mkdtemp(prefix="defender_test_")
    clean_path, eicar_path = create_test_files(test_dir)
    
    try:
        # Test clean file detection
        clean_result = scan_for_malware_using_defender(clean_path)
        if clean_result != scan_result_types.FILE_IS_CLEAN:
            logging.error(f"Clean file not detected as clean: {clean_result}")
            return False
            
        # Test EICAR file detection
        eicar_result = scan_for_malware_using_defender(eicar_path)
        if eicar_result != scan_result_types.FILE_IS_SUSPECT:
            logging.error(f"EICAR file not detected as malicious: {eicar_result}")
            return False
            
        return True
    finally:
        # Clean up
        shutil.rmtree(test_dir)
```

### 3. Direct Access to Defender Output

For troubleshooting and verification, we should also directly access and log the raw output:

```python
def verify_defender_raw_output():
    """Get raw output from Defender to verify patterns."""
    test_dir = tempfile.mkdtemp(prefix="defender_raw_")
    clean_path, eicar_path = create_test_files(test_dir)
    
    try:
        # Run direct commands
        cmd = ["mdatp", "scan", "custom", "--ignore-exclusions", "--path"]
        
        # Clean file
        clean_cmd = cmd + [clean_path]
        clean_process = subprocess.run(clean_cmd, capture_output=True, text=True)
        logging.info(f"Clean file scan output: {clean_process.stdout}")
        
        # EICAR file
        eicar_cmd = cmd + [eicar_path]
        eicar_process = subprocess.run(eicar_cmd, capture_output=True, text=True)
        logging.info(f"EICAR file scan output: {eicar_process.stdout}")
        
        return clean_process.stdout, eicar_process.stdout
    finally:
        # Clean up
        shutil.rmtree(test_dir)
```

## Main Test Script Structure

Create a unified test script (`defender_verification.py`) that:

1. Runs as part of the application codebase
2. Can be executed independently or as part of system monitoring
3. Captures and logs detailed results

```python
def main():
    """Main test execution function."""
    setup_logging()
    
    # Run main application-based test
    app_test_result = test_defender_detection()
    
    # Get and log raw output for verification
    clean_output, eicar_output = verify_defender_raw_output()
    
    # Store historical output for pattern drift detection
    store_historical_outputs(clean_output, eicar_output)
    
    # Send notifications if test failed
    if not app_test_result:
        send_alert_notification()
        
    return 0 if app_test_result else 1
```

## Scheduling Options

For Linux environments, consider these options:

### 1. Systemd Timer (Preferred)

Create a systemd service and timer:

```ini
# /etc/systemd/system/defender-test.service
[Unit]
Description=Microsoft Defender Output Format Test
After=network.target

[Service]
Type=oneshot
ExecStart=/path/to/venv/bin/python /path/to/defender_verification.py
WorkingDirectory=/path/to/application
User=appuser

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/defender-test.timer
[Unit]
Description=Run Microsoft Defender test daily

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:
```bash
sudo systemctl enable defender-test.timer
sudo systemctl start defender-test.timer
```

### 2. Cron Job

Alternative using cron:

```
# Run daily at 6am
0 6 * * * /path/to/venv/bin/python /path/to/defender_verification.py >> /var/log/defender-test.log 2>&1
```

## Notification System

Leverage the application's existing notification system:

```python
def send_alert_notification():
    """Send alert using application's notification system."""
    from shuttle.notifier import Notifier
    
    # Create notifier with appropriate configuration
    notifier = Notifier(...)
    
    # Send notification
    notifier.notify(
        title="Microsoft Defender Output Format Changed",
        message="The Microsoft Defender scan output format may have changed. "
                "Please review logs and update pattern matching logic if needed.",
        priority="high"
    )
```

## Historical Pattern Tracking

Track output patterns over time to detect gradual changes:

```python
def store_historical_outputs(clean_output, eicar_output):
    """Store outputs in a versioned format to track changes over time."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create directory if it doesn't exist
    history_dir = os.path.join(os.path.dirname(__file__), "defender_history")
    os.makedirs(history_dir, exist_ok=True)
    
    # Write outputs to timestamped files
    with open(os.path.join(history_dir, f"clean_{timestamp}.txt"), "w") as f:
        f.write(clean_output)
        
    with open(os.path.join(history_dir, f"eicar_{timestamp}.txt"), "w") as f:
        f.write(eicar_output)
```

## Development Plan

1. **Phase 1:** Create basic test script that leverages existing app functionality
2. **Phase 2:** Add comprehensive logging and pattern tracking
3. **Phase 3:** Integrate with notification system
4. **Phase 4:** Set up scheduling mechanism (systemd or cron)
5. **Phase 5:** Create reporting dashboard for historical pattern tracking

## Next Steps

1. Finalize approach selection based on team feedback
2. Create integration points with existing codebase
3. Implement basic verification script
4. Test on multiple environments to verify consistency
5. Implement scheduling mechanism
6. Set up alerting integration
