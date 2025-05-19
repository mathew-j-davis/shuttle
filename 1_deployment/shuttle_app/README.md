# Shuttle

A file transfer and scanning utility with disk space throttling capability. Shuttle handles secure file transfers with malware scanning and ensures sufficient disk space is available during operations.

## Package Components

- **shuttle.py**: Main application entry point
- **scanning.py**: Core file scanning functionality 
- **post_scan_processing.py**: Handling of scan results
- **shuttle_config.py**: Configuration handling
- **throttler.py**: Disk space monitoring and throttling

## Key Features

- **Secure File Transfer**: Ensures files are securely transferred with integrity checks
- **Malware Scanning**: Integrates with security tools to scan files
- **Disk Space Throttling**: Prevents running out of space in quarantine, destination, and hazard archive directories
- **Notification System**: Alerts administrators about critical events and errors

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

# Then install the shuttle package
cd ../shuttle_app
pip install -e .
```

This will install the package in "editable" mode, allowing you to continue developing while having it available for import in Python.

### Production Installation

For production environments:

```bash
# First, install the shuttle_common dependency
cd ../shared_library
pip install .

# Then install the shuttle package
cd ../shuttle_app
pip install .
```

## Running Shuttle

After installation, you can run Shuttle in several ways:

### 1. As a Python Module

```bash
python -m shuttle
```

### 2. Using the Command-Line Entry Point

If installed with pip, a command-line entry point is available:

```bash
run-shuttle
```

### 3. Using the Wrapper Script

```bash
python run_shuttle.py
```

## Configuration

Shuttle uses configuration settings that can be specified via:

1. Command-line arguments
2. Configuration file

See the usage output (`run-shuttle --help`) for more information on available options.

### Disk Space Throttling Configuration

The disk space throttling feature ensures there's enough free space in the quarantine, destination, and hazard archive directories before transferring files. If space is low, it stops processing new files while continuing to process already-copied files.

Configuration options include:
- `throttle`: Boolean to enable/disable throttling
- `throttle_free_space`: Minimum MB to maintain in directories

## Development

### Running Tests

```bash
# From the shuttle_app directory
python -m unittest discover
```

### Building Distribution Packages

```bash
# From the shuttle_app directory
python -m build
```

This will create distribution packages in the `dist` directory.

## Deployment

The package is designed to be deployed in environments where it can securely transfer and scan files.

Ensure that the user running the package has appropriate permissions to:
1. Access source and destination directories
2. Run malware scans
3. Create and modify files in the destination directory

## Dependencies

- **shuttle_common**: Shared utilities used by both the shuttle and defender_test modules
- **PyYAML**: For configuration file parsing

## License

[Specify your license information here]
