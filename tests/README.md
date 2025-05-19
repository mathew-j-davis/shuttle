# Shuttle Testing Framework

This directory contains automated tests for the Shuttle file transfer utility. The tests are designed to verify the functionality of key components including notifications and disk space throttling.

## Test Structure

- `test_notifier.py`: Unit tests for the notification system
- `test_throttling.py`: Unit tests for the disk space throttling feature
- `run_tests.py`: Script to discover and run all tests

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
```

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
