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

# Import modules from shuttle_common package using absolute imports
from shuttle_common.scan_utils import (
    get_mdatp_version,
    scan_for_malware_using_defender,
    parse_defender_scan_result,
    defender_scan_patterns,
    run_malware_scan,
    scan_result_types,
    process_defender_result,
    DefenderScanResult
)
from shuttle_common.logging_setup import setup_logging, LoggingOptions
from shuttle_common.config import CommonConfig, add_common_arguments, parse_common_config
from shuttle_common.notifier import Notifier
from shuttle_common.logger_injection import with_logger
from .read_write_ledger import ReadWriteLedger

# EICAR test string (standard test file for antivirus)
# This is the official EICAR test string that all antivirus programs should detect
EICAR_STRING = r'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

@with_logger
def create_test_files(logging_options=None, logger=None):
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




@with_logger
def run_defender_scan(file_path, logging_options=None, logger=None):
    """
    Run Microsoft Defender scan on a file and return the result code.
    The result code will be one of the scan_result_types values.
    
    Args:
        file_path (str): Path to the file to scan
        logging_options (LoggingOptions): Logging configuration
        
    Returns:
        int: A scan_result_types value indicating the scan result
    """
    logger.info(f"Scanning file: {file_path} using Microsoft Defender")

    try:
        return scan_for_malware_using_defender(file_path, logging_options=logging_options)
    except Exception as e:
        logger.error(f"Error running scan: {e}")
        return scan_result_types.FILE_SCAN_FAILED



@with_logger
def cleanup(temp_dir, logging_options=None, logger=None):
    """Clean up temporary files."""
    try:
        # Remove temporary directory and all contained files
        import shutil
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Error cleaning up: {e}")

@with_logger
def send_notification(message, error=False, config=None, logging_options=None, logger=None):
    """Send a notification about test results.
    
    Args:
        message (str): The message to send
        error (bool): Whether this is an error message
        config (CommonConfig): Configuration containing notification settings
        logging_options (LoggingOptions): Logging configuration options
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
                recipient_email=config.notify_recipient_email,
                sender_email=config.notify_sender_email,
                smtp_server=config.notify_smtp_server,
                smtp_port=config.notify_smtp_port,
                username=config.notify_username,
                password=config.notify_password,
                use_tls=config.notify_use_tls,
                logging_options=logging_options
            )
            subject = "Defender Test " + ("ERROR" if error else "INFO")
            notifier.notify(subject, message)
            logger.info(f"Notification sent to {config.notify_recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)

@with_logger
def update_ledger(ledger_file_path, version, test_result, test_details, logging_options=None, logger=None):
    """Update the ledger file with the test results.
    
    Args:
        ledger_file_path (str): Path to the ledger file
        version (str): Microsoft Defender version being tested
        test_result (str): 'pass' or 'fail'
        test_details (str): Details about the test result
        logging_options (LoggingOptions): Logging configuration options
    
    Returns:
        bool: True if ledger was successfully updated, False otherwise
    """
    try:
        # Expand ~ to user's home directory if present
        if ledger_file_path and ledger_file_path.startswith('~'):
            ledger_file_path = os.path.expanduser(ledger_file_path)
            
        logger.info(f"Updating ledger for version {version} with result {test_result}")
        
        # Initialize the ledger
        ledger = ReadWriteLedger(logging_options=logging_options)
        
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

@with_logger
def main(logger=None):
    # Create argument parser
    parser = argparse.ArgumentParser(description='Test Microsoft Defender scan output patterns')
    
    # Add common arguments from the shared config module
    add_common_arguments(parser)
    
    # Add any defender_test specific arguments here if needed in the future
    
    # Parse arguments and configuration
    args = parser.parse_args()
    config, _ = parse_common_config(args)
    
    # Set up logging with the log path from config
    log_file_path = None
    if config.log_path:
        log_dir = Path(config.log_path)
        log_dir.mkdir(exist_ok=True, parents=True)
        log_file_path = log_dir / f"defender_test_{datetime.datetime.now().strftime('%Y%m%d')}.log"

    logging_options = LoggingOptions(filePath=log_file_path, level=logging.INFO)
    
    # Configure hierarchy logging
    from shuttle_common.logger_injection import configure_logging
    configure_logging({
        'log_file_path': log_file_path,
        'log_level': logging.INFO
    })
    
    logger = setup_logging('defender_test', logging_options)

    logger.info("=== Starting Microsoft Defender Output Test ===")
    
    # Get the current Microsoft Defender version

    logger.info("Getting Microsoft Defender version...")
    current_version = get_mdatp_version(logging_options=logging_options)

    if not current_version:
        msg = "Failed to detect Microsoft Defender version"
        send_notification(msg, error=True, config=config)
        return 1

    logger.info(f"Testing Microsoft Defender version: {current_version}")
    
    if not config.ledger_path:    
        logger.info("No ledger file specified, will continue testing but won't update ledger")
    
    temp_dir = None
    try:
        # Create test files
        temp_dir, clean_file_path, eicar_file_path = create_test_files(logging_options)
        
        # Test clean file
        defender_result = scan_for_malware_using_defender(
            path=clean_file_path, 
            logging_options=logging_options
        )
        clean_scan = process_defender_result(
            defender_result, 
            clean_file_path, 
            config.defender_handles_suspect_files,
            logging_options
        )
        
        # Check scan result against expected outcome
        clean_result = clean_scan.scan_completed and not clean_scan.suspect_detected
        if not clean_result:
            logger.error(f"Clean test failed: expected scan_completed=True, suspect_detected=False, got scan_completed={clean_scan.scan_completed}, suspect_detected={clean_scan.suspect_detected}")
        else:
            logger.info("Clean test passed: No threats detected")
        
        # Test EICAR file
        defender_result = scan_for_malware_using_defender(
            path=eicar_file_path, 
            logging_options=logging_options
        )
        eicar_scan = process_defender_result(
            defender_result, 
            eicar_file_path, 
            config.defender_handles_suspect_files,
            logging_options
        )
        
        # For EICAR, we expect to detect a threat
        eicar_result = eicar_scan.suspect_detected
        if not eicar_result and eicar_scan.scan_completed:
            logger.error(f"EICAR test failed: expected suspect_detected=True, got suspect_detected={eicar_scan.suspect_detected}")
        else:
            logger.info("EICAR test passed: Threat detected")
        
        # Determine overall test result
        if clean_result and eicar_result:
            message = f"✅ Defender {current_version} correctly identified clean file and threat"
            
            test_details = (
                    f"Microsoft Defender {current_version}\n"
                    f"Clean test: {'PASS' if clean_result else 'FAIL'}\n"
                    f"  scan_completed={clean_scan.scan_completed}, "
                    f"suspect_detected={clean_scan.suspect_detected}\n"
                    f"EICAR test: {'PASS' if eicar_result else 'FAIL'}\n"
                    f"  scan_completed={eicar_scan.scan_completed}, "
                    f"suspect_detected={eicar_scan.suspect_detected}\n"
                    f"defender_handles_suspect_files={config.defender_handles_suspect_files}\n"
                )
            # Send notification if there's an error or if notify_summary is enabled
            if config.notify and config.notify_summary:
                send_notification(
                    f"{message}\n{test_details}", 
                    error=False, 
                    config=config, 
                    logging_options=logging_options
                )
                
            logger.info("Test completed successfully")
            result = 0
            
            # Update ledger if provided
            if config.ledger_path:


                #test_details = "tests passed"
                ledger_updated = update_ledger(config.ledger_path, current_version, "pass", test_details, logging_options)
                result_text = "successfully" if ledger_updated else "failed to"
                logger.info(f"Ledger {result_text} updated with test results")
        else:
            message = f"❌ Defender {current_version} failed scanning tests"
            
            # Always send notification for failures if notification is enabled
            if config.notify:
                test_details = (
                    f"Microsoft Defender {current_version}\n"
                    f"Clean test: {'PASS' if clean_result else 'FAIL'}\n"
                    f"  scan_completed={clean_scan.scan_completed}, "
                    f"suspect_detected={clean_scan.suspect_detected}\n"
                    f"EICAR test: {'PASS' if eicar_result else 'FAIL'}\n"
                    f"  scan_completed={eicar_scan.scan_completed}, "
                    f"suspect_detected={eicar_scan.suspect_detected}\n"
                    f"defender_handles_suspect_files={config.defender_handles_suspect_files}\n"
                )
                send_notification(
                    f"❌ Defender {current_version} failed scanning tests:\n{test_details}",
                    error=True,
                    config=config,
                    logging_options=logging_options
                )
                
            logger.error("Test failed")
            result = 1
            
            # Optionally record failed tests in ledger too
            if config.ledger_path and current_version:
                test_details = "One or more detection tests failed"
                update_ledger(config.ledger_path, current_version, "fail", test_details, logging_options)
    
    except Exception as e:

        logger.error(f"Test error: {e}", exc_info=True)
        if config.notify:
            error_message = f"❌ Defender test ERROR: {e}"
            # Add timestamp for daily runs
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_message = f"{timestamp}: {error_message}"
            send_notification(error_message, error=True, config=config, logging_options=logging_options)
        result = 2
    
    finally:
        # Clean up
        if temp_dir:
            cleanup(temp_dir, logging_options)
        
        # Generate summary message for logging
        summary = "=== Defender Output Test Complete ==="
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        summary = f"{summary} (Daily Test: {timestamp})"
        logger.info(summary)
        
    return result

