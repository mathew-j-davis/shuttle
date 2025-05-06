#!/usr/bin/env python3
"""
Unit tests for the disk space throttling feature of Shuttle.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import logging
import sys
import os
import tempfile
import shutil

# Add shuttle package to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shuttle.scanning import process_directory, shutil_copy_with_metadata
from shuttle.notifier import Notifier


class TestThrottling(unittest.TestCase):
    """Test cases for the disk space throttling feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Configure a test logger that doesn't print anything
        self.logger = logging.getLogger('test_logger')
        self.logger.setLevel(logging.CRITICAL + 1)
        
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_dir, 'source')
        self.destination_dir = os.path.join(self.temp_dir, 'destination')
        self.quarantine_dir = os.path.join(self.temp_dir, 'quarantine')
        self.hazard_archive_dir = os.path.join(self.temp_dir, 'hazard_archive')
        
        # Create directories
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.destination_dir, exist_ok=True)
        os.makedirs(self.quarantine_dir, exist_ok=True)
        os.makedirs(self.hazard_archive_dir, exist_ok=True)
        
        # Create mock notifier
        self.notifier = MagicMock(spec=Notifier)
        self.notifier.notify.return_value = True
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    @patch('os.statvfs')
    def test_throttling_enabled_sufficient_space(self, mock_statvfs):
        """Test throttling when enabled but there is sufficient space."""
        # Mock statvfs to return sufficient free space (20GB)
        mock_statvfs_result = MagicMock()
        mock_statvfs_result.f_frsize = 4096  # 4KB block size
        mock_statvfs_result.f_bavail = 5242880  # Available blocks (20GB)
        mock_statvfs.return_value = mock_statvfs_result
        
        # Create test files
        test_file_path = os.path.join(self.source_dir, 'test_file.txt')
        with open(test_file_path, 'w') as f:
            f.write('Test content')
        
        # Call process_directory with throttling enabled
        process_directory(
            source_dir=self.source_dir,
            destination_dir=self.destination_dir,
            quarantine_dir=self.quarantine_dir,
            hazard_archive_dir=self.hazard_archive_dir,
            create_quarantine_dirs=True,
            recursive=True,
            throttle=True,
            throttle_free_space=10000,  # 10GB minimum
            notifier=self.notifier,
            logger=self.logger
        )
        
        # Verify files were processed (not throttled)
        self.assertTrue(os.path.exists(os.path.join(self.destination_dir, 'test_file.txt')))
        
        # Verify notifier wasn't called (no throttling occurred)
        self.notifier.notify.assert_not_called()
    
    @patch('os.statvfs')
    def test_throttling_enabled_insufficient_space(self, mock_statvfs):
        """Test throttling when enabled and there is insufficient space."""
        # Mock statvfs to return insufficient free space (5GB)
        mock_statvfs_result = MagicMock()
        mock_statvfs_result.f_frsize = 4096  # 4KB block size
        mock_statvfs_result.f_bavail = 1310720  # Available blocks (5GB)
        mock_statvfs.return_value = mock_statvfs_result
        
        # Create test files
        test_file_path = os.path.join(self.source_dir, 'test_file.txt')
        with open(test_file_path, 'w') as f:
            f.write('Test content')
        
        # Call process_directory with throttling enabled
        process_directory(
            source_dir=self.source_dir,
            destination_dir=self.destination_dir,
            quarantine_dir=self.quarantine_dir,
            hazard_archive_dir=self.hazard_archive_dir,
            create_quarantine_dirs=True,
            recursive=True,
            throttle=True,
            throttle_free_space=10000,  # 10GB minimum
            notifier=self.notifier,
            logger=self.logger
        )
        
        # Verify notifier was called (throttling occurred)
        self.notifier.notify.assert_called()
        
        # Verify throttling message content
        notify_args = self.notifier.notify.call_args[0]
        self.assertIn("Disk Space Low", notify_args[0])  # Title
        
        # We might need to adjust this test depending on exact implementation details
        # of the notification content in the process_directory function
    
    @patch('os.statvfs')
    def test_throttling_disabled(self, mock_statvfs):
        """Test that throttling doesn't occur when disabled."""
        # Mock statvfs to return insufficient free space (5GB)
        mock_statvfs_result = MagicMock()
        mock_statvfs_result.f_frsize = 4096  # 4KB block size
        mock_statvfs_result.f_bavail = 1310720  # Available blocks (5GB)
        mock_statvfs.return_value = mock_statvfs_result
        
        # Create test files
        test_file_path = os.path.join(self.source_dir, 'test_file.txt')
        with open(test_file_path, 'w') as f:
            f.write('Test content')
        
        # Call process_directory with throttling disabled
        process_directory(
            source_dir=self.source_dir,
            destination_dir=self.destination_dir,
            quarantine_dir=self.quarantine_dir,
            hazard_archive_dir=self.hazard_archive_dir,
            create_quarantine_dirs=True,
            recursive=True,
            throttle=False,  # Throttling disabled
            throttle_free_space=10000,  # 10GB minimum, but should be ignored
            notifier=self.notifier,
            logger=self.logger
        )
        
        # Verify files were processed (not throttled despite low space)
        self.assertTrue(os.path.exists(os.path.join(self.destination_dir, 'test_file.txt')))
        
        # Verify notifier wasn't called (no throttling)
        self.notifier.notify.assert_not_called()


if __name__ == '__main__':
    unittest.main()
