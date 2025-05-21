# Scan Utility Fixes Plan

## Issues Identified

1. **Pattern Matching for "No Threats" is Imprecise**
   - Current pattern: `endsWith("0 threat(s) detected")`
   - Problem: Could match "10 threat(s) detected" incorrectly
   - Scan output contains formatting (tabs, newlines)

2. **File Not Found Handling**
   - When a file doesn't exist, defender outputs: `0 file(s) scanned`
   - Currently not detected or handled specially
   - Need to differentiate from clean scan

3. **Return Value Handling in Defender Test App**
   - `run_defender_scan` returns an integer but caller unpacks as tuple
   - Need consistent return types

4. **Notifier Parameter Mismatch**
   - Using `recipient` instead of `recipient_email`
   - Using `sender` instead of `sender_email`

## Proposed Changes

### 1. Improve Pattern Matching in `scan_utils.py`

```python
# Update pattern constants with whitespace for more precise matching
defender_scan_patterns.NO_THREATS = "\n\t0 threat(s) detected"
defender_scan_patterns.FILE_NOT_FOUND = "\n\t0 file(s) scanned\n\t0 threat(s) detected"

# Add file not found result type constant
scan_result_types.FILE_NOT_FOUND = 404

# In handle_defender_scan_result function
# Check for file not found condition first
if output.rstrip().endswith(defender_scan_patterns.FILE_NOT_FOUND):
    logger.warning("File not found or could not be scanned")
    return scan_result_types.FILE_NOT_FOUND

# Improve "no threats" pattern matching
# Since the pattern now includes newline and tab, it will only match the exact string
if output.rstrip().endswith(defender_scan_patterns.NO_THREATS):
    logger.info("No threat found")
    return scan_result_types.FILE_IS_CLEAN
```

### 2. Update Scanning Logic in `scanning.py`

```python
# Add check for file not found
if defender_result == scan_result_types.FILE_NOT_FOUND:
    logger.warning(f"File not found or couldn't be scanned: {quarantine_file_path}")
    # Decision point: how to handle missing files?
    # Option 1: Return False to indicate failure
    # Option 2: Continue with other scans
    # Option 3: Log and treat as "suspicious" conservatively
    return False
```

### 3. Update Defender Test App Return Value Handling

```python
# Ensure test_result_handler always returns a tuple
def test_result_handler(returncode, output, logging_options=None):
    # Existing code...
    return returncode, output

# Ensure run_defender_scan properly handles exceptions
try:
    return scan_for_malware_using_defender(
        file_path, 
        custom_handler=test_result_handler, 
        logging_options=logging_options
    )
except Exception as e:
    logger.error(f"Error running scan: {e}")
    return -1, str(e)  # Always return a tuple for consistency
```

### 4. Fix Notifier Parameter Names

```python
# Update the parameters in the Notifier call
notifier = Notifier(
    recipient_email=config.notify_recipient_email,  # Changed from recipient
    sender_email=config.notify_sender_email,        # Changed from sender
    smtp_server=config.notify_smtp_server,
    smtp_port=config.notify_smtp_port,
    username=config.notify_username,
    password=config.notify_password,
    use_tls=config.notify_use_tls,
    logging_options=logging_options
)
```

## Implementation Strategy

1. Fix Notifier parameter names first (simplest fix)
2. Fix pattern matching for threats detection
3. Add file not found pattern detection 
4. Update scanning.py to handle the file not found case
5. Test each change separately

This approach allows incremental testing and rollback if any issue arises.



import os

def run_malware_scan_fixed(cmd, path, result_handler, logging_options=None):
    """
    Fix for run_malware_scan that ensures consistent return type based on handler.
    
    If the result_handler returns a tuple, ensure we always return a tuple even 
    in error paths. Otherwise, return an integer as before.
    
    Example usage:
    ```
    # Apply this function
    with open('/path/to/scan_utils.py', 'r') as file:
        content = file.read()
    
    # Replace the original function with this fixed version
    content = content.replace(
        'def run_malware_scan(cmd, path, result_handler, logging_options=None):',
        run_malware_scan_fixed.__doc__ + '\ndef run_malware_scan(cmd, path, result_handler, logging_options=None):'
    )
    
    # Update the security checks to handle tuple returns
    content = content.replace(
        'return scan_result_types.FILE_SCAN_FAILED',
        '# Check if handler returns a tuple (test_result_handler) or int (normal handlers)\n        if hasattr(result_handler, "__annotations__") and "return" in result_handler.__annotations__ and result_handler.__annotations__["return"] == tuple:\n            return -1, f"Scan failed: Security check failed"\n        return scan_result_types.FILE_SCAN_FAILED'
    )
    
    with open('/path/to/scan_utils.py', 'w') as file:
        file.write(content)
    ```
    """
    pass

def pattern_updates_fix(content):
    """
    Update the pattern constants and handler function to better detect threats and handle file not found.
    
    Example usage:
    ```
    with open('/path/to/scan_utils.py', 'r') as file:
        content = file.read()
    
    content = pattern_updates_fix(content)
    
    with open('/path/to/scan_utils.py', 'w') as file:
        file.write(content)
    ```
    """
    # Add FILE_NOT_FOUND pattern
    new_patterns = 'defender_scan_patterns.THREAT_FOUND = "Threat(s) found"\n'
    new_patterns += 'defender_scan_patterns.NO_THREATS = "\\n\\t0 threat(s) detected"\n'
    new_patterns += 'defender_scan_patterns.FILE_NOT_FOUND = "\\n\\t0 file(s) scanned\\n\\t0 threat(s) detected"'
    
    content = content.replace(
        'defender_scan_patterns.THREAT_FOUND = "Threat(s) found"\n'
        'defender_scan_patterns.NO_THREATS = "0 threat(s) detected"',
        new_patterns
    )
    
    # Add FILE_NOT_FOUND result type
    new_result_types = 'scan_result_types.FILE_IS_SUSPECT = 3\n'
    new_result_types += 'scan_result_types.FILE_IS_CLEAN = 0\n'
    new_result_types += 'scan_result_types.FILE_NOT_FOUND = 404\n'
    new_result_types += 'scan_result_types.FILE_SCAN_FAILED = 100'
    
    content = content.replace(
        'scan_result_types.FILE_IS_SUSPECT = 3\n'
        'scan_result_types.FILE_IS_CLEAN = 0\n'
        'scan_result_types.FILE_SCAN_FAILED = 100',
        new_result_types
    )
    
    # Update defender scan result handler
    original_handler = 'def handle_defender_scan_result(returncode, output, logging_options=None):'
    original_handler += '\n    """\n    Process Microsoft Defender scan results.\n    \n    Args:\n        returncode (int): Process return code\n        output (str): Process output\n        logging_options (LoggingOptions, optional): Logging configuration options\n        \n    Returns:\n        int: scan_result_types value\n    """\n    logger = setup_logging(\'shuttle.common.scan_utils.handle_defender_scan_result\', logging_options)\n    \n    if returncode == 0:\n        # Always check for threat pattern first, otherwise a malicious filename could be used to add clean response text to output\n        if defender_scan_patterns.THREAT_FOUND in output:\n            logger.warning("Threats found")\n            return scan_result_types.FILE_IS_SUSPECT\n        \n        elif output.rstrip().endswith(defender_scan_patterns.NO_THREATS):\n            logger.info("No threat found")\n            return scan_result_types.FILE_IS_CLEAN'
    
    new_handler = 'def handle_defender_scan_result(returncode, output, logging_options=None):'
    new_handler += '\n    """\n    Process Microsoft Defender scan results.\n    \n    Args:\n        returncode (int): Process return code\n        output (str): Process output\n        logging_options (LoggingOptions, optional): Logging configuration options\n        \n    Returns:\n        int: scan_result_types value\n    """\n    logger = setup_logging(\'shuttle.common.scan_utils.handle_defender_scan_result\', logging_options)\n    \n    # Check for file not found condition first\n    if output.rstrip().endswith(defender_scan_patterns.FILE_NOT_FOUND):\n        logger.warning("File not found or could not be scanned")\n        return scan_result_types.FILE_NOT_FOUND\n    \n    if returncode == 0:\n        # Always check for threat pattern first, otherwise a malicious filename could be used to add clean response text to output\n        if defender_scan_patterns.THREAT_FOUND in output:\n            logger.warning("Threats found")\n            return scan_result_types.FILE_IS_SUSPECT\n        \n        elif output.rstrip().endswith(defender_scan_patterns.NO_THREATS):\n            logger.info("No threat found")\n            return scan_result_types.FILE_IS_CLEAN'
    
    content = content.replace(original_handler, new_handler)
    
    return content
