# Design Journal: Implementing Disk Space Throttling in Shuttle

## Overview

This document outlines the design for implementing disk space throttling in the Shuttle file transfer and scanning utility. The goal is to ensure there's always sufficient free space available on the destination, quarantine, and hazard archive directories before transferring files.

## Requirements

1. Before moving a file from the source directory, check if there is enough space in:
   - Quarantine directory
   - Hazard archive directory
   - Destination directory

2. Ensure that after file transfers, at least 'throttle_free_space' megabytes remain available on each filesystem.

3. If there isn't enough space, stop processing files and log an appropriate error message.

## Implementation Design

### 1. New Utility Functions in files.py

Two new utility functions will be added to the files.py module:

```python
def get_free_space_mb(path):
    """
    Get the amount of free disk space in megabytes for the filesystem containing the given path.
    
    Args:
        path (str): Path to a directory on the filesystem to check
        
    Returns:
        float: Available free space in megabytes
    """
    try:
        logger = logging.getLogger('shuttle')
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created directory {path} to check free space")
            
        stats = shutil.disk_usage(path)
        free_mb = stats.free / (1024 * 1024)  # Convert bytes to MB
        logger.info(f"Free space in {path}: {free_mb:.2f} MB")
        return free_mb
    except Exception as e:
        logger.error(f"Error checking free space for {path}: {e}")
        return 0  # Return 0 on error to be safe
```

```python
def check_free_space_for_file(file_path, target_paths, min_free_space_mb):
    """
    Check if there's enough free space to copy a file to multiple target paths,
    ensuring each target path will have at least min_free_space_mb free after the copy.
    
    Args:
        file_path (str): Path to the file being copied
        target_paths (list): List of target directory paths
        min_free_space_mb (int): Minimum free space required after copy (in MB)
        
    Returns:
        bool: True if enough space is available, False otherwise
    """
    logger = logging.getLogger('shuttle')
    
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Cannot check space for non-existent file: {file_path}")
            return True  # Assume okay if file doesn't exist
            
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # Convert bytes to MB
        logger.info(f"File size of {file_path}: {file_size_mb:.2f} MB")
        
        for target_path in target_paths:
            free_space_mb = get_free_space_mb(target_path)
            space_after_copy = free_space_mb - file_size_mb
            
            if space_after_copy < min_free_space_mb:
                logger.error(f"Not enough space in {target_path}. Free: {free_space_mb:.2f} MB, " 
                           f"Required: {file_size_mb + min_free_space_mb:.2f} MB")
                return False
                
        return True
    except Exception as e:
        logger.error(f"Error checking free space for file {file_path}: {e}")
        return False  # Return False on error to be safe
```

### 2. Integration in scan_and_process_directory

The throttling functionality should be integrated in the scan_and_process_directory function in scanning.py. Here's the relevant code to be added:

```python
def scan_and_process_directory(
    source_path,
    destination_path,
    quarantine_path,
    hazard_archive_path,
    hazard_encryption_key_file_path,
    delete_source_files,
    max_scan_threads,
    on_demand_defender,
    on_demand_clam_av,
    defender_handles_suspect_files,
    notifier,
    throttle=False,
    throttle_free_space=10000
    ):
    """
    Process all files in the source directory:
    1. Copy to quarantine
    2. Scan for malware
    3. Move clean files to destination
    4. Handle suspect files according to defender_handles_suspect_files setting

    Args:
        # ... existing parameters ...
        throttle (bool): Whether to enable throttling
        throttle_free_space (int): Minimum free space required in MB
    """
    quarantine_files = []
    logger = logging.getLogger('shuttle')

    try:
        # Create quarantine directory if it doesn't exist
        os.makedirs(quarantine_path, exist_ok=True)

        # Copy files from source to quarantine directory
        for source_root, dirs, source_files in os.walk(source_path, topdown=False):
            for source_file in source_files:
                # ... existing file validation ...

                source_file_path = os.path.join(source_root, source_file)
                
                # ... existing path validation and file checks ...
                
                # Determine paths
                rel_dir = os.path.relpath(source_root, source_path)
                quarantine_file_copy_dir = os.path.join(normalize_path(os.path.join(quarantine_path, rel_dir)))
                quarantine_file_path = os.path.join(normalize_path(os.path.join(quarantine_file_copy_dir, source_file)))
                destination_file_copy_dir = os.path.join(normalize_path(os.path.join(destination_path, rel_dir)))
                destination_file_path = os.path.join(normalize_path(os.path.join(destination_file_copy_dir, source_file)))
                
                # Check disk space if throttling is enabled
                if throttle:
                    target_paths = [quarantine_path, destination_path]
                    if hazard_archive_path:
                        target_paths.append(hazard_archive_path)
                        
                    if not check_free_space_for_file(source_file_path, target_paths, throttle_free_space):
                        logger.error(f"Skipping file {source_file_path} due to insufficient disk space")
                        if notifier:
                            notifier.notify(
                                subject="Shuttle Warning: Disk Space Low",
                                body=f"File processing for {source_file_path} was skipped due to insufficient disk space. Please free up space."
                            )
                        continue
                
                # ... existing copy and processing code ...
```

### 3. Update Process Files Function

We need to update the process_files function to pass the throttle parameters:

```python
def process_files(config, notifier):
    scan_and_process_directory(
        config.source_path,
        config.destination_path,
        config.quarantine_path,
        config.hazard_archive_path,
        config.hazard_encryption_key_file_path,
        config.delete_source_files,
        config.max_scan_threads,
        config.on_demand_defender,
        config.on_demand_clam_av,
        config.defender_handles_suspect_files,
        notifier,
        throttle=config.throttle,
        throttle_free_space=config.throttle_free_space
    )
```

### 4. Update __init__.py to Expose New Functions

```python
# Import file handling functions
from .files import (
    # ... existing imports ...
    get_free_space_mb,
    check_free_space_for_file
)

# Define what gets imported with "from shuttle import *"
__all__ = [
    # ... existing exports ...
    
    # File operations
    # ... existing exports ...
    'get_free_space_mb',
    'check_free_space_for_file',
]

## Configuration Updates

The throttling configuration is already handled in the config.py file:
- `throttle`: Boolean flag to enable/disable throttling
- `throttle_free_space`: Minimum free space required in MB

## Error Handling and Notifications

When throttling prevents file processing, we should:
- Log detailed error messages about why processing was stopped
- Send a notification using the notification system if configured
- Ensure that partial processing doesn't leave the system in an inconsistent state

## Implementation Steps

1. Add the utility functions to files.py.
2. Update the scan_and_process_directory function in scanning.py to check for free space.
3. Modify the scan_and_process_file function to handle throttling errors.
4. Update __init__.py to expose the new utility functions.
5. Add comprehensive unit tests for the throttling functionality.

## Considerations

- The checks should be performed before copying files to avoid wasting resources.
- Different filesystems may report space differently, so we'll need to handle edge cases.
- Some target directories might be on the same filesystem, which we could optimize for.
- We should ensure that error messaging is clear and actionable for administrators.

## Future Enhancements

- Add more granular throttling options (per directory).
- Implement a priority system for files when space is limited.
- Provide cleanup recommendations when space is low.
- Add monitoring for trends in space usage over time.

This design ensures we can safely implement disk space throttling while maintaining the existing functionality and code structure of the Shuttle application.
