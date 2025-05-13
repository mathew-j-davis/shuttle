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

# Import modules from common package using relative imports
from ..common.defender_utils import (
    get_mdatp_version,
    scan_for_malware_using_defender,
    handle_defender_scan_result,
    defender_scan_patterns,
    run_malware_scan
)
from ..common.logging_setup import setup_logging
from ..common.config import CommonConfig, add_common_arguments, parse_common_config
from ..common.notifier import Notifier
from .read_write_ledger import ReadWriteLedger

# Set up logging using the common module's setup function
logger = setup_logging(logger_name="defender_test")

# Use the scan patterns from the common module
THREAT_FOUND_PATTERN = defender_scan_patterns.THREAT_FOUND
NO_THREATS_PATTERN = defender_scan_patterns.NO_THREATS

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

def test_result_handler(returncode, output):
    """
    Custom result handler for testing that returns returncode and output directly.
    This differs from the standard handlers that return a scan result type.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        
    Returns:
        tuple: (returncode, output)
    """
    logger.info(f"Scan return code: {returncode}")
    logger.debug(f"Scan stdout: {output}")
    return returncode, output


def run_defender_scan(file_path):
    """Run Microsoft Defender scan on a file and return the output."""
    logger.info(f"Running scan on file: {file_path}")
    
    try:
        # Use the scan_for_malware_using_defender with our custom test_result_handler
        # that returns (returncode, output) instead of a scan result type
        return scan_for_malware_using_defender(file_path, custom_handler=test_result_handler)
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

def send_notification(message, error=False, config=None):
    """Send a notification about test results.
    
    Args:
        message (str): The message to send
        error (bool): Whether this is an error message
        config (CommonConfig): Configuration containing notification settings
    """
    # Log the message first
    if error:
        logger.error(message)
    else:
        logger.info(message)
    
    # Send notification if configured
    if config and config.notify:
        try:
            notifier = Notifier(
                recipient=config.notify_recipient_email,
                smtp_server=config.notify_smtp_server,
                smtp_port=config.notify_smtp_port,
                username=config.notify_username,
                password=config.notify_password,
                sender=config.notify_sender_email,
                use_tls=config.notify_use_tls
            )
            subject = "Defender Test " + ("ERROR" if error else "INFO")
            notifier.notify(subject, message)
            logger.info(f"Notification sent to {config.notify_recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)

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
    # Create argument parser
    parser = argparse.ArgumentParser(description='Test Microsoft Defender scan output patterns')
    
    # Add common arguments from the shared config module
    add_common_arguments(parser)
    
    # Add any defender_test specific arguments here if needed in the future
    
    # Parse arguments and configuration
    args = parser.parse_args()
    config = parse_common_config(args)
    
    # Set up logging with the log path from config
    log_file = None
    if config.log_path:
        log_dir = Path(config.log_path)
        log_dir.mkdir(exist_ok=True, parents=True)
        log_file = log_dir / f"defender_test_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        logger = setup_logging(log_file, config.log_level, logger_name="defender_test")
        logger.info(f"Logging to file: {log_file}")
    
    logger.info("=== Starting Microsoft Defender Output Test ===")
    
    # Get the current Microsoft Defender version
    current_version = None
    if config.ledger_file:
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
            
            # Send notification if there's an error or if notify_summary is enabled
            if config.notify and config.notify_summary:
                # Add timestamp for daily runs
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                message = f"{timestamp}: {message}"
                send_notification(message, error=False, config=config)
                
            logger.info("Test completed successfully")
            result = 0
            
            # Update ledger if version is available and ledger file is specified
            if config.ledger_file and current_version:
                test_details = "All detection tests passed successfully"
                update_ledger(config.ledger_file, current_version, "pass", test_details, logger)
        else:
            message = "❌ Defender test FAILED: Output patterns do not match expected formats"
            
            # Always send notification for failures if notification is enabled
            if config.notify:
                # Add timestamp for daily runs
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                message = f"{timestamp}: {message}"
                send_notification(message, error=True, config=config)
                
            logger.error("Test failed")
            result = 1
            
            # Optionally record failed tests in ledger too
            if config.ledger_file and current_version:
                test_details = "One or more detection tests failed"
                update_ledger(config.ledger_file, current_version, "fail", test_details, logger)
    
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        if config.notify:
            error_message = f"❌ Defender test ERROR: {e}"
            # Add timestamp for daily runs
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_message = f"{timestamp}: {error_message}"
            send_notification(error_message, error=True, config=config)
        result = 2
    
    finally:
        # Clean up
        if temp_dir:
            cleanup(temp_dir)
        
        # Generate summary message for logging
        summary = "=== Defender Output Test Complete ==="
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        summary = f"{summary} (Daily Test: {timestamp})"
        logger.info(summary)
        
    return result

