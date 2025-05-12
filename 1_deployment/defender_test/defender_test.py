#!/usr/bin/env python3
"""
Defender Output Test Script

This script tests Microsoft Defender's output format to ensure that the pattern
matching logic in the scanning module remains valid. It uses the EICAR test file
(a non-harmful file that all antivirus software should detect as malicious)
and a plain text file to verify both positive and negative detection scenarios.

This script should be run daily via a scheduled task to detect any changes in
Microsoft Defender's output format that might break the virus scanning functionality.

When provided with a ledger file path, it will record successfully tested versions
to maintain a history of compatible Microsoft Defender versions.
"""

import os
import sys
import subprocess
import logging
import datetime
import tempfile
import argparse
from pathlib import Path

# Import defender and ledger related modules
from defender_utils import get_mdatp_version
from read_write_ledger import ReadWriteLedger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("defender_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("defender_test")

# Expected scan output patterns - must match those in scanning.py
THREAT_FOUND_PATTERN = "Threat(s) found"
NO_THREATS_PATTERN = "0 threat(s) detected"

# EICAR test string (standard test file for antivirus)
# This is the official EICAR test string that all antivirus programs should detect
EICAR_STRING = r'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

def create_test_files():
    """Create a clean test file and an EICAR test file."""
    temp_dir = tempfile.mkdtemp(prefix="defender_test_")
    logger.info(f"Created temporary directory: {temp_dir}")
    
    # Create a clean text file
    clean_file_path = os.path.join(temp_dir, "clean_test.txt")
    with open(clean_file_path, 'w') as f:
        f.write("This is a clean test file.\n")
    logger.info(f"Created clean test file at {clean_file_path}")
    
    # Create an EICAR test file (should be detected as malicious)
    eicar_file_path = os.path.join(temp_dir, "eicar_test.txt")
    with open(eicar_file_path, 'w') as f:
        f.write(EICAR_STRING)
    logger.info(f"Created EICAR test file at {eicar_file_path}")
    
    return temp_dir, clean_file_path, eicar_file_path

def run_defender_scan(file_path):
    """Run Microsoft Defender scan on a file and return the output."""
    cmd = ["mdatp", "scan", "custom", "--ignore-exclusions", "--path", file_path]
    logger.info(f"Running scan: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        logger.info(f"Scan return code: {result.returncode}")
        logger.debug(f"Scan stdout: {result.stdout}")
        logger.debug(f"Scan stderr: {result.stderr}")
        
        return result.returncode, result.stdout
    except Exception as e:
        logger.error(f"Error running scan: {e}")
        return -1, str(e)

def verify_output_patterns(returncode, output, expected_pattern, file_type):
    """Verify that the output contains the expected pattern."""
    if expected_pattern in output:
        logger.info(f"✅ Expected pattern found in {file_type} file scan output")
        return True
    else:
        logger.error(f"❌ Expected pattern NOT found in {file_type} file scan output")
        logger.error(f"Expected: {expected_pattern}")
        logger.error(f"Actual output: {output}")
        logger.error(f"Return code: {returncode}")
        return False

def cleanup(temp_dir):
    """Clean up temporary files."""
    try:
        # Remove temporary directory and all contained files
        import shutil
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Error cleaning up: {e}")

def send_notification(message, error=False):
    """Send a notification about test results."""
    # This could be enhanced to use email, Slack, etc.
    if error:
        logger.error(message)
    else:
        logger.info(message)
    
    # If you have a notification system, integrate it here
    # For example:
    # from shuttle.notifier import Notifier
    # notifier = Notifier(...)
    # notifier.notify(...)

def update_ledger(ledger_file_path, version, test_result, test_details, logger):
    """Update the ledger file with the test results.
    
    Args:
        ledger_file_path (str): Path to the ledger file
        version (str): Microsoft Defender version being tested
        test_result (str): 'pass' or 'fail'
        test_details (str): Details about the test result
        logger: Logger instance
    
    Returns:
        bool: True if ledger was successfully updated, False otherwise
    """
    try:
        logger.info(f"Updating ledger for version {version} with result {test_result}")
        
        # Initialize the ledger
        ledger = ReadWriteLedger(logger)
        
        # Load existing ledger or create new one
        if not ledger.load(ledger_file_path):
            logger.info(f"Ledger file not found at {ledger_file_path}, will create new one")
            ledger.data = {}
        
        # Add test results to ledger
        if ledger.add_tested_version(ledger_file_path, version, test_result, test_details):
            logger.info(f"Successfully updated ledger at {ledger_file_path}")
            return True
        else:
            logger.error(f"Failed to update ledger at {ledger_file_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating ledger: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description='Test Microsoft Defender scan output patterns')
    parser.add_argument('--notify', action='store_true', help='Send notifications on results')
    parser.add_argument('--log-dir', type=str, default=None, help='Directory to store logs')
    parser.add_argument('--ledger-file', type=str, help='Path to the ledger file to update when tests pass')
    args = parser.parse_args()
    
    # Set up logging to file if log directory specified
    if args.log_dir:
        log_dir = Path(args.log_dir)
        log_dir.mkdir(exist_ok=True, parents=True)
        log_file = log_dir / f"defender_test_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    logger.info("=== Starting Microsoft Defender Output Test ===")
    
    # Get the current Microsoft Defender version
    current_version = None
    if args.ledger_file:
        logger.info("Getting Microsoft Defender version...")
        current_version = get_mdatp_version(logger)
        if not current_version:
            logger.error("Failed to get Microsoft Defender version, will continue testing but won't update ledger")
        else:
            logger.info(f"Testing Microsoft Defender version: {current_version}")
    
    temp_dir = None
    try:
        # Create test files
        temp_dir, clean_file_path, eicar_file_path = create_test_files()
        
        # Test clean file
        returncode, output = run_defender_scan(clean_file_path)
        clean_result = verify_output_patterns(returncode, output, NO_THREATS_PATTERN, "clean")
        
        # Test EICAR file
        returncode, output = run_defender_scan(eicar_file_path)
        eicar_result = verify_output_patterns(returncode, output, THREAT_FOUND_PATTERN, "EICAR")
        
        # Determine overall test result
        if clean_result and eicar_result:
            message = "✅ Defender test PASSED: Output patterns match expected formats"
            send_notification(message, error=False)
            logger.info("Test completed successfully")
            result = 0
            
            # Update ledger if version is available and ledger file is specified
            if args.ledger_file and current_version:
                test_details = "All detection tests passed successfully"
                update_ledger(args.ledger_file, current_version, "pass", test_details, logger)
        else:
            message = "❌ Defender test FAILED: Output patterns do not match expected formats"
            send_notification(message, error=True)
            logger.error("Test failed")
            result = 1
            
            # Optionally record failed tests in ledger too
            if args.ledger_file and current_version:
                test_details = "One or more detection tests failed"
                update_ledger(args.ledger_file, current_version, "fail", test_details, logger)
    
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        if args.notify:
            send_notification(f"❌ Defender test ERROR: {e}", error=True)
        result = 2
    
    finally:
        # Clean up
        if temp_dir:
            cleanup(temp_dir)
        
        logger.info("=== Defender Output Test Complete ===")
        
    return result

if __name__ == "__main__":
    sys.exit(main())
