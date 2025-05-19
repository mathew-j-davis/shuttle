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
    def check_directory_space(directory_path, file_size_mb, min_free_space_mb, logging_options=None):
        """
        Check if a directory has enough free space for a file, leaving a minimum amount free after copy.
        
        Args:
            directory_path (str): Path to the directory to check
            file_size_mb (float): Size of the file in MB
            min_free_space_mb (int): Minimum free space to maintain after copy in MB
            logging_options (LoggingOptions, optional): logging configuration details
            
        Returns:
            bool: True if directory has enough space, False otherwise
        """

        logger = setup_logging('shuttle.throttler.check_directory_space', logging_options)
        
        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path, exist_ok=True)
                
            stats = shutil.disk_usage(directory_path)
            free_mb = stats.free / (1024 * 1024)  # Convert bytes to MB
            
            has_space = (free_mb - file_size_mb) >= min_free_space_mb
            
            if not has_space:
                logger.error(f"Directory {directory_path} is full. Free: {free_mb:.2f} MB, Required: {min_free_space_mb + file_size_mb:.2f} MB")
            
            return has_space
            
        except Exception as e:
            if logger:
                logger.error(f"Error checking space in directory {directory_path}: {e}")
            return False
            
    @staticmethod
    def can_process_file(source_file_path, quarantine_path, destination_path, 
                         hazard_path, min_free_space_mb, logging_options=None):
        """
        Check if a file can be processed with the given paths and return detailed status.
        
        Args:
            source_file_path (str): Path to the source file to check
            quarantine_path (str): Path to the quarantine directory
            destination_path (str): Path to the destination directory
            hazard_path (str): Path to the hazard archive directory
            min_free_space_mb (int): Minimum free space to maintain after copy in MB
            logging_options (LoggingOptions, optional): logging configuration details
            
        Returns:
            SimpleNamespace: Object with the following attributes:
                - canProcess: Whether the file can be processed (bool)
                - quarantine_has_space: Whether the quarantine directory has space (bool)
                - destination_has_space: Whether the destination directory has space (bool)
                - hazard_has_space: Whether the hazard directory has space (bool)
                - diskError: Whether a disk error occurred (bool)
        """
        logger = setup_logging('shuttle.throttler.can_process_file', logging_options)
        
        disk_error = False
        
        try:
            # Get file size in MB
            file_size_mb = os.path.getsize(source_file_path) / (1024 * 1024)
            
            # Check space in each directory directly
            quarantine_has_space = Throttler.check_directory_space(
                quarantine_path, 
                file_size_mb, 
                min_free_space_mb,
                logging_options
            )
            
            destination_has_space = Throttler.check_directory_space(
                destination_path, 
                file_size_mb, 
                min_free_space_mb,
                logging_options
            )
            
            hazard_has_space = Throttler.check_directory_space(
                hazard_path, 
                file_size_mb, 
                min_free_space_mb,
                logging_options
            )
            
            # Log warning if any directory is full
            if not (quarantine_has_space and destination_has_space and hazard_has_space):
                logger.warning(f"Stopping file processing due to insufficient disk space")
            
        except Exception as e:
            if logger:
                logger.error(f"Error checking disk space: {e}")
            quarantine_has_space = False
            destination_has_space = False
            hazard_has_space = False
            disk_error = True
        
        # Determine if file can be processed
        can_process = (quarantine_has_space and 
                      destination_has_space and 
                      hazard_has_space and 
                      not disk_error)
        
        # Create and return result object as SimpleNamespace
        return types.SimpleNamespace(
            canProcess=can_process,
            quarantine_has_space=quarantine_has_space,
            destination_has_space=destination_has_space,
            hazard_has_space=hazard_has_space,
            diskError=disk_error
        )
