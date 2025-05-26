# Shuttle Test Architecture and Enhancement Plan

## Current Architecture Overview

### Core Components

1. **Shuttle Application**
   - Secure file transfer and scanning utility
   - Uses Microsoft Defender and/or ClamAV for malware scanning
   - Implements throttling to prevent disk space exhaustion
   - Main components: shuttle.py, scanning.py, post_scan_processing.py, throttler.py

2. **Test Infrastructure**
   - `test_shuttle_multithreaded.py`: Multithreaded throttling tests
   - `run_shuttle_with_simulator.py`: Test runner with patched MDATP simulator
   - `mdatp-simulator`: Standalone script mimicking Microsoft Defender behavior

### Throttling Test Suite (`test_shuttle_multithreaded.py`)

The throttling test suite verifies Shuttle's behavior under various resource constraints:

#### Key Classes and Methods:

- **TestParameters**: Central class encapsulating all test parameters
  ```python
  params = TestParameters(
      # Test parameters
      thread_count=1,
      clean_file_count=5,
      malware_file_count=0,
      file_size_kb=1024,
      
      # Throttling parameters
      setup_throttling=True,
      max_files_per_day=10,
      max_volume_per_day=50,
      min_free_space=1024,
      initial_files=0,
      initial_volume_mb=0,
      mock_free_space=5000,
      
      # Expected outcomes
      expected_throttled=True,
      expected_files_processed=5,
      expected_throttle_reason="THROTTLE REASON: Insufficient disk space",
      description="Test description"
  )
  ```

- **test_throttling_scenario**: Core test method used by all tests
  - Creates test files
  - Sets up throttling conditions
  - Runs Shuttle in a multithreaded environment
  - Verifies outcomes match expectations

- **Individual test methods**:
  - `test_space_throttling`: Tests throttling based on insufficient disk space
  - `test_daily_volume_limit`: Tests throttling based on daily volume limit
  - `test_daily_volume_limit_with_existing_log`: Tests volume limit with existing log
  - `test_daily_file_count_limit_no_existing_log`: Tests file count limit without log
  - `test_daily_file_count_limit_with_existing_log`: Tests file count limit with log
  - `test_throttling_disabled`: Tests with throttling disabled
  - `test_throttling_configurable`: Configurable test with command-line args

- **Auto-calculation of expected outcomes**:
  - `calculate_expected_outcomes()` method in TestParameters
  - Determines whether throttling should occur
  - Calculates how many files should be processed
  - Determines appropriate throttle reason message

#### Test Flow:

1. Create TestParameters (fixed or from command line)
2. Set up test environment (files, throttling)
3. Run Shuttle with simulator
4. Verify results against expected outcomes

### Simulator Architecture (`run_shuttle_with_simulator.py`)

This module serves as the test runner that patches Microsoft Defender with a simulator:

#### Key Features:

- **Patching Mechanism**:
  ```python
  patchers = [patch('shuttle_common.scan_utils.DEFENDER_COMMAND', simulator_script)]
  ```
  - Replaces real DEFENDER_COMMAND with simulator script path
  - Uses Python's unittest.mock.patch

- **Disk Space Simulation**:
  ```python
  def mock_get_free_space_mb(directory_path):
      """Mock implementation that returns simulated free space minus files already processed"""
      # Calculate total size of files in the directory
      total_size_mb = 0
      if os.path.exists(directory_path):
          for filename in os.listdir(directory_path):
              file_path = os.path.join(directory_path, filename)
              if os.path.isfile(file_path):
                  # Get file size in MB
                  file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                  total_size_mb += file_size_mb
                  
      # Return simulated free space minus the space used by files
      return mock_free_space - total_size_mb
  ```
  - Dynamically calculates available space based on files in directory
  - Currently uses a single mock_free_space value for all paths

- **Simulator Configuration**:
  - Sets up simulator ledger file to approve version "0.0.0.0"
  - Configures command-line arguments for simulator
  - Makes simulator script executable

#### MDATP Simulator:

- Standalone script that mimics Microsoft Defender behavior
- Detects "malware" based on filename containing "malware"
- Returns appropriate exit codes and formatted output
- Supports version, scan, and status commands

## Enhancement Requirements

### 1. Real Defender Support

**Requirement**: Allow tests to run with real Microsoft Defender instead of only the simulator.

**Implementation Plan**:
- Add `--no-defender-simulator` parameter to `run_shuttle_with_simulator.py`
- Conditionally apply the Defender patch only when simulator is enabled
- Handle EICAR test string for real malware detection

**Code Impact**:
- Modify `run_shuttle_with_simulator.py` to conditionally apply patches
- Update malware file creation logic in test code

### 2. EICAR Test Files

**Requirement**: Use EICAR test string in malware files when using real Defender.

**Implementation Plan**:
- Create a function to generate EICAR-based test files
- Account for size limitations (EICAR is only detected in small files)
- Maintain filename-based detection for simulator mode

**Code Impact**:
- Add EICAR string constant
- Modify file creation logic in tests
- Add conditional logic based on simulator mode

### 3. Path-Specific Space Mocking

**Requirement**: Mock disk space differently for each path (quarantine, hazard, destination).

**Implementation Plan**:
- Enhance `mock_get_free_space_mb` to handle different space values per path
- Create a mapping of paths to available space values
- Support command-line parameters for each path's space value

**Code Impact**:
- Refactor space mocking function to use path mapping
- Update command-line argument parsing
- Modify the TestParameters class to support path-specific space values

### 4. Subdirectory Support

**Requirement**: Ensure space mocking works with nested subdirectory paths.

**Implementation Plan**:
- Implement path normalization or prefix matching for space calculation
- Handle cases where monitored paths are subdirectories
- Ensure consistent behavior with arbitrary nesting levels

**Code Impact**:
- Update path comparison logic in mock space function
- Add test cases for subdirectory scenarios
- Implement common prefix determination for nested paths

## Implementation Guidelines

### Code Navigation Tips

Key files to explore and modify:
- `/home/mathew/shuttle/tests/run_shuttle_with_simulator.py` - Main test runner to modify
- `/home/mathew/shuttle/tests/test_shuttle_multithreaded.py` - Test suite to enhance
- `/home/mathew/shuttle/tests/mdatp_simulator_app/simulator.py` - Simulator implementation
- `/home/mathew/shuttle/src/shuttle_app/shuttle/throttle_utils.py` - Throttling implementation

### Testing Strategy

1. **Incremental Changes**:
   - Start with the `--no-defender-simulator` flag implementation
   - Then add EICAR support
   - Finally implement path-specific space mocking

2. **Verification Points**:
   - Each feature should work in isolation
   - Combined features should work together
   - Both simulator and real Defender modes should be tested

3. **Test Cases**:
   - Simulator mode with standard malware files
   - Real Defender mode with EICAR files
   - Different space values for different paths
   - Nested subdirectory scenarios

### EICAR String Information

The EICAR test string is a standardized test file used to verify antivirus detection:
```
X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*
```

Key considerations:
- File must be small (usually <25KB) for reliable detection
- Should be placed at the beginning of the file
- No modification to the string should be made

## Example Implementation Snippets

### No-Simulator Flag Implementation

```python
def parse_args():
    parser = argparse.ArgumentParser(description='Run Shuttle with simulator')
    parser.add_argument('--no-defender-simulator', action='store_true',
                        help='Use real Microsoft Defender instead of simulator')
    parser.add_argument('--mock-free-space', type=int, default=0,
                        help='Mock free disk space in MB (0 = no mocking)')
    # Add arguments for path-specific space values
    parser.add_argument('--quarantine-space', type=int, default=None,
                        help='Mock free space for quarantine path in MB')
    parser.add_argument('--hazard-space', type=int, default=None,
                        help='Mock free space for hazard path in MB')
    parser.add_argument('--destination-space', type=int, default=None,
                        help='Mock free space for destination path in MB')
    return parser.parse_args()

# Later in the code:
args = parse_args()
patchers = []

# Only patch if not using real defender
if not args.no_defender_simulator:
    patchers.append(patch('shuttle_common.scan_utils.DEFENDER_COMMAND', simulator_script))
```

### Path-Specific Space Mocking

```python
# Create a mapping of paths to space values
path_space_mapping = {}
if args.quarantine_space is not None:
    path_space_mapping[quarantine_path] = args.quarantine_space
if args.hazard_space is not None:
    path_space_mapping[hazard_path] = args.hazard_space
if args.destination_space is not None:
    path_space_mapping[destination_path] = args.destination_space

# Default fallback space value
default_mock_space = args.mock_free_space

def mock_get_free_space_mb(directory_path):
    """Mock implementation that returns path-specific simulated free space"""
    # Normalize the path for comparison
    norm_path = os.path.normpath(directory_path)
    
    # Find the appropriate space value for this path
    space_value = None
    
    # Check for exact path match first
    if norm_path in path_space_mapping:
        space_value = path_space_mapping[norm_path]
    else:
        # Check if the path is a subdirectory of any monitored paths
        for monitored_path, space in path_space_mapping.items():
            if norm_path.startswith(monitored_path + os.path.sep):
                space_value = space
                break
    
    # If no specific value found, use default
    if space_value is None:
        space_value = default_mock_space
        
    # Calculate total size of files in the directory
    total_size_mb = 0
    if os.path.exists(directory_path):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                # Get file size in MB
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                total_size_mb += file_size_mb
                
    # Return simulated free space minus the space used by files
    return space_value - total_size_mb
```

### EICAR File Creation

```python
# EICAR test string constant
EICAR_STRING = r'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

def create_test_files(base_path, count, size_kb, is_malware=False, use_real_defender=False):
    """Create test files for shuttle testing
    
    Args:
        base_path: Directory to create files in
        count: Number of files to create
        size_kb: Size of each file in KB
        is_malware: Whether these should be malware files
        use_real_defender: Whether to use EICAR string for real defender
    """
    os.makedirs(base_path, exist_ok=True)
    
    files_created = []
    for i in range(count):
        if is_malware:
            filename = f"malware_test_{i}.dat"
        else:
            filename = f"clean_test_{i}.dat"
            
        file_path = os.path.join(base_path, filename)
        
        with open(file_path, 'wb') as f:
            if is_malware and use_real_defender:
                # Use EICAR string for real defender tests
                # Note: Only works for small files, so we'll limit size if needed
                if size_kb > 20:  # Limit size for EICAR detection
                    actual_size_kb = 20
                    print(f"WARNING: Limiting malware file size to 20KB for EICAR detection")
                else:
                    actual_size_kb = size_kb
                
                # Write EICAR string
                f.write(EICAR_STRING.encode('utf-8'))
                
                # Pad to reach desired file size
                remaining_bytes = (actual_size_kb * 1024) - len(EICAR_STRING)
                if remaining_bytes > 0:
                    f.write(b'\0' * remaining_bytes)
            else:
                # Standard random data approach
                f.write(os.urandom(size_kb * 1024))
                
        files_created.append(file_path)
        
    return files_created
```

## Common Pitfalls and How to Avoid Them

1. **Path Comparison Errors**
   - Always normalize paths before comparison
   - Use os.path.normpath() to handle different separators
   - Consider case sensitivity issues on different platforms

2. **EICAR Detection Issues**
   - Keep files small (under 25KB)
   - Don't modify the EICAR string
   - Ensure the string is at the beginning of the file

3. **Patch Context Management**
   - Always use patch as a context manager
   - Ensure all patchers are started and stopped properly
   - Be careful about nested patches

4. **Command Line Argument Handling**
   - Provide clear defaults for all arguments
   - Handle missing arguments gracefully
   - Document all parameters in help text

## Next Development Steps

1. Implement the `--no-defender-simulator` flag
2. Add EICAR test file support
3. Implement path-specific space mocking
4. Add subdirectory support for space mocking
5. Update tests to verify all new functionality
6. Update documentation to reflect changes
