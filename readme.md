# Shuttle Project

## System Flow

```
┌─────────────────┐                   ┌─────────────────┐
│                 │                   │                 │
│  Source Files   │                   │    Throttler    │
│                 │                   │ (Space Checks)  │
└────────┬────────┘                   └────────┬────────┘
         │                                     │
         │         ┌─────────────────┐         │
         │         │                 │         │
         └────────►│    Quarantine   │◄────────┘
                   │  (Temp Storage) │
                   └────────┬────────┘
                            │
                            │
                   ┌────────┴────────┐
                   │                 │
                   │   File Hashing  │
                   │  (Verification) │
                   └────────┬────────┘
                            │
                            ▼
         ┌─────────────────────────────────┐
         │                                 │
         │    DailyProcessingTracker       │
         │   (File & Volume Tracking)      │
         │                                 │
         └─────────────────┬───────────────┘
                           │             
                           ▼             
         ┌─────────────────────────────────┐
         │                                 │
         │          Malware Scan           │
         │   (Microsoft Defender/ClamAV)   │
         │                                 │
         └──────────┬─────────────┬────────┘
                    │             │
           Clean Files           Suspect Files
                    │             │
                    ▼             ▼
       ┌──────────────────┐ ┌─────────────────────┐
       │                  │ │                     │
       │   Destination    │ │  Hazard Archive     │
       │    Directory     │ │  (GPG Encryption)   │
       │                  │ │                     │
       └──────────────────┘ └─────────────────────┘
                     │             │
                     └──────┬──────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │                  │
                  │   Cleanup        │
                  │ (Source files)   │
                  │                  │
                  └──────────────────┘
```

## Overview

WARNING THIS SOFTWARE IS EXPERIMENTAL 
THIS IS UNTESTED, NO GUARANTEES OR WARRANTEES
YOU ARE RESPONSIBLE FOR YOUR OWN ACTIONS

Shuttle is a secure file transfer and scanning utility designed to safely move files between directories while performing malware scanning. It is intended to be deployed on a hardened, locked-down machine that functions as a security intermediary between untrusted systems and protected networks.

### Primary Use Case
Shuttle addresses the critical security challenge of transferring data files from equipment running old, unpatched operating systems (such as industrial control systems, legacy medical devices, or aging infrastructure) to secure networks without risking the integrity of the protected environment. By providing a controlled, monitored, and scanned transfer point, Shuttle helps organizations maintain security while dealing with the reality of legacy systems that cannot be updated.

 It features. 

- On-demand malware scanning using Microsoft Defender and ClamAV
- Disk space monitoring and throttling to prevent filling drives
- Secure encryption and handling of suspect files 
- Configurable notification system for errors and status updates
- File integrity verification during transfers
- Parallel processing for improved performance 

**Note:** This project is under active development. When using with Microsoft Defender, you may experience stability issues if scanning with multiple threads.

## System Requirements

- **Operating System**: Linux-based (Ubuntu, Debian, RHEL, Fedora, etc.)
- **Python**: Version 3.6 or higher (can be installed via provided scripts)
- **Malware Scanner** (at least one):
  - ClamAV
  - Microsoft Defender for Linux
- **Encryption**: GPG/GnuPG for suspect file encryption
- **Disk Space**: Sufficient space for:
  - Quarantine directory (temporary file storage)
  - Hazard archive (encrypted suspect files)
  - Log files and tracking database
- **Network**: SMTP access for email notifications (optional)
- **Permissions**: Ability to install system packages and create service accounts

**Important**: The installation and configuration scripts can install Python, ClamAV, and other required system tools automatically based on your selections.

**Disclaimer**: This software is provided as-is without any warranties. Users are responsible for evaluating the suitability of this software for their specific security requirements and compliance obligations. Always test thoroughly in a non-production environment before deployment.

## Core Components

The project is organized into:

- Three modules:

1. **Main Shuttle Application** (`shuttle_app`) - The primary file transfer and scanning orchestration system.
2. **Defender Test App** (`shuttle_defender_test_app`) - A standalone utility to test Microsoft Defender integration
3. **Common Library** (`shuttle_common`) - Shared utilities used by both applications

- Extensive installation and environment configuration utilities.
- Extensive configurable automated tests

## Key Features

### Secure File Transfer
Files are safely moved between source and destination directories with integrity checks. The process ensures files are stable (not being written to) before processing, and verifies integrity using file hashes.

### Malware Scanning
Files are scanned using configurable scanners:
- **ClamAV**: Primary recommended scanner
- **Microsoft Defender**: Available as an alternative or additional scanner

When both scanners are enabled, files must pass both scans to be considered clean. The recommended configuration is to use ClamAV for on-demand scanning while configuring Microsoft Defender for real-time protection on the filesystem.

### File Tracking and Metrics
The DailyProcessingTracker component:
- Tracks every processed file with unique hash identifiers
- Maintains metrics by outcome category (success/failure/suspect)
- Provides detailed reporting of number and volume of files transferred

### Suspect File Handling
When a file is identified as suspicious:
1. **Microsoft Defender Handling** (if configured):
   - Defender automatically quarantines the file according to its settings
   - The script verifies Defender has removed the file
2. **Fallback Handling**:
   - Files are encrypted using GPG with a public key
   - Encrypted files are moved to a hazard archive directory
   - Original filenames and timestamps are preserved

### Disk Space Management
Throttling system monitors available disk space in all relevant directories and prevents processing when space is low to avoid filling up disks.

### Logging and Notifications
- Comprehensive logging with configurable levels to syslog and file
- Hierarchy logging shows call chains in DEBUG mode using function-level loggers
- Email notifications for errors, suspect files, and process completion
- Logger injection pattern using `logging_options` parameter provides consistent logging across all modules

### Concurrency and Single Instance
- Uses `ProcessPoolExecutor` for parallel file processing
- Enforces single instance operation via lock file mechanism

## Installation

Shuttle provides interactive installation scripts for easy setup:

```bash
# Clone the repository
git clone <repository-url>
cd shuttle

# Run the interactive installation wizard
./scripts/1_install.sh

# Configure users, groups, permissions, and services
./scripts/2_post_install_config.sh
```

The installation wizard will guide you through:
- Choosing installation type (development, user, or service)
- Installing Python and system dependencies
- Setting up virtual environments
- Installing scanner software (ClamAV/Defender)
- Configuring file paths and permissions

## Quick Start

1. **Clone and Install**
   ```bash
   git clone <repository-url>
   cd shuttle
   ./scripts/1_install.sh
   ```

2. **Configure Environment**
   ```bash
   ./scripts/2_post_install_config.sh
   ```

3. **Set Up Configuration**
   - Copy and edit the example configuration file
   - Set source, destination, and quarantine paths
   - Configure scanner preferences
   - Set up email notifications (optional)

4. **Test Scanner Integration** (if using Microsoft Defender)
   ```bash
   run-shuttle-defender-test
   ```

5. **Start Processing Files**
   ```bash
   run-shuttle
   ```

## Running the Application

### Activating the Environment

```bash
# activate your virtual environment
source /path/to/venv/bin/activate
# set environment variables
source /path/to/config/shuttle_env.sh
```

### Execution Methods

If using Microsoft Defender, run the defender test first to validate that your defender configuration is compatible with shuttle.

This test will use an [EICAR file](https://en.wikipedia.org/wiki/EICAR_test_file), a safe simulation of a malware file to trigger a positive detection by Defender. 

Shuttle will not run unless a test has been run on the current configuration of defender on your system. 

1. **Run defender test first**:
   ```bash
   run-shuttle-defender-test
   ```

2. **Command-line Tool** :
   ```bash
   run-shuttle
   ```


You don't need to provide parameters if they're configured in the settings file.

### Basic Configuration Example

```ini
# ~/.config/shuttle/shuttle_config.ini
[paths]
source_path = /var/shuttle/source
destination_path = /var/shuttle/destination
quarantine_path = /var/shuttle/quarantine
hazard_archive_path = /var/shuttle/hazard

[scanning]
scanner_type = clamav
enable_parallel_scanning = true
max_threads = 4

[notifications]
smtp_server = smtp.example.com
sender_email = shuttle@example.com
recipient_email = admin@example.com
```

See the [Configuration Guide](docs/readme_configuration.md) for all available options.

## Troubleshooting

Common issues and solutions:

- **Single instance lock**: If Shuttle reports it's already running, check for stale lock files in the tracking directory
- **Scanner not found**: Ensure the scanner is installed and accessible in PATH
- **Permission denied**: Verify the service account has appropriate permissions on all configured directories
- **Email notifications failing**: Check SMTP configuration and network connectivity
- **Defender test failing**: Review Defender configuration and ensure real-time protection is enabled

For detailed troubleshooting, check the logs in your configured tracking directory.

## Documentation Index

### Core Documentation
- [Architecture](docs/readme_architecture.md) - System design and component interactions
- [Modules](docs/readme_modules.md) - Detailed description of key modules
- [Configuration](docs/readme_configuration.md) - Configuration options and settings
- [Command Reference](docs/readme_command_reference.md) - Command-line arguments and settings

### Setup and Deployment
- [Development](docs/readme_development.md) - Guide for developers including GPG key generation
- [Deployment Notes](docs/readme_deployment_notes.md) - Instructions for deployment
- [Environment Files](docs/environment_files.md) - Environment variable configuration
- [Cron Notes](docs/readme_cron_notes.md) - Setting up scheduled tasks

### Testing and Development
- [Testing Framework](tests/README.md) - Test suite overview, environment setup, and GPG key generation for tests
- [Test Execution Guide](tests/run.md) - Detailed guide for running tests
- [VSCode Debugging](docs/readme_vscode_remote_python_debugging.md) - Remote debugging guide

### Additional Resources
- [Samba Configuration](docs/samba-config.md) - Setting up Windows file shares
- [Process Diagram](dev_notes/updated_shuttle_process_diagram.md) - Detailed process flow diagram
