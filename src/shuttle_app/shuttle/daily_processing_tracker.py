"""
Daily Processing Tracker for Shuttle file transfer utility.

Provides functionality to track daily file processing metrics for throttling purposes.
"""

import os
import yaml
import logging
from datetime import datetime
from shuttle_common.logging_setup import setup_logging


class DailyProcessingTracker:
    """
    Tracks file processing metrics for daily throttling limits.
    
    This class maintains a YAML data file with daily statistics on files processed
    and data volume to enforce daily throttling limits.
    """
    
    def __init__(self, data_directory, logging_options=None):
        """
        Initialize the daily processing tracker.
        
        Args:
            data_directory: Directory path for storing tracking data files
            logging_options: Logging configuration for activity reporting
        """
        self.data_directory = data_directory
        self.activity_logger = setup_logging('shuttle.throttle_tracker', logging_options)
        self.today = datetime.now().date()
        self.tracking_file = os.path.join(data_directory, f"throttle_{self.today.isoformat()}.yaml")
        self.run_data = {
            'start_time': datetime.now().isoformat(),
            'files_processed': 0,
            'volume_processed_mb': 0
        }
        self.daily_totals = self._load_daily_totals()
        
        # Initialize pending counters for files in quarantine but not yet processed
        self.pending_files = 0
        self.pending_volume_mb = 0.0
        
    def _load_daily_totals(self):
        """
        Load the current day's totals from the tracking file.
        
        Returns:
            dict: Current daily totals or zeroed counters if no tracking file exists
        """
        if not os.path.exists(self.tracking_file):
            self.activity_logger.info(f"No existing tracking data for today, creating new record")
            return {'files_processed': 0, 'volume_processed_mb': 0}
                
        try:
            with open(self.tracking_file, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'totals' in data:
                    self.activity_logger.info(f"Loaded existing tracking data with {data['totals']['files_processed']} files and {data['totals']['volume_processed_mb']} MB processed today")
                    return data['totals']
                return {'files_processed': 0, 'volume_processed_mb': 0}
        except Exception as e:
            self.activity_logger.error(f"Error loading tracking data: {e}")
            return {'files_processed': 0, 'volume_processed_mb': 0}
    
    def check_limits(self, file_count_limit=None, volume_limit_mb=None, file_size_mb=0):
        """
        Check if daily limits would be exceeded by processing another file.
        
        Args:
            file_count_limit: Maximum number of files to process per day
            volume_limit_mb: Maximum volume in MB to process per day
            file_size_mb: Size of the file to be processed in MB
            
        Returns:
            tuple: (can_proceed, message)
                - can_proceed: True if processing can continue, False if limit reached
                - message: Description of the limit reached or None
        """
        # Calculate totals including pending files
        total_files = self.daily_totals['files_processed'] + self.pending_files + 1  # +1 for current file
        total_volume = self.daily_totals['volume_processed_mb'] + self.pending_volume_mb + file_size_mb
        
        if file_count_limit and file_count_limit > 0 and total_files > file_count_limit:
            return False, f"Daily file count limit ({file_count_limit}) would be exceeded with {total_files} files"
                
        if volume_limit_mb and volume_limit_mb > 0 and total_volume > volume_limit_mb:
            return False, f"Daily volume limit ({volume_limit_mb} MB) would be exceeded with {total_volume:.2f} MB"
                
        return True, None
        
    def add_pending_file(self, file_size_mb):
        """
        Track a file that has been approved for processing but hasn't completed yet.
        
        Args:
            file_size_mb: Size of the file in MB
            
        Returns:
            None
        """
        self.pending_files += 1
        self.pending_volume_mb += file_size_mb
        self.activity_logger.debug(f"Added pending file ({file_size_mb:.2f} MB). Now tracking {self.pending_files} pending files with {self.pending_volume_mb:.2f} MB")
        
    def complete_pending_file(self, file_size_mb):
        """
        Move a file from pending to processed status.
        
        Args:
            file_size_mb: Size of the file in MB
            
        Returns:
            None
        """
        if self.pending_files > 0:
            self.pending_files -= 1
            self.pending_volume_mb -= file_size_mb
            self.activity_logger.debug(f"Completed pending file ({file_size_mb:.2f} MB). Now tracking {self.pending_files} pending files")
            
            # Add to processed counts
            self.update_counts(1, file_size_mb)
        else:
            self.activity_logger.warning(f"Attempted to complete a pending file when none were tracked. Adding directly to processed counts.")
            self.update_counts(1, file_size_mb)
    
    def update_counts(self, files_processed, volume_processed_mb):
        """
        Update the counts for the current run.
        
        Args:
            files_processed: Number of files processed in this run
            volume_processed_mb: Volume of data processed in MB in this run
        """
        self.run_data['files_processed'] += files_processed
        self.run_data['volume_processed_mb'] += volume_processed_mb
        
        self.daily_totals['files_processed'] += files_processed
        self.daily_totals['volume_processed_mb'] += volume_processed_mb
        
        # Log the update
        self.activity_logger.info(f"Updated processing counts: +{files_processed} files, +{volume_processed_mb:.2f} MB")
        self.activity_logger.info(f"Daily totals now: {self.daily_totals['files_processed']} files, {self.daily_totals['volume_processed_mb']:.2f} MB")
        
        # Save the updated counts to the tracking file
        self._save_daily_totals()
    
    def initialize_with_values(self, files_processed=0, volume_processed_mb=0.0):
        """
        Initialize the tracking file with specific values.
        
        This is primarily useful for testing or setting up initial state.
        
        Args:
            files_processed: Initial number of files processed
            volume_processed_mb: Initial volume processed in MB
        """
        self.daily_totals = {
            'files_processed': files_processed,
            'volume_processed_mb': volume_processed_mb
        }
        
        self.activity_logger.info(f"Initializing tracking with {files_processed} files and {volume_processed_mb:.2f} MB")
        self._save_daily_totals()
        
    def _save_daily_totals(self):
        """Save the current daily totals to the tracking file."""
        os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
        
        try:
            with open(self.tracking_file, 'w') as f:
                yaml.dump({
                    'start_time': self.run_data['start_time'],
                    'totals': self.daily_totals
                }, f)
        except Exception as e:
            self.activity_logger.error(f"Error saving tracking data: {e}")
            
    def log_rejected_file(self, file_path, reason):
        """
        Log a file that was rejected due to throttling limits.
        
        Args:
            file_path (str): Path to the file that was rejected
            reason (str): Reason the file was rejected
        """
        self.activity_logger.warning(f"File rejected due to throttling: {file_path}. Reason: {reason}")
    
    def close(self):
        """
        Update the tracking file with the current run data and close the tracker.
        
        This should be called at the end of processing to finalize the entry.
        """
        # Just save the daily totals
        self._save_daily_totals()
        
        # Log a message about finalization
        self.activity_logger.info(f"Finalized daily processing tracking at {self.tracking_file}")
        self.activity_logger.info(f"Daily totals: {self.daily_totals['files_processed']} files, {self.daily_totals['volume_processed_mb']:.2f} MB")
