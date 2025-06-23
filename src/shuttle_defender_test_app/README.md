# Shuttle Defender Test

A package for testing Microsoft Defender's output format and tracking compatible versions. This ensures that the pattern matching logic used in shuttle's scanning module remains compatible with the current Defender version.

## Package Components

- **shuttle_defender_test.py**: Core testing functionality for Microsoft Defender output patterns
- **read_write_ledger.py**: Handles recording and retrieving tested Defender versions

## Prerequisites

- Python 3.6 or higher
- `shuttle_common` package installed

## Installation

### Development Installation

For developers who want to modify the code while using it:

```bash
# First, install the shuttle_common dependency (if not already installed)
cd ../shared_library
pip install -e .

# Then install the shuttle_defender_test package
cd ../shuttle_defender_test_app
pip install -e .
```

This will install the package in "editable" mode, allowing you to continue developing while having it available for import in Python.

### Production Installation

For production environments:

```bash
# First, install the shuttle_common dependency
cd ../shared_library
pip install .

# Then install the shuttle_defender_test package
cd ../shuttle_defender_test_app
pip install .
```

## Running the Defender Test

After installation, you can run the defender test in several ways:

### 1. As a Python Module

```bash
python -m shuttle_defender_test
```

### 2. Using the Command-Line Entry Point

If installed with pip, a command-line entry point is available:

```bash
run-shuttle-defender-test
```

### 3. Using the Wrapper Script

```bash
python run_shuttle_defender_test.py
```

## Configuration

The defender test uses configuration settings that can be specified via:

1. Command-line arguments
2. Configuration file

See the usage output (`run-shuttle-defender-test --help`) for more information on available options.

## Development

### Running Tests

```bash
# From the shuttle_defender_test_app directory
python -m unittest discover
```

### Building Distribution Packages

```bash
# From the shuttle_defender_test_app directory
python -m build
```

This will create distribution packages in the `dist` directory.

## Deployment

The package is designed to be deployed in environments where it can access Microsoft Defender and can update the ledger file to record successful tests.

Ensure that the user running the package has appropriate permissions to:
1. Run Microsoft Defender scans
2. Write to the ledger file location

## Dependencies

- **shuttle_common**: Shared utilities used by both the shuttle and defender_test modules
- **PyYAML**: For ledger operations

## License

[Specify your license information here]
