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

The included debug configurations in `.vscode/launch.json` provide easy ways to run tests:

- **Debug test_shuttle_multithreaded**: Runs all tests in the file
- **Debug test_throttling_tests**: Runs only throttling-related tests
- **Debug test_space_throttling**: Runs only the space throttling test

## Examples for Triggering Different Throttling Scenarios

### Space Throttling

To trigger space throttling, set `mock_free_space` lower than the total size of the files to be processed:

```python
# In the test setup or by modifying the class attribute
self.mock_free_space = 5  # MB, very low space
self.file_size_kb = 1024  # 1MB files
self.clean_file_count = 10  # Will need 10MB total
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
