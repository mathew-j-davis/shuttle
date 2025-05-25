# Shuttle Throttling Integration Test Design

This document outlines the design for a comprehensive integration test for Shuttle's throttling functionality. The test will be based on the existing `test_shuttle_multithread.py` with minimal modifications to test:

1. Multi-threading capabilities
2. Disk space throttling
3. Daily file count limits (with and without existing throttle logs)
4. Daily volume limits (with and without existing throttle logs)

## Base Structure

We'll maintain the overall test structure from `test_shuttle_multithread.py` while adding:

- New command line parameters for throttling limits
- Methods to create/modify throttle log files
- Test methods for each throttling scenario
- Mocking for disk space checking

## Key Modifications

### 1. Additional Command Line Parameters

```python
# Add these to the existing parameters
parser.add_argument('--max-files', type=int, default=10, 
                   help='Daily file count limit (default: 10)')
parser.add_argument('--max-volume', type=int, default=50, 
                   help='Daily volume limit in MB (default: 50)')
parser.add_argument('--min-free-space', type=int, default=100, 
                   help='Minimum free disk space in MB (default: 100)')

# Parameters for initial values in throttle log
parser.add_argument('--initial-files', type=int, default=0, 
                   help='Initial daily file count in throttle log (default: 0)')
parser.add_argument('--initial-volume', type=float, default=0.0, 
                   help='Initial daily volume in MB in throttle log (default: 0.0)')

# Parameter for mocking disk space
parser.add_argument('--mock-free-space', type=float, default=0.0, 
                   help='Mock free space in MB for disk space checks (default: 0.0, disables mocking)')
```

### 2. Test Setup Modifications

```python
def setUp(self):
    # Existing setup code...
    
    # Add a logs directory
    self.logs_dir = os.path.join(self.temp_dir, 'logs')
    os.makedirs(self.logs_dir, exist_ok=True)
    
    # Create a mock notifier that we can inspect
    self.notifier = MagicMock(spec=Notifier)
    
    # Configure logging options
    self.logging_options = {
        'log_path': self.logs_dir,
    }
```

### 3. Helper Methods

```python
def create_throttle_log(self, files_processed=0, volume_processed_mb=0):
    """Create a throttle log file with specified initial values"""
    throttle_logs_dir = os.path.join(self.logs_dir, 'throttle_logs')
    os.makedirs(throttle_logs_dir, exist_ok=True)
    
    # Initialize ThrottleLogger and set daily totals
    throttle_logger = ThrottleLogger(log_path=throttle_logs_dir)
    throttle_logger.daily_totals = {
        'files_processed': files_processed,
        'volume_processed_mb': volume_processed_mb
    }
    throttle_logger.save_daily_totals()
    return throttle_logger

def run_shuttle_with_throttling(self, throttle=True, throttle_free_space=100, 
                               throttle_max_file_count_per_day=0, 
                               throttle_max_file_volume_per_day=0):
    """Run shuttle with specified throttling parameters"""
    cmd = [
        sys.executable, self.simulator_runner,
        '--source', self.source_dir,
        '--destination', self.destination_dir,
        '--quarantine', self.quarantine_dir,
        '--hazard', self.hazard_dir,
        '--threads', str(self.thread_count),
    ]
    
    # Add throttling parameters
    if throttle:
        cmd.append('--throttle')
        cmd.extend(['--throttle-free-space', str(throttle_free_space)])
        
        if throttle_max_file_count_per_day > 0:
            cmd.extend(['--throttle-max-file-count', str(throttle_max_file_count_per_day)])
            
        if throttle_max_file_volume_per_day > 0:
            cmd.extend(['--throttle-max-file-volume', str(throttle_max_file_volume_per_day)])
    
    # Add logging options
    cmd.extend(['--log-path', self.logs_dir])
    
    # Run the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result
```

## 4. Test Methods

### Space Throttling Test

```python
@patch('shuttle.throttler.Throttler.check_directory_space')
def test_space_throttling(self, mock_check_space):
    """Test throttling based on available disk space"""
    # Mock the disk space check to return insufficient space
    mock_check_space.return_value = False
    
    # Create test files
    self.create_test_files(clean_count=5)
    
    # Run shuttle with throttling enabled
    result = self.run_shuttle_with_throttling(
        throttle=True,
        throttle_free_space=100,
        throttle_max_file_count_per_day=0,  # No daily file limit
        throttle_max_file_volume_per_day=0  # No daily volume limit
    )
    
    # Verify throttling occurred
    self.assertIn("Disk Space Warning", result.stdout)
    self.assertEqual(len(os.listdir(self.destination_dir)), 0)
```

### Daily File Count Tests

```python
def test_daily_file_count_limit_with_existing_log(self):
    """Test throttling with daily file count limit and existing log"""
    # Create throttle log with some files already processed
    initial_files = 7
    self.create_throttle_log(files_processed=initial_files)
    
    # Create test files (enough to exceed limit when added to initial count)
    self.create_test_files(clean_count=5)
    
    # Run shuttle with daily file count limit
    result = self.run_shuttle_with_throttling(
        throttle=True,
        throttle_free_space=0,  # No space throttling
        throttle_max_file_count_per_day=10,  # Limit of 10 files/day
        throttle_max_file_volume_per_day=0  # No volume limit
    )
    
    # Verify throttling occurred after processing some files
    self.assertIn("Daily Limit", result.stdout)
    processed_count = len(os.listdir(self.destination_dir))
    self.assertEqual(processed_count, 3)  # Should process 3 files to reach limit of 10
```

```python
def test_daily_file_count_limit_no_existing_log(self):
    """Test throttling with daily file count limit without existing log"""
    # Create test files (more than the limit)
    self.create_test_files(clean_count=15)
    
    # Run shuttle with daily file count limit
    result = self.run_shuttle_with_throttling(
        throttle=True,
        throttle_free_space=0,  # No space throttling
        throttle_max_file_count_per_day=10,  # Limit of 10 files/day
        throttle_max_file_volume_per_day=0  # No volume limit
    )
    
    # Verify throttling occurred after processing some files
    self.assertIn("Daily Limit", result.stdout)
    processed_count = len(os.listdir(self.destination_dir))
    self.assertEqual(processed_count, 10)  # Should process 10 files before hitting limit
```

### Daily Volume Tests

```python
def test_daily_volume_limit_with_existing_log(self):
    """Test throttling with daily volume limit and existing log"""
    # Create throttle log with some volume already processed (30MB)
    self.create_throttle_log(files_processed=6, volume_processed_mb=30)
    
    # Create test files (each 5MB)
    file_size_mb = 5
    self.create_test_files(clean_count=10, file_size_mb=file_size_mb)
    
    # Run shuttle with daily volume limit
    result = self.run_shuttle_with_throttling(
        throttle=True,
        throttle_free_space=0,  # No space throttling
        throttle_max_file_count_per_day=0,  # No file count limit
        throttle_max_file_volume_per_day=50  # Limit of 50MB/day
    )
    
    # Verify throttling occurred after processing some files
    self.assertIn("Daily Limit", result.stdout)
    self.assertIn("volume limit", result.stdout)
    
    # Should process 4 files (20MB) before hitting limit (30MB + 20MB = 50MB)
    processed_count = len(os.listdir(self.destination_dir))
    self.assertEqual(processed_count, 4)
```

```python
def test_daily_volume_limit_no_existing_log(self):
    """Test throttling with daily volume limit without existing log"""
    # Create test files (each 5MB)
    file_size_mb = 5
    self.create_test_files(clean_count=15, file_size_mb=file_size_mb)
    
    # Run shuttle with daily volume limit
    result = self.run_shuttle_with_throttling(
        throttle=True,
        throttle_free_space=0,  # No space throttling
        throttle_max_file_count_per_day=0,  # No file count limit
        throttle_max_file_volume_per_day=50  # Limit of 50MB/day
    )
    
    # Verify throttling occurred after processing some files
    self.assertIn("Daily Limit", result.stdout)
    self.assertIn("volume limit", result.stdout)
    
    # Should process 10 files (50MB total) before hitting limit
    processed_count = len(os.listdir(self.destination_dir))
    self.assertEqual(processed_count, 10)
```

### Multi-threading with Throttling

```python
def test_multithreading_with_throttling(self):
    """Test multi-threaded processing with throttling"""
    # Set up a higher thread count
    original_thread_count = self.thread_count
    self.thread_count = 4
    
    # Create test files (each 2MB)
    file_size_mb = 2
    self.create_test_files(clean_count=20, file_size_mb=file_size_mb)
    
    # Run shuttle with volume limit that should allow exactly half the files
    start_time = time.time()
    result = self.run_shuttle_with_throttling(
        throttle=True,
        throttle_free_space=0,  # No space throttling
        throttle_max_file_count_per_day=0,  # No file count limit
        throttle_max_file_volume_per_day=20  # Limit of 20MB/day (should allow 10 files)
    )
    end_time = time.time()
    
    # Verify throttling occurred correctly
    self.assertIn("Daily Limit", result.stdout)
    processed_count = len(os.listdir(self.destination_dir))
    self.assertEqual(processed_count, 10)  # Should process 10 files (20MB total)
    
    # Reset thread count
    self.thread_count = original_thread_count
```

### Throttling Disabled Test

```python
@patch('shuttle.throttler.Throttler.check_directory_space')
def test_throttling_disabled(self, mock_check_space):
    """Test that throttling can be disabled"""
    # Mock disk space check to return insufficient space
    mock_check_space.return_value = False
    
    # Create throttle log with counts exceeding limits
    self.create_throttle_log(files_processed=100, volume_processed_mb=1000)
    
    # Create test files
    self.create_test_files(clean_count=5)
    
    # Run shuttle with throttling disabled
    result = self.run_shuttle_with_throttling(
        throttle=False,  # Throttling disabled
        throttle_free_space=100,
        throttle_max_file_count_per_day=10,
        throttle_max_file_volume_per_day=50
    )
    
    # Verify all files were processed despite throttling conditions
    self.assertEqual(len(os.listdir(self.destination_dir)), 5)
    self.assertNotIn("Disk Space Warning", result.stdout)
    self.assertNotIn("Daily Limit", result.stdout)
```

## Implementation Strategy

1. Create a new file `test_throttling_integration.py` based on `test_shuttle_multithread.py`
2. Add the log directory to the test setup
3. Modify the test runner to pass throttling parameters
4. Add helper methods for throttle logs 
5. Implement the test methods

For disk space mocking, we'll patch the `check_directory_space` method rather than modifying actual disk space.

The test will use the real shuttle codebase but with the MDATP simulator, ensuring we're testing the actual throttling implementation while controlling the test environment.
