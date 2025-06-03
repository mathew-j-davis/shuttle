"""
Test Shuttle with simulator using multiple files to test multithreading and throttling



TEST PROCESS OVERVIEW:

TestShuttle
┣━━ Individual Test Methods
┃   ┣━━ test_space_throttling
┃   ┣━━ test_daily_volume_limit
┃   ┣━━ test_daily_volume_limit_with_existing_log
┃   ┣━━ test_daily_file_count_limit_with_existing_log
┃   ┣━━ test_daily_file_count_limit_no_existing_log
┃   ┣━━ test_throttling_disabled
┃   ┗━━ test_throttling_configurable
┃       ┗━━ _parse_command_line_args
┃
┣━━ test_throttling_scenario (Main test function)
┃   ┣━━ _setup_test_environment
┃   ┃   ┣━━ _create_throttle_log
┃   ┃   ┗━━ _setup_disk_space_mocking
┃   ┃
┃   ┣━━ _create_test_files
┃   ┃
┃   ┣━━ _print_throttling_prediction
┃   ┃
┃   ┣━━ IF params.setup_throttling:
┃   ┃   ┗━━ _run_shuttle_with_throttling
┃   ┃       ┣━━ _build_base_command
┃   ┃       ┣━━ _add_throttling_params
┃   ┃       ┗━━ _run_shuttle_with_command
┃   ┃           ┗━━ subprocess.Popen(cmd) → run_shuttle_with_simulator.py
┃   ┃
┃   ┣━━ ELSE:
┃   ┃   ┗━━ _run_shuttle_no_throttling
┃   ┃       ┣━━ _build_base_command
┃   ┃       ┗━━ _run_shuttle_with_command
┃   ┃           ┗━━ subprocess.Popen(cmd) → run_shuttle_with_simulator.py
┃   ┃
┃   ┗━━ _verify_test_results
┃
┣━━ setUp (Initializes test environment)
┃   ┣━━ Create temporary directories
┃   ┗━━ Set up mock objects
┃
┗━━ tearDown (Cleans up test environment)
    ┣━━ Remove lock file
    ┗━━ Remove temp directory
    
"""

import os
import sys
import time
import unittest
import yaml
import subprocess
import shutil
import datetime
import random
import string
import argparse
from unittest.mock import patch, MagicMock

from tempfile import mkdtemp

# Import the Notifier class for mocking
from shuttle_common.notifier import Notifier

# Import throttling-related modules
from shuttle.daily_processing_tracker import DailyProcessingTracker
from shuttle.throttler import Throttler

# No need to modify Python path - we're using the simulator runner script directly

# EICAR test string for real Defender tests
# Note: Most scanners will only detect this in files smaller than 128KB
EICAR_STRING = r'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
# Maximum size for reliable EICAR detection (64KB to be safe)
EICAR_MAX_SIZE_KB = 64

def mb_to_kb(mb):
    return mb * 1024
    
class TestParameters:
    """Class to hold all test parameters"""
    
    def __init__(self, **kwargs):
        # Test parameters
        self.thread_count = kwargs.get('thread_count')
        self.clean_file_count = kwargs.get('clean_file_count')
        self.malware_file_count = kwargs.get('malware_file_count')
        self.file_size_kb = kwargs.get('file_size_kb')
        
        # Throttling parameters
        self.setup_throttling = kwargs.get('setup_throttling')
        self.max_files_per_day = kwargs.get('max_files_per_day')
        self.max_volume_per_day_mb = kwargs.get('max_volume_per_day_mb')
        self.min_free_space_mb = kwargs.get('min_free_space_mb')
        self.initial_files = kwargs.get('initial_files')
        self.initial_volume_mb = kwargs.get('initial_volume_mb')
        self.mock_free_space_mb = kwargs.get('mock_free_space_mb')
        
        # Path-specific mock space parameters
        self.mock_free_space_quarantine_mb = kwargs.get('mock_free_space_quarantine_mb', self.mock_free_space_mb)
        self.mock_free_space_destination_mb = kwargs.get('mock_free_space_destination_mb', self.mock_free_space_mb)
        self.mock_free_space_hazard_mb = kwargs.get('mock_free_space_hazard_mb', self.mock_free_space_mb)
        
        self.daily_processing_tracker_logs_path = kwargs.get('daily_processing_tracker_logs_path')
        
        # Expected outcomes
        self.expected_throttled = kwargs.get('expected_throttled')
        self.expected_files_processed = kwargs.get('expected_files_processed')
        self.expected_throttle_reason = kwargs.get('expected_throttle_reason')
        self.description = kwargs.get('description')
        
        # Simulator settings
        self.use_simulator = kwargs.get('use_simulator')
        
    @classmethod
    def from_command_line(cls, args=None):
        """Create TestParameters from command line arguments"""
        # Parse arguments if not provided
        if args is None:
            import argparse
            parser = argparse.ArgumentParser(description="Configurable throttling test")
            
            # Test parameters
            parser.add_argument("--thread-count", type=int, help="Number of threads to use")
            parser.add_argument("--clean-file-count", type=int, help="Number of clean files to create")
            parser.add_argument("--malware-file-count", type=int, help="Number of malware files to create")
            parser.add_argument("--file-size-kb", type=int, help="Size of each file in KB")
            parser.add_argument("--file-size-mb", type=int, help="Size of each file in MB")
            
            # Throttling parameters
            parser.add_argument("--max-files-per-day", type=int, help="Maximum number of files per day")
            parser.add_argument("--max-volume-per-day-mb", type=int, help="Maximum volume per day in MB")
            parser.add_argument("--min-free-space-mb", type=int, help="Minimum free space in MB")
            parser.add_argument("--initial-files", type=int, help="Initial files count in throttle log")
            parser.add_argument("--initial-volume-mb", type=float, help="Initial volume in MB in throttle log")
            parser.add_argument("--mock-free-space-mb", type=float, help="Mock free space in MB (used as fallback)")
            
            # Path-specific mock space parameters
            parser.add_argument("--mock-free-space-quarantine-mb", type=float, help="Mock free space for quarantine path in MB")
            parser.add_argument("--mock-free-space-destination-mb", type=float, help="Mock free space for destination path in MB")
            parser.add_argument("--mock-free-space-hazard-mb", type=float, help="Mock free space for hazard archive path in MB")
            
            # Simulator parameters
            parser.add_argument("--no-defender-simulator", action="store_true", 
                              help="Use real Microsoft Defender instead of simulator (EICAR test files will be limited to 64KB)")
            
            args = parser.parse_args()
        
        # Create TestParameters with default values
        params = cls.with_defaults()
        
        # Override parameters with command-line values
        if hasattr(args, 'thread_count') and args.thread_count is not None:
            params.thread_count = args.thread_count
        if hasattr(args, 'clean_file_count') and args.clean_file_count is not None:
            params.clean_file_count = args.clean_file_count
        if hasattr(args, 'malware_file_count') and args.malware_file_count is not None:
            params.malware_file_count = args.malware_file_count
        # Handle file size parameters - prioritize file_size_kb if provided, otherwise use file_size_mb
        if hasattr(args, 'file_size_kb') and args.file_size_kb is not None:
            params.file_size_kb = args.file_size_kb
        elif hasattr(args, 'file_size_mb') and args.file_size_mb is not None:
            # Convert MB to KB
            params.file_size_kb = args.file_size_mb * 1024
        
        # Throttling parameters
        if hasattr(args, 'max_files_per_day') and args.max_files_per_day is not None:
            params.max_files_per_day = args.max_files_per_day
        if hasattr(args, 'max_volume_per_day_mb') and args.max_volume_per_day_mb is not None:
            params.max_volume_per_day_mb = args.max_volume_per_day_mb
        elif hasattr(args, 'max_volume_per_day') and args.max_volume_per_day is not None:
            # For backward compatibility
            params.max_volume_per_day_mb = args.max_volume_per_day
            
        if hasattr(args, 'min_free_space_mb') and args.min_free_space_mb is not None:
            params.min_free_space_mb = args.min_free_space_mb
        if hasattr(args, 'initial_files') and args.initial_files is not None:
            params.initial_files = args.initial_files
        if hasattr(args, 'initial_volume_mb') and args.initial_volume_mb is not None:
            params.initial_volume_mb = args.initial_volume_mb
        if hasattr(args, 'mock_free_space_mb') and args.mock_free_space_mb is not None:
            params.mock_free_space_mb = args.mock_free_space_mb
        elif hasattr(args, 'mock_free_space_mb') and args.mock_free_space_mb is not None:
            # For backward compatibility
            params.mock_free_space_mb = args.mock_free_space_mb
        
        # Path-specific mock space parameters
        if hasattr(args, 'mock_free_space_quarantine_mb') and args.mock_free_space_quarantine_mb is not None:
            params.mock_free_space_quarantine_mb = args.mock_free_space_quarantine_mb
        elif hasattr(args, 'mock_free_space_quarantine') and args.mock_free_space_quarantine is not None:
            # For backward compatibility
            params.mock_free_space_quarantine_mb = args.mock_free_space_quarantine
            
        if hasattr(args, 'mock_free_space_destination_mb') and args.mock_free_space_destination_mb is not None:
            params.mock_free_space_destination_mb = args.mock_free_space_destination_mb
        elif hasattr(args, 'mock_free_space_destination') and args.mock_free_space_destination is not None:
            # For backward compatibility
            params.mock_free_space_destination_mb = args.mock_free_space_destination
            
        if hasattr(args, 'mock_free_space_hazard_mb') and args.mock_free_space_hazard_mb is not None:
            params.mock_free_space_hazard_mb = args.mock_free_space_hazard_mb
        elif hasattr(args, 'mock_free_space_hazard') and args.mock_free_space_hazard is not None:
            # For backward compatibility
            params.mock_free_space_hazard_mb = args.mock_free_space_hazard
        
        # Only set up throttling if at least one throttling parameter is non-zero
        params.setup_throttling = (params.max_files_per_day > 0 or 
                                 params.max_volume_per_day_mb > 0 or 
                                 params.min_free_space_mb > 0)
        
        # Set simulator mode based on command line flag
        if hasattr(args, 'no_defender_simulator'):
            params.use_simulator = not args.no_defender_simulator
            
        return params
    
    def display_summary(self):
        """Display a summary of test parameters"""
        print("\nRunning configurable throttling test with the following parameters:")
        print(f"Thread count: {self.thread_count}")
        print(f"Clean files: {self.clean_file_count}")
        print(f"Malware files: {self.malware_file_count}")
        print(f"File size: {self.file_size_kb} KB")
        
        if self.max_files_per_day > 0:
            print(f"Max files per day: {self.max_files_per_day} files")
            
        if self.max_volume_per_day_mb > 0:
            print(f"Max volume per day: {self.max_volume_per_day_mb} MB")
            
        if self.min_free_space_mb > 0:
            print(f"Min free space: {self.min_free_space_mb} MB")
        if self.initial_files is not None and self.initial_files > 0:
            print(f"Initial files: {self.initial_files}")
        if self.initial_volume_mb is not None and self.initial_volume_mb > 0:
            print(f"Initial volume: {self.initial_volume_mb} MB")
        
        # Only display mock space if it's actually being used
        if self.mock_free_space_mb is not None:
            print(f"General mock free space: {self.mock_free_space_mb} MB")
        
        if self.mock_free_space_quarantine_mb is not None and self.mock_free_space_quarantine_mb != self.mock_free_space_mb:
            print(f"Mock free space (quarantine): {self.mock_free_space_quarantine_mb} MB")
        if self.mock_free_space_destination_mb is not None and self.mock_free_space_destination_mb != self.mock_free_space_mb:
            print(f"Mock free space (destination): {self.mock_free_space_destination_mb} MB")
        if self.mock_free_space_hazard_mb is not None and self.mock_free_space_hazard_mb != self.mock_free_space_mb:
            print(f"Mock free space (hazard): {self.mock_free_space_hazard_mb} MB")
        
        print(f"Using simulator: {self.use_simulator}\n")
        
        # Show EICAR warning if needed
        if not self.use_simulator and self.malware_file_count > 0:
            if self.file_size_kb > EICAR_MAX_SIZE_KB:
                print(f"\nNOTE: Using real Microsoft Defender with EICAR test files")
                print(f"Malware files will be limited to {EICAR_MAX_SIZE_KB}KB regardless of --file-size-kb setting")
    
    @classmethod
    def with_defaults(cls, **kwargs):
        """Create a parameter object with defaults for any missing values"""
        defaults = {
            # Test parameters
            'thread_count': 1,
            'clean_file_count': 5,
            'malware_file_count': 0,
            'file_size_kb': 100,
            
            # Throttling parameters
            'setup_throttling': True,
            'max_files_per_day': 10,
            'max_volume_per_day_mb': 1024,
            'min_free_space_mb': 10,  # 10 MB
            'initial_files': 0,
            'initial_volume_mb': 0.0,
            'mock_free_space_mb': 1024,
            'daily_processing_tracker_logs_path': None,
            
            # Expected outcomes
            'expected_throttled': False,
            'expected_files_processed': None,
            'expected_throttle_reason': None,
            
            # Simulator settings
            'use_simulator': True,  # Default to using simulator
            'description': "Generic throttling test"
        }
        
        # Apply defaults for any missing values
        params = defaults.copy()
        params.update(kwargs)
        return cls(**params)
    
    def _check_space_throttling(self, space_mb, file_size_kb, min_free_space_kb, total_files, required_files=None, clean_files=0):
        """Check if a space constraint will cause throttling
        
        Args:
            space_mb: Available space in MB
            file_size_kb: Size of each file in KB
            min_free_space_kb: Minimum free space required in KB
            total_files: Total number of files to process
            required_files: Number of files that must fit (default: all files)
            clean_files: Number of clean files that would process before this check
                        (for hazard directory where only malware files need to fit)
        
        Returns:
            tuple: (throttled, files_processed, reason)
                - throttled: True if throttling will occur
                - files_processed: Number of files that can be processed
                - reason: Throttle reason message if throttled, None otherwise
        """
        if space_mb is None:
            # No space constraint specified
            return False, total_files, None
            
        # Convert space from MB to KB
        space_kb = space_mb * 1024
        
        # Calculate available space for files after reserving minimum free space
        available_space_for_files_kb = max(0, space_kb - min_free_space_kb)
        
        # If required_files not specified, assume all files must fit
        if required_files is None:
            required_files = total_files
            
        # Calculate how many of the required files can fit in available space
        max_files_with_space = int(available_space_for_files_kb / file_size_kb) if file_size_kb > 0 else required_files
        
        if max_files_with_space < required_files:
            # Not enough space for all required files
            reason = "THROTTLE REASON: Insufficient disk space"
            
            if max_files_with_space <= 0 and clean_files == 0:
                # No files can be processed
                return True, 0, reason
                
            # Some files can be processed (clean files + as many required files as fit)
            files_processed = clean_files + max_files_with_space
            return True, min(files_processed, total_files), reason
            
        # Enough space for all required files
        return False, total_files, None
        
    def calculate_expected_outcomes(self):
        """Calculate expected outcomes based on input parameters
        
        This method automatically determines:
        1. Whether throttling is expected to occur
        2. How many files should be processed
        3. What throttle reason message to expect
        
        You can call this after setting up parameters to have expectations calculated
        rather than explicitly specified.
        """
        # Check if using real defender (no simulator)
        if hasattr(self, 'use_simulator') and self.use_simulator is False:
            # If there are no malware files, we can still predict the outcome
            if self.malware_file_count == 0:
                print("\nUsing real Defender with only clean files - outcome prediction is reliable")
            else:
                print("\nUsing real Defender with EICAR simulated malware files - skipping outcome prediction")
                print("When using real Defender with EICAR simulated malware files, outcomes cannot be reliably predicted due to:")
                print("uncertain timing of Defender behavior with the simulated malware files")
                
                # Set neutral expected outcomes
                self.expected_throttled = None
                self.expected_files_processed = None
                self.expected_throttle_reason = None
                return self
        
        total_file_count = self.clean_file_count + self.malware_file_count
        file_size_mb = self.file_size_kb / 1024
        total_volume_mb = total_file_count * file_size_mb
        
        # Default to no throttling with all files processed
        self.expected_throttled = False
        self.expected_files_processed = total_file_count
        self.expected_throttle_reason = None
        
        # No throttling checks if throttling is disabled
        if not self.setup_throttling:
            return self
        
        # Calculate remaining allowed files and volume based on initial values
        remaining_files = self.max_files_per_day - self.initial_files if self.max_files_per_day > 0 else float('inf')
        remaining_volume = self.max_volume_per_day_mb - self.initial_volume_mb if self.max_volume_per_day_mb > 0 else float('inf')
        
        # Space throttling - check if we'll run out of space in any of the paths
        file_size_kb = self.file_size_kb
        min_free_space_kb = self.min_free_space_mb * 1024  # Convert MB to KB
        
        # First check quarantine space (this is checked first in the real code)
        quarantine_space_mb = self.mock_free_space_quarantine_mb if hasattr(self, 'mock_free_space_quarantine_mb') and self.mock_free_space_quarantine_mb is not None else self.mock_free_space_mb
        throttled, files_processed, reason = self._check_space_throttling(
            quarantine_space_mb, file_size_kb, min_free_space_kb, total_file_count
        )
        if throttled:
            self.expected_throttled = True
            self.expected_files_processed = files_processed
            self.expected_throttle_reason = reason
            return self
        
        # Check destination space
        destination_space_mb = self.mock_free_space_destination_mb if hasattr(self, 'mock_free_space_destination_mb') and self.mock_free_space_destination_mb is not None else self.mock_free_space_mb
        throttled, files_processed, reason = self._check_space_throttling(
            destination_space_mb, file_size_kb, min_free_space_kb, total_file_count
        )
        if throttled:
            self.expected_throttled = True
            self.expected_files_processed = files_processed
            self.expected_throttle_reason = reason
            return self
        
        # Check hazard archive space (only matters if we have malware files)
        if self.malware_file_count > 0:
            hazard_space_mb = self.mock_free_space_hazard_mb if hasattr(self, 'mock_free_space_hazard_mb') and self.mock_free_space_hazard_mb is not None else self.mock_free_space_mb
            throttled, files_processed, reason = self._check_space_throttling(
                hazard_space_mb, file_size_kb, min_free_space_kb, total_file_count,
                required_files=self.malware_file_count, clean_files=self.clean_file_count
            )
            if throttled:
                self.expected_throttled = True
                self.expected_files_processed = files_processed
                self.expected_throttle_reason = reason
                return self
            
        # File count throttling
        if self.max_files_per_day > 0 and remaining_files < total_file_count:
            self.expected_throttled = True
            self.expected_files_processed = min(remaining_files, total_file_count)
            self.expected_throttle_reason = "THROTTLE REASON: Daily Limit Reached"
            return self
            
        # Volume throttling
        if self.max_volume_per_day_mb > 0 and remaining_volume < total_volume_mb:
            # Calculate how many files we can process before hitting volume limit
            files_before_limit = int(remaining_volume / file_size_mb)
            self.expected_throttled = True
            self.expected_files_processed = min(files_before_limit, total_file_count)
            self.expected_throttle_reason = "THROTTLE REASON: Daily Limit Reached"
            return self
        
        # If we get here, no throttling will occur
        return self
    
    def __str__(self):
        """String representation for debugging"""
        return (
            f"Test Parameters: {self.description}\n"
            f"  Thread count: {self.thread_count}\n"
            f"  File counts: {self.clean_file_count} clean, {self.malware_file_count} malware\n"
            f"  File size: {self.file_size_kb} KB ({self.file_size_kb/1024:.2f} MB)\n"
            f"  Mock free space: {self.mock_free_space_mb} MB\n"
            f"  Daily limits: {self.max_files_per_day} files, {self.max_volume_per_day} MB\n"
            f"  Min free space: {self.min_free_space} MB\n"
            f"  Initial log values: {self.initial_files} files, {self.initial_volume_mb} MB\n"
        )


class TestShuttle(unittest.TestCase):
    """Test case for Shuttle multithreading with simulator with throttling support"""
    
    # Flag to determine if all tests should run
    run_all_tests = True
    
    def run_test_scenario(self, params):
        """
        Unified test method for all throttling scenarios
        
        Args:
            params: TestParameters object with all required parameters
        """
        print(f"\nRunning throttling scenario: {params.description}")
        print(params)
        
        # Store params as instance variable so _create_test_files can access it
        self.params = params
        
        # Create test directories
        self._create_test_directories()
        
        try:
            # Setup mock disk space if requested
            if params.mock_free_space_mb is not None and params.mock_free_space_mb > 0:
                self._setup_disk_space_mocking(params.mock_free_space_mb)
            
            # Create throttle log with initial values if needed
            if params.initial_files > 0 or params.initial_volume_mb > 0:
                self._create_throttle_log(
                    files_processed=params.initial_files, 
                    volume_processed_mb=params.initial_volume_mb
                )
            
            # Create test files
            clean_files, malware_files = self._create_test_files(
                clean_file_count=params.clean_file_count,
                malware_file_count=params.malware_file_count,
                file_size_kb=params.file_size_kb
            )
            
            total_file_count = params.clean_file_count + params.malware_file_count
            
            # Predict throttling behavior based on parameters
            self._print_throttling_prediction(params)
            
            # Run Shuttle with appropriate throttling settings
            result = self._run_shuttle(params)
            
            # Verify expected results
            processed_count = len(os.listdir(self.destination_dir))
            
            # Verify throttling status
            if params.expected_throttled:
                self.assertIn("throttling", result['output'].lower(), 
                              f"Expected throttling but it didn't occur. Output: {result['output']}")
                if params.expected_throttle_reason:
                    self.assertIn(params.expected_throttle_reason, result['output'], 
                                  f"Expected throttle reason '{params.expected_throttle_reason}' not found in output: {result['output']}")
            else:
                # Check if any throttling happened unexpectedly
                self.assertNotIn("throttling activated", result['output'].lower(), 
                                f"Unexpected throttling occurred. Output: {result['output']}")
            
            # Verify processed count
            if params.expected_files_processed is not None:
                self.assertEqual(processed_count, params.expected_files_processed, 
                               f"Expected {params.expected_files_processed} files to be processed, but got {processed_count}")
            elif not params.expected_throttled:
                # If no specific count expected and no throttling, all files should be processed
                self.assertEqual(processed_count, total_file_count, 
                               f"Expected all {total_file_count} files to be processed, but got {processed_count}")
                
            return result
                
        finally:
            # Clean up test directories
            self._cleanup_test_directories()
            
    # def test_throttling_configurable(self):
    #     """Configurable test entry point that uses command-line arguments"""
    #     # Parse command-line arguments
    #     args = self._parse_arguments()
        
    #     # Create parameters from command line args with defaults for missing values
    #     params = TestParameters.with_defaults(**vars(args))
        
    #     # Auto-calculate expected outcomes based on the parameters
    #     # This means the user doesn't need to specify expected_throttled, expected_files_processed, etc.
    #     params.calculate_expected_outcomes()
        
    #     # Run the test with the configured parameters
    #     return self.run_test_scenario(params)
    
    def setUp(self):
        """Set up the test environment"""
        # Create temporary directories in SHUTTLE_WORK_DIR/tmp
        work_dir = os.environ.get('SHUTTLE_WORK_DIR', os.path.expanduser('~/shuttle/work'))
        tmp_base = os.path.join(work_dir, 'tmp')
        os.makedirs(tmp_base, exist_ok=True)
        
        # Create a unique test directory with timestamp and random suffix
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        self.temp_dir = os.path.join(tmp_base, f'multithread_test_{timestamp}_{random_suffix}')        
        os.makedirs(self.temp_dir, exist_ok=True)
        self.source_dir = os.path.join(self.temp_dir, 'source')
        self.destination_dir = os.path.join(self.temp_dir, 'destination')
        self.quarantine_dir = os.path.join(self.temp_dir, 'quarantine')
        self.hazard_dir = os.path.join(self.temp_dir, 'hazard')
        
        os.makedirs(self.source_dir)
        os.makedirs(self.destination_dir)
        os.makedirs(self.quarantine_dir)
        os.makedirs(self.hazard_dir)
        
        # Add logs directory for throttle logs
        self.logs_dir = os.path.join(self.temp_dir, 'logs')
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Create a mock notifier that we can inspect
        self.notifier = MagicMock(spec=Notifier)
        
        # Configure logging options
        self.logging_options = {
            'log_path': self.logs_dir,
        }
        
        # Throttling will be set up in the test_throttling_scenario method
        # based on the TestParameters object passed to it
        
        # Path to the run_shuttle_with_simulator.py script
        self.simulator_runner = os.path.join(os.path.dirname(__file__), 'run_shuttle_with_simulator.py')
        
        # Path to a lock file in the temp directory
        self.lock_file = os.path.join(self.temp_dir, 'shuttle.lock')
    
    def tearDown(self):
        """Clean up temporary directories after the test"""
        # Remove lock file if it exists
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
            
        # Remove temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def _create_test_files(self, clean_file_count, malware_file_count, file_size_kb):
        """
        Create test files in the source directory.
        
        Args:
            clean_file_count: Number of clean files to create
            malware_file_count: Number of malware files to create
            file_size_kb: Size of each file in KB
            
        Returns:
            tuple: (list of clean file paths, list of malware file paths)
        """
        clean_files = []
        malware_files = []
        
        # Check if we're using the simulator or real defender
        using_simulator = True
        if hasattr(self, 'params') and hasattr(self.params, 'use_simulator'):
            using_simulator = self.params.use_simulator
        
        # Generate random data once and reuse
        random_data = ''.join(random.choices(string.ascii_letters + string.digits, 
                                             k=file_size_kb * 1024))
        
        # Create clean files
        for i in range(clean_file_count):
            filename = f'clean_file_{i:03d}.txt'
            filepath = os.path.join(self.source_dir, filename)
            with open(filepath, 'w') as f:
                f.write(random_data)
            clean_files.append(filepath)
        
        # Create malware files
        for i in range(malware_file_count):
            filename = f'malware_file_{i:03d}.txt'
            filepath = os.path.join(self.source_dir, filename)
            
            with open(filepath, 'wb') as f:
                if not using_simulator:
                    # For real Defender, use EICAR test string with size limit
                    if file_size_kb > EICAR_MAX_SIZE_KB:
                        print(f"WARNING: Requested malware file size {file_size_kb}KB exceeds EICAR detection limit.")
                        print(f"Creating {EICAR_MAX_SIZE_KB}KB EICAR test file instead.")
                        actual_size_kb = EICAR_MAX_SIZE_KB
                    else:
                        actual_size_kb = file_size_kb
                    
                    # Write EICAR string at beginning of file
                    f.write(EICAR_STRING.encode('utf-8'))
                    
                    # Pad to reach desired file size
                    remaining_bytes = (actual_size_kb * 1024) - len(EICAR_STRING)
                    if remaining_bytes > 0:
                        f.write(b'\0' * remaining_bytes)
                else:
                    # For simulator, use "malware" string in random data
                    # Convert to bytes for consistency with EICAR case
                    midpoint = len(random_data) // 2
                    malware_data = random_data[:midpoint] + "malware" + random_data[midpoint:]
                    f.write(malware_data.encode('utf-8'))
            
            malware_files.append(filepath)
        
        return clean_files, malware_files

    def run_test_scenario(self, params):
        """Run a throttling test scenario with the given parameters"""
        # Print test description
        print(f"\n=== Running Test: {params.description} ===")
        
        # Setup test environment
        self._setup_test_environment(params)
        
        # Create test files
        clean_files, malware_files = self._create_test_files(
            clean_file_count=params.clean_file_count,
            malware_file_count=params.malware_file_count,
            file_size_kb=params.file_size_kb
        )
        
        print(f"Created {len(clean_files)} clean files and {len(malware_files)} malware files")
        
        # Print throttling prediction
        self._print_throttling_prediction(params)
        
        # Run shuttle with the appropriate throttling settings
        result = self._run_shuttle(params)
        
        # Verify results
        self._verify_test_results(params, result)
        
        return result
        
    def _print_throttling_prediction(self, params):
        """Print a prediction of throttling behavior based on parameters"""
        total_volume_mb = (params.clean_file_count * params.file_size_kb) / 1024
        
        print("Throttling prediction:")
        print(f"  Files to process: {params.clean_file_count}")
        print(f"  Total volume: {total_volume_mb:.2f}MB")
        
        if params.setup_throttling:
            # Print file count throttling prediction
            if params.max_files_per_day > 0:
                remaining_files = params.max_files_per_day - params.initial_files
                print(f"  File count limit: {params.max_files_per_day} (already processed: {params.initial_files})")
                print(f"  Remaining files allowed: {remaining_files}")
                
                if remaining_files <= 0:
                    print("  PREDICTION: Will throttle immediately due to file count limit")
                elif remaining_files < params.clean_file_count:
                    print(f"  PREDICTION: Will throttle after processing {remaining_files} files due to file count limit")
            
            # Print volume throttling prediction
            if params.max_volume_per_day_mb > 0:
                remaining_volume_mb = params.max_volume_per_day_mb - params.initial_volume_mb
                print(f"  Volume limit: {params.max_volume_per_day_mb}MB (already processed: {params.initial_volume_mb}MB)")
                print(f"  Remaining volume allowed: {remaining_volume_mb:.2f}MB")
                
                if remaining_volume_mb <= 0:
                    print("  PREDICTION: Will throttle immediately due to volume limit")
                elif remaining_volume_mb < total_volume_mb:
                    files_before_volume_limit = int(remaining_volume_mb / (params.file_size_kb / 1024))
                    print(f"  PREDICTION: Will throttle after processing {files_before_volume_limit} files due to volume limit")
            
            # Print space throttling prediction
            if params.min_free_space_mb > 0 and params.mock_free_space_mb is not None:
                print(f"  Free space requirement: {params.min_free_space_mb}MB (mocked available: {params.mock_free_space_mb}MB)")
                
                if params.mock_free_space_mb < params.min_free_space_mb:
                    print("  PREDICTION: Will throttle immediately due to insufficient free space")
        else:
            print("  Throttling is disabled - all files should be processed")
        
    def _setup_test_environment(self, params):
        """Set up the test environment for a throttling test"""
        # Create throttle log if initial values are specified
        if params.initial_files > 0 or params.initial_volume_mb > 0:
            self._create_throttle_log(params.initial_files, params.initial_volume_mb)
        
        # Check if any mock space parameter is set
        has_mock_space = hasattr(params, 'mock_free_space_mb') and params.mock_free_space_mb and params.mock_free_space_mb > 0
        has_mock_quarantine = hasattr(params, 'mock_free_space_quarantine_mb') and params.mock_free_space_quarantine_mb and params.mock_free_space_quarantine_mb > 0
        has_mock_destination = hasattr(params, 'mock_free_space_destination_mb') and params.mock_free_space_destination_mb and params.mock_free_space_destination_mb > 0
        has_mock_hazard = hasattr(params, 'mock_free_space_hazard_mb') and params.mock_free_space_hazard_mb and params.mock_free_space_hazard_mb > 0
        
        # Set up disk space mocking if any mock space parameter is specified
        if has_mock_space or has_mock_quarantine or has_mock_destination or has_mock_hazard:
            # We don't actually need to set up mocking here since we're using run_shuttle_with_simulator.py
            # which will handle the mocking based on command-line parameters
            # This method is kept for compatibility and future use
            if has_mock_space:
                print(f"Using mock free space: {params.mock_free_space_mb}MB general")
            if has_mock_quarantine:
                print(f"Using mock free space: {params.mock_free_space_quarantine_mb}MB for quarantine path")
            if has_mock_destination:
                print(f"Using mock free space: {params.mock_free_space_destination_mb}MB for destination path")
            if has_mock_hazard:
                print(f"Using mock free space: {params.mock_free_space_hazard_mb}MB for hazard path")
            
    def _create_throttle_log(self, files_processed=0, volume_processed_mb=0.0):
        """Create a throttle log file with specified initial values"""
        # Use the daily_processing_tracker_logs_path from the test parameters if set, otherwise use default logs directory
        throttle_logs_dir = self.logs_dir
            
        os.makedirs(throttle_logs_dir, exist_ok=True)
        
        # Initialize DailyProcessingTracker with the specified values
        daily_processing_tracker = DailyProcessingTracker(data_directory=throttle_logs_dir)
        daily_processing_tracker.initialize_with_values(files_processed, volume_processed_mb)
        
        print(f"Created throttle log with {files_processed} files and {volume_processed_mb}MB volume")
        return daily_processing_tracker
    
    # _setup_disk_space_mocking method removed as it's no longer needed
    
    def _run_shuttle(self, params):
        """Run Shuttle with or without throttling based on parameters
        
        Args:
            params: TestParameters with settings for the test
        
        Returns:
            Dictionary with test results
        """
        # Build the base command
        cmd = self._build_base_command(params)
        
        # Add throttling parameters if throttling is enabled
        if params.setup_throttling:
            cmd = self._add_throttling_params(cmd, params)
            
        # Add mock space parameters (independent from throttling)
        cmd = self._add_mock_space_params(cmd, params)
        
        # Run shuttle with the command
        return self._run_shuttle_with_command(cmd, params)
    
    def _build_base_command(self, params):
        """Build the base command for running Shuttle with simulator"""
        # Create the same throttle_logs_dir path that we use in create_throttle_log()
        throttle_logs_parent = self.logs_dir
        
        cmd = [
            sys.executable,  # Use the current Python interpreter
            self.simulator_runner,
            '--source-path', self.source_dir,
            '--destination-path', self.destination_dir,
            '--quarantine-path', self.quarantine_dir,
            '--hazard-archive-path', self.hazard_dir,
            '--on-demand-defender',  # Boolean flag, presence means True
            # No --on-demand-clam-av to avoid ClamAV errors
            '--skip-stability-check',  # Boolean flag, presence means True
            '--max-scan-threads', str(params.thread_count),  # Thread count from parameters
            '--log-path', throttle_logs_parent,  # Use the parent directory of throttle_logs
            '--lock-file', self.lock_file
        ]
        
        # Add throttle logs path if specified
        if params.daily_processing_tracker_logs_path:
            cmd.extend(['--daily-processing-tracker-logs-path', params.daily_processing_tracker_logs_path])
        else:
            cmd.extend(['--daily-processing-tracker-logs-path', self.logs_dir])
            
        return cmd
    
    def _add_throttling_params(self, cmd, params):
        """Add throttling parameters to the command"""
        # Add throttling parameters if throttling is enabled
        if params.setup_throttling:
            # Add throttle flag to enable throttling
            cmd.append('--throttle')
            
            # Add max files per day if specified
            if params.max_files_per_day and params.max_files_per_day > 0:
                cmd.extend(['--throttle-max-file-count-per-day', str(params.max_files_per_day)])
            
            # Add max volume per day if specified (in MB)
            if params.max_volume_per_day_mb and params.max_volume_per_day_mb > 0:
                cmd.extend(['--throttle-max-file-volume-per-day-mb', str(params.max_volume_per_day_mb)])
            
            # Add min free space if specified (in MB)
            if params.min_free_space_mb and params.min_free_space_mb > 0:
                cmd.extend(['--throttle-free-space-mb', str(params.min_free_space_mb)])
                
        return cmd
        
    def _add_mock_space_params(self, cmd, params):
        """Add disk space mocking parameters to the command"""
        # Check if any mock space parameter is set
        has_mock_default = (hasattr(params, 'mock_free_space_mb') and params.mock_free_space_mb and params.mock_free_space_mb > 0)

        has_mock_quarantine = hasattr(params, 'mock_free_space_quarantine_mb') and params.mock_free_space_quarantine_mb and params.mock_free_space_quarantine_mb > 0

        # If any mock space parameter is set, add path-specific parameters
        if has_mock_quarantine or has_mock_default:
            quarantine_value = params.mock_free_space_quarantine_mb if has_mock_quarantine else params.mock_free_space_mb
            cmd.extend(['--mock-free-space-quarantine-mb', str(quarantine_value)])
        
        has_mock_destination = hasattr(params, 'mock_free_space_destination_mb') and params.mock_free_space_destination_mb and params.mock_free_space_destination_mb > 0

        if has_mock_destination or has_mock_default:
            destination_value = params.mock_free_space_destination_mb if has_mock_destination else params.mock_free_space_mb
            cmd.extend(['--mock-free-space-destination-mb', str(destination_value)])

        has_mock_hazard = hasattr(params, 'mock_free_space_hazard_mb') and params.mock_free_space_hazard_mb and params.mock_free_space_hazard_mb > 0

        if has_mock_hazard or has_mock_default:
            hazard_value = params.mock_free_space_hazard_mb if has_mock_hazard else params.mock_free_space_mb
            cmd.extend(['--mock-free-space-hazard-mb', str(hazard_value)])
            
        return cmd
    
    def _run_shuttle_with_command(self, cmd, params):
        """Run Shuttle with the given command"""
        # Print the command for debugging
        print("\n----------------------------------------------------------------")
        print("Running simulator with command:")
        for i, arg in enumerate(cmd):
            if i == 0:
                # First item is the Python interpreter
                print(f"Python: {arg}")
            elif i == 1:
                # Second item is the script path
                print(f"Script: {arg}")
            else:
                # Other arguments
                if arg.startswith('--'):
                    # Start a new line for each flag
                    print(f"\n  {arg}", end='')
                else:
                    # Continue on same line for flag values
                    print(f" {arg}", end='')
        print("\n----------------------------------------------------------------\n")
        
        # Record start time
        start_time = time.time()
        
        # Run the command and stream output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Collect output while streaming it to console
        output_lines = []
        print("\n--- Shuttle Output Begin ---")
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            # Strip trailing whitespace but keep the newline at the end if it exists
            cleaned_line = line.rstrip('\n')
            print(cleaned_line)  # Print with proper line breaks
            output_lines.append(line)
        print("--- Shuttle Output End ---\n")
        
        # Close stdout and get return code
        process.stdout.close()
        return_code = process.wait()
        
        # Record end time
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Join all output for error reporting if needed
        output = ''.join(output_lines)
        
        # Check that the process ran successfully
        self.assertEqual(return_code, 0, 
                        f"Process failed with code {return_code}\nOutput: {output}")
        
        print(f"Processing completed in {elapsed_time:.2f} seconds")
        
        return {
            'output': output,
            'return_code': return_code,
            'elapsed_time': elapsed_time
        }
    def _verify_test_results(self, params, result):
        """Verify the results of a throttling test"""
        # Count files actually processed
        files_processed = len([f for f in os.listdir(self.destination_dir) if f.startswith('clean_file_')])
        
        print(f"Files processed: {files_processed}")
        
        # Check if throttling occurred
        # Look for any of the common throttling messages
        throttle_messages = [
            "THROTTLE REASON:",  # New standardized format
            "Throttling activated",
            "Daily throttling limit would be exceeded",
            "throttling limit would be exceeded",
            "File rejected due to throttling",
            "would exceed the daily limit",
            "Insufficient disk space",
            "Daily limit exceeded"
        ]
        throttled = any(msg in result['output'] for msg in throttle_messages)
        
        # Skip verification if expected outcomes are None (real defender case)
        if params.expected_throttled is None or params.expected_files_processed is None:
            print("\nSkipping verification of outcomes when using real defender")
            print(f"Test completed with {files_processed} files processed")
            print(f"Throttled: {throttled}, Reason: (verification skipped)")
            return
        
        # Verify that the expected number of files were processed
        self.assertEqual(files_processed, params.expected_files_processed, 
                         f"Expected {params.expected_files_processed} files to be processed, but got {files_processed}")
        
        # Verify throttling behavior
        if params.expected_throttled:
            self.assertTrue(throttled, "Expected throttling to occur, but it did not")
            
            # Check for specific throttle reason if provided
            if params.expected_throttle_reason:
                # Simply check for the exact string specified in the test
                self.assertIn(params.expected_throttle_reason, result['output'], 
                             f"Expected throttle reason '{params.expected_throttle_reason}' not found in output")
        else:
            self.assertFalse(throttled, "Expected no throttling, but throttling occurred")
    
    def test_space_throttling(self):
        """Test throttling based on available disk space"""
        params = TestParameters(
            # Test parameters
            thread_count=1,
            clean_file_count=20,
            malware_file_count=0,
            file_size_kb=mb_to_kb(1),     # 1MB files
            
            # Throttling parameters
            setup_throttling=True,
            max_files_per_day=0,       # No file count limit
            max_volume_per_day_mb=0,      # No volume limit
            min_free_space_mb=100,     # Require 1GB minimum free space (in MB)
            initial_files=0,
            initial_volume_mb=0,
            mock_free_space_mb=110,      
            daily_processing_tracker_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=10,  
            expected_throttle_reason="THROTTLE REASON: Insufficient disk space",
            description="Space throttling with insufficient disk space"
        )
        self.run_test_scenario(params)
    
    def test_daily_volume_limit(self):
        """Test throttling with daily volume limit"""
        params = TestParameters(
            # Test parameters
            thread_count=1,
            clean_file_count=10,      # Create 10 files (50MB total)
            malware_file_count=0,
            file_size_kb=5 * 1024,    # 5MB files
            
            # Throttling parameters
            setup_throttling=True,
            max_files_per_day=0,      # No file count limit
            max_volume_per_day_mb=50,    # Limit of 50MB/day
            min_free_space_mb=0,         # No space throttling
            initial_files=6,          # 6 files already processed
            initial_volume_mb=30,     # 30MB already processed
            mock_free_space_mb=20000,    # 20TB - plenty of space (testing volume limit, not space)
            daily_processing_tracker_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=4,  # Should process 4 files (20MB) before hitting 50MB limit
            expected_throttle_reason="THROTTLE REASON: Daily Limit Reached",
            description="Daily volume limit with existing log"
        )
        self.run_test_scenario(params)
    
    def test_throttling_disabled(self):
        """Test that throttling can be disabled"""
        # All parameters explicitly defined
        params = TestParameters(
            # Test parameters
            thread_count=1,
            clean_file_count=5,
            malware_file_count=0,
            file_size_kb=100,
            
            # Throttling parameters
            setup_throttling=False,  # Key difference: throttling disabled
            max_files_per_day=1,     # Would limit if throttling enabled
            max_volume_per_day_mb=2,    # Would limit if throttling enabled
            min_free_space_mb=1024,     # Would throttle if enabled (requires 1GB in MB)
            initial_files=100,       # Would trigger throttling if enabled
            initial_volume_mb=0,
            mock_free_space_mb=5,       # Low free space
            daily_processing_tracker_logs_path=None,
            
            # Expected outcomes
            expected_throttled=False,  # No throttling should occur
            expected_files_processed=5,  # All files should process
            expected_throttle_reason=None,
            description="Throttling disabled"
        )
        self.run_test_scenario(params)
        
    def test_daily_file_count_limit_with_existing_log(self):
        """Test throttling with daily file count limit and existing log"""
        # All parameters explicitly defined
        params = TestParameters(
            # Test parameters
            thread_count=1,
            clean_file_count=5,
            malware_file_count=0,
            file_size_kb=100,
            
            # Throttling parameters
            setup_throttling=True,
            max_files_per_day=10,
            max_volume_per_day_mb=50,
            min_free_space_mb=0,
            initial_files=7,      # Already processed 7 files
            initial_volume_mb=0,
            mock_free_space_mb=20000,  # 20TB - plenty of space
            daily_processing_tracker_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=3,  # Only 3 more files can be processed (10-7)
            expected_throttle_reason="THROTTLE REASON: Daily Limit Reached",
            description="Daily file count limit with existing log"
        )
        self.run_test_scenario(params)
        
    def test_daily_volume_limit_with_existing_log(self):
        """Test throttling with daily volume limit and existing log"""
        # All parameters explicitly defined
        params = TestParameters(
            # Test parameters
            thread_count=1,
            clean_file_count=10,       # Create 10 files (50MB total)
            malware_file_count=0,
            file_size_kb=5 * 1024,     # 5MB files
            
            # Throttling parameters
            setup_throttling=True,
            max_files_per_day=0,       # No file count limit
            max_volume_per_day_mb=50,     # Limit of 50MB/day
            min_free_space_mb=0,          # No space throttling
            initial_files=8,           # 8 files already processed
            initial_volume_mb=40,      # 40MB already processed
            mock_free_space_mb=20000,     # 20TB - plenty of space (testing volume limit, not space)
            daily_processing_tracker_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=2,  # Should process 2 files (10MB) before hitting 50MB limit
            expected_throttle_reason="THROTTLE REASON: Daily Limit Reached",
            description="Daily volume limit with existing log"
        )
        self.run_test_scenario(params)
        
    def test_daily_file_count_limit_no_existing_log(self):
        """Test throttling with daily file count limit without existing log"""
        # All parameters explicitly defined
        params = TestParameters(
            # Test parameters
            thread_count=1,
            clean_file_count=10,
            malware_file_count=0,
            file_size_kb=100,
            
            # Throttling parameters
            setup_throttling=True,
            max_files_per_day=2,
            max_volume_per_day_mb=1000,
            min_free_space_mb=0,
            initial_files=0,
            initial_volume_mb=0,
            mock_free_space_mb=20000,  # 20TB - plenty of space
            daily_processing_tracker_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=2,
            expected_throttle_reason="THROTTLE REASON: Daily Limit Reached",
            description="Daily file count limit without existing log"
        )
        self.run_test_scenario(params)
        
    def test_path_specific_mock_space(self):
        """Test path-specific mock space throttling"""
        # All parameters explicitly defined

        params = TestParameters(
            # Test parameters
            thread_count=1,
            clean_file_count=5,
            malware_file_count=0,
            file_size_kb=mb_to_kb(1),
            
            # Throttling parameters
            setup_throttling=True,
            max_files_per_day=0,
            max_volume_per_day_mb=0,
            min_free_space_mb=100,  
            initial_files=0,
            initial_volume_mb=0,
            # General mock space has plenty of space
            mock_free_space_mb=103,
            # But destination has limited space
            mock_free_space_quarantine_mb=5000,  # Plenty of space in quarantine
            mock_free_space_destination_mb=103,  # Limited space in destination 
            mock_free_space_hazard_mb=5000,    # Plenty of space in hazard archive
            daily_processing_tracker_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=3,  # Should process none due to destination space check
            expected_throttle_reason="THROTTLE REASON: Insufficient disk space",
            description="Path-specific insufficient disk space (destination)"
        )
        self.run_test_scenario(params)
        
    def run_configurable(self, args=None):
        """Configurable test entry point that uses command-line parameters"""
        # Create TestParameters from command line arguments
        params = TestParameters.from_command_line(args)
        
        # Display parameter summary
        params.display_summary()
        
        # Auto-calculate expected outcomes based on parameters
        params.calculate_expected_outcomes()
        
        # Set up test environment
        self.setUp()
        
        try:
            # Run the test with the configured parameters
            result = self.run_test_scenario(params)
            print("\nTest completed successfully!")
            return 0
        except Exception as e:
            print(f"\nTest failed with error: {e}")
            return 1
        finally:
            try:
                self.tearDown()
            except Exception as e:
                print(f"Error during test cleanup: {e}")
        

if __name__ == '__main__':
    # When run directly, execute the configurable test
    unittest.main()
