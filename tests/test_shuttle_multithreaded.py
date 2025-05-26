"""
Test Shuttle with simulator using multiple files to test multithreading and throttling



TEST PROCESS OVERVIEW:

TestShuttleMultithreading
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
        self.max_volume_per_day = kwargs.get('max_volume_per_day')
        self.min_free_space = kwargs.get('min_free_space')
        self.initial_files = kwargs.get('initial_files')
        self.initial_volume_mb = kwargs.get('initial_volume_mb')
        self.mock_free_space = kwargs.get('mock_free_space')
        self.throttle_logs_path = kwargs.get('throttle_logs_path')
        
        # Expected outcomes
        self.expected_throttled = kwargs.get('expected_throttled')
        self.expected_files_processed = kwargs.get('expected_files_processed')
        self.expected_throttle_reason = kwargs.get('expected_throttle_reason')
        self.description = kwargs.get('description')
        
        # Simulator settings
        self.use_simulator = kwargs.get('use_simulator')
    
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
            'max_volume_per_day': 2,
            'min_free_space': 1,
            'initial_files': 0,
            'initial_volume_mb': 0.0,
            'mock_free_space': 5,
            'throttle_logs_path': None,
            
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
    
    def calculate_expected_outcomes(self):
        """Calculate expected outcomes based on input parameters
        
        This method automatically determines:
        1. Whether throttling is expected to occur
        2. How many files should be processed
        3. What throttle reason message to expect
        
        You can call this after setting up parameters to have expectations calculated
        rather than explicitly specified.
        """
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
        remaining_volume = self.max_volume_per_day - self.initial_volume_mb if self.max_volume_per_day > 0 else float('inf')
        
        # Space throttling - first check if we'll run out of space
        if self.mock_free_space is not None and self.mock_free_space < self.min_free_space:
            self.expected_throttled = True
            # First file gets copied to quarantine, then space check fails
            self.expected_files_processed = min(2, total_file_count)
            self.expected_throttle_reason = "THROTTLE REASON: Insufficient disk space"
            return self
            
        # File count throttling
        if self.max_files_per_day > 0 and remaining_files < total_file_count:
            self.expected_throttled = True
            self.expected_files_processed = min(remaining_files, total_file_count)
            self.expected_throttle_reason = "THROTTLE REASON: Daily limit exceeded"
            return self
            
        # Volume throttling
        if self.max_volume_per_day > 0 and remaining_volume < total_volume_mb:
            # Calculate how many files we can process before hitting volume limit
            files_before_limit = int(remaining_volume / file_size_mb)
            self.expected_throttled = True
            self.expected_files_processed = min(files_before_limit, total_file_count)
            self.expected_throttle_reason = "THROTTLE REASON: Daily limit exceeded"
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
            f"  Mock free space: {self.mock_free_space} MB\n"
            f"  Daily limits: {self.max_files_per_day} files, {self.max_volume_per_day} MB\n"
            f"  Min free space: {self.min_free_space} MB\n"
            f"  Initial log values: {self.initial_files} files, {self.initial_volume_mb} MB\n"
        )


class TestShuttleMultithreading(unittest.TestCase):
    """Test case for Shuttle multithreading with simulator with throttling support"""
    
    # Flag to determine if all tests should run
    run_all_tests = True
    
    def test_throttling_scenario(self, params):
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
            if params.mock_free_space is not None and params.mock_free_space > 0:
                self._setup_disk_space_mocking(params.mock_free_space)
            
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
            if params.setup_throttling:
                result = self._run_shuttle_with_throttling(params)
            else:
                result = self._run_shuttle_no_throttling(params)
            
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
            
    def test_throttling_configurable(self):
        """Configurable test entry point that uses command-line arguments"""
        # Parse command-line arguments
        args = self._parse_arguments()
        
        # Create parameters from command line args with defaults for missing values
        params = TestParameters.with_defaults(**vars(args))
        
        # Auto-calculate expected outcomes based on the parameters
        # This means the user doesn't need to specify expected_throttled, expected_files_processed, etc.
        params.calculate_expected_outcomes()
        
        # Run the test with the configured parameters
        return self.test_throttling_scenario(params)
    
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

    def test_throttling_scenario(self, params):
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
        if params.setup_throttling:
            result = self._run_shuttle_with_throttling(params)
        else:
            result = self._run_shuttle_no_throttling(params)
        
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
            if params.max_volume_per_day > 0:
                remaining_volume_mb = params.max_volume_per_day - params.initial_volume_mb
                print(f"  Volume limit: {params.max_volume_per_day}MB (already processed: {params.initial_volume_mb}MB)")
                print(f"  Remaining volume allowed: {remaining_volume_mb:.2f}MB")
                
                if remaining_volume_mb <= 0:
                    print("  PREDICTION: Will throttle immediately due to volume limit")
                elif remaining_volume_mb < total_volume_mb:
                    files_before_volume_limit = int(remaining_volume_mb / (params.file_size_kb / 1024))
                    print(f"  PREDICTION: Will throttle after processing {files_before_volume_limit} files due to volume limit")
            
            # Print space throttling prediction
            if params.min_free_space > 0 and params.mock_free_space is not None:
                print(f"  Free space requirement: {params.min_free_space}GB (mocked available: {params.mock_free_space}GB)")
                
                if params.mock_free_space < params.min_free_space:
                    print("  PREDICTION: Will throttle immediately due to insufficient free space")
        else:
            print("  Throttling is disabled - all files should be processed")
        
    def _setup_test_environment(self, params):
        """Set up the test environment for a throttling test"""
        # Create throttle log if initial values are specified
        if params.initial_files > 0 or params.initial_volume_mb > 0:
            self._create_throttle_log(params.initial_files, params.initial_volume_mb)
        
        # Set up disk space mocking if specified
        if params.mock_free_space is not None and params.mock_free_space > 0:
            self._setup_disk_space_mocking(params.mock_free_space)
            
    def _create_throttle_log(self, files_processed=0, volume_processed_mb=0.0):
        """Create a throttle log file with specified initial values"""
        # Use the throttle_logs_path from the test parameters if set, otherwise use default logs directory
        throttle_logs_dir = self.logs_dir
            
        os.makedirs(throttle_logs_dir, exist_ok=True)
        
        # Initialize DailyProcessingTracker with the specified values
        throttle_logger = DailyProcessingTracker(data_directory=throttle_logs_dir)
        throttle_logger.initialize_with_values(files_processed, volume_processed_mb)
        
        print(f"Created throttle log with {files_processed} files and {volume_processed_mb}MB volume")
        return throttle_logger
    
    def _setup_disk_space_mocking(self, mock_free_space_mb):
        """Set up mocking for disk space checks
        
        Args:
            mock_free_space_mb: Free space to mock in MB
        """
        # Convert MB to bytes for the mock (if we were actually mocking)
        # mock_free_space_bytes = mock_free_space_mb * 1024 * 1024
        
        # Setup a patcher for the os.statvfs function used to check free space
        # This is a simplified approach - in a real test we'd use unittest.mock.patch
        # to replace the actual disk space check function
        print(f"Mocking available disk space as {mock_free_space_mb}MB")
        
        # In a real implementation, we would use something like:
        # patcher = patch('os.statvfs', return_value=Mock(f_bavail=..., f_frsize=...))
        # self.addCleanup(patcher.stop)
        # patcher.start()
    
    def _run_shuttle_with_throttling(self, params):
        """Test Shuttle with throttling enabled using TestParameters"""
        # Build the command with throttling parameters
        cmd = self._build_base_command(params)
        
        # Add throttling parameters
        cmd = self._add_throttling_params(cmd, params)
        
        # Run shuttle with the command
        return self._run_shuttle_with_command(cmd, params)
    
    def _run_shuttle_no_throttling(self, params):
        """Test Shuttle with throttling disabled using TestParameters"""
        # Build the command without throttling parameters
        cmd = self._build_base_command(params)
        
        # Run shuttle with the base command (no throttling parameters)
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
        if params.throttle_logs_path:
            cmd.extend(['--throttle-logs-path', params.throttle_logs_path])
        else:
            cmd.extend(['--throttle-logs-path', self.logs_dir])
            
        return cmd
    
    def _add_throttling_params(self, cmd, params):
        """Add throttling parameters to the command"""
        if params.setup_throttling:
            # Add throttle flag to enable throttling
            cmd.append('--throttle')
            
            # Add max files per day if specified
            if params.max_files_per_day and params.max_files_per_day > 0:
                cmd.extend(['--throttle-max-file-count-per-day', str(params.max_files_per_day)])
            
            # Add max volume per day if specified
            if params.max_volume_per_day and params.max_volume_per_day > 0:
                cmd.extend(['--throttle-max-file-volume-per-day', str(params.max_volume_per_day)])
            
            # Add min free space if specified (in MB)
            if params.min_free_space and params.min_free_space > 0:
                cmd.extend(['--throttle-free-space', str(params.min_free_space)])
        
        # Add mock free space if specified (in MB)
        if params.mock_free_space and params.mock_free_space > 0:
            # Use the mock_free_space value directly as MB
            cmd.extend(['--mock-free-space', str(params.mock_free_space)])
            
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
            clean_file_count=5,
            malware_file_count=0,
            file_size_kb=1024,     # 1MB files
            
            # Throttling parameters
            setup_throttling=True,
            max_files_per_day=0,       # No file count limit
            max_volume_per_day=0,      # No volume limit
            min_free_space=1,          # Require 1MB minimum free space
            initial_files=0,
            initial_volume_mb=0,
            mock_free_space=3.1,       # Mock 3.1 MB free space (below threshold)
            throttle_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=2,  # Two files get processed before throttling kicks in
            expected_throttle_reason="THROTTLE REASON: Insufficient disk space",
            description="Space throttling with insufficient disk space"
        )
        self.test_throttling_scenario(params)
    
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
            max_volume_per_day=50,    # Limit of 50MB/day
            min_free_space=0,         # No space throttling
            initial_files=6,          # 6 files already processed
            initial_volume_mb=30,     # 30MB already processed
            mock_free_space=20000,    # 20TB - plenty of space (testing volume limit, not space)
            throttle_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=4,  # Should process 4 files (20MB) before hitting 50MB limit
            expected_throttle_reason="THROTTLE REASON: Daily limit exceeded",
            description="Daily volume limit with existing log"
        )
        self.test_throttling_scenario(params)
    
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
            max_volume_per_day=2,    # Would limit if throttling enabled
            min_free_space=1000,     # Would throttle if enabled (requires 1GB)
            initial_files=100,       # Would trigger throttling if enabled
            initial_volume_mb=0,
            mock_free_space=5,       # Low free space
            throttle_logs_path=None,
            
            # Expected outcomes
            expected_throttled=False,  # No throttling should occur
            expected_files_processed=5,  # All files should process
            expected_throttle_reason=None,
            description="Throttling disabled"
        )
        self.test_throttling_scenario(params)
        
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
            max_volume_per_day=50,
            min_free_space=0,
            initial_files=7,      # Already processed 7 files
            initial_volume_mb=0,
            mock_free_space=20000,  # 20TB - plenty of space
            throttle_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=3,  # Only 3 more files can be processed (10-7)
            expected_throttle_reason="THROTTLE REASON: Daily limit exceeded",
            description="Daily file count limit with existing log"
        )
        self.test_throttling_scenario(params)
        
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
            max_volume_per_day=50,     # Limit of 50MB/day
            min_free_space=0,          # No space throttling
            initial_files=8,           # 8 files already processed
            initial_volume_mb=40,      # 40MB already processed
            mock_free_space=20000,     # 20TB - plenty of space (testing volume limit, not space)
            throttle_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=2,  # Should process 2 files (10MB) before hitting 50MB limit
            expected_throttle_reason="THROTTLE REASON: Daily limit exceeded",
            description="Daily volume limit with existing log"
        )
        self.test_throttling_scenario(params)
        
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
            max_volume_per_day=1000,
            min_free_space=0,
            initial_files=0,
            initial_volume_mb=0,
            mock_free_space=20000,  # 20TB - plenty of space
            throttle_logs_path=None,
            
            # Expected outcomes
            expected_throttled=True,
            expected_files_processed=2,
            expected_throttle_reason="THROTTLE REASON: Daily limit exceeded",
            description="Daily file count limit without existing log"
        )
        self.test_throttling_scenario(params)
        
    def test_throttling_configurable(self):
        """Configurable test entry point that uses command-line parameters"""
        # Parse command-line arguments
        args = self._parse_command_line_args()
        
        # Create TestParameters with command-line values, falling back to defaults where not specified
        params = TestParameters.with_defaults()
        
        # Override parameters with command-line values
        if args.thread_count is not None:
            params.thread_count = args.thread_count
        if args.clean_file_count is not None:
            params.clean_file_count = args.clean_file_count
        if args.malware_file_count is not None:
            params.malware_file_count = args.malware_file_count
        if args.file_size_kb is not None:
            params.file_size_kb = args.file_size_kb
        
        # Throttling parameters
        if args.max_files_per_day is not None:
            params.max_files_per_day = args.max_files_per_day
        if args.max_volume_per_day is not None:
            params.max_volume_per_day = args.max_volume_per_day
        if args.min_free_space is not None:
            params.min_free_space = args.min_free_space
        if args.initial_files is not None:
            params.initial_files = args.initial_files
        if args.initial_volume_mb is not None:
            params.initial_volume_mb = args.initial_volume_mb
        if args.mock_free_space is not None:
            params.mock_free_space = args.mock_free_space
        
        # Only set up throttling if at least one throttling parameter is non-zero
        params.setup_throttling = (params.max_files_per_day > 0 or 
                                 params.max_volume_per_day > 0 or 
                                 params.min_free_space > 0)
        
        # Set simulator mode based on command line flag
        params.use_simulator = not args.no_defender_simulator
        
        # If using real defender, print a warning about EICAR size limitation
        if not params.use_simulator and params.malware_file_count > 0:
            if params.file_size_kb > EICAR_MAX_SIZE_KB:
                print(f"\nNOTE: Using real Microsoft Defender with EICAR test files")
                print(f"Malware files will be limited to {EICAR_MAX_SIZE_KB}KB regardless of --file-size-kb setting")
        
        # Auto-calculate expected outcomes based on parameters
        params.calculate_expected_outcomes()
        
        # Run the test with the configured parameters
        return self.test_throttling_scenario(params)
    
    def _parse_command_line_args(self):
        """Parse command-line arguments for the configurable test"""
        parser = argparse.ArgumentParser(description="Configurable throttling test")
        
        # Test parameters
        parser.add_argument("--thread-count", type=int, help="Number of threads to use")
        parser.add_argument("--clean-file-count", type=int, help="Number of clean files to create")
        parser.add_argument("--malware-file-count", type=int, help="Number of malware files to create")
        parser.add_argument("--file-size-kb", type=int, help="Size of each file in KB")
        
        # Throttling parameters
        parser.add_argument("--max-files-per-day", type=int, help="Maximum number of files per day")
        parser.add_argument("--max-volume-per-day", type=int, help="Maximum volume per day in MB")
        parser.add_argument("--min-free-space", type=int, help="Minimum free space in GB")
        parser.add_argument("--initial-files", type=int, help="Initial files count in throttle log")
        parser.add_argument("--initial-volume-mb", type=float, help="Initial volume in MB in throttle log")
        parser.add_argument("--mock-free-space", type=float, help="Mock free space in GB")
        
        # Simulator parameters
        parser.add_argument("--no-defender-simulator", action="store_true", 
                          help="Use real Microsoft Defender instead of simulator (EICAR test files will be limited to 64KB)")
        
        return parser.parse_args()

if __name__ == '__main__':
    # When run directly, execute the configurable test
    unittest.main()
