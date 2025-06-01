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
    and data volume to enforce daily throttling limits. It also tracks individual files
    throughout their processing lifecycle, including outcomes (success, failure, suspect).
    """
    
    def __init__(self, data_directory, logging_options=None):
        """
        Initialize the daily processing tracker.
        
        Args:
            data_directory: Directory path for storing tracking data files
            logging_options: Logging configuration for activity reporting
        """
        self.data_directory = data_directory
        self.activity_logger = setup_logging('shuttle.daily_processing_tracker', logging_options)
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
        
        # Initialize outcome-specific counters and file records dictionary
        self.file_records = {}  # Dictionary of file records by file_hash
        self.successful_files = 0
        self.successful_volume_mb = 0.0
        self.failed_files = 0
        self.failed_volume_mb = 0.0
        self.suspect_files = 0
        self.suspect_volume_mb = 0.0
        
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
    
    def get_total_files_count(self, include_pending=True, include_additional=0):
        """
        Get the total number of files processed today.
        
        Args:
            include_pending: Whether to include files currently being processed
            include_additional: Additional files to add to the count (for checks)
            
        Returns:
            int: Total number of files processed today
        """
        base_count = self.daily_totals['files_processed']
        pending_count = self.pending_files if include_pending else 0
        return base_count + pending_count + include_additional
    
    def get_total_volume_mb(self, include_pending=True, include_additional_mb=0.0):
        """
        Get the total volume of files processed today in MB.
        
        Args:
            include_pending: Whether to include files currently being processed
            include_additional_mb: Additional volume to add (for checks)
            
        Returns:
            float: Total volume processed today in MB
        """
        base_volume = self.daily_totals['volume_processed_mb']
        pending_volume = self.pending_volume_mb if include_pending else 0.0
        return base_volume + pending_volume + include_additional_mb
        
    def add_pending_file(self, file_path, file_size_mb, file_hash, source_path):
        """
        Track a file that has been approved for processing.
        
        Args:
            file_path: Path to the file in quarantine
            file_size_mb: Size of the file in MB
            file_hash: Unique hash identifier for the file
            source_path: Original path of the file before quarantine
            
        Returns:
            str: The file hash for later reference
        """
        timestamp = datetime.now().isoformat()
        
        self.pending_files += 1
        self.pending_volume_mb += file_size_mb
        
        # Get relative source path for better readability
        rel_source_path = os.path.relpath(source_path, os.path.dirname(source_path))
        
        # Track the specific file using hash as identifier
        self.file_records[file_hash] = {
            'file_path': file_path,
            'source_path': rel_source_path,
            'file_size_mb': file_size_mb,
            'status': 'pending',
            'quarantine_time': timestamp,
            'process_time': None,
            'outcome': None,
            'error': None
        }
        
        self.activity_logger.debug(f"Added pending file: {file_path} ({file_size_mb:.2f} MB), hash: {file_hash}")
        return file_hash  # Return hash for later reference
        
    def complete_pending_file(self, file_hash, outcome='success', error=None):
        """
        Move a file from pending to processed status.
        
        Args:
            file_hash: Unique hash identifier of the file to complete
            outcome: Processing outcome ('success', 'failed', or 'suspect')
            error: Error message if outcome is 'failed'
            
        Returns:
            bool: True if file was successfully completed, False otherwise
        """
        if file_hash not in self.file_records:
            self.activity_logger.warning(f"File hash {file_hash} not found in tracking records")
            return False
            
        record = self.file_records[file_hash]
        
        # Update file record
        record['status'] = 'completed'
        record['process_time'] = datetime.now().isoformat()
        record['outcome'] = outcome
        record['error'] = error
        
        # Update counters
        self.pending_files -= 1
        self.pending_volume_mb -= record['file_size_mb']
        
        # Update outcome-specific counters
        if outcome == 'success':
            self.successful_files += 1
            self.successful_volume_mb += record['file_size_mb']
        elif outcome == 'suspect':
            self.suspect_files += 1
            self.suspect_volume_mb += record['file_size_mb']
        else:  # failed
            self.failed_files += 1
            self.failed_volume_mb += record['file_size_mb']
        
        # Update daily totals
        self.daily_totals['files_processed'] += 1
        self.daily_totals['volume_processed_mb'] += record['file_size_mb']
        
        # Save updated data
        self._save_daily_totals()
        
        self.activity_logger.debug(f"Completed file: {record['file_path']} with outcome: {outcome}")
        return True
    
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
        """Save the current daily totals to the tracking file with transaction safety."""
        os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
        
        # Use a temporary file for atomic write
        temp_file = self.tracking_file + '.tmp'
        
        try:
            # Write to temporary file first
            with open(temp_file, 'w') as f:
                yaml.dump({
                    'start_time': self.run_data['start_time'],
                    'totals': self.daily_totals,
                    'metrics': {
                        'successful_files': self.successful_files,
                        'successful_volume_mb': self.successful_volume_mb,
                        'failed_files': self.failed_files,
                        'failed_volume_mb': self.failed_volume_mb,
                        'suspect_files': self.suspect_files,
                        'suspect_volume_mb': self.suspect_volume_mb,
                        'pending_files': self.pending_files,
                        'pending_volume_mb': self.pending_volume_mb
                    }
                }, f)
            
            # Replace the original file with the temporary file
            if os.path.exists(self.tracking_file):
                os.replace(temp_file, self.tracking_file)
            else:
                os.rename(temp_file, self.tracking_file)
                
        except Exception as e:
            self.activity_logger.error(f"Error saving tracking data: {e}")
            # Try to remove the temporary file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
    def log_rejected_file(self, file_path, reason):
        """
        Log a file that was rejected due to throttling limits.
        
        Args:
            file_path (str): Path to the file that was rejected
            reason (str): Reason the file was rejected
        """
        self.activity_logger.warning(f"File rejected due to throttling: {file_path}. Reason: {reason}")
    
    def generate_summary(self):
        """
        Generate a comprehensive summary of processing.
        
        Returns:
            dict: Summary containing metrics and statistics
        """
        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.run_data['start_time'])
        duration_seconds = (end_time - start_time).total_seconds()
        
        summary = {
            'start_time': self.run_data['start_time'],
            'end_time': end_time.isoformat(),
            'duration_seconds': duration_seconds,
            'totals': {
                'files_processed': self.get_total_files_count(include_pending=False),
                'volume_processed_mb': self.get_total_volume_mb(include_pending=False),
                'successful_files': self.successful_files,
                'successful_volume_mb': self.successful_volume_mb,
                'failed_files': self.failed_files,
                'failed_volume_mb': self.failed_volume_mb,
                'suspect_files': self.suspect_files,
                'suspect_volume_mb': self.suspect_volume_mb,
                'pending_files': self.pending_files,
                'pending_volume_mb': self.pending_volume_mb
            },
            'processing_rate': {
                'files_per_second': self.daily_totals['files_processed'] / max(1, duration_seconds),
                'mb_per_second': self.daily_totals['volume_processed_mb'] / max(1, duration_seconds)
            },
            'daily_totals': self.daily_totals
        }
        
        return summary
    
    def generate_task_summary(self):
        """
        Generate a summary of tasks for use in scanning module.
        
        Returns:
            dict: Task summary with file counts and volumes by category
        """
        return {
            'successful_files': self.successful_files,
            'successful_volume_mb': self.successful_volume_mb,
            'failed_files': self.failed_files,
            'failed_volume_mb': self.failed_volume_mb,
            'suspect_files': self.suspect_files,
            'suspect_volume_mb': self.suspect_volume_mb,
            'pending_files': self.pending_files,
            'pending_volume_mb': self.pending_volume_mb,
            'total_files': self.successful_files + self.failed_files + self.suspect_files,
            'total_volume_mb': self.successful_volume_mb + self.failed_volume_mb + self.suspect_volume_mb
        }
    
    def _save_run_summary(self):
        """Save a summary of this run to a separate file."""
        summary_file = os.path.join(
            self.data_directory,
            f"summary_{self.today.isoformat()}_{datetime.now().strftime('%H%M%S')}.yaml"
        )
        
        try:
            summary = self.generate_summary()
            with open(summary_file, 'w') as f:
                yaml.dump(summary, f)
            self.activity_logger.info(f"Saved run summary to {summary_file}")
        except Exception as e:
            self.activity_logger.error(f"Error saving run summary: {e}")
    
    def export_to_yaml(self, file_path=None):
        """
        Export file records to YAML format.
        
        Args:
            file_path: Optional path for the export file
            
        Returns:
            str: Path to the export file or None if export failed
        """
        if file_path is None:
            file_path = os.path.join(
                self.data_directory,
                f"export_{self.today.isoformat()}_{datetime.now().strftime('%H%M%S')}.yaml"
            )
        
        try:
            # Prepare data structure for export
            export_data = {
                'export_time': datetime.now().isoformat(),
                'run_start_time': self.run_data['start_time'],
                'files': {}
            }
            
            # Add each file record
            for file_hash, record in self.file_records.items():
                export_data['files'][file_hash] = record.copy()
                
            # Write to file
            with open(file_path, 'w') as f:
                yaml.dump(export_data, f)
                    
            self.activity_logger.info(f"Exported file records to {file_path}")
            return file_path
        except Exception as e:
            self.activity_logger.error(f"Error exporting to YAML: {e}")
            return None
    
    def close(self):
        """
        Finalize tracking and save all data.
        
        This should be called at the end of processing to finalize the entry.
        """
        # Handle any remaining pending files
        pending_hashes = [hash for hash, record in self.file_records.items()
                        if record['status'] == 'pending']
        
        if pending_hashes:
            self.activity_logger.warning(f"Found {len(pending_hashes)} pending files during shutdown")
            for file_hash in pending_hashes:
                self.complete_pending_file(file_hash, 'unknown', 'Process terminated before completion')
        
        # Save summary data for this run
        self._save_run_summary()
        
        # Save final totals
        self._save_daily_totals()
        
        # Log a message about finalization
        self.activity_logger.info(f"Finalized daily processing tracking at {self.tracking_file}")
        self.activity_logger.info(f"Daily totals: {self.daily_totals['files_processed']} files, {self.daily_totals['volume_processed_mb']:.2f} MB")
