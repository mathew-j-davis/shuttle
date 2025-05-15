# Common Module

This module contains shared code that is used by both the `shuttle` and `defender_test` modules.

## Purpose

By centralizing these shared components, we achieve:
1. Code reuse between different applications
2. Easier maintenance (changes in one place update all uses)
3. Consistent behavior across applications
4. Support for different permission models and users

## Components

### defender_utils.py
Utility functions for working with Microsoft Defender, particularly for version detection.

### ledger.py
Base class for working with the Defender version ledger file, which tracks tested versions.

### notifier.py
Email notification system for alerting administrators about important events or errors.

### logging_setup.py
Common logging configuration used across applications.

## Usage

To use these components in either the shuttle module or defender_test module:

```python
# Import specific components
from common.defender_utils import get_mdatp_version
from common.ledger import Ledger
from common.notifier import Notifier
from common.logging_setup import setup_logging

# Or import everything 
from common import *
```


## Common Module Components

### Classes
- **CommonConfig** - Shared configuration settings
- **Notifier** - Email notification system
  - `__init__()` - Initialize with email settings
  - `notify(title, message)` - Send notification
- **Ledger** - Tracks tested defender versions
  - `__init__(logger)` - Initialize ledger
  - `load(ledger_file_path)` - Load ledger data
  - `is_version_tested(version)` - Check if version is tested

### Functions
- **setup_logging(log_file, log_level, logger_name)** - Configure logging
- **add_common_arguments(parser)** - Add shared CLI arguments
- **parse_common_config(args, settings_file_path)** - Parse common settings
- **get_mdatp_version()** - Get Microsoft Defender version
- **run_malware_scan(cmd, path, result_handler)** - Run malware scan
- **scan_for_malware_using_defender(path)** - Scan using Defender

### Constants
- **scan_result_types** - Scan result type constants
  - `FILE_IS_SUSPECT`
  - `FILE_IS_CLEAN`
  - `FILE_SCAN_FAILED`