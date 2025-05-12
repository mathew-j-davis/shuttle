# Microsoft Defender Test and Ledger Integration Design

## Overview

This document outlines the design for integrating the Microsoft Defender testing process with a ledger system to record successfully tested versions. The goal is to ensure that the Shuttle application only runs with verified versions of Microsoft Defender, reducing the risk of false negatives in malware detection.

## Components

1. **defender_test.py** - Tests Microsoft Defender using EICAR files
2. **read_write_ledger.py** - Reads and writes to the ledger file
3. **ledger.yaml** - Stores information about tested versions
4. **defender_utils.py** - Contains utility functions for working with Microsoft Defender

## Implementation Plan

### 1. Add Ledger Integration to defender_test.py

Update defender_test.py to accept a ledger file path and update the ledger when tests pass:

~~~python
import argparse
import os
import sys
import logging
from datetime import datetime
from read_write_ledger import ReadWriteLedger
from defender_utils import get_mdatp_version

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Test Microsoft Defender and update ledger')
    parser.add_argument('--ledger-file', help='Path to the ledger file to update when tests pass')
    parser.add_argument('--log-dir', help='Directory to write logs to')
    parser.add_argument('--notify', action='store_true', help='Send notifications on test results')
    args = parser.parse_args()
    
    # Configure logging
    # [existing logging setup code]
    
    # Get current Microsoft Defender version
    logger.info("Getting Microsoft Defender version...")
    current_version = get_mdatp_version(logger)
    
    if not current_version:
        logger.error("Failed to get Microsoft Defender version. Cannot proceed with test.")
        return 1
    
    logger.info(f"Testing Microsoft Defender version: {current_version}")
    
    # Run defender tests
    test_result = run_defender_tests()
    
    # If tests passed and ledger file is specified, update the ledger
    if test_result == 0 and args.ledger_file:
        logger.info(f"Tests passed. Updating ledger file: {args.ledger_file}")
        update_ledger(args.ledger_file, current_version, logger)
    
    return test_result

def run_defender_tests():
    # [existing test code]
    pass

def update_ledger(ledger_file_path, version, logger):
    try:
        # Create ledger instance
        ledger = ReadWriteLedger(ledger_file_path, logger)
        
        # Load existing data (if any)
        ledger.load()
        
        # Check if version already exists
        if ledger.is_version_tested(version):
            logger.info(f"Version {version} already in ledger. No update needed.")
            return True
        
        # Add version to ledger
        test_time = datetime.now().isoformat()
        test_details = "All detection tests passed successfully"
        ledger.add_tested_version(version, "pass", test_details)
        
        # Save ledger
        ledger.save()
        logger.info(f"Successfully added version {version} to ledger")
        return True
        
    except Exception as e:
        logger.error(f"Error updating ledger: {e}")
        return False

if __name__ == "__main__":
    sys.exit(main())
~~~

### 2. Command Line Changes

The defender_test.py script will now accept a new optional argument:

~~~
--ledger-file PATH  Path to the ledger file to update when tests pass
~~~

### 3. Test Flow

1. Get current Microsoft Defender version using defender_utils.get_mdatp_version()
2. Run EICAR and clean file tests
3. If tests pass:
   a. Check if ledger file path was provided
   b. If yes, try to update the ledger:
      i. Load existing ledger data
      ii. Check if version already exists in ledger
      iii. If not, add version with timestamp and result
      iv. Save updated ledger
4. Return appropriate exit code

### 4. Ledger Structure

The ledger will follow this YAML structure:

~~~yaml
defender:
  tested_versions:
    - version: "101.12345.123"
      test_time: "2025-05-09T10:30:00"
      test_result: "pass"
      test_details: "All detection tests passed"
    - version: "101.12345.456"
      test_time: "2025-05-01T14:22:00"
      test_result: "pass" 
      test_details: "All detection tests passed"
~~~

## Security and Error Handling

1. The defender_test.py will not fail if ledger updates fail - it will log the error and continue
2. Only versions that pass all tests will be added to the ledger
3. The test user must have write access to the ledger file
4. The Shuttle application user only needs read access to the ledger file

## Further Enhancements

1. Add expiration dates for tested versions
2. Implement a notification system for when defender versions change
3. Add support for testing specific defender versions (for retrospective verification)