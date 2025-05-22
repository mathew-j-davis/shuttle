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
Comprehensive logging with configurable levels and email notifications for errors, suspect files, and process completion.

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

- [Architecture](Architecture.md) - System design and component interactions
- [Modules](Modules.md) - Detailed description of key modules
- [Configuration](Configuration.md) - Configuration options and settings
- [Development](Development.md) - Guide for developers
- [Command Reference](Command_Reference.md) - Command-line arguments and settings
