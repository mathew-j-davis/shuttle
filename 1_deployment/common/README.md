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
