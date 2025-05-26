# Shuttle Multithreaded Tests

This document describes how to run and configure the multithreaded tests for Shuttle, particularly focusing on throttling scenarios.

## Overview

The `test_shuttle_multithreaded.py` file contains tests that verify Shuttle's functionality in multithreaded environments with various throttling conditions:

- Space throttling (based on available disk space)
- Daily file count limits
- Daily volume limits

## Test Parameters

### Command-line Arguments

When running the test directly, you can use these command-line arguments:

```bash
python test_shuttle_multithreaded.py [OPTIONS]
```

### File Creation Parameters

| Parameter | Description | Default |
|-----------|-------------|----------|
| `--threads` | Number of threads to use for scanning | 1 |
| `--clean-files` | Number of clean files to create | 20 |
| `--malware-files` | Number of malware files to create | 10 |
| `--file-size` | Size of test files in KB | 100 |
| `--file-size-kb` | Size of test files in KB (same as `--file-size`) | 100 |
| `--file-size-mb` | Size of test files in MB (converted to KB automatically) | 0 |

### Throttling Parameters

| Parameter | Description | Default |
|-----------|-------------|----------|
| `--mock-free-space` | Simulated free disk space (MB) | 1000 |
| `--min-free-space` | Minimum free space required (MB) | 100 |
| `--max-files-per-day` | Maximum files to process per day | 10 |
| `--max-volume-per-day` | Maximum volume to process per day (MB) | 50 |
| `--initial-files` | Initial files count in throttle log | 0 |
| `--initial-volume` | Initial volume in throttle log (MB) | 0.0 |

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

## Running Specific Tests

### From Command Line

To run a specific test:

```bash
python -m unittest test_shuttle_multithreaded.TestShuttleMultithreading.test_space_throttling
```

### Using VSCode Debug Configurations

The included debug configurations in `.vscode/launch.json` provide easy ways to run tests. Here are the available throttling test configurations and their expected behavior:

#### Running All Tests

```json
{
    "name": "Debug test_shuttle_multithreaded",
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
    "args": []
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

##### Basic Volume Limit Test

```json
{
    "name": "Debug test_daily_volume_limit",
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
    "args": ["-k", "test_daily_volume_limit"]
}
```

**Expected Behavior**: The test creates a log with 30MB already processed, creates larger files (5MB each), and verifies that only 4 more files (20MB) are processed before hitting the 50MB limit.

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
