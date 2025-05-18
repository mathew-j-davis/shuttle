# Common Module

This module contains shared code that is used by both the `shuttle` and `defender_test` modules.

## Purpose

By centralizing these shared components, we achieve:
1. Code reuse between different applications
2. Easier maintenance (changes in one place update all uses)
3. Consistent behavior across applications
4. Support for different permission models and users

## Components

### scan_utils.py
Utility functions for working with Microsoft Defender and ClamAV scanning, including version detection, scan execution and results handling.

### files.py
File handling utilities for secure path operations, file integrity checking, and disk operations.

### ledger.py
Base class for working with the Defender version ledger file, which tracks tested versions.

### notifier.py
Email notification system for alerting administrators about important events or errors.

### logging_setup.py
Common logging configuration used across applications with hierarchical logger naming.

### config.py
Configuration classes and utilities for parsing common settings from command line and config files.

### throttler.py
Disk space throttling to ensure sufficient free space before processing files.

## Usage

To use these components in either the shuttle module or defender_test module:

```python
# Import specific components
from common.scan_utils import get_mdatp_version, scan_for_malware_using_defender
from common.ledger import Ledger
from common.notifier import Notifier
from common.logging_setup import setup_logging, LoggingOptions
from common.files import get_file_hash, verify_file_integrity

# Or import everything 
from common import *

# Setup hierarchical logging
logging_options = LoggingOptions(filePath="path/to/log.log", level=logging.INFO)
logger = setup_logging('shuttle.component.function_name', logging_options)
```

## Common Module Components

### Classes
- **CommonConfig** - Shared configuration settings
  - Logging, throttling, notification, and ledger settings
- **LoggingOptions** - Configuration options for the logging system
  - `__init__(filePath, level)` - Initialize logging options
- **Notifier** - Email notification system
  - `__init__(recipient_email, sender_email, ..., logging_options)` - Initialize with email settings
  - `notify(title, message)` - Send notification
- **Ledger** - Tracks tested defender versions
  - `__init__(logging_options)` - Initialize ledger
  - `load(ledger_file_path)` - Load ledger data
  - `is_version_tested(version)` - Check if version is tested
- **Throttler** - Manages disk space throttling
  - `can_process_file(file_path, dirs, threshold, logging_options)` - Check if file can be processed

### Functions
- **setup_logging(name, logging_options)** - Configure hierarchical logging
- **add_common_arguments(parser)** - Add shared CLI arguments
- **parse_common_config(args, settings_file_path)** - Parse common settings
- **get_mdatp_version(logging_options)** - Get Microsoft Defender version
- **run_malware_scan(cmd, path, result_handler, logging_options)** - Run malware scan
- **scan_for_malware_using_defender(path, logging_options)** - Scan using Defender
- **get_file_hash(file_path, logging_options)** - Calculate file hash
- **verify_file_integrity(source_file_path, comparison_file_path, logging_options)** - Verify file integrity 

### Constants
- **scan_result_types** - Scan result type constants
  - `FILE_IS_SUSPECT`
  - `FILE_IS_CLEAN`
  - `FILE_SCAN_FAILED`