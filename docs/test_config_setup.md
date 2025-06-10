# Test Configuration Setup

## Problem Statement

The shuttle tests are failing because boolean command-line flags cannot explicitly set values to `false`. When a flag is omitted, the system falls back to the config file values, which may not match test expectations. This causes tests like `test_throttling_disabled` to fail because throttling might be enabled in the user's config file.

## Solution

Introduce a test-specific configuration file with all boolean flags set to `false` by default, allowing tests to explicitly enable only the features they need.

## Implementation Steps

### 1. Add New Environment Variable

Add to `.env`:
```bash
SHUTTLE_TEST_CONFIG_PATH=/home/mathew/shuttle/test_area/config.conf
```

### 2. Create Test Configuration File

Create `/home/mathew/shuttle/test_area/config.conf` with all boolean flags set to false:

```ini
[general]
# All boolean flags default to false for testing
test_source_write_access = false
delete_source_files_after_copying = false
on_demand_defender = false
on_demand_clam_av = false
throttle = false
skip_stability_check = false
defender_handles_suspect_files = false
notify = false
notify_summary = false

# Required paths - tests will override these
source_path = /tmp/test_source
destination_path = /tmp/test_destination
quarantine_path = /tmp/test_quarantine

# Other settings with safe defaults
max_scan_threads = 1
log_level = INFO

[notifications]
# Notification settings disabled by default
use_tls = false

[throttling]
# Throttling disabled by default
free_space_mb = 0
max_file_count_per_day = 0
max_file_volume_per_day_mb = 0
```

### 3. Update Test Runner Scripts

Modify test runner scripts to use `SHUTTLE_TEST_CONFIG_PATH` when set:

#### a. Update `run_shuttle_with_simulator.py`

Add after argument parsing:
```python
# Use test config if available
test_config_path = os.environ.get('SHUTTLE_TEST_CONFIG_PATH')
if test_config_path and os.path.exists(test_config_path):
    # Ensure test config is used
    if '--config-file' not in sys.argv:
        sys.argv.extend(['--config-file', test_config_path])
```

#### b. Update `run_tests.py`

Add environment setup:
```python
# Set test config path if not already set
if 'SHUTTLE_TEST_CONFIG_PATH' not in os.environ:
    test_config_path = os.path.join(
        os.environ.get('SHUTTLE_TEST_WORK_DIR', '/tmp'),
        'config.conf'
    )
    os.environ['SHUTTLE_TEST_CONFIG_PATH'] = test_config_path
```

### 4. Update VSCode Launch Configuration

The launch configuration should already include the environment variable:

```json
{
    "name": "Debug Tests",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/tests/run_tests.py",
    "console": "integratedTerminal",
    "justMyCode": false,
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}/src/shared_library:${workspaceFolder}/src/shuttle_app:${workspaceFolder}/tests/mdatp_simulator_app:${env:PYTHONPATH}",
        "SHUTTLE_CONFIG_PATH": "${workspaceFolder}/config/config.conf",
        "SHUTTLE_TEST_CONFIG_PATH": "${workspaceFolder}/test_area/config.conf",
        "SHUTTLE_VENV_PATH": "${workspaceFolder}/.venv",
        "SHUTTLE_TEST_WORK_DIR": "${workspaceFolder}/test_area/"
    },
    "args": []
}
```

### 5. Test Setup Script

Create a script to generate the test config file:

```bash
#!/bin/bash
# scripts/setup_test_config.sh

TEST_CONFIG_DIR="${SHUTTLE_TEST_WORK_DIR:-/home/mathew/shuttle/test_area}"
TEST_CONFIG_PATH="${TEST_CONFIG_DIR}/config.conf"

# Create test area directory if it doesn't exist
mkdir -p "${TEST_CONFIG_DIR}"

# Generate test config file
cat > "${TEST_CONFIG_PATH}" << 'EOF'
[general]
# All boolean flags default to false for testing
test_source_write_access = false
delete_source_files_after_copying = false
on_demand_defender = false
on_demand_clam_av = false
throttle = false
skip_stability_check = false
defender_handles_suspect_files = false
notify = false
notify_summary = false

# Required paths - tests will override these
source_path = /tmp/test_source
destination_path = /tmp/test_destination
quarantine_path = /tmp/test_quarantine

# Other settings with safe defaults
max_scan_threads = 1
log_level = INFO

[notifications]
# Notification settings disabled by default
use_tls = false

[throttling]
# Throttling disabled by default
free_space_mb = 0
max_file_count_per_day = 0
max_file_volume_per_day_mb = 0
EOF

echo "Test configuration created at: ${TEST_CONFIG_PATH}"
```

## Benefits

1. **Predictable Test Behavior**: Tests start with known false values for all boolean flags
2. **Explicit Control**: Tests can enable only the features they need via command-line flags
3. **Isolation**: Test configuration is separate from user configuration
4. **No Code Changes**: Works with existing shuttle configuration system

## Example Test Usage

With this setup, a test can now:

```python
# Test with throttling disabled (relies on test config having throttle=false)
params = TestParameters(
    setup_throttling=False,  # This ensures --throttle flag is NOT added
    # ... other parameters
)

# Test with throttling enabled (explicitly adds --throttle flag)
params = TestParameters(
    setup_throttling=True,   # This ensures --throttle flag IS added
    # ... other parameters
)
```

## Testing the Fix

After implementing:

1. Run the setup script: `./scripts/setup_test_config.sh`
2. Run the failing test: `python -m unittest tests.test_shuttle.TestShuttle.test_throttling_disabled`
3. The test should now pass because throttling is disabled by default in the test config

## Future Considerations

1. Add the test config generation to the CI/CD pipeline
2. Consider versioning the test config file
3. Add validation to ensure test config has all required settings