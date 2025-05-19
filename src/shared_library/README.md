# Shuttle Common Package

This package contains shared code that is used by both the `shuttle` and `defender_test` modules.

## Installation

For development:
```bash
# From the shared_library directory
pip install -e .
```

For production:
```bash
# From the shared_library directory
pip install .
```

## Purpose

By centralizing these shared components, we achieve:
1. Code reuse between different applications
2. Easier maintenance (changes in one place update all uses)
3. Consistent behavior across applications
4. Support for different permission models and users

## Components

The package includes:
- Scanning utilities (scan_utils.py)
- File handling utilities (files.py)
- Ledger system (ledger.py)
- Notification system (notifier.py)
- Logging setup (logging_setup.py)
- Configuration utilities (config.py)

## Usage

```python
# Import specific components
from shuttle_common import Ledger, Notifier, setup_logging
from shuttle_common.files import some_function

# Or use the package version
from shuttle_common import __version__
print(f"Using shuttle_common version {__version__}")
```
