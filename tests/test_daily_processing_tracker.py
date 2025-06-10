"""
Unit tests for the refactored DailyProcessingTracker class.
"""

import unittest
import os
import tempfile
import shutil
import yaml
from datetime import datetime

from shuttle.daily_processing_tracker import DailyProcessingTracker


class TestDailyProcessingTracker(unittest.TestCase):
    
    def setUp(self):
        """Set up a test environment with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = DailyProcessingTracker(
            data_directory=self.temp_dir
        )
        
        # Sample file data for testing
        self.file_path = "/path/to/quarantine/file.txt"
        self.source_path = "/path/to/source/file.txt"
        self.file_size_mb = 1.5
        self.file_hash = "sample_hash_123456"
        self.relative_file_path = "file.txt"
        
    def tearDown(self):
        """Clean up the test environment."""
        # Close the tracker first
        if hasattr(self, 'tracker'):
            self.tracker.close()
            
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
        
    def test_initialization(self):
        """Test tracker initialization with empty directory."""
        # Assert initial counter values
        self.assertEqual(self.tracker.pending_files, 0)
        self.assertEqual(self.tracker.pending_volume_mb, 0.0)
        self.assertEqual(self.tracker.successful_files, 0)
        self.assertEqual(self.tracker.successful_volume_mb, 0.0)
        self.assertEqual(self.tracker.failed_files, 0)
        self.assertEqual(self.tracker.failed_volume_mb, 0.0)
        self.assertEqual(self.tracker.suspect_files, 0)
        self.assertEqual(self.tracker.suspect_volume_mb, 0.0)
        self.assertEqual(len(self.tracker.file_records), 0)
        
    def test_add_pending_file(self):
        """Test adding a pending file with hash and path."""
        # Add a pending file
        returned_relative_path = self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        
        # Assert the relative file path is returned correctly
        self.assertEqual(returned_relative_path, self.relative_file_path)
        
        # Assert counters are updated
        self.assertEqual(self.tracker.pending_files, 1)
        self.assertEqual(self.tracker.pending_volume_mb, self.file_size_mb)
        
        # Assert the file record is stored correctly
        self.assertIn(self.relative_file_path, self.tracker.file_records)
        record = self.tracker.file_records[self.relative_file_path]
        self.assertEqual(record['file_path'], self.file_path)
        self.assertEqual(record['file_size_mb'], self.file_size_mb)
        self.assertEqual(record['status'], 'pending')
        self.assertEqual(record['file_hash'], self.file_hash)
        self.assertIsNotNone(record['quarantine_time'])
        
    def test_complete_pending_file_success(self):
        """Test completing a pending file as successful."""
        # Add a pending file first
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        
        # Complete the file with success outcome
        result = self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='success'
        )
        
        # Assert the result is True
        self.assertTrue(result)
        
        # Assert counters are updated correctly
        self.assertEqual(self.tracker.pending_files, 0)
        self.assertEqual(self.tracker.pending_volume_mb, 0.0)
        self.assertEqual(self.tracker.successful_files, 1)
        self.assertEqual(self.tracker.successful_volume_mb, self.file_size_mb)
        self.assertEqual(self.tracker.failed_files, 0)
        self.assertEqual(self.tracker.failed_volume_mb, 0.0)
        
        # Assert the file record is updated correctly
        record = self.tracker.file_records[self.relative_file_path]
        self.assertEqual(record['status'], 'completed')
        self.assertEqual(record['outcome'], 'success')
        self.assertIsNotNone(record['process_time'])
        
    def test_complete_pending_file_failed(self):
        """Test completing a pending file as failed."""
        # Add a pending file first
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        
        # Complete the file with failed outcome
        error_message = "Test error message"
        result = self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='failed',
            error=error_message
        )
        
        # Assert the result is True
        self.assertTrue(result)
        
        # Assert counters are updated correctly
        self.assertEqual(self.tracker.pending_files, 0)
        self.assertEqual(self.tracker.pending_volume_mb, 0.0)
        self.assertEqual(self.tracker.successful_files, 0)
        self.assertEqual(self.tracker.successful_volume_mb, 0.0)
        self.assertEqual(self.tracker.failed_files, 1)
        self.assertEqual(self.tracker.failed_volume_mb, self.file_size_mb)
        
        # Assert the file record is updated correctly
        record = self.tracker.file_records[self.relative_file_path]
        self.assertEqual(record['status'], 'completed')
        self.assertEqual(record['outcome'], 'failed')
        self.assertEqual(record['error'], error_message)
        
    def test_complete_pending_file_suspect(self):
        """Test completing a pending file as suspect."""
        # Add a pending file first
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        
        # Complete the file with suspect outcome
        result = self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='suspect'
        )
        
        # Assert the result is True
        self.assertTrue(result)
        
        # Assert counters are updated correctly
        self.assertEqual(self.tracker.pending_files, 0)
        self.assertEqual(self.tracker.pending_volume_mb, 0.0)
        self.assertEqual(self.tracker.successful_files, 0)
        self.assertEqual(self.tracker.successful_volume_mb, 0.0)
        self.assertEqual(self.tracker.failed_files, 0)
        self.assertEqual(self.tracker.failed_volume_mb, 0.0)
        self.assertEqual(self.tracker.suspect_files, 1)
        self.assertEqual(self.tracker.suspect_volume_mb, self.file_size_mb)
        
        # Assert the file record is updated correctly
        record = self.tracker.file_records[self.relative_file_path]
        self.assertEqual(record['status'], 'completed')
        self.assertEqual(record['outcome'], 'suspect')
        
    def test_missing_file_path(self):
        """Test completing a file with non-existent relative file path."""
        # Try to complete a non-existent file
        result = self.tracker.complete_pending_file(
            relative_file_path="non_existent_path.txt",
            outcome='success'
        )
        
        # Assert the result is False
        self.assertFalse(result)
        
        # Assert counters remain unchanged
        self.assertEqual(self.tracker.pending_files, 0)
        self.assertEqual(self.tracker.pending_volume_mb, 0.0)
        self.assertEqual(self.tracker.successful_files, 0)
        self.assertEqual(self.tracker.successful_volume_mb, 0.0)
        
    def test_get_total_files_count(self):
        """Test the file counting method."""
        # Add some files
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        
        second_relative_path = "second.txt"
        self.tracker.add_pending_file(
            file_path="/path/to/second/file.txt",
            file_size_mb=2.0,
            file_hash="second_hash_789012",
            source_path="/path/to/source/second.txt",
            relative_file_path=second_relative_path
        )
        
        # Complete one file
        self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='success'
        )
        
        # Test with pending files included
        self.assertEqual(self.tracker.get_total_files_count(include_pending=True), 2)  # 1 completed + 1 pending
        
        # Test without pending files
        self.assertEqual(self.tracker.get_total_files_count(include_pending=False), 1)  # 1 completed only
        
        # Test with additional count
        self.assertEqual(self.tracker.get_total_files_count(include_pending=True, include_additional=2), 4)  # 1 completed + 1 pending + 2 additional
    
    def test_get_total_volume_mb(self):
        """Test the volume calculation method."""
        # Add some files
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        
        second_relative_path = "second.txt"
        self.tracker.add_pending_file(
            file_path="/path/to/second/file.txt",
            file_size_mb=2.0,
            file_hash="second_hash_789012",
            source_path="/path/to/source/second.txt",
            relative_file_path=second_relative_path
        )
        
        # Complete one file
        self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='success'
        )
        
        # Test with pending files included
        self.assertAlmostEqual(self.tracker.get_total_volume_mb(include_pending=True), 3.5)  # 1.5 completed + 2.0 pending
        
        # Test without pending files
        self.assertAlmostEqual(self.tracker.get_total_volume_mb(include_pending=False), 1.5)  # 1.5 completed only
        
        # Test with additional volume
        self.assertAlmostEqual(self.tracker.get_total_volume_mb(include_pending=True, include_additional_mb=1.0), 4.5)  # 1.5 completed + 2.0 pending + 1.0 additional
    
    def test_save_daily_totals(self):
        """Test saving totals to file with transaction safety."""
        # Add and complete a file to update counters
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='success'
        )
        
        # Check that the tracking file exists
        tracking_file = os.path.join(self.temp_dir, f"throttle_{datetime.now().date().isoformat()}.yaml")
        self.assertTrue(os.path.exists(tracking_file))
        
        # Load the file and check its contents
        with open(tracking_file, 'r') as f:
            data = yaml.safe_load(f)
            
        # Verify structure and values
        self.assertIn('start_time', data)
        self.assertIn('totals', data)
        self.assertIn('metrics', data)
        self.assertEqual(data['totals']['files_processed'], 1)
        self.assertEqual(data['totals']['volume_processed_mb'], self.file_size_mb)
        self.assertEqual(data['metrics']['successful_files'], 1)
        self.assertEqual(data['metrics']['successful_volume_mb'], self.file_size_mb)
    
    def test_close_with_pending(self):
        """Test close() with pending files."""
        # Add two pending files
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        
        second_relative_path = "another.txt"
        self.tracker.add_pending_file(
            file_path="/path/to/another/file.txt",
            file_size_mb=2.5,
            file_hash="another_hash_789012",
            source_path="/path/to/source/another.txt",
            relative_file_path=second_relative_path
        )
        
        # Verify we have two pending files
        self.assertEqual(self.tracker.pending_files, 2)
        self.assertEqual(self.tracker.pending_volume_mb, self.file_size_mb + 2.5)
        
        # Close the tracker
        self.tracker.close()
        
        # Verify pending files are marked as 'unknown'
        self.assertEqual(self.tracker.pending_files, 0)
        self.assertEqual(self.tracker.pending_volume_mb, 0.0)
        
        # Check that both records are marked as completed with 'unknown' outcome
        for relative_path in [self.relative_file_path, second_relative_path]:
            record = self.tracker.file_records[relative_path]
            self.assertEqual(record['status'], 'completed')
            self.assertEqual(record['outcome'], 'unknown')
            self.assertIsNotNone(record['process_time'])
            self.assertIn('Process terminated', record['error'])
    
    def test_generate_summary(self):
        """Test summary generation."""
        # Add and complete files with different outcomes
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='success'
        )
        
        # Add and complete a failed file
        failed_relative_path = "failed.txt"
        self.tracker.add_pending_file(
            file_path="/path/to/failed/file.txt",
            file_size_mb=1.0,
            file_hash="failed_hash_654321",
            source_path="/path/to/source/failed.txt",
            relative_file_path=failed_relative_path
        )
        self.tracker.complete_pending_file(
            relative_file_path=failed_relative_path,
            outcome='failed',
            error="Test failure"
        )
        
        # Add a pending file
        pending_relative_path = "pending.txt"
        self.tracker.add_pending_file(
            file_path="/path/to/pending/file.txt",
            file_size_mb=0.5,
            file_hash="pending_hash_111222",
            source_path="/path/to/source/pending.txt",
            relative_file_path=pending_relative_path
        )
        
        # Generate a summary
        summary = self.tracker.generate_summary()
        
        # Verify summary contents
        self.assertIn('start_time', summary)
        self.assertIn('end_time', summary)
        self.assertIn('duration_seconds', summary)
        self.assertIn('totals', summary)
        self.assertIn('processing_rate', summary)
        
        # Verify counters
        totals = summary['totals']
        self.assertEqual(totals['successful_files'], 1)
        self.assertEqual(totals['successful_volume_mb'], self.file_size_mb)
        self.assertEqual(totals['failed_files'], 1)
        self.assertEqual(totals['failed_volume_mb'], 1.0)
        self.assertEqual(totals['pending_files'], 1)
        self.assertEqual(totals['pending_volume_mb'], 0.5)
    
    def test_generate_task_summary(self):
        """Test task summary generation."""
        # Add and complete files with different outcomes
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='success'
        )
        
        # Add and complete a suspect file
        suspect_relative_path = "suspect.txt"
        self.tracker.add_pending_file(
            file_path="/path/to/suspect/file.txt",
            file_size_mb=2.0,
            file_hash="suspect_hash_789012",
            source_path="/path/to/source/suspect.txt",
            relative_file_path=suspect_relative_path
        )
        self.tracker.complete_pending_file(
            relative_file_path=suspect_relative_path,
            outcome='suspect'
        )
        
        # Generate a task summary
        summary = self.tracker.generate_task_summary()
        
        # Verify summary contents
        self.assertEqual(summary['successful_files'], 1)
        self.assertEqual(summary['successful_volume_mb'], self.file_size_mb)
        self.assertEqual(summary['suspect_files'], 1)
        self.assertEqual(summary['suspect_volume_mb'], 2.0)
        self.assertEqual(summary['total_files'], 2)  # success + suspect
        self.assertEqual(summary['total_volume_mb'], self.file_size_mb + 2.0)
    
    def test_export_to_yaml(self):
        """Test exporting file records to YAML."""
        # Add and complete files with different outcomes
        self.tracker.add_pending_file(
            file_path=self.file_path,
            file_size_mb=self.file_size_mb,
            file_hash=self.file_hash,
            source_path=self.source_path,
            relative_file_path=self.relative_file_path
        )
        self.tracker.complete_pending_file(
            relative_file_path=self.relative_file_path,
            outcome='success'
        )
        
        # Export to YAML
        export_path = os.path.join(self.temp_dir, "test_export.yaml")
        result_path = self.tracker.export_to_yaml(export_path)
        
        # Check that the export succeeded
        self.assertEqual(result_path, export_path)
        self.assertTrue(os.path.exists(export_path))
        
        # Load the exported file
        with open(export_path, 'r') as f:
            export_data = yaml.safe_load(f)
        
        # Verify the exported data
        self.assertIn('export_time', export_data)
        self.assertIn('run_start_time', export_data)
        self.assertIn('files', export_data)
        self.assertIn(self.relative_file_path, export_data['files'])
        
        # Check the file record
        file_record = export_data['files'][self.relative_file_path]
        self.assertEqual(file_record['file_path'], self.file_path)
        self.assertEqual(file_record['outcome'], 'success')
        self.assertEqual(file_record['file_hash'], self.file_hash)


if __name__ == '__main__':
    unittest.main()