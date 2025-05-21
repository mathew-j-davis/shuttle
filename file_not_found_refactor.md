# Moving File Not Found Handling to Common Module

## ScanResult Class in scan_utils.py

```python
class ScanResult:
    def __init__(self, scan_completed=False, suspect_detected=False, handler_managing=False):
        self.scan_completed = scan_completed
        self.suspect_detected = suspect_detected  # was a threat found?
        self.handler_managing = handler_managing  # is defender handling it?
```

## process_defender_result Helper

```python
def process_defender_result(result_code, path, defender_handles_suspect=False, logging_options=None):
    """Process defender scan result and determine actions"""
    logger = setup_logging('shuttle.common.scan_utils.process_defender_result', logging_options)
    
    # Threat detection
    if result_code == scan_result_types.FILE_IS_SUSPECT:
        msg = "letting Defender handle it" if defender_handles_suspect else "handling internally"

        logger.warning(f"Threats found in {path}, {msg}")
        return ScanResult(True, True, defender_handles_suspect)
        
    # File not found
    elif result_code == scan_result_types.FILE_NOT_FOUND:
        if defender_handles_suspect:
            logger.warning(f"File not found at {path}, assuming Defender quarantined it")
            return ScanResult(True, True, True)  # treat as suspect + handled
        else:
            logger.warning(f"File not found at {path}")
            return ScanResult(False, False, False)  # error condition
            
    # Clean case
    elif result_code == scan_result_types.FILE_IS_CLEAN:
        logger.info(f"No threats found in {path}")
        return ScanResult(True, False, False)
        
    # Other errors
    else:
        logger.warning(f"Scan failed for {path} with code {result_code}")
        return ScanResult(False, False, False)
```

## Update scanning.py

```python
# In scan_and_process_file function
defender_result = scan_for_malware_using_defender(path, logging_options)
result = process_defender_result(defender_result, path, defender_handles_suspect_files)

# Update status flags
suspect_file_detected = result.suspect_detected
scanner_handling_suspect_file = result.handler_managing

# Return early if file not found and not handled by defender
if not result.scan_completed and not result.suspect_detected:
    return False
```

## Update defender test app

```python
defender_result = scan_for_malware_using_defender(file_path, logging_options)
result = process_defender_result(defender_result, file_path, defender_handles_suspect_files)

if not result.scan_completed and not result.suspect_detected:
    logger.error(f"Test file not found: {file_path}")
    # Handle error appropriately
elif result.scan_completed and not result.suspect_detected:
    passed = True
```

## Benefits
- Single implementation for handling file not found cases
- Same logic works for both the shuttle app and test app
- Clear handling when Defender removes files before we scan them
