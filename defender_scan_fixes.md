# Defender Scan Issues and Fixes

## 1. Unpacking Error Issue

### Problem
The error `TypeError: cannot unpack non-iterable int object` occurs because:

```python
# In main() function
returncode, output = run_defender_scan(clean_file_path, logging_options)
```

But the actual execution path is:
1. `run_defender_scan` calls `scan_for_malware_using_defender` with `custom_handler=test_result_handler`
2. `scan_for_malware_using_defender` calls `run_malware_scan`
3. `run_malware_scan` should call `custom_handler` but something is going wrong

The function `test_result_handler` is correctly defined to return a tuple:
```python
def test_result_handler(returncode, output, logging_options=None):
    logger = setup_logging('defender_test.test_result_handler', logging_options)
    logger.info(f"Scan return code: {returncode}")
    logger.debug(f"Scan stdout: {output}")
    return returncode, output  # Returns a tuple
```

### Fix Approach
We need to verify if `run_malware_scan` is correctly calling the custom handler. The most likely issue is that it's not passing the handler result back correctly or is short-circuiting before reaching the handler.

## 2. Pattern Matching Improvements

### Problems
1. The current pattern checking could match "10 threat(s) detected" when it should only match "0 threat(s) detected"
2. No special handling for "file not found" scenario

### Fix Approach
1. Update pattern constants to include the exact format with tabs and newlines:
   ```python
   defender_scan_patterns.NO_THREATS = "\n\t0 threat(s) detected"
   defender_scan_patterns.FILE_NOT_FOUND = "\n\t0 file(s) scanned\n\t0 threat(s) detected"
   ```

2. Add handling for file not found:
   ```python
   scan_result_types.FILE_NOT_FOUND = 404

   # In handler:
   if output.rstrip().endswith(defender_scan_patterns.FILE_NOT_FOUND):
       logger.warning("File not found or could not be scanned")
       return scan_result_types.FILE_NOT_FOUND
   ```

## 3. Implementation Steps

1. First, examine the trace through `run_malware_scan` to identify where the tuple return is being lost

2. Fix the return value handling to ensure `test_result_handler` results are properly passed back

3. Update the pattern constants and handler for more precise matching

4. Test with both existing and missing files to verify all paths
