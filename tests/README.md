# Shuttle Testing Framework

This directory contains automated tests for the Shuttle file transfer utility. The tests are designed to verify the functionality of key components including notifications, disk space throttling, and Microsoft Defender for Endpoint (MDATP) simulation.

## Test Structure

- `test_notifier.py`: Unit tests for the notification system
- `test_throttling.py`: Unit tests for the disk space throttling feature
- `test_mdatp_simulator.py`: Tests for the Microsoft Defender simulator
- `test_shuttle_with_simulator.py`: Integration tests using the MDATP simulator
- `run_shuttle_with_simulator.py`: Script to run Shuttle with the MDATP simulator
- `run_tests.py`: Script to discover and run all tests

### MDATP Simulator

The `mdatp_simulator_app` directory contains a standalone simulator for Microsoft Defender for Endpoint (MDATP) that can be used for testing without requiring the actual Microsoft Defender installation:

- `mdatp_simulator_app/mdatp_simulator/simulator.py`: Core simulator that emulates MDATP commands
- `simulator_ledger.yaml`: Ledger file that approves the simulator version for testing
- `mdatp_simulator_test_files/`: Test files for the simulator including clean and malware samples

## Running Tests

### Running All Tests

To run all tests, execute the following command from this directory:

```bash
python run_tests.py
```

### Running Individual Test Files

To run tests from a specific file:

```bash
python -m unittest test_notifier.py
python -m tests.test_mdatp_simulator
```

### MDATP Simulator Tests

#### Running the Integration Test

To run the integration test that validates Shuttle's behavior with the MDATP simulator:

```bash
# From the project root
python -m tests.test_shuttle_with_simulator

# Or directly run the file
python tests/test_shuttle_with_simulator.py
```

This test:
1. Creates temporary directories (source, destination, quarantine, hazard)
2. Places test files in the source directory
3. Runs Shuttle with the simulator
4. Verifies files are correctly processed based on scan results

#### Running Shuttle with the MDATP Simulator

To run Shuttle manually with the MDATP simulator instead of the real Microsoft Defender:

```bash
python tests/run_shuttle_with_simulator.py -SourcePath /path/to/source -DestinationPath /path/to/dest -QuarantinePath /path/to/quarantine
```

The script accepts all standard Shuttle parameters. For example, a more complete example would be:

```bash
python tests/run_shuttle_with_simulator.py \
  -SourcePath /path/to/source \
  -DestinationPath /path/to/dest \
  -QuarantinePath /path/to/quarantine \
  -HazardArchivePath /path/to/hazard \
  -OnDemandDefender \
  -LogPath /path/to/logs
```

# Note: Boolean flags like -OnDemandDefender are now present/absent style flags.
# Include the flag to set it to True, omit the flag to keep it False.

This is useful for testing Shuttle's scanning functionality without requiring an actual Microsoft Defender installation.

### Running Specific Test Cases

To run a specific test case:

```bash
python -m unittest test_notifier.TestNotifier.test_notify_success
```

## Test Coverage

Current test coverage includes:

1. **Notifier Tests**
   - Initialization
   - Handling missing configuration
   - Successful notification sending
   - Error handling during SMTP communication

2. **Throttling Tests**
   - Throttling behavior with sufficient disk space
   - Throttling behavior with insufficient disk space
   - Disabled throttling behavior

3. **MDATP Simulator Tests**
   - Version command functionality (`mdatp version`)
   - Scan command functionality (`mdatp scan`)
     - Handling of clean files (no threats detected)
     - Detection of malware files (threats detected)
     - Handling of non-existent files (file not found)
   - Integration with Shuttle workflow
     - Proper file classification (clean vs malware)
     - Proper file handling based on scan results
     - Simulator detection and warning messages

## Adding New Tests

To add new tests:

1. Create a new test file with the naming convention `test_*.py`
2. Import the necessary modules from the shuttle package
3. Create a class that inherits from `unittest.TestCase`
4. Add test methods with names starting with `test_`
5. The test runner will automatically discover and run these tests

## Test Dependencies

Tests use the standard library `unittest` framework and make extensive use of the `unittest.mock` module for mocking external dependencies.

## Manual Testing

For manual testing of the notification system, you can use the script in the `test_and_admin_scripts` directory:

```bash
../test_and_admin_scripts/notifier_test.py --recipient "recipient@example.com" --sender "sender@example.com" --smtp-server "smtp.example.com" --smtp-port 587 --username "username" --password "password"
```

Or use the shell script wrapper:

```bash
../test_and_admin_scripts/run_notifier_test.sh
```

Remember to update the configuration values in these scripts before running them.
