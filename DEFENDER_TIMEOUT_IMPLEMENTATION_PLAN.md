# Malware Scanner Timeout Implementation Plan

## Problem Summary

Malware scanners (particularly Microsoft Defender on Linux) can have bugs that cause scan processes to lock up indefinitely. This prevents shuttle from completing its processing and can lead to data inconsistency if not handled properly.

## Solution Overview

Implement a configurable timeout mechanism with retry logic that:
1. Kills hung scan processes after a timeout
2. Retries scans up to a configured count with wait periods
3. Gracefully handles shutdown when retry count is exhausted
4. Ensures data consistency by properly cleaning up files

## Configuration Requirements

### New Config Parameters

Add to `CommonConfig` in `/src/shared_library/shuttle_common/config.py`:
```python
# Malware scan timeout settings (applies to all scanners: Defender, ClamAV, etc.)
malware_scan_timeout_seconds: int = 300  # Default 5 minutes (0 = no timeout)
malware_scan_retry_wait_seconds: int = 30  # Wait between retries (0 = no wait)
malware_scan_retry_count: int = 3  # Max retries before giving up (0 = unlimited)
```

### Config File Section
Add to `[scanning]` section in config files:
```ini
[scanning]
malware_scan_timeout_seconds = 300        # 0 = no timeout
malware_scan_retry_wait_seconds = 30       # 0 = no wait between retries
malware_scan_retry_count = 3               # 0 = unlimited retries
```

### Command Line Arguments
Add to `add_common_arguments()`:
```python
parser.add_argument('--malware-scan-timeout-seconds', 
                    type=int,
                    help='Timeout for malware scan in seconds (default: 300, 0 = no timeout)')
parser.add_argument('--malware-scan-retry-wait-seconds', 
                    type=int,
                    help='Wait time between scan retries in seconds (default: 30, 0 = no wait)')
parser.add_argument('--malware-scan-retry-count', 
                    type=int,
                    help='Maximum number of scan retries (default: 3, 0 = unlimited)')
```

## ✅ Implementation Status: COMPLETED with ALL Fixes Applied

All timeout and shutdown functionality has been successfully implemented with:
- ✅ Graceful multithreaded shutdown support
- ✅ Fixed infinite hang in graceful shutdown (bounded timeout added)
- ✅ Comprehensive error handling in shutdown process
- ✅ Standardized config parameter names (no backward compatibility needed - new feature)

## Implementation Changes ✅ COMPLETED

### 1. ✅ Update `run_malware_scan()` in `scan_utils.py`

**Current Code (lines 189-209):**
```python
def run_malware_scan(cmd, path, result_handler):
    # ... validation code ...
    try:
        logger.info(f"Scanning file {path} for malware...")
        
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        scan_time = time.time() - start_time
        # ... rest of function
```

**New Implementation:**
```python
def run_malware_scan(cmd, path, result_handler, timeout_seconds=None):
    """
    Run a malware scan with timeout support.
    
    Args:
        cmd: Command to run as list
        path: Path to file being scanned
        result_handler: Function to process results
        timeout_seconds: Timeout in seconds (None for no timeout)
        
    Returns:
        int: scan_result_types value
        
    Raises:
        ScanTimeoutError: If scan times out after all retries
    """
    # ... existing validation code ...
    
    try:
        logger.info(f"Scanning file {path} for malware...")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds  # Add timeout
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Scan timed out after {timeout_seconds} seconds for {path}")
            raise ScanTimeoutError(f"Scan timed out for {path}")
            
        scan_time = time.time() - start_time
        # ... rest remains same
```

### 2. Create Custom Exception

Add to `scan_utils.py`:
```python
class ScanTimeoutError(Exception):
    """Raised when a malware scan times out"""
    pass
```

### 3. Update `scan_for_malware_using_defender()`

**Current Code (lines 248-268):**
```python
def scan_for_malware_using_defender(path):
    cmd = [
        DEFENDER_COMMAND,
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path"
    ]
    return run_malware_scan(cmd, path, parse_defender_scan_result)
```

**New Implementation:**
```python
def scan_for_malware_using_defender(path, config=None):
    """
    Scan using Defender with retry logic for timeouts.
    
    Args:
        path: File path to scan
        config: CommonConfig object with timeout settings
        
    Returns:
        Scan result or raises ScanTimeoutError after all retries
    """
    cmd = [
        DEFENDER_COMMAND,
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path"
    ]
    
    # Config defaults are already set in CommonConfig, use them directly
    timeout = config.defender_scan_timeout_seconds if config else 300
    retry_wait = config.defender_scan_retry_wait_seconds if config else 30
    retry_count = config.defender_scan_retry_count if config else 3
    
    logger = get_logger()
    
    # Handle special cases for zero values
    if timeout == 0:
        timeout = None  # No timeout
        
    # If retry_count is 0, use unlimited retries
    attempt = 0
    while True:
        try:
            return run_malware_scan(cmd, path, parse_defender_scan_result, timeout)
        except ScanTimeoutError:
            attempt += 1
            
            # Check if we should retry
            if retry_count > 0 and attempt >= retry_count:
                logger.error(f"Scan timeout after {retry_count} attempts for {path}")
                raise
            
            # Log retry attempt
            if retry_count > 0:
                logger.warning(f"Scan timeout on attempt {attempt}/{retry_count} for {path}")
            else:
                logger.warning(f"Scan timeout on attempt {attempt} (unlimited retries) for {path}")
            
            # Wait before retry (unless wait time is 0)
            if retry_wait > 0:
                logger.debug(f"Waiting {retry_wait}s before retry")
                time.sleep(retry_wait)
```

### 4. Update `scan_and_process_file()` in `scanning.py`

Add config parameter and handle timeout:
```python
def scan_and_process_file(file_paths, hazard_key_path, hazard_path, delete_source, use_defender, use_clamav, defender_handles_suspect, config=None):
    # ... existing code ...
    
    if on_demand_defender:
        logger.info(f"Scanning file {quarantine_file_path} for malware...")
        try:
            defender_result = scan_for_malware_using_defender(quarantine_file_path, config)
        except ScanTimeoutError:
            # Treat timeout as scan failure
            logger.error(f"Defender scan timed out for {quarantine_file_path}")
            return ScanTimeoutResult(quarantine_file_path, source_file_path)
```

### 5. Create Timeout Result Class

Add to `scanning.py`:
```python
class ScanTimeoutResult:
    """Result object for scan timeout"""
    def __init__(self, quarantine_path, source_path):
        self.quarantine_path = quarantine_path
        self.source_path = source_path
        self.is_timeout = True
        self.is_suspect = False  # Treat timeouts as failures, not suspects
```

### 6. Update `process_scan_tasks()` to Handle Shutdown

**Key Changes:**
1. Track timeout count across all files
2. Stop processing when max timeouts reached
3. Return shutdown flag

```python
def process_scan_tasks(scan_tasks, max_scan_threads, daily_processing_tracker=None, config=None):
    """
    Process scan tasks with timeout shutdown capability.
    
    Returns:
        tuple: (results, successful_files, failed_files, timeout_shutdown)
    """
    results = []
    total_files = len(scan_tasks)
    processed_count = 0
    failed_count = 0
    timeout_count = 0
    timeout_shutdown = False
    
    # Get max timeouts from config (0 means unlimited, so set high number)
    max_timeouts = config.defender_scan_retry_count if config else 3
    if max_timeouts == 0:
        max_timeouts = float('inf')  # Unlimited retries means no shutdown
    
    # ... existing parallel/sequential logic ...
    
    # In task result processing:
    if hasattr(task_result, 'is_timeout') and task_result.is_timeout:
        timeout_count += 1
        if timeout_count >= max_timeouts:
            logger.error(f"Reached maximum timeout count ({max_timeouts}), shutting down processing")
            timeout_shutdown = True
            # Cancel remaining tasks
            executor.shutdown(wait=False, cancel_futures=True)
            break
            
    return results, processed_count - failed_count, failed_count, timeout_shutdown
```

### 7. Update `scan_and_process_directory()` for Cleanup

**Critical Section (lines 695-723):**
```python
# Process all scan tasks
results, successful_files, failed_files, timeout_shutdown = process_scan_tasks(
    scan_tasks,
    max_scan_threads,
    daily_processing_tracker,
    config
)

# Handle timeout shutdown with proper cleanup
if timeout_shutdown:
    logger.error("Processing stopped due to excessive scan timeouts")
    
    # CRITICAL: Perform cleanup for processed files
    # 1. Remove successfully moved files from source (if delete_source_files)
    # 2. Remove quarantine directory contents
    # 3. Ensure hazard files are encrypted and source removed
    
    cleanup_after_timeout_shutdown(
        quarantine_files,
        results,
        source_path,
        destination_path,
        hazard_archive_path,
        delete_source_files,
        quarantine_path
    )
    
    # Send critical error notification
    if notifier:
        notifier.notify_error(
            "Shuttle: Critical Timeout Error",
            f"Processing stopped due to excessive Defender timeouts.\n"
            f"Processed {successful_files} files successfully before shutdown.\n"
            f"Failed files: {failed_files}\n"
            f"Please check Defender service health."
        )
    
    return  # Exit early

# Normal cleanup continues...
remove_directory_contents(quarantine_path)
clean_up_source_files(quarantine_files, results, source_path, delete_source_files)
```

### 8. Implement Cleanup Function

```python
def cleanup_after_timeout_shutdown(quarantine_files, results, source_path, destination_path, 
                                 hazard_archive_path, delete_source_files, quarantine_path):
    """
    Ensure data consistency after timeout shutdown.
    
    Critical operations:
    1. Remove source files that were successfully processed
    2. Ensure hazard files are properly handled
    3. Clean quarantine directory
    """
    logger = get_logger()
    logger.info("Starting cleanup after timeout shutdown")
    
    # Process each file based on its result
    for i, (q_path, s_path, d_path) in enumerate(quarantine_files):
        if i >= len(results):
            # File was never processed - leave source intact
            logger.debug(f"File never processed: {s_path}")
            continue
            
        result = results[i]
        
        if result is True:
            # Successfully moved to destination
            if delete_source_files:
                try:
                    os.remove(s_path)
                    logger.info(f"Removed source file after successful transfer: {s_path}")
                except Exception as e:
                    logger.error(f"Failed to remove source file {s_path}: {e}")
                    
        elif hasattr(result, 'is_suspect') and result.is_suspect:
            # File was moved to hazard - ensure source is removed
            if delete_source_files:
                try:
                    os.remove(s_path)
                    logger.info(f"Removed source file after hazard detection: {s_path}")
                except Exception as e:
                    logger.error(f"Failed to remove hazard source {s_path}: {e}")
    
    # Clean quarantine directory
    try:
        remove_directory_contents(quarantine_path)
        logger.info("Cleaned quarantine directory")
    except Exception as e:
        logger.error(f"Failed to clean quarantine: {e}")
```

## Testing Strategy

### Unit Tests
1. Test timeout detection in `run_malware_scan()`
2. Test retry logic in `scan_for_malware_using_defender()`
3. Test cleanup function with various file states

### Integration Tests
1. Mock defender with controllable delays
2. Test full pipeline with timeout scenarios
3. Verify data consistency after timeout shutdown

### Manual Testing
1. Use `sleep` command instead of defender for testing
2. Verify cleanup with real file operations
3. Test notification delivery

## Rollout Plan

### Phase 1: Add Configuration
1. Update config classes
2. Add command line arguments
3. Update config file examples

### Phase 2: Implement Core Logic
1. Add timeout to subprocess calls
2. Implement retry logic
3. Create result classes

### Phase 3: Implement Cleanup
1. Track file states properly
2. Implement cleanup function
3. Add shutdown handling

### Phase 4: Testing
1. Unit tests
2. Integration tests
3. Production pilot

## Risk Mitigation

### Data Consistency
- Never remove source file unless certain of destination/hazard state
- Log all cleanup operations
- Send notifications on timeout shutdown

### Performance Impact
- Timeout adds minimal overhead to normal operations
- Retry logic only activated on timeout
- Configurable parameters allow tuning

### Backward Compatibility
- Default timeout values if config missing
- Existing installations continue working
- New parameters are optional

## Configuration Examples

### Conservative (Long timeout, few retries)
```ini
scan_timeout_seconds = 600  # 10 minutes
scan_retry_wait_seconds = 60  # 1 minute wait
scan_retry_count = 2  # 2 retries max
```

### Aggressive (Short timeout, more retries)
```ini
scan_timeout_seconds = 120  # 2 minutes
scan_retry_wait_seconds = 15  # 15 second wait
scan_retry_count = 5  # 5 retries max
```

### Testing (Very short for debugging)
```ini
scan_timeout_seconds = 10  # 10 seconds
scan_retry_wait_seconds = 5  # 5 second wait
scan_retry_count = 2  # 2 retries
```

### No Timeout (Unlimited retries)
```ini
scan_timeout_seconds = 0  # No timeout - let Defender run forever
scan_retry_wait_seconds = 60  # 1 minute wait between retries
scan_retry_count = 0  # Unlimited retries - never give up
```

### No Delays (Fast retries)
```ini
scan_timeout_seconds = 120  # 2 minute timeout
scan_retry_wait_seconds = 0  # No wait between retries
scan_retry_count = 10  # Many fast attempts
```

## Graceful Shutdown Enhancement ✅ COMPLETED

### Problem Addressed
The initial implementation had different shutdown behaviors for single-threaded vs multi-threaded execution:
- **Sequential mode**: Graceful exception handling  
- **Parallel mode**: Abrupt future cancellation that could interrupt running scans

### Solution Implemented
Simplified graceful shutdown mechanism using existing timeout parameter:

#### No New Configuration Needed
The existing `malware_scan_timeout_seconds` parameter naturally bounds execution time, eliminating the need for an additional graceful shutdown timeout.

#### Graceful Shutdown Behavior
1. **When timeout limit reached**: Stop accepting new scan tasks
2. **Wait for running scans**: Allow currently running scans to complete (bounded by existing timeout)
3. **Cancel unstarted tasks**: Only cancel futures that haven't started execution yet
4. **Logging**: Clear visibility into shutdown process and completion

#### Key Benefits
- **Thread safety**: No abrupt interruption of running scans
- **Data consistency**: Running scans complete their cleanup properly  
- **Simple configuration**: Uses existing timeout parameter (no new config needed)
- **Visibility**: Clear logging of shutdown progress

#### Example Behavior
```
[ERROR] Reached maximum timeout count (3), shutting down processing
[INFO] Waiting for 5 running scans to complete (max 300s per scan)...
[INFO] Graceful shutdown: 5 running scans completed
[INFO] Cancelled 12 unstarted scan tasks
```

### Simplified Configuration

All timeout behavior is controlled by existing parameters:

#### Production
```ini
scan_timeout_seconds = 300       # 5 minutes per scan (bounds shutdown time)
scan_retry_count = 3             # Shutdown after 3 timeouts
```

#### Testing  
```ini
scan_timeout_seconds = 30        # 30 seconds per scan (faster shutdown)
scan_retry_count = 2             # Shutdown after 2 timeouts
```

---

*Generated: 2025-01-08*  
*Updated: 2025-01-08 - Added graceful shutdown enhancement*  
*Purpose: Guide implementation of malware scanner timeout handling*  
*Critical: Ensures data consistency and thread safety during timeout scenarios*