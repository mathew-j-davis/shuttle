"""
Throttler module for Shuttle file transfer utility.

Provides functionality to monitor and throttle file processing based on available disk space.
"""

import os
import shutil
import logging
import types
from typing import Optional
from shuttle_common.logging_setup import setup_logging
from shuttle_common.logger_injection import get_logger


class Throttler:
    """
    Class that handles disk space throttling to prevent disk space issues during file transfers.
    
    This class provides functionality to check available disk space in directories used by Shuttle:
    - Quarantine directory
    - Destination directory
    - Hazard archive directory
    
    If any directory has insufficient space (less than the configured minimum),
    it prevents file processing.
    """
    
    @staticmethod
    def get_free_space_mb(directory_path):
        """
        Get the free space in a directory in megabytes.
        
        Args:
            directory_path (str): Path to the directory to check
            
        Returns:
            float: Free space in MB, or 0 if there was an error
        """

        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path, exist_ok=True)
                
            stats = shutil.disk_usage(directory_path)
            free_mb = stats.free / (1024 * 1024)  # Convert bytes to MB
            return free_mb
        except Exception:
            return 0.0
    
    @staticmethod
    def check_directory_space(directory_path, file_size_mb, min_free_space_mb, include_pending_volume=False, pending_volume_mb=0, logging_options=None):
        """
        Check if a directory has enough free space for a file, leaving a minimum amount free after copy.
        
        Args:
            directory_path (str): Path to the directory to check
            file_size_mb (float): Size of the file in MB
            min_free_space_mb (int): Minimum free space to maintain after copy in MB
            logging_options (LoggingOptions, optional): logging configuration details
            include_pending_volume (bool): Whether to include pending volume in the calculation
            pending_volume_mb (float): Volume of pending files in MB to consider
            
        Returns:
            bool: True if directory has enough space, False otherwise
        """
        logger = get_logger(logging_options=logging_options)
        
        try:
            # Get free space in MB
            free_mb = Throttler.get_free_space_mb(directory_path)
            
            # Calculate required space, optionally including pending volume
            required_space_mb = file_size_mb + min_free_space_mb
            if include_pending_volume:
                required_space_mb += pending_volume_mb
                logger.debug(f"Including pending volume of {pending_volume_mb:.2f} MB in space check")
            
            # Check if there's enough space
            has_space = free_mb >= required_space_mb
            
            if not has_space:
                logger.error(f"Directory {directory_path} is full. Free: {free_mb:.2f} MB, Required: {required_space_mb:.2f} MB")
            
            return has_space
            
        except Exception as e:
            logger.error(f"Error checking space in directory {directory_path}: {e}")
            return False
            
    @staticmethod
    def can_process_file(source_file_path, quarantine_path, destination_path, 
                         hazard_path, min_free_space_mb, daily_totals=None, max_files_per_day=0, 
                         max_volume_per_day_mb=0, logging_options=None):
        """
        Check if a file can be processed with the given paths and return detailed status.
        
        Args:
            source_file_path (str): Path to the source file to check
            quarantine_path (str): Path to the quarantine directory
            destination_path (str): Path to the destination directory
            hazard_path (str): Path to the hazard archive directory
            min_free_space_mb (int): Minimum free space to maintain after copy in MB
            daily_totals (dict): Current daily totals with 'files_processed' and 'volume_processed_mb' keys
            max_files_per_day (int): Maximum number of files to process per day (0 for no limit)
            max_volume_per_day_mb (int): Maximum volume to process per day in MB (0 for no limit)
            logging_options (LoggingOptions, optional): logging configuration details
            
        Returns:
            SimpleNamespace: Object with the following attributes:
                - canProcess: Whether the file can be processed (bool)
                - quarantine_has_space: Whether the quarantine directory has space (bool)
                - destination_has_space: Whether the destination directory has space (bool)
                - hazard_has_space: Whether the hazard directory has space (bool)
                - diskError: Whether a disk error occurred (bool)
                - daily_limit_exceeded: Whether a daily throttling limit was exceeded (bool)
                - daily_limit_message: Description of the daily limit that was exceeded (str)
        """
        
        # Default values
        quarantine_has_space = True
        destination_has_space = True
        hazard_has_space = True
        disk_error = False
        daily_limit_exceeded = False
        daily_limit_message = ""
        
        # Get logger for this method
        logger = get_logger(logging_options=logging_options)
        
        # Check daily throttling limits if enabled
        if daily_totals and (max_files_per_day > 0 or max_volume_per_day_mb > 0):
            try:
                # Get file size in MB for checking volume limits
                file_size_bytes = os.path.getsize(source_file_path)
                file_size_mb = file_size_bytes / (1024 * 1024)  # Convert to MB
                
                logger.debug(f"Checking daily throttle limits: files={max_files_per_day}, volume={max_volume_per_day_mb}MB")
                
                # Check if already at the limit
                if max_files_per_day > 0 and daily_totals['files_processed'] >= max_files_per_day:
                    daily_limit_exceeded = True
                    daily_limit_message = f"Daily file count limit ({max_files_per_day}) exceeded with {daily_totals['files_processed']} files already processed"
                    logger.debug(daily_limit_message)
                    
                # Check if this file would exceed the volume limit
                elif max_volume_per_day_mb > 0 and daily_totals['volume_processed_mb'] + file_size_mb > max_volume_per_day_mb:
                    daily_limit_exceeded = True
                    daily_limit_message = f"Daily volume limit ({max_volume_per_day_mb} MB) would be exceeded with {daily_totals['volume_processed_mb'] + file_size_mb:.2f} MB"
                    logger.debug(daily_limit_message)
            except Exception as e:
                logger.error(f"Error checking daily limits: {e}")
                # Continue with disk space checks even if daily limit check fails
                
        try:
            # Get file size in MB
            file_size_mb = os.path.getsize(source_file_path) / (1024 * 1024)
            
            # Calculate pending volume from daily totals if available
            pending_volume_mb = 0
            if daily_totals and hasattr(daily_totals, 'get'):
                # If we have a tracker object, try to get pending volume from it
                if hasattr(daily_totals, 'pending_volume_mb'):
                    pending_volume_mb = daily_totals.pending_volume_mb
                    logger.debug(f"Using pending volume of {pending_volume_mb:.2f} MB from tracker")
            
            # Check space in quarantine directory (no pending volume, files already there)
            quarantine_has_space = Throttler.check_directory_space(
                quarantine_path, 
                file_size_mb, 
                min_free_space_mb,
                include_pending_volume=False,
                logging_options=logging_options
            )
            
            # Check space in destination directory (include pending volume)
            destination_has_space = Throttler.check_directory_space(
                destination_path, 
                file_size_mb, 
                min_free_space_mb,
                include_pending_volume=True,
                pending_volume_mb=pending_volume_mb,
                logging_options=logging_options
            )
            
            # Check space in hazard archive directory (include pending volume)
            hazard_has_space = Throttler.check_directory_space(
                hazard_path, 
                file_size_mb, 
                min_free_space_mb,
                include_pending_volume=True,
                pending_volume_mb=pending_volume_mb,
                logging_options=logging_options
            )
            
            # Log warning if any directory is full
            if not (quarantine_has_space and destination_has_space and hazard_has_space):
                logger.warning(f"Stopping file processing due to insufficient disk space")
            
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            quarantine_has_space = False
            destination_has_space = False
            hazard_has_space = False
            disk_error = True
        
        # Determine if file can be processed
        can_process = (quarantine_has_space and 
                      destination_has_space and 
                      hazard_has_space and 
                      not disk_error and
                      not daily_limit_exceeded)
        
        # Create and return result object as SimpleNamespace
        return types.SimpleNamespace(
            canProcess=can_process,
            quarantine_has_space=quarantine_has_space,
            destination_has_space=destination_has_space,
            hazard_has_space=hazard_has_space,
            diskError=disk_error,
            daily_limit_exceeded=daily_limit_exceeded,
            daily_limit_message=daily_limit_message
        )
        
    # The check_daily_limits functionality has been moved directly into can_process_file and handle_throttle_check
