# Shuttle Bug Analysis and Fix Proposals

## Bug 1: Throttling Disk Space Check

### Current Behavior
The throttler doesn't correctly check available disk space, likely because it's checking the specific directory path rather than the underlying mount point (partition).

### Issue Analysis
In `throttler.py`, the code currently uses:

```python
stats = shutil.disk_usage(directory_path)
```

This checks the space of the filesystem containing the directory, but there are two problems:
1. If the directory doesn't exist yet, it creates it first but then checks space of an empty dir
2. It doesn't identify the actual mount point, so it might be checking a subdirectory's apparent space rather than the root partition

### Proposed Solution
Add a function to find the mount point of a path, then check disk space on that mount point:

```python
def get_mount_point(path):
    """Get the mount point of a path."""
    path = os.path.abspath(path)
    while path != os.path.sep:
        if os.path.ismount(path):
            return path
        path = os.path.dirname(path)
    return path  # Return root if no other mount point found
```

Then modify the `check_directory_space` method:

```python
@staticmethod
def check_directory_space(directory_path, file_size_mb, min_free_space_mb, logging_options=None):
    logger = setup_logging('shuttle.throttler.check_directory_space', logging_options)
    
    try:
        # Ensure directory exists
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
        
        # Get the mount point to check actual partition space
        mount_point = Throttler.get_mount_point(directory_path)
        logger.debug(f"Checking disk space at mount point: {mount_point} for directory: {directory_path}")
        
        # Check disk usage on the mount point
        stats = shutil.disk_usage(mount_point)
        free_mb = stats.free / (1024 * 1024)  # Convert bytes to MB
        
        has_space = (free_mb - file_size_mb) >= min_free_space_mb
        
        if not has_space:
            logger.error(f"Partition containing {directory_path} is low on space. Mount point: {mount_point}, Free: {free_mb:.2f} MB, Required: {min_free_space_mb + file_size_mb:.2f} MB")
        else:
            logger.debug(f"Sufficient space on partition containing {directory_path}. Mount point: {mount_point}, Free: {free_mb:.2f} MB, Need: {min_free_space_mb + file_size_mb:.2f} MB")
        
        return has_space
        
    except Exception as e:
        if logger:
            logger.error(f"Error checking space for directory {directory_path}: {e}")
        return False
```

## Bug 2: Multithreading Not Working

### Current Behavior
Multithreading for file scanning isn't functioning correctly, even when `max_scan_threads` is set greater than 1.

### Issue Analysis
The scanning module is using `ProcessPoolExecutor` from `concurrent.futures`, but may have issues with:

1. Properly submitting tasks to the executor
2. Handling shared state between processes
3. Potential deadlocks or race conditions
4. Pickling issues with the functions or arguments

Looking at the code in `scanning.py`:
```python
if max_scan_threads > 1:
    # Using multiprocessing for scanning
    with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
        # ... possibly not properly submitting tasks or collecting results
```

### Proposed Solution
Revise the multithreading implementation with a clearer task submission pattern:

```python
if max_scan_threads > 1:
    logger.info(f"Scanning using process pool with {max_scan_threads} workers")
    
    # Prepare list of scan tasks
    scan_tasks = []
    for source_file in files_to_scan:
        # Add task details to list
        scan_tasks.append((source_file, dest_file_path, ...))
    
    # Process files in parallel
    results = []
    with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
        # Map our scan function to all tasks and collect futures
        futures = {executor.submit(scan_single_file, *task): task[0] for task in scan_tasks}
        
        # Process results as they complete
        for future in as_completed(futures):
            src_file = futures[future]
            try:
                result = future.result()
                results.append((src_file, result))
                logger.info(f"Completed scan of {src_file}")
            except Exception as exc:
                logger.error(f"Scan of {src_file} generated an exception: {exc}")
                results.append((src_file, None))
```

This implementation:
1. Clearly defines each task before starting the executor
2. Uses `submit()` and `as_completed()` for better control
3. Handles exceptions from each worker process
4. Provides better logging for debugging

We'll also need to refactor the scanning logic to create a standalone function `scan_single_file` that can be pickled and sent to worker processes.

## Implementation Plan

1. **Throttling Fix**:
   - Add `get_mount_point` function to Throttler class
   - Update `check_directory_space` to use the mount point
   - Add detailed logging for debugging
   - Write tests to validate the fix

2. **Multithreading Fix**:
   - Refactor scanning logic to have a pure function for individual file scanning
   - Reimplement the parallel scanning using proper task submission
   - Add detailed logging to track parallel execution
   - Add a test case that verifies parallel scanning works

Both fixes should be implemented with care to maintain backward compatibility and ensure proper error handling.
