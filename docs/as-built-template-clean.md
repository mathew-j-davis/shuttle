---
title: "As-Built Documentation - Shuttle File Transfer System"
output:
  word_document:
    reference_doc: as-built-shuttle-file-transfer-system.docx
---


# Shuttle File Transfer System - As-Built Documentation

## Document Information
- **Installation Date**: [DATE]
- **Document Version**: 1.0
- **Prepared By**: [YOUR NAME]
- **Organization**: [ORGANIZATION]

---

## Executive Summary

This document provides comprehensive as-built documentation for the Shuttle file transfer system installation. Shuttle is a secure file processing system that scans incoming files for malware before delivering them to a publishing destination.

### What Shuttle Does

Shuttle reads files from a source directory and processes them through malware scanning. 
Shuttle delivers clean files to a destination directory while isolating suspicious files in an encrypted archive. 
It's designed for environments that need automated, secure file transfer with guaranteed malware protection.

### How It Works

1. **File Detection**: Reads files from source directory
2. **Quarantine**: Moves files to isolated quarantine area
3. **Hash Generation**: Creates file integrity checksums
4. **Malware Scanning**: Scans files using Microsoft Defender and/or ClamAV
5. **Clean Delivery**: Moves clean files to destination directory
6. **Threat Isolation**: Encrypts and archives any suspicious files
7. **Notification**: Sends email alerts for errors and threats

### Key Security Features
- **Zero-trust processing**: All files quarantined before scanning
- **Encrypted threat storage**: Malware archived with GPG encryption
- **Process isolation**: Service accounts with minimal privileges
- **Single-instance enforcement**: Prevents concurrent processing conflicts
- **Comprehensive logging**: All actions logged to files and syslog

## 2. System Requirements and Prerequisites

## Shuttle Server

<!---
check kernel version
uname -r

check ubuntu version
lsb_release -a

check cpu
lscpu

check ram 
free --mega
-->

- **Server Hostname**: []
- **Server IP Address**: []

### Operating System
- **OS**: Ubuntu 24.04.2 LTS
- **Kernel**: []
- **Architecture**: x86_64

### Software Dependencies
- Python 3.8 or higher
- Microsoft Defender for Linux (mdatp)
- ClamAV (optional)
- Samba (for Windows file sharing)

### Hardware Requirements
- **CPU**: [CPU SPECS]
- **RAM**: [RAM AMOUNT]
- **Disk Space**: 
  - System: [SYSTEM DISK]
  - Source Path: [SOURCE DISK/MOUNT]
  - Quarantine Path: [QUARANTINE DISK/MOUNT]
  - Destination Path: [DESTINATION DISK/MOUNT]


### Hardware 

- **CPU**: 
  - Vendor ID:            []
  - Model name:           []
  - CPU family:           []
  - Model:                []
  - Thread(s) per core:   []
  - Core(s) per socket:   []
  - Socket(s):            []
  
- **RAM**: 
  - [] MB (according to free --mega)

  
- **Disk Space**:
  - System:           []
  - Source Path:      /mnt/in                   [] GB
  - Quarantine Path:  /mnt/quarantine           [] GB
  - Hazard Path:      /mnt/hazard               [] GB
  - Destination Path: /mnt/out                  [] GB



## Installation Configuration

### Paths

| Directory    | Path                                    | Purpose                         |
|--------------|-----------------------------------------|---------------------------------|
| venv         | /opt/shuttle/venv                       | Python virtual environment      |
| installation | /opt/shuttle/venv/bin                   | Application source code         |
| config       | /etc/shuttle                            | Config and keys, write via sudo |
| ledger       | /etc/shuttle/ledger.yaml                | Processing ledger file          |
| logs         | /var/log/shuttle                        | Log directory                   |
| source       | /mnt/in                                 | Samba users via ACL (future)    |
| quarantine   | /mnt/quarantine                         | Service accounts only           |
| hazard       | /mnt/hazard                             | Malware isolation               |
| destination  | /mnt/out                                | Network users via ACL (future)  |
| tests        | /var/tmp/shuttle/tests/                 | Tests                           |
| test config  | /var/tmp/shuttle/tests/test_config.yaml | Test configuration file         |
| test work    | /var/tmp/shuttle/tests/test_area        | Temporary test area             |
| scripts      | /usr/local/bin/launch-shuttle           | Launch wrapper for shuttle      |
| scripts      | /usr/local/bin/launch-shuttle-defender-test | Launch wrapper for defender test |
| executables  | /opt/shuttle/venv/bin/run-shuttle           | Pip entry point for shuttle      |
| executables  | /opt/shuttle/venv/bin/run-shuttle-defender-test | Pip entry point for defender test |

### Access Control 

#### Groups
| Group                | Purpose                              | Owned Directories                                        |
|----------------------|--------------------------------------|----------------------------------------------------------|
| shuttle_common_users | Read config, write logs, read ledger | /etc/shuttle (r), /var/log/shuttle (rw), ledger.json (r) |
| shuttle_owners       | Own all data directories             | /mnt/in, /mnt/quarantine, /mnt/hazard, /mnt/out          |
| shuttle_testers      | Run tests                            | /var/tmp/shuttle/tests/                                  |

#### Local Accounts
| Account                      | Shell             | Primary Purpose          | Group Memberships                                           |
|------------------------------|-------------------|--------------------------|-------------------------------------------------------------|
| shuttle_runner               | /usr/sbin/nologin | Main shuttle application | shuttle_common_users, shuttle_owners                        |
| shuttle_defender_test_runner | /usr/sbin/nologin | Defender testing         | shuttle_common_users                                        |
| shuttle_tester               | /usr/sbin/nologin | Testing                  | shuttle_testers                                             |
| shuttle_admin                | /usr/sbin/nologin | Admin                    | shuttle_common_users, shuttle_owners, shuttle_testers, sudo |

### Group Path Permissions

note: where a group has read access to a directory they have +x for the directory, but not files

| group                  | venv          | installation   | config        | ledger   | logs           | source         | quarantine     | hazard         | destination    | tests          | test config   | test work      |
|------------------------|---------------|----------------|---------------|----------|----------------|----------------|----------------|----------------|----------------|----------------|---------------|----------------|
| *                      | r (dir: +x)   | r (dir: +x)    |               |          |                |                |                |                |                |                |               |                |
| shuttle_common_users   |               |                | r (dir: +x)   | r        | rw (dir: +x)   |                |                |                |                |                |               |                |
| shuttle_owners         |               |                |               |          |                | rw (dir: +x)   | rw (dir: +x)   | rw (dir: +x)   | rw (dir: +x)   |                |               |                |
| shuttle_testers        |               |                |               |          |                |                |                |                |                | rw (dir: +x)   | rw            | rw (dir: +x)   |


### User Level Path Permissions

| user direct                  | venv | installation | config | ledger | logs | source | quarantine | hazard | destination | tests | test config | test work |
|------------------------------|------|--------------|--------|--------|------|--------|------------|--------|-------------|-------|-------------|-----------|
| shuttle_defender_test_runner |      |              |        | rw     |      |        |            |        |             |       |             |           |


### User Path Permissions + User Group Path Permissions

| user direct + groups         | venv        | installation | config      | ledger | logs         | source       | quarantine   | hazard       | destination  | tests        | test config | test work    |
|------------------------------|-------------|--------------|-------------|--------|--------------|--------------|--------------|--------------|--------------|--------------|-------------|--------------|
| shuttle_defender_test_runner | r (dir: +x) | r (dir: +x)  | r (dir: +x) | rw     | rw (dir: +x) |              |              |              |              |              |             |              |
| shuttle_runner               | r (dir: +x) | r (dir: +x)  | r (dir: +x) | r      | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) |              |             |              |
| shuttle_tester               | r (dir: +x) | r (dir: +x)  |             |        |              |              |              |              |              | rw (dir: +x) | rw          | rw (dir: +x) |
| shuttle_admin                | r (dir: +x) | r (dir: +x)  | r (dir: +x) | r      | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw          | rw (dir: +x) |
| shuttle_admin + sudo         | rw (dir:+x) | rw (dir:+x)  | rw (dir:+x) | rw     | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw          | rw (dir: +x) |

### Access information organised by path

| Directory   | Path                                    | Owner                        | Group                | Directory Mode   | File Mode        | Owner Dir | Owner File | Group Dir | Group File | Other Dir | Other File | ACL Users | Notes                                                           |
|-------------|-----------------------------------------|------------------------------|----------------------|------------------|------------------|-----------|------------|-----------|------------|-----------|------------|-----------|-----------------------------------------------------------------|
| venv        | /opt/shuttle/venv                       | root                         | root                 | 0755 (rwxr-xr-x) | 0644 (rw-r--r--) | rwx       | rw-        | r-x       | r--        | r-x       | r--        | -         | Python virtual environment, and installation of shuttle modules |
| config      | /etc/shuttle                            | root                         | shuttle_common_users | 2750 (rwxr-s---) | 0640 (rw-r-----) | rwx       | rw-        | r-x       | r--        | ---       | ---        | -         | Config and keys, write via sudo                                 |
| ledger      | /etc/shuttle/ledger.yaml                | shuttle_defender_test_runner | shuttle_common_users | N/A              | 0640 (rw-r-----) | N/A       | rw-        | N/A       | r--        | N/A       | ---        | -         | Processing ledger file                                          |
| logs        | /var/log/shuttle                        | root                         | shuttle_common_users | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Log directory                                                   |
| source      | /mnt/in                                 | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Samba users via ACL (future)                                    |
| quarantine  | /mnt/quarantine                         | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Service accounts only                                           |
| hazard      | /mnt/hazard                             | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Malware isolation                                               |
| destination | /mnt/out                                | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Network users via ACL (future)                                  |
| tests       | /var/tmp/shuttle/tests/                 | root                         | shuttle_testers      | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Tests                                                           |
| test config | /var/tmp/shuttle/tests/test_config.yaml | root                         | shuttle_testers      | N/A              | 0660 (rw-rw----) | N/A       | rw-        | N/A       | rw-        | N/A       | ---        | -         | Test configuration file                                         |
| test work   | /var/tmp/shuttle/tests/test_area        | root                         | shuttle_testers      | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Temporary test area                                             |
| scripts     | /usr/local/bin/launch-shuttle           | root                         | root                 | N/A              | 0755 (rwxr-xr-x) | N/A       | rwx        | N/A       | r-x        | N/A       | r-x        | -         | Launch script with environment setup for shuttle                |
| scripts     | /usr/local/bin/launch-shuttle-defender-test | root                     | root                 | N/A              | 0755 (rwxr-xr-x) | N/A       | rwx        | N/A       | r-x        | N/A       | r-x        | -         | Launch script with environment setup for defender test          |
| executables | /opt/shuttle/venv/bin/run-shuttle           | root                     | root                 | N/A              | 0755 (rwxr-xr-x) | N/A       | rwx        | N/A       | r-x        | N/A       | r-x        | -         | Pip-installed entry point for shuttle application               |
| executables | /opt/shuttle/venv/bin/run-shuttle-defender-test | root                 | root                 | N/A              | 0755 (rwxr-xr-x) | N/A       | rwx        | N/A       | r-x        | N/A       | r-x        | -         | Pip-installed entry point for defender test application         |


### Environment Variables 

| Variable             | Value                            | Purpose                              |
|----------------------|----------------------------------|--------------------------------------|
| VIRTUAL_ENV          | /opt/shuttle/venv                | Virtual environment path             |
| PATH                 | /opt/shuttle/venv/bin:$PATH      | Include virtual environment binaries |
| SHUTTLE_CONFIG_PATH  | /etc/shuttle/config.conf         | Primary configuration file           |


## Shuttle Configuration

### Configuration File

Location: `/etc/shuttle/config.conf`

```ini

[paths]
log_path = /var/log/shuttle
ledger_file_path = /etc/shuttle/ledger.yaml
hazard_encryption_key_path = /etc/shuttle/shuttle_public.gpg
daily_processing_tracker_logs_path = /var/log/shuttle

source_path = /mnt/in
quarantine_path = /mnt/quarantine
hazard_archive_path = /mnt/hazard
destination_path = /mnt/out

[settings]
max_scan_threads = 1
throttle_max_file_count_per_run = 1000
throttle_max_file_volume_per_run_mb = 1024
throttle_max_file_volume_per_day_mb = 0
throttle_max_file_count_per_day = 0
delete_source_files_after_copying = True
defender_handles_suspect_files = True
on_demand_defender = True
on_demand_clam_av = False
throttle = True
throttle_free_space_mb = 100

[logging]
#log level during testing
log_level=DEBUG

#final production value
# log_level = INFO

[scanning]
malware_scan_timeout_seconds = 60
malware_scan_timeout_ms_per_byte = 0.01
malware_scan_retry_wait_seconds = 30
malware_scan_retry_count = 5

[notifications]
notify = True
notify_summary = True
recipient_email = shuttle-notifications@host.com
recipient_email_error = shuttle-error@host.com
recipient_email_summary = shuttle-notifications@host.com
recipient_email_hazard = shuttle-alert@host.com
sender_email = 
smtp_server = 
smtp_port = 25
username = 
password = 
use_tls = True

```