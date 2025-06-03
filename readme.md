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
         │ (File & Volume Tracking)        │
         │                                 │
         └──────────┬─────────────┬────────┘
                    │             │
                    ▼             ▼
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

Shuttle is a secure file transfer and scanning utility designed to safely move files between directories while performing malware scanning. It features:

- On-demand malware scanning using Microsoft Defender and ClamAV
- Disk space monitoring and throttling to prevent filling up disks
- Secure handling of suspect files (quarantine and encrypted archiving)
- Configurable notification system for errors and status updates
- Proper file integrity verification during transfers
- Comprehensive file tracking and metrics reporting
- Parallel processing for improved performance (experimental - not ready for use)

**Note:** This project is under active development. When using with Microsoft Defender, it's recommended to limit to a single processing thread.

## Core Components

The project is organized into several key components:

1. **Main Shuttle Application** (`shuttle_app`) - The primary file transfer and scanning utility
2. **Defender Test App** (`shuttle_defender_test_app`) - A standalone utility to test Microsoft Defender integration
3. **Common Library** (`shuttle_common`) - Shared utilities used by both applications

## Key Features

### Secure File Transfer
Files are safely moved between source and destination directories with proper integrity checks. The process ensures files are stable (not being written to) before processing, and verifies integrity using file hashes.

### Malware Scanning
Files are scanned using configurable scanners:
- **ClamAV**: Primary recommended scanner
- **Microsoft Defender**: Available as an alternative or additional scanner

When both scanners are enabled, files must pass both scans to be considered clean. The recommended configuration is to use ClamAV for on-demand scanning while configuring Microsoft Defender for real-time protection on the filesystem.

### File Tracking and Metrics
The DailyProcessingTracker component:
- Tracks every processed file with unique hash identifiers
- Maintains comprehensive metrics by outcome category (success/failure/suspect)
- Provides detailed reporting capabilities for operational insights
- Handles persistence of tracking data with transaction safety
- Supports proper shutdown with pending file handling

### Suspect File Handling
When a file is identified as suspicious:
1. **Microsoft Defender Handling** (if configured):
   - Defender automatically quarantines the file according to its settings
   - The script verifies Defender has removed the file
2. **Manual Handling**:
   - Files are encrypted using GPG with a public key
   - Encrypted files are moved to a hazard archive directory
   - Original filenames and timestamps are preserved

### Disk Space Management
Throttling system monitors available disk space in all relevant directories and prevents processing when space is low to avoid filling up disks.

### Logging and Notifications
- Comprehensive logging with configurable levels to syslog and file
- Hierarchy logging shows call chains in DEBUG mode using `@with_logger` decorator
- Email notifications for errors, suspect files, and process completion
- Logger injection pattern provides consistent logging across all modules

### Concurrency and Single Instance
- Uses `ProcessPoolExecutor` for parallel file processing
- Enforces single instance operation via lock file mechanism

## Running the Application

### Activating the Environment

```bash
source ./scripts/1_deployment/05_activate_venv_CALL_BY_SOURCE.sh
```

### Execution Methods

1. **Module Method**:
   ```bash
   python3 -m shuttle.shuttle
   ```

2. **Command-line Tool** (when installed via pip):
   ```bash
   run-shuttle
   ```

3. **Direct Script Execution**:
   ```bash
   python3 /path/to/bin/run_shuttle.py
   ```

You don't need to provide parameters if they're configured in the settings file.

## Documentation Index

- [Architecture](docs/readme_architecture.md) - System design and component interactions
- [Modules](docs/readme_modules.md) - Detailed description of key modules
- [Configuration](docs/readme_configuration.md) - Configuration options and settings
- [Development](docs/readme_development.md) - Guide for developers
- [Command Reference](docs/readme_command_reference.md) - Command-line arguments and settings
- [Deployment Notes](docs/readme_deployment_notes.md) - Instructions for deployment
- [Cron Notes](docs/readme_cron_notes.md) - Setting up scheduled tasks
- [VSCode Debugging](docs/readme_vscode_remote_python_debugging.md) - Remote debugging guide
- [Samba Configuration](docs/samba-config.md) - Setting up Windows file shares
- [Process Diagram](dev_notes/updated_shuttle_process_diagram.md) - Detailed process flow diagram
