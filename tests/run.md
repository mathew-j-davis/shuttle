# Running Shuttle Tests

This guide explains how to run the shuttle test suite in various ways.

## Prerequisites

1. Activate the virtual environment:
   ```bash
   source ./scripts/1_deployment/05_source_activate_venv.sh
   ```

2. Ensure all modules are installed in development mode:
   ```bash
   ./scripts/1_deployment/08_install_shared.sh -e
   ./scripts/1_deployment/09_install_defender_test.sh -e
   ./scripts/1_deployment/10_install_shuttle.sh -e
   ```

## Running All Tests

### Using the Test Runner Script
The simplest way to run all tests:
```bash
python tests/run_tests.py
```

### Using unittest Discovery
Run all tests using Python's unittest discovery:
```bash
python -m unittest discover tests
```

## Running Test Groups

### By Module
Run all tests in a specific test module:
```bash
# Daily Processing Tracker tests
python -m unittest tests.test_daily_processing_tracker

# Notifier tests
python -m unittest tests.test_notifier

# Shuttle main tests
python -m unittest tests.test_shuttle

# MDATP Simulator tests
python -m unittest tests.test_mdatp_simulator

# Hierarchy logging tests
python -m unittest tests.test_hierarchy_logging_integration

# Shuttle with validator tests
python -m unittest tests.test_shuttle_with_validator
```

### By Test Class
Run all tests in a specific class:
```bash
python -m unittest tests.test_daily_processing_tracker.TestDailyProcessingTracker
python -m unittest tests.test_notifier.TestNotifier
python -m unittest tests.test_shuttle.TestShuttle
```

## Running Individual Tests

### Using Full Test Path
Run a specific test method:
```bash
# Format: python -m unittest module.class.method
python -m unittest tests.test_daily_processing_tracker.TestDailyProcessingTracker.test_initialization
python -m unittest tests.test_daily_processing_tracker.TestDailyProcessingTracker.test_add_pending_file
python -m unittest tests.test_notifier.TestNotifier.test_init
python -m unittest tests.test_shuttle.TestShuttle.test_space_throttling
```

### Using the -k Parameter (Pattern Matching)
Run tests matching a pattern:
```bash
# Run all tests with "throttle" in the name
python -m unittest discover tests -k throttle

# Run all tests with "daily" in the name
python -m unittest discover tests -k daily

# Run all tests with "notification" in the name
python -m unittest discover tests -k notification

# Run specific test by partial name
python -m unittest discover tests -k test_add_pending_file
```

## Using the Configurable Test Script

The `run_configurable_shuttle_test.py` script allows you to run shuttle tests with custom parameters.

### Basic Usage
```bash
python tests/run_configurable_shuttle_test.py
```

### With Custom Parameters

#### Thread Count and File Parameters
```bash
# Run with 4 threads, 20 clean files, 5 malware files
python tests/run_configurable_shuttle_test.py \
    --thread-count 4 \
    --clean-file-count 20 \
    --malware-file-count 5 \
    --file-size-kb 1024
```

#### Throttling Parameters
```bash
# Test with daily limits
python tests/run_configurable_shuttle_test.py \
    --thread-count 2 \
    --clean-file-count 50 \
    --max-files-per-day 30 \
    --max-volume-per-day-mb 100 \
    --min-free-space-mb 500
```

#### Mock Disk Space
```bash
# Test with limited disk space
python tests/run_configurable_shuttle_test.py \
    --clean-file-count 10 \
    --file-size-mb 10 \
    --mock-free-space-mb 50 \
    --min-free-space-mb 100
```

#### Path-Specific Mock Space
```bash
# Test with different space limits for different paths
python tests/run_configurable_shuttle_test.py \
    --clean-file-count 10 \
    --malware-file-count 5 \
    --mock-free-space-quarantine-mb 1000 \
    --mock-free-space-destination-mb 50 \
    --mock-free-space-hazard-mb 100
```

#### Using Real Defender (No Simulator)
```bash
# Use real Microsoft Defender instead of simulator
python tests/run_configurable_shuttle_test.py \
    --no-defender-simulator \
    --clean-file-count 5 \
    --malware-file-count 2
```

### All Available Parameters

```bash
python tests/run_configurable_shuttle_test.py --help
```

Key parameters:
- `--thread-count`: Number of processing threads (default: 1)
- `--clean-file-count`: Number of clean test files (default: 5)
- `--malware-file-count`: Number of malware test files (default: 0)
- `--file-size-kb`: Size of each file in KB
- `--file-size-mb`: Size of each file in MB (alternative to --file-size-kb)
- `--max-files-per-day`: Daily file count limit (0 = no limit)
- `--max-volume-per-day-mb`: Daily volume limit in MB (0 = no limit)
- `--min-free-space-mb`: Minimum free space requirement in MB
- `--initial-files`: Pre-existing file count in daily log
- `--initial-volume-mb`: Pre-existing volume in daily log
- `--mock-free-space-mb`: Mock available disk space (general)
- `--mock-free-space-quarantine-mb`: Mock space for quarantine path
- `--mock-free-space-destination-mb`: Mock space for destination path
- `--mock-free-space-hazard-mb`: Mock space for hazard archive path
- `--no-defender-simulator`: Use real Defender instead of simulator

## Running Tests with Specific Log Levels

For more verbose output during tests:
```bash
# Set DEBUG level for detailed logs
PYTHONPATH=. python -m unittest tests.test_daily_processing_tracker -v

# Run with verbose unittest output
python -m unittest discover tests -v
```

## Test Output

Tests will output:
- `.` for each successful test
- `F` for failed tests
- `E` for tests with errors
- `s` for skipped tests

At the end, you'll see a summary:
```
----------------------------------------------------------------------
Ran 25 tests in 45.123s

OK
```

Or if there are failures:
```
FAILED (failures=2, errors=1)
```

## Tips

1. **Run specific throttling scenarios**:
   ```bash
   python -m unittest tests.test_shuttle.TestShuttle.test_space_throttling
   python -m unittest tests.test_shuttle.TestShuttle.test_daily_volume_limit
   ```

2. **Test with different file sizes**:
   ```bash
   # Small files (100KB each)
   python tests/run_configurable_shuttle_test.py --file-size-kb 100
   
   # Large files (100MB each)
   python tests/run_configurable_shuttle_test.py --file-size-mb 100
   ```

3. **Simulate production scenarios**:
   ```bash
   # High volume with throttling
   python tests/run_configurable_shuttle_test.py \
       --thread-count 8 \
       --clean-file-count 1000 \
       --file-size-mb 5 \
       --max-volume-per-day-mb 10000 \
       --min-free-space-mb 5000
   ```

## Configuring VSCode for Test Debugging

### Setting up launch.json

Create or update `.vscode/launch.json` in your project root:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Current Test File",
            "type": "python",
            "request": "launch",
            "module": "unittest",
            "args": [
                "${file}"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Specific Test Method",
            "type": "python",
            "request": "launch",
            "module": "unittest",
            "args": [
                "${fileBasenameNoExtension}.TestClassName.test_method_name"
            ],
            "console": "integratedTerminal",
            "justMyCode": false,
            "cwd": "${workspaceFolder}/tests"
        },
        {
            "name": "Debug All Tests",
            "type": "python",
            "request": "launch",
            "module": "unittest",
            "args": [
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Configurable Test",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/tests/run_configurable_shuttle_test.py",
            "args": [
                "--thread-count", "2",
                "--clean-file-count", "10",
                "--file-size-mb", "5"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Test with Pattern",
            "type": "python",
            "request": "launch",
            "module": "unittest",
            "args": [
                "discover",
                "-s",
                "tests",
                "-k",
                "${input:testPattern}"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Shuttle with Simulator",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/tests/run_shuttle_with_simulator.py",
            "args": [
                "--source-path", "${workspaceFolder}/test_data/source",
                "--destination-path", "${workspaceFolder}/test_data/destination",
                "--quarantine-path", "${workspaceFolder}/test_data/quarantine",
                "--mock-free-space-mb", "100"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ],
    "inputs": [
        {
            "id": "testPattern",
            "type": "promptString",
            "description": "Enter test pattern (e.g., 'throttle', 'daily', 'notification')"
        }
    ]
}
```

### Using the Debug Configurations

1. **Debug Current Test File**: 
   - Open any test file (e.g., `test_daily_processing_tracker.py`)
   - Set breakpoints where needed
   - Select "Debug Current Test File" from the Run and Debug dropdown
   - Press F5 or click the green play button

2. **Debug Specific Test Method**:
   - Edit the configuration to specify the exact test
   - Example: Change args to `["test_daily_processing_tracker.TestDailyProcessingTracker.test_add_pending_file"]`
   - Set breakpoints in the test method or the code it calls
   - Run the configuration

3. **Debug with Custom Parameters**:
   - Use the "Debug Configurable Test" configuration
   - Modify the args array to test different scenarios
   - Great for debugging throttling or threading issues

### Tips for VSCode Debugging

1. **Set Python Path**: Ensure VSCode is using the correct Python interpreter:
   - Cmd/Ctrl + Shift + P → "Python: Select Interpreter"
   - Choose the virtual environment from the shuttle project

2. **Breakpoint Features**:
   - Conditional breakpoints: Right-click on a breakpoint → "Edit Breakpoint" → Add condition
   - Logpoints: Right-click in gutter → "Add Logpoint" → Enter message to log without stopping

3. **Debug Console**: Use the Debug Console to evaluate expressions while paused:
   ```python
   # While debugging, you can type:
   self.tracker.pending_files
   locals()
   import pprint; pprint.pprint(self.file_records)
   ```

## Using run_shuttle_with_simulator.py

The `run_shuttle_with_simulator.py` script allows you to run shuttle with a malware detector simulator and optional disk space mocking.

### Basic Usage

```bash
python tests/run_shuttle_with_simulator.py [shuttle arguments] [simulator arguments]
```

### Key Features

1. **MDATP Simulator**: By default, uses a simulator instead of real Microsoft Defender
2. **Disk Space Mocking**: Can simulate low disk space conditions
3. **Path-Specific Mocking**: Can set different space limits for different paths
4. **Pass-Through Arguments**: All shuttle arguments are passed through

### Examples

#### Basic Run with Simulator
```bash
python tests/run_shuttle_with_simulator.py \
    --source-path /path/to/source \
    --destination-path /path/to/destination \
    --quarantine-path /path/to/quarantine
```

#### With Mock Disk Space
```bash
# Simulate 100MB free space everywhere
python tests/run_shuttle_with_simulator.py \
    --source-path /path/to/source \
    --destination-path /path/to/destination \
    --mock-free-space-mb 100
```

#### Path-Specific Mock Space
```bash
# Different space limits for different paths
python tests/run_shuttle_with_simulator.py \
    --source-path /path/to/source \
    --destination-path /path/to/destination \
    --mock-free-space-quarantine-mb 1000 \
    --mock-free-space-destination-mb 50 \
    --mock-free-space-hazard-mb 200
```

#### Use Real Microsoft Defender
```bash
# Bypass simulator and use real Defender
python tests/run_shuttle_with_simulator.py \
    --source-path /path/to/source \
    --destination-path /path/to/destination \
    --no-defender-simulator
```

#### With Throttling Parameters
```bash
python tests/run_shuttle_with_simulator.py \
    --source-path /path/to/source \
    --destination-path /path/to/destination \
    --throttle \
    --throttle-max-file-count-per-day 100 \
    --throttle-max-file-volume-per-day-mb 1000 \
    --throttle-free-space-mb 500 \
    --mock-free-space-mb 400
```

### Simulator-Specific Arguments

- `--mock-free-space-mb <MB>`: General mock free space (applies to all paths unless overridden)
- `--mock-free-space-quarantine-mb <MB>`: Mock space for quarantine path only
- `--mock-free-space-destination-mb <MB>`: Mock space for destination path only
- `--mock-free-space-hazard-mb <MB>`: Mock space for hazard archive path only
- `--no-defender-simulator`: Use real Microsoft Defender instead of simulator

### How It Works

1. **Defender Simulation**: 
   - Patches the defender command to use a Python simulator
   - Simulator identifies files containing "malware" as threats
   - Automatically uses a pre-approved ledger for version 0.0.0.0

2. **Disk Space Mocking**:
   - Patches the `Throttler.get_free_space_mb` method
   - Returns mock values for specified paths
   - Falls back to real disk space for unmocked paths

3. **Argument Handling**:
   - Extracts simulator-specific arguments
   - Passes remaining arguments to shuttle's main function
   - Automatically adds required flags like `--skip-stability-check`

### Integration with Tests

The configurable test script uses this simulator internally:
```bash
# This test script calls run_shuttle_with_simulator.py
python tests/run_configurable_shuttle_test.py \
    --thread-count 4 \
    --clean-file-count 20 \
    --mock-free-space-mb 100
```

## Troubleshooting

1. **Import Errors**: Ensure you've activated the virtual environment and installed all modules
2. **Permission Errors**: Some tests create temporary files; ensure you have write permissions
3. **Defender Tests**: The simulator tests don't require Microsoft Defender, but `--no-defender-simulator` does
4. **Disk Space**: Some tests mock disk space; ensure you have enough real space for test files
5. **VSCode Debugging**: If breakpoints aren't hit, check that "justMyCode" is set to false
6. **Simulator Issues**: The simulator script must be executable; the runner handles this automatically