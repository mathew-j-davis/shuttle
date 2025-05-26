# Shuttle Multithreaded Tests

This document describes how to run and configure the multithreaded tests for Shuttle, particularly focusing on throttling scenarios.

## Overview

The `test_shuttle_multithreaded.py` file contains tests that verify Shuttle's functionality in multithreaded environments with various throttling conditions:

- Space throttling (based on available disk space)
- Daily file count limits (with and without existing log)
- Daily volume limits (with and without existing log)
- Tests with throttling disabled

## Test Structure

The test suite uses a unified approach with the `TestParameters` class to encapsulate all test parameters:

1. **TestParameters class**: A centralized way to define all test parameters
2. **test_throttling_scenario**: The core test method that all tests use
3. **Individual test methods**: Each defines its specific parameters and calls `test_throttling_scenario`
4. **test_throttling_configurable**: A special test that uses command-line arguments

## Test Parameters

### TestParameters Class

All tests use the `TestParameters` class to encapsulate test parameters:

```python
params = TestParameters(
    # Test parameters
    thread_count=1,
    clean_file_count=5,
    malware_file_count=0,
    file_size_kb=1024,     # 1MB files
    
    # Throttling parameters
    setup_throttling=True,
    max_files_per_day=10,       # File count limit
    max_volume_per_day=50,      # Volume limit in MB
    min_free_space=1024,        # Minimum free space in MB
    initial_files=0,            # Initial files in throttle log
    initial_volume_mb=0,        # Initial volume in throttle log
    mock_free_space=5000,       # Mock free space in MB
    
    # Expected outcomes
    expected_throttled=True,    # Whether throttling should occur
    expected_files_processed=5, # How many files should be processed
    expected_throttle_reason="THROTTLE REASON: Insufficient disk space",
    description="Test description"
)
```

### Command-line Arguments

When running the configurable test directly, you can use these command-line arguments:

```bash
python test_shuttle_multithreaded.py [OPTIONS]
```

### Available Parameters

| Parameter | Description | Default |
|-----------|-------------|----------|
| `--thread-count` | Number of threads to use for scanning | 1 |
| `--clean-file-count` | Number of clean files to create | 5 |
| `--malware-file-count` | Number of malware files to create | 0 |
| `--file-size-kb` | Size of test files in KB | 100 |
| `--max-files-per-day` | Maximum files to process per day | 10 |
| `--max-volume-per-day` | Maximum volume to process per day (MB) | 2 |
| `--min-free-space` | Minimum free space required (MB) | 1 |
| `--initial-files` | Initial files count in throttle log | 0 |
| `--initial-volume-mb` | Initial volume in throttle log (MB) | 0.0 |
| `--mock-free-space` | Simulated free disk space (MB) | 5 |
| `--no-defender-simulator` | Use real Microsoft Defender instead of simulator | false |

### Class Attributes

For more fine-grained control when running individual tests or through a debugger, you can modify these class attributes:

| Attribute | Description | Default |
|-----------|-------------|---------|
| `thread_count` | Number of threads for multithreading | 1 |
| `clean_file_count` | Number of clean test files | 20 |
| `malware_file_count` | Number of malware test files | 10 |
| `file_size_kb` | Size of each test file in KB | 100 |
| `run_all_tests` | Flag to run all tests | True |

### Throttling Parameters

For throttling tests, you can modify these attributes:

| Attribute | Description | Default |
|-----------|-------------|---------|
| `max_files_per_day` | Maximum files to process per day | 10 |
| `max_volume_per_day` | Maximum volume to process per day (MB) | 50 |
| `min_free_space` | Minimum free space required (MB) | 100 |
| `initial_files` | Initial files count in throttle log | 0 |
| `initial_volume` | Initial volume in throttle log (MB) | 0.0 |
| `mock_free_space` | Simulated free disk space (MB) | 1000 |

## Auto-Calculation of Expected Outcomes

The configurable test automatically calculates expected outcomes based on input parameters. This means you don't need to specify expected results when running it via command line.

### How Auto-Calculation Works

The `calculate_expected_outcomes()` method in `TestParameters` determines:

1. Whether throttling should occur
2. How many files should be processed
3. What throttle reason message to expect

```python
# Example of creating parameters with auto-calculated outcomes
params = TestParameters(
    clean_file_count=5,
    max_files_per_day=10,
    initial_files=7,  # Already processed 7 files
    # No need to specify expected outcomes!
).calculate_expected_outcomes()

# Now params.expected_files_processed will be 3
# params.expected_throttled will be True
# params.expected_throttle_reason will be set appropriately
```

The configurable test (`test_throttling_configurable`) automatically uses this feature.

## Running Specific Tests

### From Command Line

To run a specific test:

```bash
python -m unittest test_shuttle_multithreaded.TestShuttleMultithreading.test_space_throttling
```

To run the configurable test with command-line arguments:

```bash
python tests/test_shuttle_multithreaded.py --clean-file-count 5 --max-files-per-day 10 --initial-files 7
```

### Using VSCode Debug Configurations

The included debug configurations in `.vscode/launch.json` provide easy ways to run tests:

### Available Debug Configurations

All debug configurations follow this basic template, with different test methods:

```json
{
    "name": "Debug test_space_throttling",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_space_throttling"]
}
```

### Available Test Methods

The test suite includes several test methods for different throttling scenarios:

1. **test_space_throttling**: Tests throttling based on insufficient disk space
2. **test_daily_volume_limit**: Tests throttling based on daily volume limit
3. **test_daily_volume_limit_with_existing_log**: Tests volume limit with existing log
4. **test_daily_file_count_limit_no_existing_log**: Tests file count limit without log
5. **test_daily_file_count_limit_with_existing_log**: Tests file count limit with log
6. **test_throttling_disabled**: Tests with throttling disabled
7. **test_throttling_configurable**: Configurable test with command-line args
}
```

This runs all tests in the test_shuttle_multithreaded.py file using default parameters.

#### Running Specific Types of Throttle Tests

Instead of trying to run all throttle tests at once (which can be problematic with command-line escaping), we have separate configurations for each type of throttling test:

##### Running Daily File Count Tests

```json
{
    "name": "Run Daily File Count Tests",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_daily_file_count"]
}
```

This runs all daily file count limit tests.

##### Running Daily Volume Tests

```json
{
    "name": "Run Daily Volume Tests",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_daily_volume"]
}
```

This runs all daily volume limit tests.

##### Running Space Throttling Tests

```json
{
    "name": "Run Space Throttling Tests",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_space_throttling"]
}
```

This runs space-based throttling tests.

##### Running General Throttling Tests

```json
{
    "name": "Run Throttling Tests",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_throttling"]
}
```

This runs general throttling-related tests (like `test_throttling_disabled`).

#### Daily File Count Limit Tests

##### With Existing Log

```json
{
    "name": "Debug test_daily_file_count_limit_with_existing_log",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": [
        "-k", "test_daily_file_count_limit_with_existing_log",
        "--initial-files", "7",
        "--max-files-per-day", "10",
        "--clean-files", "5"
    ]
}
```

**Expected Behavior**: The test creates a log with 7 files already processed, creates 5 new files, and verifies that only 3 files are processed before hitting the daily limit of 10 files.

##### Without Existing Log

```json
{
    "name": "Debug test_daily_file_count_limit_no_existing_log",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_daily_file_count_limit_no_existing_log"]
}
```

**Expected Behavior**: The test creates 15 files, sets a daily limit of 10 files, and verifies that exactly 10 files are processed before hitting the limit.

#### Daily Volume Limit Tests

##### With Existing Log

```json
{
    "name": "Debug test_daily_volume_limit_with_existing_log",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_daily_volume_limit_with_existing_log"]
}
```

**Expected Behavior**: The test creates a log with 30MB already processed, creates 10 files of 5MB each, and verifies that only 4 files (20MB) are processed before hitting the 50MB daily volume limit.

### Configuring a Custom Launch for the Configurable Test

To create a custom launch configuration for the configurable test with specific parameters:

```json
{
    "name": "Custom Throttling Test",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": [
        "-k", "test_throttling_configurable",
        "--clean-file-count", "5",
        "--max-files-per-day", "10",
        "--initial-files", "7"
    ]
}
```

## Standardized Throttle Messages

All throttle messages now follow a standardized format for easier testing:

- Space throttling: `THROTTLE REASON: Insufficient disk space in required directories`
- File limit: `THROTTLE REASON: Daily limit exceeded - Daily file count limit (X) would be exceeded with Y files`
- Volume limit: `THROTTLE REASON: Daily limit exceeded - Daily volume limit (X MB) would be exceeded with Y MB`

## Testing with Real Microsoft Defender

By default, tests use the Microsoft Defender simulator, which detects files containing the word "malware" in their content. However, you can now run tests with real Microsoft Defender by using the `--no-defender-simulator` flag.

### EICAR Test Files

When using real Microsoft Defender, the test suite automatically creates EICAR test files instead of the simulator-compatible files. The [EICAR test string](https://en.wikipedia.org/wiki/EICAR_test_file) is a standard test file used to verify antivirus detection without using real malware.

### File Size Limitations

When using real Microsoft Defender with EICAR test files, there are some important limitations to be aware of:

- EICAR test files must be small (< 64KB) to be reliably detected by most antivirus software
- If you specify a larger file size with `--file-size-kb`, the test will automatically limit malware files to 64KB
- You'll see a warning message when this size limitation is applied

### Example Usage

```bash
# Run tests with real Microsoft Defender
python tests/test_shuttle_multithreaded.py --no-defender-simulator

# Run a specific test with real Microsoft Defender
python -m unittest test_shuttle_multithreaded.TestShuttleMultithreading.test_space_throttling --no-defender-simulator

# Run a configurable test with real Microsoft Defender
python tests/test_shuttle_multithreaded.py --no-defender-simulator --clean-file-count 5 --malware-file-count 2
```

### Running Shuttle with Real Defender

You can also use the `run_shuttle_with_simulator.py` script with real Defender:

```bash
python tests/run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/dest --no-defender-simulator
```

## Summary

With these tests you can thoroughly test Shuttle's throttling capabilities in a variety of scenarios. The tests are now more maintainable, explicitly define their parameters, and provide a configurable test entry point for custom testing with both simulated and real scanning options.

#### Space Throttling Test

```json
{
    "name": "Debug test_space_throttling",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/test_shuttle_multithreaded.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_WORK_DIR": "${workspaceFolder}/work"
    },
    "args": ["-k", "test_space_throttling",
            "--min-free-space", "1",
            "--mock-free-space", "3",
            "--file-size-mb", "1",
            "--clean-files", "10",
            "--malware-files", "0",
            "--threads", "1"
            ]
}
```

**Expected Behavior**: The test creates 10 files of 1MB each with only 3MB of free space and a 1MB minimum free space requirement. It verifies that space throttling kicks in after processing 2 files (leaving 1MB free).

## Examples for Triggering Different Throttling Scenarios

### Space Throttling

To trigger space throttling, set `mock_free_space` lower than the total size of the files to be processed plus the required minimum free space:

```python
# In the test setup or by modifying the class attribute
self.mock_free_space = 5  # MB, very low space
self.min_free_space = 1   # Keep at least 1MB free
self.file_size_kb = 1024  # 1MB files
self.clean_file_count = 10  # Will need 10MB total, but only 4 will process
```

### Daily File Count Limit

To trigger the daily file count limit:

```python
# Set the limit lower than the number of files to process
self.max_files_per_day = 5
self.clean_file_count = 20  # More than the limit
```

### Daily Volume Limit

To trigger the daily volume limit:

```python
# Set a low volume limit
self.max_volume_per_day = 10  # MB
self.file_size_kb = 1024  # 1MB files
self.clean_file_count = 20  # Will need 20MB total
```

### Pre-existing Log Data

To simulate a scenario where files have already been processed:

```python
# Create initial log with existing processed files/volume
self.create_throttle_log(files_processed=7, volume_processed_mb=30)
```

## Test Environment

The tests automatically set up:
- Temporary directories for source, destination, quarantine, and hazard
- Mock disk space monitoring
- Throttle log files as needed

## Notes

- The dynamic space checking calculates remaining space based on files already processed
- Tests use a simulated Microsoft Defender for endpoint scanning
- Each test automatically cleans up temporary files and directories
