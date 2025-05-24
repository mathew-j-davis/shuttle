"""
Throttling utilities for Shuttle.

This module contains functions to handle disk space throttling.
"""

import os
from shuttle_common.logging_setup import setup_logging

def handle_throttle_check(
        source_file_path, 
        quarantine_path,
        destination_path,
        hazard_archive_path,
        throttle_free_space,
        throttler,
        notifier=None,
        logging_options=None
    ):
    """
    Check if a file can be processed based on available disk space.
    
    Args:
        source_file_path: Path to the source file
        quarantine_path: Path to the quarantine directory
        destination_path: Path to the destination directory
        hazard_archive_path: Path to the hazard archive directory
        throttle_free_space: Minimum free space to maintain in MB
        throttler: Throttler instance to use for checks
        notifier: Notifier instance for sending notifications (optional)
        logging_options: Logging configuration options
        
    Returns:
        bool: True if processing can continue, False if it should stop
    """
    # Create a logger for this function
    logger = setup_logging('shuttle.throttle_utils.handle_throttle_check', logging_options)
    
    # Default values
    assume_quarantine_has_space = True
    assume_destination_has_space = True
    assume_hazard_has_space = True
    disk_error = False
    can_continue = True
    
    try:
        # Check if we can process this file based on available space
        throttle_result = throttler.can_process_file(
            source_file_path, 
            quarantine_path,
            destination_path,
            hazard_archive_path,
            throttle_free_space,
            logging_options
        )
        
        # Extract results for each directory from the result object
        assume_quarantine_has_space = throttle_result.quarantine_has_space
        assume_destination_has_space = throttle_result.destination_has_space
        assume_hazard_has_space = throttle_result.hazard_has_space
        disk_error = throttle_result.diskError
        
        # If file can't be processed due to space constraints
        if (
            not throttle_result.canProcess or 
            not assume_quarantine_has_space or 
            not assume_destination_has_space or 
            not assume_hazard_has_space or 
            disk_error
        ):
            logger.warning("Stopping file processing due to insufficient disk space")

            if not assume_quarantine_has_space:
                logger.warning("Could not validate quarantine directory had enough space. The disk may have run out of space, or may have other issues")

            if not assume_destination_has_space:
                logger.warning("Could not validate destination directory had enough space. The disk may have run out of space, or may have other issues")

            if not assume_hazard_has_space:
                logger.warning("Could not validate hazard directory had enough space. The disk may have run out of space, or may have other issues")

            if disk_error:
                logger.warning("When attempting to check disk space, an error occurred.")
            
            # Set return value to indicate processing should stop
            can_continue = False
            
            # If notifier is provided, send notification about the disk issue
            if notifier:
                disk_message = ""
                summary_title = "Shuttle Process Stopped - Disk Issue"
                
                if not assume_quarantine_has_space:
                    disk_message += "Quarantine directory space low. "
                if not assume_destination_has_space:
                    disk_message += "Destination directory space low. "
                if not assume_hazard_has_space:
                    disk_message += "Hazard archive directory space low. "
                if disk_error:
                    disk_message += "Disk error when checking space. "
                
                logger.info(f"Sending disk space notification: {disk_message}")
                notifier.notify(summary_title, disk_message)
            
    except Exception as e:
        logger.error(f"Error in throttling checks: {e}")
        disk_error = True
        can_continue = False
        
        # Send error notification if notifier provided
        if notifier:
            error_message = f"Critical error during throttle check: {str(e)}"
            notifier.notify("Shuttle Throttle Error", error_message)
    
    return can_continue
