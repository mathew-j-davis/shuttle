"""
Per-run tracking for Shuttle file processing.

This module provides functionality to track file counts and volumes processed 
during a single execution/run of the Shuttle application, enforcing per-run limits.
"""

import os
import logging
from typing import Optional
from shuttle_common.logger_injection import get_logger


class PerRunTracker:
    """
    Track file counts and volumes processed during a single execution/run.
    
    This class provides functionality to:
    - Track the number of files processed in the current run
    - Track the total volume (MB) of files processed in the current run
    - Check if per-run limits would be exceeded
    - Provide counters for throttling decisions
    """
    
    def __init__(self, logging_options=None):
        """
        Initialize the per-run tracker.
        
        Args:
            logging_options: Optional logging configuration
        """
        self.logger = get_logger()
        
        # Counters for current run
        self._files_processed = 0
        self._volume_processed_mb = 0.0
        
        # Pending items (copied to quarantine but not yet processed)
        self._pending_files = 0
        self._pending_volume_mb = 0.0
        
        self.logger.debug("PerRunTracker initialized")
    
    def add_pending_file(self, file_path: str, file_size_mb: float, logging_options=None):
        """
        Add a file to pending processing (when copied to quarantine).
        
        Args:
            file_path: Path to the file
            file_size_mb: Size of the file in MB
            logging_options: Optional logging configuration
        """
        logger = get_logger()
        
        self._pending_files += 1
        self._pending_volume_mb += file_size_mb
        
        logger.debug(f"Added pending file: {os.path.basename(file_path)} ({file_size_mb:.2f} MB)")
        logger.debug(f"Pending totals: {self._pending_files} files, {self._pending_volume_mb:.2f} MB")
    
    def complete_file_processing(self, file_path: str, file_size_mb: float, logging_options=None):
        """
        Mark a file as completed (after scanning and final disposition).
        
        Args:
            file_path: Path to the file
            file_size_mb: Size of the file in MB
            logging_options: Optional logging configuration
        """
        logger = get_logger()
        
        # Move from pending to processed
        if self._pending_files > 0:
            self._pending_files -= 1
        if self._pending_volume_mb >= file_size_mb:
            self._pending_volume_mb -= file_size_mb
        
        self._files_processed += 1
        self._volume_processed_mb += file_size_mb
        
        logger.debug(f"Completed file: {os.path.basename(file_path)} ({file_size_mb:.2f} MB)")
        logger.debug(f"Run totals: {self._files_processed} processed, {self._pending_files} pending")
    
    def get_total_files_count(self, include_additional: int = 0) -> int:
        """
        Get total file count including processed and pending files.
        
        Args:
            include_additional: Additional files to include in calculation
            
        Returns:
            Total file count (processed + pending + additional)
        """
        return self._files_processed + self._pending_files + include_additional
    
    def get_total_volume_mb(self, include_additional_mb: float = 0.0) -> float:
        """
        Get total volume including processed and pending volumes.
        
        Args:
            include_additional_mb: Additional volume to include in calculation
            
        Returns:
            Total volume in MB (processed + pending + additional)
        """
        return self._volume_processed_mb + self._pending_volume_mb + include_additional_mb
    
    def get_processed_files_count(self) -> int:
        """Get number of files that have been completed."""
        return self._files_processed
    
    def get_processed_volume_mb(self) -> float:
        """Get volume of files that have been completed."""
        return self._volume_processed_mb
    
    def get_pending_files_count(self) -> int:
        """Get number of files that are pending processing."""
        return self._pending_files
    
    def get_pending_volume_mb(self) -> float:
        """Get volume of files that are pending processing."""
        return self._pending_volume_mb
    
    @property
    def pending_volume_mb(self) -> float:
        """Property to access pending volume (for compatibility with daily tracker interface)."""
        return self._pending_volume_mb
    
    def get_run_summary(self, logging_options=None) -> str:
        """
        Get a summary of the current run statistics.
        
        Args:
            logging_options: Optional logging configuration
            
        Returns:
            String summary of run statistics
        """
        logger = get_logger()
        
        total_files = self.get_total_files_count()
        total_volume = self.get_total_volume_mb()
        
        summary = (
            f"Run summary: {total_files} files ({self._files_processed} processed, {self._pending_files} pending), "
            f"{total_volume:.2f} MB ({self._volume_processed_mb:.2f} processed, {self._pending_volume_mb:.2f} pending)"
        )
        
        logger.debug(summary)
        return summary