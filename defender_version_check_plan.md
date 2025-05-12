# Microsoft Defender Version Check Implementation Plan

## Overview

This document outlines the implementation for checking if the current Microsoft Defender version has been successfully tested according to the status.yaml file.

## Components

### 1. Add Status File Handling to defender_utils.py

First, we'll add functions to `defender_utils.py` to read and check versions in the status file:

```python
import yaml
import logging
from typing import Optional, List, Dict, Any

def load_ledger_file(ledger_file_path: str, logger=None) -> Optional[Dict[str, Any]]:
    """
    Load the ledger YAML file.
    
    Args:
        ledger_file_path (str): Path to the ledger.yaml file
        logger: Optional logger instance
        
    Returns:
        dict: Loaded YAML data or None if file couldn't be loaded
    """
    if logger is None:
        logger = logging.getLogger('shuttle')
        
    try:
        with open(ledger_file_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.error(f"Ledger file not found at: {ledger_file_path}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing ledger file: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading ledger file: {e}")
        return None

def is_version_tested(ledger_data: Dict[str, Any], version: str, logger=None) -> bool:
    """
    Check if the specified version has been successfully tested.
    
    Args:
        ledger_data (dict): Ledger data loaded from YAML file
        version (str): Version string to check
        logger: Optional logger instance
        
    Returns:
        bool: True if version has been tested successfully, False otherwise
    """
    if logger is None:
        logger = logging.getLogger('shuttle')
        
    try:
        if 'defender' not in ledger_data:
            logger.error("No 'defender' section in ledger file")
            return False
            
        if 'tested_versions' not in ledger_data['defender']:
            logger.error("No 'tested_versions' list in ledger file")
            return False
            
        tested_versions = ledger_data['defender']['tested_versions']
        
        # Check if version exists in the tested_versions list
        for tested_version in tested_versions:
            if (isinstance(tested_version, dict) and 
                'version' in tested_version and 
                tested_version['version'] == version and
                'test_result' in tested_version and
                tested_version['test_result'] == 'pass'):
                    
                logger.info(f"Found matching tested version: {version}")
                return True
                
        logger.warning(f"Version {version} not found in tested versions or did not pass testing")
        return False
        
    except Exception as e:
        logger.error(f"Error checking tested versions: {e}")
        return False
```

### 2. Import Functions into shuttle.py

Update the imports in shuttle.py to include the new functions:

```python
from .defender_utils import get_mdatp_version, load_ledger_file, is_version_tested
```

### 3. Update Config Loading in shuttle.py

Make sure the config includes the ledger_file_path:

```python
# In parse_config function in config.py
parser.add_argument('-LedgerFilePath', help='Path to the ledger file')
```

### 4. Update the Microsoft Defender Check in shuttle.py

Replace the current check with a comprehensive version check:

```python
if config.on_demand_defender:
    # Get current version of Microsoft Defender
    current_version = get_mdatp_version(logger)
    
    if not current_version:
        logger.error("Could not get Microsoft Defender version")
        sys.exit(1)
    
    logger.info(f"Current Microsoft Defender version: {current_version}")
    
    # Skip test verification if explicitly configured to do so
    if getattr(config, 'skip_defender_test', False):
        logger.warning("Skipping Microsoft Defender version test verification (not recommended)")
    else:
        # Check if ledger file path is provided
        if not config.ledger_file_path:
            logger.error("Ledger file path not provided. Cannot verify Microsoft Defender version.")
            sys.exit(1)
        
        # Load ledger file
        ledger_data = load_ledger_file(config.ledger_file_path, logger)
        if not ledger_data:
            logger.error("Failed to load ledger file. Cannot verify Microsoft Defender version.")
            sys.exit(1)
        
        # Check if current version has been tested
        if not is_version_tested(ledger_data, current_version, logger):
            logger.error(f"Microsoft Defender version {current_version} has not been tested.")
            logger.error("Please run the Defender test script for this version before using Shuttle.")
            logger.error("Or use -SkipDefenderTest option (not recommended).")
            sys.exit(1)
        
        logger.info(f"Microsoft Defender version {current_version} has been tested and passed.")
```

## Implementation Steps

1. **Add Functions to defender_utils.py**:
   - Implement `load_status_file` function
   - Implement `is_version_tested` function
   - Add unit tests for these functions

2. **Update Config System**:
   - Add `status_file_path` to ShuttleConfig class
   - Add command line option for status file path
   - Add option to skip version test (for emergencies only)

3. **Update shuttle.py**:
   - Import the new functions
   - Implement the version check logic
   - Add detailed logging for each step

4. **Error Handling**:
   - Make sure all functions handle missing files gracefully
   - Provide clear error messages when versions don't match
   - Add detailed logging to help diagnose issues

## Testing Strategy

1. **Test with Matching Version**:
   - Create a status file with the current Microsoft Defender version
   - Verify that the application runs correctly

2. **Test with Non-Matching Version**:
   - Create a status file with a different version
   - Verify that the application exits with an appropriate error

3. **Test with Missing/Invalid Status File**:
   - Remove or corrupt the status file
   - Verify that the application handles this gracefully

4. **Test Skip Option**:
   - Verify that the -SkipDefenderTest option works correctly
   - Ensure appropriate warnings are logged
