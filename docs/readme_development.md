# Shuttle Development Guide

## Project Structure

```
shuttle/
├── src/                        # All source code
│   ├── shared_library/         # Shared code used by both applications
│   │   └── shuttle_common/     # The shuttle_common module
│   ├── shuttle_app/            # Shuttle file transfer application
│   │   ├── bin/                # Executable scripts
│   │   └── shuttle/            # The shuttle module
│   │       ├── __init__.py
│   │       ├── shuttle.py           # Main entry point
│   │       ├── shuttle_config.py    # App-specific config
│   │       ├── scanning.py          # File scanning logic
│   │       ├── post_scan_processing.py  # Result handling
│   │       └── throttler.py         # Disk space management
│   └── shuttle_defender_test_app/   # Defender test application
│       ├── bin/                # Executable scripts
│       └── shuttle_defender_test/   # The shuttle_defender module
│           ├── __init__.py
│           ├── shuttle_defender_test.py  # Test runner
│           └── read_write_ledger.py      # Version tracking
├── scripts/                    # All utility scripts
│   ├── 0_key_generation/       # Key generation script
│   ├── 1_deployment/           # Installation scripts (numbered 01-10)
│   ├── health_check_tests/     # Health check and testing scripts
│   └── vscode_debugging/      # VS Code debugging configurations
├── example/                    # Example configurations and files
└── tests/                      # Test suite
```

## Shared Library (shuttle_common)

- **config.py** - Configuration handling and settings management
- **scan_utils.py** - Scanning utilities for malware detection
- **files.py** - File operations and integrity verification
- **logging_setup.py** - Logging configuration
- **notifier.py** - Email notification system
- **ledger.py** - Interface for Defender compatibility tracking

## Development Environment

### Dependencies

#### System Dependencies
- Python 3.6+
- lsof: Used to check if files are in use
  ```bash
  sudo apt-get install lsof
  ```
- gpg: Required for encryption of hazard files
  ```bash
  sudo apt-get install gnupg
  ```

#### Virus Scanning Software
- ClamAV (Primary virus scanner):
  ```bash
  sudo apt-get install clamav clamav-daemon
  sudo systemctl start clamav-daemon  # Start the daemon
  sudo systemctl enable clamav-daemon  # Enable at start-up
  sudo freshclam                      # Update virus definitions
  ```
- Microsoft Defender (Optional):
  Follow the [official installation guide](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually)

### Setting Up

1. Clone the repository
2. Run the appropriate setup scripts as described below
3. Create configuration file in one of the standard locations

#### Setup Scripts

The deployment scripts in `scripts/1_deployment/` have specific requirements:

- **Scripts requiring sudo**:
  - `01_sudo_install_dependencies.sh` - System packages installation
  - `02_sudo_install_python.sh` - Python installation
  - `03_sudo_install_clamav.sh` - ClamAV installation

- **Scripts requiring source**:
  - `05_activate_venv_CALL_BY_SOURCE.sh` - Must be called with `source` to properly activate the environment

- **Python scripts**:
  - `07_setup_test_environment_linux.py` - Called with Python interpreter

#### Virtual Environment Notes

- **VS Code Users**: VS Code has its own way of managing Python virtual environments
  - Use the VS Code Python extension to select the interpreter
  - The extension will automatically activate the environment for terminals and debugging
  - For scripts that require `source`, use the VS Code terminal after selecting the interpreter

- **Command Line Users**: 
  - Activate the environment with `source path/to/venv/bin/activate`
  - Or use `python -m venv` to create and manage environments

#### Environment Variables

The application uses these environment variables (set by `scripts/1_deployment/00_set_env.sh`):

- `SHUTTLE_CONFIG_PATH` - Path to the configuration file
- `SHUTTLE_VENV_PATH` - Path to the virtual environment
- `SHUTTLE_WORK_DIR` - Path to the working directory

The script creates a `shuttle_env.sh` file that can be sourced in future sessions:

```bash
source /path/to/shuttle_env.sh
```

During development, you may also need:

- `PYTHONPATH` - To include project directories

#### Package Installation

When installing the packages with the scripts, use the `-e` flag for editable mode:

```bash
# Install packages in development (editable) mode
./08_install_shared.sh -e
./09_install_defender.sh -e
./10_install_shuttle.sh -e
```

Editable mode allows you to modify the code without reinstalling the package.

### GPG Key Management for Malware Encryption

Shuttle uses GPG encryption to securely handle potential malware:

#### Key Generation

The `scripts/0_key_generation/00_generate_shuttle_keys.sh` script generates a GPG key pair:

```bash
# Generates:
# - shuttle_public.gpg - Public key to deploy on the target machine
# - shuttle_private.gpg - Private key to keep secure elsewhere
```

**Important security notes:**
- The private key should NEVER be deployed on the target machine
- Only the public key is needed on the machine running Shuttle

#### Configuring the Public Key Path

In the settings file, add the path to your public key:

```conf
[paths]
...
hazard_encryption_key_path = /path/to/shuttle_public.gpg
```

#### How Encryption Works

When Shuttle identifies a potential malware file:
1. The malware detection tool first attempts to handle it
2. If automatic handling isn't possible, Shuttle encrypts the file using the public GPG key
3. The encrypted file can only be decrypted using the private key

## Key Workflows

### File Processing

The main file processing workflow:

1. Discover files in source directory
2. Check if files are safe and stable
3. Copy to quarantine directory
4. Scan files for malware
5. Process based on results:
   - Clean: Move to destination
   - Suspect: Archive or let Defender handle

### Configuration Loading

Configuration is loaded following this process:

1. Parse command line arguments
2. Search for config file in standard locations
3. Load settings with priority: CLI > config file > defaults
4. Create configuration objects

### Throttling

The disk space throttling system:

1. Check available space in relevant directories
2. Compare against minimum required (configured value)
3. If any directory is below threshold:
   - Stop processing new files
   - Send notification

## Testing

### Test App

The defender test app verifies Microsoft Defender integration:

1. Creates test files (clean file and EICAR test file)
2. Runs scans on both files
3. Verifies expected detection results
4. Updates compatibility ledger

### Future Test Areas

- File integrity verification
- Throttling system
- Notification system
- Configuration handling

## Common Issues

1. **Missing Configuration**:
   - Check standard locations listed in Configuration.md
   - Verify file permissions

2. **Scan Failures**:
   - Ensure Microsoft Defender or ClamAV is installed
   - Check scan utility paths

3. **Import Errors**:
   - Verify Python path includes project directories
   - Check module structure and imports

4. **File Path Issues**:
   - Use absolute paths when possible
   - For relative paths, understand the working directory

5. **Disk Space Problems**:
   - Check throttle_free_space setting
   - Verify directory permissions and quotas

## Deployment

### Directory Structure

1. **Application Source Code**
   - **Location:** `/opt/shuttle/src`
   - **Purpose:** Contains all Python modules

2. **Deployment Scripts**
   - **Location:** `/opt/shuttle/scripts/1_deployment`
   - **Purpose:** Installation scripts (01-10)

3. **Temporary Setup Scripts**
   - **Location:** `/tmp/shuttle/setup`
   - **Purpose:** One-time setup scripts

### Installation Workflow

The installation uses a sequence of numbered scripts:

0. **Environment Setup**
   - `00_set_env.sh` - Set up environment variables, creates `shuttle_env.sh` for future sessions

1. **System Dependencies** (01-03)
   - `01_sudo_install_dependencies.sh` - Install required system packages
   - `02_sudo_install_python.sh` - Install Python and development tools
   - `03_sudo_install_clamav.sh` - Install ClamAV for virus scanning

2. **Python Environment** (04-06)
   - `04_create_venv.sh` - Create Python virtual environment
   - `05_activate_venv_CALL_BY_SOURCE.sh` - Activate virtual environment (call with `source`)
   - `06_install_python_dev_dependencies.sh` - Install required Python packages

3. **Test Environment Setup** (07)
   - `07_setup_config.py` - Configure the test environment

4. **Module Installation** (08-10)
   - `08_install_shared.sh` - Install shared library module
   - `09_install_defender.sh` - Install defender test module
   - `10_install_shuttle.sh` - Install shuttle application module

### Development Mode Installation

For editable installation, add the `-e` flag:

```bash
./10_install_shuttle.sh -e
./08_install_shared.sh -e
./09_install_defender.sh -e
```

### Command-line Tools

The project provides two main command-line tools that are installed when the packages are set up:

1. **run-shuttle** - Main file transfer and scanning utility
   - Installed via the entry point in shuttle_app/setup.py
   - Maps to `shuttle.shuttle:main`
   - Handles file transfer, scanning, and processing

2. **run-defender-test** - Defender compatibility testing tool
   - Installed via the entry point in shuttle_defender_test_app/setup.py
   - Maps to `shuttle_defender_test.shuttle_defender_test:main`
   - Tests Microsoft Defender's pattern matching compatibility

### Running as Cron Jobs

To schedule periodic execution:

```bash
# Example cron entry (in root crontab)
0 0 * * * run-shuttle
```

Ensure the virtual environment is activated or the PATH includes the installed binaries.
