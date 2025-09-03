#!/usr/bin/env python3
"""
Test to verify that per_run_tracker parameter is properly passed through
the function chain in scanning.py after the fix.
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add src directories to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'shared_library'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'shuttle_app'))

from shuttle.scanning import process_scan_tasks, scan_and_process_directory


class TestPerRunTrackerFix(unittest.TestCase):
    """Test that per_run_tracker parameter is properly passed through the call chain"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Set up mock daily tracker with proper return values
        self.mock_daily_tracker = Mock()
        self.mock_daily_tracker.generate_task_summary.return_value = {
            'successful_files': 0,
            'successful_volume_mb': 0.0,
            'failed_files': 0,
            'failed_volume_mb': 0.0,
            'suspect_files': 0,
            'suspect_volume_mb': 0.0,
            'pending_files': 0,
            'pending_volume_mb': 0.0,
            'total_files': 0,
            'total_volume_mb': 0.0
        }
        self.mock_daily_tracker.complete_pending_file.return_value = True
        
        # Set up mock per-run tracker
        self.mock_per_run_tracker = Mock()
        self.mock_per_run_tracker.complete_file_processing.return_value = None
        
        # Set up mock config
        self.mock_config = Mock()
        self.mock_config.malware_scan_retry_count = 3
        self.mock_config.malware_scan_timeout_seconds = 300
        
    def test_process_scan_tasks_accepts_per_run_tracker(self):
        """Test that process_scan_tasks accepts per_run_tracker parameter"""
        # This should not raise a TypeError about unexpected keyword argument
        results, successful, failed, timeout = process_scan_tasks(
            scan_tasks=[],
            max_scan_threads=1,
            daily_processing_tracker=self.mock_daily_tracker,
            per_run_tracker=self.mock_per_run_tracker,
            config=self.mock_config
        )
        
        # Verify the function ran without NameError
        self.assertEqual(results, [])
        self.assertEqual(successful, 0)
        self.assertEqual(failed, 0)
        self.assertFalse(timeout)
        
    def test_process_scan_tasks_with_sequential_processing(self):
        """Test per_run_tracker in sequential processing mode"""
        # Update the mock tracker summary to reflect 1 successful file
        self.mock_daily_tracker.generate_task_summary.return_value = {
            'successful_files': 1,
            'successful_volume_mb': 1.0,
            'failed_files': 0,
            'failed_volume_mb': 0.0,
            'suspect_files': 0,
            'suspect_volume_mb': 0.0,
            'pending_files': 0,
            'pending_volume_mb': 0.0,
            'total_files': 1,
            'total_volume_mb': 1.0
        }
        
        # Create a mock task that returns success
        mock_task = (
            ("/tmp/quarantine/test.txt", "/tmp/source/test.txt", "/tmp/dest/test.txt", "hash123", "test.txt"),
            "/tmp/key.pem",
            "/tmp/hazard",
            False,  # delete_source_files
            True,   # on_demand_defender
            False,  # on_demand_clam_av
            False   # defender_handles_suspect_files
        )
        
        with patch('shuttle.scanning.call_scan_and_process_file') as mock_scan:
            mock_scan.return_value = True  # Successful scan
            
            # Mock file size check
            with patch('os.path.getsize') as mock_getsize:
                mock_getsize.return_value = 1024 * 1024  # 1MB
                
                results, successful, failed, timeout = process_scan_tasks(
                    scan_tasks=[mock_task],
                    max_scan_threads=1,  # Sequential
                    daily_processing_tracker=self.mock_daily_tracker,
                    per_run_tracker=self.mock_per_run_tracker,
                    config=self.mock_config
                )
        
        # Verify per_run_tracker was called
        self.mock_per_run_tracker.complete_file_processing.assert_called()
        # Verify results
        self.assertEqual(successful, 1)
        self.assertEqual(failed, 0)
        
    def test_scan_and_process_directory_passes_per_run_tracker(self):
        """Test that scan_and_process_directory properly passes per_run_tracker"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "source")
            dest_path = os.path.join(temp_dir, "dest")
            quarantine_path = os.path.join(temp_dir, "quarantine")
            hazard_path = os.path.join(temp_dir, "hazard")
            
            # Create directories
            os.makedirs(source_path)
            os.makedirs(dest_path)
            os.makedirs(quarantine_path)
            os.makedirs(hazard_path)
            
            # Create a test file
            test_file = os.path.join(source_path, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            # Mock the scanner functions
            with patch('shuttle.scanning.scan_for_malware_using_defender') as mock_defender:
                with patch('shuttle.scanning.scan_for_malware_using_clam_av') as mock_clamav:
                    with patch('shuttle.scanning.process_defender_result') as mock_process:
                        # Set up mocks to return clean results
                        mock_defender.return_value = None
                        mock_clamav.return_value = None
                        mock_process.return_value = Mock(
                            suspect_detected=False,
                            scanner_handles_suspect=False,
                            scan_completed=True
                        )
                        
                        # This should work without NameError for per_run_tracker
                        try:
                            scan_and_process_directory(
                                source_path=source_path,
                                destination_path=dest_path,
                                quarantine_path=quarantine_path,
                                hazard_archive_path=hazard_path,
                                hazard_encryption_key_file_path="/dev/null",
                                delete_source_files=False,
                                max_scan_threads=1,
                                on_demand_defender=True,
                                on_demand_clam_av=False,
                                defender_handles_suspect_files=False,
                                throttle=False,
                                daily_processing_tracker=self.mock_daily_tracker,
                                per_run_tracker=self.mock_per_run_tracker,
                                config=self.mock_config
                            )
                            # If we get here without NameError, the fix is working
                            name_error_raised = False
                        except NameError as e:
                            if 'per_run_tracker' in str(e):
                                name_error_raised = True
                                raise
                            else:
                                # Some other NameError, re-raise
                                raise
                        
                        self.assertFalse(name_error_raised, 
                                       "per_run_tracker NameError should not be raised")


if __name__ == '__main__':
    unittest.main()