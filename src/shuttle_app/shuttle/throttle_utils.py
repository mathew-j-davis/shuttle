"""
Throttling utilities for Shuttle.

This module contains functions to handle disk space throttling and daily throttling.
"""

import os
import yaml
from datetime import datetime
from shuttle_common.logging_setup import setup_logging

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
        throttle_logger: ThrottleLogger instance for daily limit tracking
        notifier: Notifier instance for sending notifications (optional)
        logging_options: Logging configuration options
        
    Returns:
        bool: True if processing can continue, False if it should stop
    """
    # Create a logger for this function
    logger = setup_logging('shuttle.throttle_utils.handle_throttle_check', logging_options)
    
    # Default values
    can_continue = True
    daily_limit_exceeded = False
    daily_limit_message = ""
    
    # Get daily totals from throttle_logger if available
    daily_totals = None
    if throttle_logger and (max_files_per_day > 0 or max_volume_per_day > 0):
        daily_totals = throttle_logger.daily_totals
        logger.debug(f"Current daily totals: {daily_totals['files_processed']} files, {daily_totals['volume_processed_mb']:.2f} MB")
    
    try:
        # Check if we can process this file based on available space and daily limits
        throttle_result = throttler.can_process_file(
            source_file_path, 
            quarantine_path,
            destination_path,
            hazard_archive_path,
            throttle_free_space,
            daily_totals,
            max_files_per_day,
            max_volume_per_day,
            logging_options
        )
        
        # Extract results for each directory from the result object
        assume_quarantine_has_space = throttle_result.quarantine_has_space
        assume_destination_has_space = throttle_result.destination_has_space
        assume_hazard_has_space = throttle_result.hazard_has_space
        disk_error = throttle_result.diskError
        
        # If all checks passed, return True
        if throttle_result.canProcess:
            return True
        else:
            # Handle cases where throttle checks failed
            
            # Check for daily limit exceeded
            if throttle_result.daily_limit_exceeded:
                # Log the daily limit exceeded message
                logger.warning(f"Daily throttling limit reached: {throttle_result.daily_limit_message}")
                
                # Send notification if available
                if notifier:
                    notifier.notify(
                        "Shuttle Daily Limit Reached", 
                        f"Processing stopped: {throttle_result.daily_limit_message}\n\n"
                        f"File: {os.path.basename(source_file_path)}\n"
                        f"Daily limits: {max_files_per_day or 'unlimited'} files, {max_volume_per_day or 'unlimited'} MB"
                    )
                    
                # If daily throttling is used, update throttle log
                if throttle_logger:
                    # Log the attempted file for auditing
                    throttle_logger.log_rejected_file(source_file_path, throttle_result.daily_limit_message)
                    
            # Check for disk space issues
            elif not throttle_result.quarantine_has_space or not throttle_result.destination_has_space or not throttle_result.hazard_has_space:
                # Create a summary of which directories are lacking space
                disk_message = "Insufficient disk space:\n"
                
                if not throttle_result.quarantine_has_space:
                    disk_message += "- Quarantine directory is full\n"
                if not throttle_result.destination_has_space:
                    disk_message += "- Destination directory is full\n"
                if not throttle_result.hazard_has_space:
                    disk_message += "- Hazard archive directory is full\n"
                if throttle_result.diskError:
                    disk_message += "Disk error when checking space. "
                
                logger.info(f"Disk space throttling activated: {disk_message}")
                
                # Send notification if available
                if notifier:
                    summary_title = "Shuttle Disk Space Alert"
                    notifier.notify(summary_title, disk_message)
            
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
        can_continue = False
        
        # Send error notification if notifier provided
        if notifier:
            error_message = f"Critical error during throttle check: {str(e)}"
            notifier.notify("Shuttle Throttle Error", error_message)
    
    return can_continue


class ThrottleLogger:
    """
    Tracks and logs file processing for daily throttling limits.
    
    This class maintains a YAML log file with daily statistics on files processed
    and data volume to enforce daily throttling limits.
    """
    
    def __init__(self, log_path, logging_options=None):
        """
        Initialize the throttle logger.
        
        Args:
            log_path: Directory path for storing log files
            logging_options: Logging configuration options
        """
        self.log_path = log_path
        self.logger = setup_logging('shuttle.throttle_logger', logging_options)
        self.today = datetime.now().date()
        self.log_file = os.path.join(log_path, f"throttle_{self.today.isoformat()}.yaml")
        self.run_data = {
            'start_time': datetime.now().isoformat(),
            'files_processed': 0,
            'volume_processed_mb': 0
        }
        self.daily_totals = self._load_daily_totals()
        
    def _load_daily_totals(self):
        """
        Load the current day's totals from the log file.
        
        Returns:
            dict: Current daily totals or zeroed counters if no log exists
        """
        if not os.path.exists(self.log_file):
            self.logger.info(f"No existing throttle log for today, creating new tracking")
            return {'files_processed': 0, 'volume_processed_mb': 0}
                
        try:
            with open(self.log_file, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'totals' in data:
                    self.logger.info(f"Loaded existing throttle log with {data['totals']['files_processed']} files and {data['totals']['volume_processed_mb']} MB processed today")
                    return data['totals']
                return {'files_processed': 0, 'volume_processed_mb': 0}
        except Exception as e:
            self.logger.error(f"Error loading throttle log: {e}")
            return {'files_processed': 0, 'volume_processed_mb': 0}
    
    def check_limits(self, file_count_limit=None, volume_limit_mb=None):
        """
        Check if daily limits would be exceeded.
        
        Args:
            file_count_limit: Maximum number of files to process per day
            volume_limit_mb: Maximum volume in MB to process per day
            
        Returns:
            tuple: (can_proceed, message)
                - can_proceed: True if processing can continue, False if limit reached
                - message: Description of the limit reached or None
        """
        if file_count_limit and file_count_limit > 0 and self.daily_totals['files_processed'] >= file_count_limit:
            return False, f"Daily file count limit ({file_count_limit}) exceeded with {self.daily_totals['files_processed']} files already processed"
                
        if volume_limit_mb and volume_limit_mb > 0 and self.daily_totals['volume_processed_mb'] >= volume_limit_mb:
            return False, f"Daily volume limit ({volume_limit_mb} MB) exceeded with {self.daily_totals['volume_processed_mb']} MB already processed"
                
        return True, None
    
    def update_counts(self, files_processed, volume_processed_mb):
        """
        Update the counts for the current run.
        
        Args:
            files_processed: Number of files successfully processed
            volume_processed_mb: Volume of data processed in MB
        """
        self.run_data['files_processed'] += files_processed
        self.run_data['volume_processed_mb'] += volume_processed_mb
        self.logger.info(f"Updated throttle log: +{files_processed} files, +{volume_processed_mb:.2f} MB")
    
    def log_rejected_file(self, file_path, reason):
        """
        Log a file that was rejected due to throttling limits.
        
        Args:
            file_path (str): Path to the file that was rejected
            reason (str): Reason the file was rejected
        """
        self.logger.warning(f"File rejected due to throttling: {file_path}")
        self.logger.warning(f"Reason: {reason}")
        
        # Add to rejected files list if we have data structure for it
        if hasattr(self, 'run_data') and 'rejected_files' not in self.run_data:
            self.run_data['rejected_files'] = []
            
        if hasattr(self, 'run_data') and 'rejected_files' in self.run_data:
            # Add the rejected file entry
            rejected_entry = {
                'file': os.path.basename(file_path),
                'time': datetime.now().isoformat(),
                'reason': reason
            }
            self.run_data['rejected_files'].append(rejected_entry)
    
    def close(self):
        """
        Update the log file with the current run data and close the logger.
        
        This should be called at the end of processing to finalize the log entry.
        """
        self.run_data['end_time'] = datetime.now().isoformat()
        
        # Update totals
        new_totals = {
            'files_processed': self.daily_totals['files_processed'] + self.run_data['files_processed'],
            'volume_processed_mb': self.daily_totals['volume_processed_mb'] + self.run_data['volume_processed_mb']
        }
        
        # Load existing log or create new structure
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
            except Exception:
                data = {}
        else:
            data = {
                'date': self.today.isoformat(),
                'runs': []
            }
        
        # Ensure required structure exists
        if 'runs' not in data:
            data['runs'] = []
        
        # Add current run
        data['runs'].append(self.run_data)
        data['totals'] = new_totals
        
        # Write updated log
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        
        self.logger.info(f"Finalized throttle log at {self.log_file}")
        self.logger.info(f"Daily totals: {new_totals['files_processed']} files, {new_totals['volume_processed_mb']:.2f} MB")
