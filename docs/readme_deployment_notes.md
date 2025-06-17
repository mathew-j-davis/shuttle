# Installation and Setup Guide

This guide provides instructions for installing and setting up the Shuttle project in different environments: development, user production, and system production.

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
│   ├── 1_deployment_steps/     # Installation scripts (numbered 01-10)
│   ├── health_check_tests/     # Health check and testing scripts
│   ├── vscode_debugging/       # VS Code debugging configurations
│   └── 1_install.sh              # Interactive installation script
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

## Directory Structure

The directory structure is dynamic and depends on where the git repository is cloned and which installation mode is used:

### Source Code Location
- **Always:** Where you clone the git repository (e.g., `/home/user/shuttle`, `/opt/company/shuttle`)
- **Contains:** All Python modules, scripts, tests, and documentation

### Dynamic Paths by Installation Mode

| Component               | Development (`-e`)                 | User Production (`-u`)             | System Production (default)   |
|-------------------------|------------------------------------|------------------------------------|-------------------------------|
| **Config File**         | `PROJECT_ROOT/config/config.conf` | `~/.config/shuttle/config.conf`    | `/etc/shuttle/config.conf`    |
| **Virtual Environment** | `PROJECT_ROOT/.venv`               | `~/.local/share/shuttle/venv`      | `/opt/shuttle/venv`           |
| **Working Directory**   | `PROJECT_ROOT/work`                | `~/.local/share/shuttle/work`      | `/var/lib/shuttle`            |
| **Test Work Directory** | `PROJECT_ROOT/test_area`           | `~/.local/share/shuttle/test_area` | `/var/lib/shuttle/test_area`  |
| **Environment Script**  | `PROJECT_ROOT/config/shuttle_env.sh` | `~/.config/shuttle/shuttle_env.sh` | `/etc/shuttle/shuttle_env.sh` |

### Working Directory Structure
All modes create this structure within their respective working directory:
```
work/
├── incoming/     # Source files (input)
├── processed/    # Destination files (output)  
├── quarantine/   # Temporary quarantine area
├── hazard/       # Encrypted malware archive
├── logs/         # Application logs
└── ledger/       # Defender compatibility tracking
```

## Installation Methods

### Recommended: Interactive Installation Script

The easiest way to install Shuttle is using the interactive installation script:

```bash
cd /path/to/shuttle
./scripts/1_install.sh
```

This script provides:
- **Guided setup** with clear prompts and explanations
- **Installation mode selection** (development, user, or system production)
- **Automatic dependency detection** and installation
- **Virtual environment management** (create, use existing, or global install)
- **Configuration generation** with customizable options
- **Consistent validation** and error handling

The interactive script handles the entire installation process automatically, including:
1. Virtual environment detection and setup
2. System dependency installation (Python, ClamAV, etc.)
3. Configuration file generation
4. Module installation in the correct order
5. Environment variable setup

### Manual Installation Workflow

For advanced users or automated deployments, the installation process can be done manually using numbered scripts (01-10):

1. **System Dependencies** (01, 03-05)
   - `01_sudo_install_python.sh` - Install Python and development tools **FIRST**
   - `03_sudo_install_dependencies.sh` - Install required system packages
   - `05_sudo_install_clamav.sh` - Install ClamAV for virus scanning
   - `04_check_defender_is_installed.sh` - Check Microsoft Defender configuration

2. **Python Environment** (02, 06)
   - `02_env_and_venv.sh` - Set up environment variables and create virtual environment
   - `06_install_python_dev_dependencies.sh` - Install required Python packages

3. **Configuration Setup** (07)
   - `07_setup_config.py` - Create configuration file and directories with customizable options

4. **Module Installation** (08-10)
   - `08_install_shared.sh` - Install shared library module
   - `09_install_defender_test.sh` - Install defender test module
   - `10_install_shuttle.sh` - Install shuttle application module

**Important:** Python must be installed before creating the virtual environment, so the sequence is critical.

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

## Configuration Script Usage

The `07_setup_config.py` script accepts command-line arguments to customize your Shuttle installation. This allows for flexible deployment scenarios without modifying the script.

### Basic Usage

```bash
# Use defaults (working directory subdirectories)
python ./scripts/1_deployment_steps/07_setup_config.py

# Get help on all available options
python ./scripts/1_deployment_steps/07_setup_config.py --help
```

### Common Configuration Examples

#### Development Setup
```bash
python ./scripts/1_deployment_steps/07_setup_config.py \
    --log-level DEBUG \
    --max-scan-threads 1 \
    --no-notify
```

#### Production Setup with Custom Paths
```bash
python ./scripts/1_deployment_steps/07_setup_config.py \
    --source-path /srv/data/incoming \
    --destination-path /srv/data/processed \
    --quarantine-path /tmp/shuttle/quarantine \
    --log-path /var/log/shuttle \
    --hazard-archive-path /secure/malware-archive \
    --log-level INFO \
    --max-scan-threads 4 \
    --throttle-free-space-mb 1000
```

#### Enterprise Setup with Notifications
```bash
python ./scripts/1_deployment_steps/07_setup_config.py \
    --source-path /mnt/shares/inbound \
    --destination-path /mnt/shares/processed \
    --log-path /var/log/shuttle \
    --log-level INFO \
    --max-scan-threads 8 \
    --throttle-free-space-mb 2000 \
    --notify --notify-summary \
    --notify-recipient-email-error security@company.com \
    --notify-recipient-email-summary reports@company.com \
    --notify-recipient-email-hazard security@company.com \
    --notify-sender-email shuttle@company.com \
    --notify-smtp-server smtp.company.com \
    --notify-smtp-port 587 \
    --notify-username shuttle-service \
    --notify-use-tls
```

### Key Configuration Options

| Category | Options | Description |
|----------|---------|-------------|
| **Paths** | `--source-path`, `--destination-path`, `--quarantine-path` | Override default working directory structure |
| **Scanning** | `--max-scan-threads`, `--on-demand-defender`, `--on-demand-clam-av` | Configure virus scanning behavior |
| **Throttling** | `--throttle-free-space-mb`, `--no-throttle` | Disk space management |
| **Logging** | `--log-level`, `--log-path` | Control logging verbosity and location |
| **Notifications** | `--notify`, `--notify-*-email`, `--notify-smtp-*` | Email notification setup |

### Path Defaults

If not specified, paths default to subdirectories within the working directory:

- **Source**: `WORK_DIR/incoming`
- **Destination**: `WORK_DIR/processed`  
- **Quarantine**: `WORK_DIR/quarantine`
- **Logs**: `WORK_DIR/logs`
- **Hazard Archive**: `WORK_DIR/hazard`
- **Ledger**: `CONFIG_DIR/ledger/ledger.yaml`
- **Encryption Key**: `CONFIG_DIR/shuttle_public.gpg`

### Development Mode Installation

By default, modules are installed in standard mode. For development mode (editable installation), add the `-e` flag to these scripts:

```bash
./scripts/1_deployment_steps/08_install_shared.sh -e
./scripts/1_deployment_steps/09_install_defender_test.sh -e
./scripts/1_deployment_steps/10_install_shuttle.sh -e
```

**Note:** The interactive `1_install.sh` script automatically handles development mode installation when you select the development installation mode.

## Data Directory Setup

For production deployments, you should create and configure these directories:

### Tracking Data Directory

The DailyProcessingTracker component requires a directory to store its YAML data files:

1. **Create the directory**:
   ```bash
   sudo mkdir -p /var/lib/shuttle/tracking
   ```

2. **Set permissions**:
   ```bash
   sudo chown <shuttle_user>:<shuttle_group> /var/lib/shuttle/tracking
   sudo chmod 755 /var/lib/shuttle/tracking
   ```

3. **Configure in settings**:
   ```ini
   [paths]
   tracking_data_path = /var/lib/shuttle/tracking
   ```
   
4. **Backup considerations**:
   - Include this directory in your backup strategy
   - These files contain important metrics and processing history
   - YAML files are date-stamped and can be safely archived

### Log Files

Log files should be properly configured for production:

1. **Create log directory**:
   ```bash
   sudo mkdir -p /var/log/shuttle
   ```

2. **Set permissions**:
   ```bash
   sudo chown <shuttle_user>:<shuttle_group> /var/log/shuttle
   sudo chmod 755 /var/log/shuttle
   ```

3. **Configure log rotation**:
   Create a file at `/etc/logrotate.d/shuttle` with:
   ```
   /var/log/shuttle/*.log {
     daily
     missingok
     rotate 14
     compress
     delaycompress
     notifempty
     create 640 <shuttle_user> <shuttle_group>
   }
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

## Lifecycle Management

Shuttle now implements proper component lifecycle management:

1. **Initialization**: Components are created and configured
2. **Operation**: Normal processing of files occurs
3. **Shutdown**: 
   - Tracking data is saved
   - Pending files are handled
   - Resources are properly released

For proper shutdown handling, ensure Shuttle is launched with appropriate signal handling:

```bash
# Example systemd service file
[Unit]
Description=Shuttle File Transfer and Scanning Service
After=network.target

[Service]
Type=simple
User=shuttle
Group=shuttle
WorkingDirectory=/opt/shuttle
ExecStart=/opt/shuttle/venv/bin/python -m shuttle.shuttle
Restart=on-failure
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

## Disk Space Throttling Feature

The Shuttle application includes a disk space throttling feature that:
- Checks available free space in quarantine, destination, and hazard archive directories
- Stops processing new files when space is low while continuing to process already-copied files
- Sends notifications about directories requiring attention

Configuration includes parameters:
- `throttle` (boolean) - Enable/disable throttling
- `throttle_free_space` (integer) - Minimum MB to maintain

By following these guidelines, you can efficiently deploy and manage the Shuttle project on your Ubuntu server.


## Environment Variables and Configuration

### Environment Variables

Shuttle uses two main environment variables that are automatically set during installation:

- **`SHUTTLE_CONFIG_PATH`**: Path to the main configuration file
- **`SHUTTLE_TEST_WORK_DIR`**: Directory used by automated tests (separate from production work directory)

These are automatically configured in the environment script (`shuttle_env.sh`) which is created in the config directory.

### Activating the Shuttle Environment

After installation, activate the Shuttle environment with:

```bash
# Load environment variables
source /path/to/config/shuttle_env.sh

# Activate virtual environment (if using one)
source /path/to/config/shuttle_activate_virtual_environment.sh
```

### Environment Management

The `02_env_and_venv.sh` script handles both environment variable setup and virtual environment creation:

1. **Environment Variables**: Creates `shuttle_env.sh` in the config directory
2. **Virtual Environment**: Creates a Python virtual environment if requested
3. **IDE Integration**: In development mode, creates a `.env` file for IDE support
4. **Activation Helper**: Creates `shuttle_activate_virtual_environment.sh` for easy venv activation

### Virtual Environment Troubleshooting

If you encounter issues with the virtual environment:

- **Check if active**: Look for `(venv)` in your prompt or run:
  ```bash
  echo $VIRTUAL_ENV
  which python
  ```

- **Manual activation**: If the helper script doesn't work:
  ```bash
  source /path/to/.venv/bin/activate
  ```

- **Verify Python version**: Ensure you're using the correct Python:
  ```bash
  python --version
  which python
  ```