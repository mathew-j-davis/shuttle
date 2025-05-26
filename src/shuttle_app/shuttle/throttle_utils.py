"""
Throttling utilities for Shuttle.

This module contains functions to handle disk space throttling and daily throttling.
"""

import os
import yaml
from datetime import datetime
from shuttle_common.logging_setup import setup_logging
from shuttle.daily_processing_tracker import DailyProcessingTracker

def handle_throttle_check(
        source_file_path, 
        quarantine_path,
        destination_path,
        hazard_archive_path,
        throttle_free_space,
        throttler,
        max_files_per_day=0,
        max_volume_per_day=0,
        throttle_logger=None,
        notifier=None,
        logging_options=None
    ):
    """
    Check if a file can be processed based on available disk space and daily processing limits.
    
    Args:
        source_file_path: Path to the source file
        quarantine_path: Path to the quarantine directory
        destination_path: Path to the destination directory
        hazard_archive_path: Path to the hazard archive directory
        throttle_free_space: Minimum free space to maintain in MB
        throttler: Throttler instance to use for checks
        max_files_per_day: Maximum number of files to process per day (0 for no limit)
        max_volume_per_day: Maximum volume to process per day in MB (0 for no limit)
        throttle_logger: DailyProcessingTracker instance for daily limit tracking
        notifier: Notifier instance for sending notifications (optional)
        logging_options: Logging configuration options
        
    Returns:
        bool: True if processing can continue, False if it should stop
    """
    # Create a logger for this function
    logger = setup_logging('shuttle.throttle_utils.handle_throttle_check', logging_options)
    
    # Default values
    can_continue = True
    
    # Get file size for throttling calculations
    file_size_bytes = 0
    file_size_mb = 0
    try:
        file_size_bytes = os.path.getsize(source_file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)  # Convert to MB
        logger.debug(f"File size for {os.path.basename(source_file_path)}: {file_size_mb:.2f} MB")
    except Exception as e:
        logger.warning(f"Could not determine file size for {source_file_path}: {e}")
    
    try:
        # STEP 1: Check disk space in all directories
        # Check quarantine directory (no pending volume needed - files already there)
        quarantine_has_space = throttler.check_directory_space(
            quarantine_path,
            file_size_mb,
            throttle_free_space,
            logging_options,
            include_pending_volume=False
        )
        
        # Get pending volume for destination and hazard checks
        pending_volume_mb = 0
        if throttle_logger:
            pending_volume_mb = throttle_logger.pending_volume_mb
            logger.debug(f"Using pending volume of {pending_volume_mb:.2f} MB for space checks")
        
        # Check destination directory (include pending volume)
        destination_has_space = throttler.check_directory_space(
            destination_path,
            file_size_mb,
            throttle_free_space,
            logging_options,
            include_pending_volume=True,
            pending_volume_mb=pending_volume_mb
        )
        
        # Check hazard archive directory (include pending volume)
        hazard_has_space = throttler.check_directory_space(
            hazard_archive_path,
            file_size_mb,
            throttle_free_space,
            logging_options,
            include_pending_volume=True,
            pending_volume_mb=pending_volume_mb
        )
        
        # Determine if disk space check passed
        space_check_passed = quarantine_has_space and destination_has_space and hazard_has_space
        
        if not space_check_passed:
            # At least one directory didn't have enough space
            can_continue = False
            logger.warning("THROTTLE REASON: Insufficient disk space in required directories")
            
            # Log which directories failed
            if not quarantine_has_space:
                logger.warning(f"Quarantine directory does not have enough space: {quarantine_path}")
            if not destination_has_space:
                logger.warning(f"Destination directory does not have enough space: {destination_path}")
            if not hazard_has_space:
                logger.warning(f"Hazard archive directory does not have enough space: {hazard_archive_path}")
            
            # Send notification if available
            if notifier:
                disk_message = "Insufficient disk space: \n"
                if not quarantine_has_space:
                    disk_message += f"- Quarantine directory is full\n"
                if not destination_has_space:
                    disk_message += f"- Destination directory is full\n"
                if not hazard_has_space:
                    disk_message += f"- Hazard archive directory is full\n"
                
                notifier.notify("Shuttle Disk Space Alert", disk_message)
            
            return False  # Stop processing due to disk space issues
        
        # STEP 2: Check daily limits if applicable
        if throttle_logger and (max_files_per_day > 0 or max_volume_per_day > 0):
            # Check if this file would exceed daily limits
            can_proceed, limit_message = throttle_logger.check_limits(
                file_count_limit=max_files_per_day,
                volume_limit_mb=max_volume_per_day,
                file_size_mb=file_size_mb
            )
            
            if not can_proceed:
                # Daily limit would be exceeded
                can_continue = False
                logger.warning(f"THROTTLE REASON: Daily limit exceeded - {limit_message}")
                
                # Send notification if available
                if notifier:
                    notifier.notify(
                        "Shuttle Daily Limit Reached", 
                        f"Processing stopped: {limit_message}\n\n"
                        f"File: {os.path.basename(source_file_path)}\n"
                        f"Daily limits: {max_files_per_day or 'unlimited'} files, {max_volume_per_day or 'unlimited'} MB"
                    )
                
                # Log the rejected file
                throttle_logger.log_rejected_file(source_file_path, limit_message)
                return False  # Stop processing due to daily limits
            else:
                # File is approved - add to pending files
                throttle_logger.add_pending_file(file_size_mb)
                logger.debug(f"File approved and added to pending: {source_file_path} ({file_size_mb:.2f} MB)")
        
        # All checks passed
        logger.debug("All throttle checks passed")
        return True
        
    except Exception as e:
        logger.error(f"Error in throttling checks: {e}")
        
        # Send error notification if notifier provided
        if notifier:
            error_message = f"Critical error during throttle check: {str(e)}"
            notifier.notify("Shuttle Throttle Error", error_message)
        
        return False  # Stop processing due to error
    
    return can_continue  # This line will never be reached due to explicit returns above


# ThrottleLogger has been completely replaced by DailyProcessingTracker
# Please use DailyProcessingTracker directly from the daily_processing_tracker module
