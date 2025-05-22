# Deployment and Script Management on Ubuntu Server

This guide provides instructions for deploying and managing the Shuttle project on an Ubuntu server.
The steps below will guide you through the process of deploying and managing the Shuttle project on an Ubuntu server


## Project Structure

The project has been reorganized for better maintainability and deployment:

```
shuttle/
├── src/                        # All source code
│   ├── shared_library/         # Shared code used by both applications
│   │   └── shuttle_common/     # The shuttle_common module
│   ├── shuttle_app/            # Shuttle file transfer application
│   │   ├── bin/                # Executable scripts
│   │   └── shuttle/            # The shuttle module
│   └── shuttle_defender_test_app/   # Defender test application
│       ├── bin/                # Executable scripts
│       └── shuttle_defender_test/   # The shuttle_defender module
├── scripts/                    # All utility scripts
│   ├── 0_key_generation/       # Key generation script
│   ├── 1_deployment/           # Installation scripts (numbered 01-10)
│   ├── health_check_tests/     # Health check and testing scripts
│   └── vscode_debugging/      # VS Code debugging configurations
├── example/                    # Example configurations and files
└── tests/                      # Test suite
```

## GPG Key Configuration

Shuttle requires GPG for encrypting files detected as potential malware. 

**Note:** For detailed information about key generation, security practices, and configuration, see the [Development Guide](readme_development.md#gpg-key-management-for-malware-encryption).

Key points to remember for deployment:
- Only deploy the public key on the target machine
- Configure the key path in settings:
  ```ini
  [paths]
  hazard_encryption_key_path = /path/to/shuttle_public.gpg
  ```
- The test environment setup (`07_setup_config.py`) includes a default test location
- For production, update this path to your actual public key location

## Directory Structure for Deployment

### 1. Application Source Code
- **Location:** `/opt/shuttle/src`
- **Purpose:** Contains the Python modules for shared library, shuttle app, and defender app.

### 2. Deployment Scripts
- **Location:** `/opt/shuttle/scripts/1_deployment`
- **Purpose:** Contains the numbered installation scripts (01-10) to set up the entire system.
- **Setup:**
  - Copy the deployment scripts from `shuttle/scripts/1_deployment` to `/opt/shuttle/scripts/1_deployment` on the server.

### 3. Temporary Setup Scripts
- **Location:** `/tmp/shuttle/setup`
- **Purpose:** For scripts that only need to be run once and don't need to persist.
- **Setup:**
  - Copy necessary setup scripts to this temporary location on the server.

## Installation Workflow

The installation process follows a sequential workflow using numbered scripts (01-10):

1. **System Dependencies** (01-03)
   - `01_sudo_install_dependencies.sh` - Install required system packages
   - `02_sudo_install_python.sh` - Install Python and development tools
   - `03_sudo_install_clamav.sh` - Install ClamAV for virus scanning

2. **Python Environment** (04-06)
   - `04_create_venv.sh` - Create Python virtual environment
   - `05_activate_venv_CALL_BY_SOURCE.sh` - Activate virtual environment (call with `source`)
   - `06_install_python_dependencies.sh` - Install required Python packages

If you have issues with the virtual environment, see the Appendix for additional notes.

3. **Test Environment Setup** (07)
   - `07_setup_test_environment_linux.py` - Configure the test environment

4. **Module Installation** (08-10)
   - `08_install_shared.sh` - Install shared library module
   - `09_install_defender.sh` - Install defender test module
   - `10_install_shuttle.sh` - Install shuttle application module

### Additional Installation Details

#### Required Supporting Applications

The installation scripts require these applications to be installed and accessible:

- **lsof**: Used to check if files are in use
  ```bash
  sudo apt-get install lsof
  ```
  
- **gpg**: Required for encryption of hazard files
  ```bash
  sudo apt-get install gnupg
  ```

#### Virus Scanning Software

- **ClamAV** (Primary virus scanner):
  ```bash
  sudo apt-get install clamav clamav-daemon
  ```
  After installation:
  ```bash
  sudo systemctl start clamav-daemon  # Start the daemon
  sudo systemctl enable clamav-daemon  # Enable at start-up
  sudo freshclam                      # Update virus definitions
  ```

- **Microsoft Defender** (Optional):
  If you plan to use Microsoft Defender, follow the [official installation guide](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually)

#### Virus Scanning Configuration

The Shuttle application supports the following scanning configurations:

1. ClamAV on-demand scanning can be enabled or disabled (`on_demand_clam_av=True|False`)
2. Microsoft Defender on-demand scanning can be enabled or disabled (`on_demand_defender=True|False`)
3. Microsoft Defender can also be configured for real-time protection independent of this application

When both scanners are enabled for on-demand scanning, files must pass both scans to be considered clean. 

### Development Mode Installation

By default, modules are installed in standard mode. For development mode (editable installation), add the `-e` or `--editable` flag to these scripts:

```bash
./10_install_shuttle.sh -e
./08_install_shared.sh -e
./09_install_defender.sh -e
```

## Running Scripts as Cron Jobs

- **Cron Job Setup:**
  - Use the root crontab to schedule scripts that need to run periodically.
  - Ensure scripts are executable and configured to run within the virtual environment.
  - Example cron job entry:
    ```bash
    0 0 * * * /opt/shuttle/src/shuttle_app/bin/run_shuttle.py
    ```

## Best Practices

- **Permissions:** Set appropriate permissions for directories and scripts to prevent unauthorized access.
- **Environment Management:** Always activate the venv before running scripts:
  ```bash
  source /path/to/venv/bin/activate
  ```
- **Dependency Chain:** Follow the installation sequence (01-10) to ensure proper dependency management.
- **Testing:** Run the test suite after installation to verify functionality.
- **Documentation:** Refer to the module-specific READMEs in each source directory for detailed usage instructions.

## Disk Space Throttling Feature

The Shuttle application includes a disk space throttling feature that:
- Checks available free space in quarantine, destination, and hazard archive directories
- Stops processing new files when space is low while continuing to process already-copied files
- Sends notifications about directories requiring attention

Configuration includes parameters:
- `throttle` (boolean) - Enable/disable throttling
- `throttle_free_space` (integer) - Minimum MB to maintain

By following these guidelines, you can efficiently deploy and manage the Shuttle project on your Ubuntu server.



## Appendix: Additional Notes on Virtual Environment Setup and Activation

The Shuttle project uses a Python virtual environment to manage dependencies. The installation scripts include dedicated tools for creating and activating this environment.

### Creating the Virtual Environment

The `04_create_venv.sh` script handles creation of the virtual environment:

```bash
#!/bin/bash

# Check if Python3 and pip are installed
if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
    echo "Python3 and/or pip3 are not installed. Please run install_python.sh first."
    exit 1
fi

# Create a virtual environment
echo "Creating a virtual environment..."
python3 -m venv venv

# Set execute permissions on activate
echo "Set execute permissions on virtual environment activate..."
chmod +x ./venv/bin/activate
```

This script:
1. Verifies Python3 and pip3 are installed
2. Creates a virtual environment in the `venv` directory
3. Ensures the activation script has proper execution permissions

### Activating the Virtual Environment

The `05_activate_venv_CALL_BY_SOURCE.sh` script must be called using the `source` command to properly activate the environment:

```bash
source ./05_activate_venv_CALL_BY_SOURCE.sh
```

The script checks if a virtual environment is already active and activates it if not:

```bash
#!/bin/bash

# to activate this outside of the script you need to call like this:
# source ./activate_venv.sh 

if [[ "$VIRTUAL_ENV" == "" ]]
then
    # Activate the virtual environment
    echo "Activating the virtual environment..."
    . venv/bin/activate
fi
```

### Virtual Environment Troubleshooting

If you encounter issues with the virtual environment on Ubuntu:

- **Verify Activation**: Check if the environment is active by examining the prompt (should show "(venv)") or by checking:
  ```bash
  echo $VIRTUAL_ENV
  which python
  which pip
  ```

- **Activation Failures**: If activation doesn't work, ensure the activate script has execute permissions:
  ```bash
  chmod +x ./venv/bin/activate
  ```

- **Using Full Paths**: If all else fails, use full paths to the Python executables:
  ```bash
  ./venv/bin/python -m pip install -r requirements.txt
  ```

These steps should help resolve common issues related to virtual environment activation and usage on Ubuntu.