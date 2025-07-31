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
| installation | /opt/shuttle                            | Application source code         |
| config       | /etc/shuttle                            | Config and keys, write via sudo |
| ledger       | /var/log/shuttle/ledger.json            | Processing ledger file          |
| logs         | /var/log/shuttle                        | Log directory                   |
| source       | /mnt/in                                 | Samba users via ACL (future)    |
| quarantine   | /mnt/quarantine                         | Service accounts only           |
| hazard       | /mnt/hazard                             | Malware isolation               |
| destination  | /mnt/out                                | Network users via ACL (future)  |
| tests        | /var/tmp/shuttle/tests/                 | Tests                           |
| test config  | /var/tmp/shuttle/tests/test_config.yaml | Test configuration file         |
| test work    | /var/tmp/shuttle/tests/test_area        | Temporary test area             |

### Access Control 

#### Groups
| Group                | Purpose                              | Owned Directories                                        |
|----------------------|--------------------------------------|----------------------------------------------------------|
| shuttle_common_users | Read config, write logs, read ledger | /etc/shuttle (r), /var/log/shuttle (rw), ledger.json (r) |
| shuttle_owners       | Own all data directories             | /mnt/in, /mnt/quarantine, /mnt/hazard, /mnt/out          |
| shuttle_testers      | Run tests                            | /var/tmp/shuttle/tests/                                  |

#### Local Accounts
| Account                 | Shell             | Primary Purpose          | Group Memberships                                           |
|-------------------------|-------------------|--------------------------|-------------------------------------------------------------|
| shuttle_runner          | /usr/sbin/nologin | Main shuttle application | shuttle_common_users, shuttle_owners                        |
| shuttle_defender_tester | /usr/sbin/nologin | Defender testing         | shuttle_common_users                                        |
| shuttle_tester          | /usr/sbin/bash    | Testing                  | shuttle_testers                                             |
| shuttle_admin           | /usr/sbin/bash    | Admin                    | shuttle_common_users, shuttle_owners, shuttle_testers, sudo |

### Group Path Permissions

note: where a group has read access to a directory they have +x for the directory, but not files

| group                  | venv          | installation   | config        | ledger   | logs           | source         | quarantine     | hazard         | destination    | tests          | test config   | test work      |
|------------------------|---------------|----------------|---------------|----------|----------------|----------------|----------------|----------------|----------------|----------------|---------------|----------------|
| *                      | r (dir: +x)   | r (dir: +x)    |               |          |                |                |                |                |                |                |               |                |
| shuttle_common_users   |               |                | r (dir: +x)   | r        | rw (dir: +x)   |                |                |                |                |                |               |                |
| shuttle_owners         |               |                |               |          |                | rw (dir: +x)   | rw (dir: +x)   | rw (dir: +x)   | rw (dir: +x)   |                |               |                |
| shuttle_testers        |               |                |               |          |                |                |                |                |                | rw (dir: +x)   | rw            | rw (dir: +x)   |


### User Level Path Permissions

| user direct             | venv | installation | config | ledger | logs | source | quarantine | hazard | destination | tests | test config | test work |
|-------------------------|------|--------------|--------|--------|------|--------|------------|--------|-------------|-------|-------------|-----------|
| shuttle_defender_tester |      |              |        | rw     |      |        |            |        |             |       |             |           |


### User Path Permissions + User Group Path Permissions

| user direct + groups    | venv        | installation | config      | ledger | logs         | source       | quarantine   | hazard       | destination  | tests        | test config | test work    |
|-------------------------|-------------|--------------|-------------|--------|--------------|--------------|--------------|--------------|--------------|--------------|-------------|--------------|
| shuttle_defender_tester | r (dir: +x) | r (dir: +x)  | r (dir: +x) | rw     | rw (dir: +x) |              |              |              |              |              |             |              |
| shuttle_runner          | r (dir: +x) | r (dir: +x)  | r (dir: +x) | r      | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) |              |             |              |
| shuttle_tester          | r (dir: +x) | r (dir: +x)  |             |        |              |              |              |              |              | rw (dir: +x) | rw          | rw (dir: +x) |
| shuttle_admin           | r (dir: +x) | r (dir: +x)  | r (dir: +x) | r      | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw          | rw (dir: +x) |
| shuttle_admin + sudo    | rw (dir:+x) | rw (dir:+x)  | rw (dir:+x) | rw     | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw (dir: +x) | rw          | rw (dir: +x) |

### Access information organised by path

| Directory   | Path                                    | Owner                        | Group                | Directory Mode   | File Mode        | Owner Dir | Owner File | Group Dir | Group File | Other Dir | Other File | ACL Users | Notes                                                           |
|-------------|-----------------------------------------|------------------------------|----------------------|------------------|------------------|-----------|------------|-----------|------------|-----------|------------|-----------|-----------------------------------------------------------------|
| venv        | /opt/shuttle/venv                       | root                         | root                 | 0755 (rwxr-xr-x) | 0644 (rw-r--r--) | rwx       | rw-        | r-x       | r--        | r-x       | r--        | -         | Python virtual environment, and installation of shuttle modules |
| config      | /etc/shuttle                            | root                         | shuttle_common_users | 2750 (rwxr-s---) | 0640 (rw-r-----) | rwx       | rw-        | r-x       | r--        | ---       | ---        | -         | Config and keys, write via sudo                                 |
| ledger      | /etc/shuttle/ledger.json                | shuttle_defender_test_runner | shuttle_common_users | N/A              | 0640 (rw-r-----) | N/A       | rw-        | N/A       | r--        | N/A       | ---        | -         | Processing ledger file                                          |
| logs        | /var/log/shuttle                        | root                         | shuttle_common_users | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Log directory                                                   |
| source      | /mnt/in                                 | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Samba users via ACL (future)                                    |
| quarantine  | /mnt/quarantine                         | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Service accounts only                                           |
| hazard      | /mnt/hazard                             | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Malware isolation                                               |
| destination | /mnt/out                                | root                         | shuttle_owners       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Network users via ACL (future)                                  |
| tests       | /var/tmp/shuttle/tests/                 | root                         | shuttle_testers      | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Tests                                                           |
| test config | /var/tmp/shuttle/tests/test_config.yaml | root                         | shuttle_testers      | N/A              | 0660 (rw-rw----) | N/A       | rw-        | N/A       | rw-        | N/A       | ---        | -         | Test configuration file                                         |
| test work   | /var/tmp/shuttle/tests/test_area        | root                         | shuttle_testers      | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx       | rw-        | rwx       | rw-        | ---       | ---        | -         | Temporary test area                                             |


### Environment Variables 

| Variable             | Value                            | Purpose                              |
|----------------------|----------------------------------|--------------------------------------|
| VIRTUAL_ENV          | /opt/shuttle/venv                | Virtual environment path             |
| PATH                 | /opt/shuttle/venv/bin:$PATH      | Include virtual environment binaries |
| SHUTTLE_CONFIG_PATH  | /etc/shuttle/shuttle_config.yaml | Primary configuration file           |





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

## Security Configuration

### Firewall Rules 

### Samba Configuration

#### Environment File Location

```bash
# Production environment variables
/etc/shuttle/shuttle_env.sh

# Source in cron or systemd:
source /etc/shuttle/shuttle_env.sh
```

---

## Automation and Scheduling

### Cron Jobs
```bash
# User: [CRON_USER]
# Crontab location: [PATH]

[SCHEDULE] [COMMAND] # [DESCRIPTION]

# Example:
45 7 * * MON-FRI su shuttle_defender_tester -c "/usr/local/bin/run-shuttle-defender-test >> /var/log/shuttle/defender-test-cron.log 2>&1"
* 8-18 * * MON-FRI su shuttle_runner -c "/usr/local/bin/run-shuttle >> /var/log/shuttle/shuttle-cron.log 2>&1"
```

### Permission Mode Explanation

#### Directory Modes (2xxx indicates setgid)
- **2750**: rwxr-s--- (Owner: full, Group: read/execute, Others: none, setgid)
- **2755**: rwxr-sr-x (Owner: full, Group: read/execute, Others: read/execute, setgid)
- **2770**: rwxrws--- (Owner: full, Group: full, Others: none, setgid)
- **2775**: rwxrwsr-x (Owner: full, Group: full, Others: read/execute, setgid)

#### File Modes
- **0640**: rw-r----- (Owner: read/write, Group: read, Others: none)
- **0644**: rw-r--r-- (Owner: read/write, Group: read, Others: read)
- **0660**: rw-rw---- (Owner: read/write, Group: read/write, Others: none)
- **0664**: rw-rw-r-- (Owner: read/write, Group: read/write, Others: read)

#### ACL Notation
- **rwX**: Read, write, execute on directories only (capital X)
- **r-X**: Read, execute on directories only
- **rwx**: Read, write, execute (lowercase x includes files - avoided for data)

### 5.6 Environment Variables and Paths

#### System Environment Variables
| Variable | Value | Purpose | Set In |
|----------|-------|---------|--------|
| PATH | /opt/shuttle/venv/bin:$PATH | Include virtual environment binaries | /etc/shuttle/shuttle_env.sh |
| PYTHONPATH | /opt/shuttle/src | Python module search path | /etc/shuttle/shuttle_env.sh |
| SHUTTLE_CONFIG_PATH | /etc/shuttle/shuttle_config.yaml | Primary configuration file | /etc/shuttle/shuttle_env.sh |
| SHUTTLE_INSTALL_MODE | service | Installation mode indicator | /etc/shuttle/shuttle_env.sh |
| VIRTUAL_ENV | /opt/shuttle/venv | Virtual environment path | Activation script |

#### Path Summary (Production Defaults)
| Path Type | Location | Environment Variable |
|-----------|----------|---------------------|
| Installation | /opt/shuttle | N/A |
| Virtual Environment | /opt/shuttle/venv | VIRTUAL_ENV |
| Configuration | /etc/shuttle/shuttle_config.yaml | SHUTTLE_CONFIG_PATH |
| Source | /mnt/in | (from config file) |
| Destination | /mnt/out | (from config file) |
| Quarantine | /mnt/quarantine | (from config file) |
| Hazard | /mnt/hazard | (from config file) |
| Logs | /var/log/shuttle | (from config file) |
| Test Config | /etc/shuttle/test_config.yaml | (from config file) |
| Test Work | /var/tmp/shuttle/test_area | (from config file) |

#### Environment File Location
```bash
# Production environment variables
/etc/shuttle/shuttle_env.sh

# Source in cron or systemd:
source /etc/shuttle/shuttle_env.sh
```

---

## 6. Malware Scanning Configuration

### 6.1 Microsoft Defender
```bash
# Status
mdatp health --field licensed
mdatp health --field real_time_protection_enabled

# Configuration
Real-time Protection: [ENABLED/DISABLED]
Cloud Protection: [ENABLED/DISABLED]
Archive Scanning: [ENABLED/DISABLED]
```

### 6.2 ClamAV (if configured)
```bash
# Database location: [PATH]
# Update frequency: [SCHEDULE]
# Configuration file: [PATH]
```

---

## 7. Automation and Scheduling

### 7.1 Cron Jobs
```bash
# User: [CRON_USER]
# Crontab location: [PATH]

[SCHEDULE] [COMMAND] # [DESCRIPTION]

# Example:
*/5 * * * * /usr/local/bin/run-shuttle >> /var/log/shuttle/cron.log 2>&1
```

### 7.2 Systemd Services (if applicable)
```ini
# Service name: shuttle.service
# Location: /etc/systemd/system/shuttle.service

[Unit]
Description=[DESCRIPTION]
After=[DEPENDENCIES]

[Service]
Type=[TYPE]
User=[USER]
ExecStart=[COMMAND]
Environment=[ENV_VARS]

[Install]
WantedBy=[TARGET]
```

---

## 8. Monitoring and Logging

### 8.1 Log Locations
| Log Type | Location | Rotation Policy | Retention |
|----------|----------|-----------------|-----------|
| Application | [PATH] | [POLICY] | [DAYS] |
| Syslog | [PATH] | [POLICY] | [DAYS] |
| Audit | [PATH] | [POLICY] | [DAYS] |

### 8.2 Monitoring Integration
- **Syslog Server**: [SERVER:PORT]
- **SIEM Integration**: [DETAILS]
- **Alerting**: [EMAIL/SNMP/OTHER]

---

## 9. Network Configuration

### 9.1 Network Interfaces
```
Interface: [INTERFACE_NAME]
IP Address: [IP_ADDRESS/SUBNET]
Gateway: [GATEWAY]
DNS Servers: [DNS1, DNS2]
```

### 9.2 Network Shares
| Share Path | Mount Point | Protocol | Authentication |
|------------|-------------|----------|----------------|
| [UNC_PATH] | [MOUNT] | [SMB/NFS] | [METHOD] |

---

## 10. Operational Procedures

### 10.1 Daily Operations
1. **Automated Processing**: Runs every [INTERVAL] via cron
2. **Log Review**: Check [LOG_PATH] for errors
3. **Email Notifications**: Sent to [EMAIL_ADDRESSES]

### 10.2 Maintenance Tasks
| Task | Frequency | Procedure |
|------|-----------|-----------|
| Log rotation | Daily | Automated via logrotate |
| Malware DB update | [FREQUENCY] | [PROCEDURE] |
| Disk space check | [FREQUENCY] | [PROCEDURE] |

### 10.3 Emergency Procedures
1. **Service Failure**: [PROCEDURE]
2. **Disk Full**: [PROCEDURE]
3. **Malware Detection**: [PROCEDURE]

---

## 11. Backup and Recovery

### 11.1 Backup Configuration
- **Configuration Files**: [BACKUP_LOCATION]
- **Backup Schedule**: [SCHEDULE]
- **Retention Policy**: [POLICY]

### 11.2 Recovery Procedures
1. **Configuration Recovery**: [PROCEDURE]
2. **Service Restoration**: [PROCEDURE]

---

## 12. Testing and Validation

### 12.1 Installation Validation
```bash
# Test commands executed:
[COMMAND] # Expected result: [RESULT]
```

### 12.2 Functional Testing
| Test Case | Procedure | Expected Result | Actual Result |
|-----------|-----------|-----------------|---------------|
| File transfer | [PROCEDURE] | [EXPECTED] | [ACTUAL] |
| Malware detection | [PROCEDURE] | [EXPECTED] | [ACTUAL] |

---

## 13. Known Issues and Limitations

### 13.1 Known Limitations
- Maximum path length: 260 characters (Windows compatibility)
- Empty directory cleanup requires multiple runs due to mtime updates
- Single instance enforcement may delay processing during long scans

### 13.2 Workarounds
| Issue | Workaround |
|-------|------------|
| [ISSUE] | [WORKAROUND] |

---

## 14. Support and Maintenance

### 14.1 Support Contacts
- **Primary Contact**: [NAME] - [EMAIL] - [PHONE]
- **Backup Contact**: [NAME] - [EMAIL] - [PHONE]
- **Technical Documentation**: See /home/mathew/shuttle/CLAUDE.md for development guidance

### 14.2 Documentation
- **Source Code**: [REPOSITORY_URL]
- **User Guide**: [LOCATION]
- **Admin Guide**: [LOCATION]

---

## 15. Change Log

| Date | Version | Change Description | Changed By |
|------|---------|-------------------|------------|
| [DATE] | 1.0 | Initial installation | [NAME] |

---

## Appendices

### Appendix A: Complete Configuration Files
[Include full configuration file contents]

### Appendix B: Security Audit Results
[Include output from security_audit.py]

### Appendix C: Network Diagram
[Include network topology diagram]

### Appendix D: Directory Structure
```
/path/to/shuttle/
├── src/
├── scripts/
├── docs/
└── ...
```

---

**Document End**