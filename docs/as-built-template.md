# Shuttle File Transfer System - As-Built Documentation

## Document Information
- **Installation Date**: [DATE]
- **Document Version**: 1.0
- **Prepared By**: [YOUR NAME]
- **Organization**: [ORGANIZATION]
- **Server Hostname**: [HOSTNAME]
- **Server IP Address**: [IP ADDRESS]

---

## 1. Executive Summary

This document provides comprehensive as-built documentation for the Shuttle file transfer system installation. Shuttle is a secure file processing system that automatically scans incoming files for malware before delivering them to their final destination.

### 1.1 What Shuttle Does
Shuttle monitors a source directory for new files, automatically processes them through malware scanning, and delivers clean files to a destination directory while isolating suspicious files in an encrypted archive. It's designed for environments that need automated, secure file transfer with guaranteed malware protection.

### 1.2 How It Works
1. **File Detection**: Monitors source directory for new files
2. **Quarantine**: Immediately moves all files to isolated quarantine area
3. **Hash Generation**: Creates file integrity checksums
4. **Malware Scanning**: Scans files using Microsoft Defender and/or ClamAV
5. **Clean Delivery**: Moves clean files to destination directory
6. **Threat Isolation**: Encrypts and archives any suspicious files
7. **Notification**: Sends email alerts for errors and threats

### 1.3 Key Security Features
- **Zero-trust processing**: All files quarantined before scanning
- **Encrypted threat storage**: Malware archived with AES encryption
- **Process isolation**: Service accounts with minimal privileges
- **Single-instance enforcement**: Prevents concurrent processing conflicts
- **Comprehensive logging**: All actions logged to syslog and files

---

## 2. System Requirements and Prerequisites

### 2.1 Operating System
- **OS**: Ubuntu Server 20.04 LTS / 22.04 LTS
- **Kernel**: [KERNEL VERSION]
- **Architecture**: x86_64

### 2.2 Software Dependencies
- Python 3.8 or higher
- Microsoft Defender for Linux (mdatp)
- ClamAV (optional)
- Samba (for Windows file sharing)
- UFW (Uncomplicated Firewall)
- Postfix or equivalent (for email notifications)

### 2.3 Hardware Requirements
- **CPU**: [CPU SPECS]
- **RAM**: [RAM AMOUNT]
- **Disk Space**: 
  - System: [SYSTEM DISK]
  - Source Path: [SOURCE DISK/MOUNT]
  - Quarantine Path: [QUARANTINE DISK/MOUNT]
  - Destination Path: [DESTINATION DISK/MOUNT]

---

## 3. Installation Configuration

### 3.1 Installation Paths
```
Shuttle Installation Directory: [INSTALLATION PATH]
Configuration Directory: [CONFIG PATH]
Virtual Environment: [VENV PATH]
Log Directory: [LOG PATH]
Installation Defaults Config: [INSTALLATION PATH]/config/installation_defaults.conf
```

### 3.2 User Account Structure

#### Service Accounts
| Account | Type | Shell | Primary Purpose | Group Memberships |
|---------|------|-------|-----------------|-------------------|
| shuttle_runner | Service | /usr/sbin/nologin | Main shuttle application | shuttle_common_users, shuttle_owners |
| shuttle_defender_test_runner | Service | /usr/sbin/nologin | Defender testing | shuttle_common_users |
| shuttle_tester | Service | /usr/sbin/nologin | Application testing | shuttle_testers |

#### Network Users (ACL-based access only)
| Account | Type | Shell | Primary Purpose | Group Memberships |
|---------|------|-------|-----------------|-------------------|
| shuttle_samba_in_user | Network | /usr/sbin/nologin | Inbound file submission via Samba | shuttle_samba_in_users |
| shuttle_out_user | Network | /usr/sbin/nologin | Outbound file retrieval | shuttle_out_users |

#### Administrative Users
| Account | Type | Shell | Primary Purpose | Group Memberships |
|---------|------|-------|-----------------|-------------------|
| [ADMIN_USER] | Admin | /bin/bash | System administration | shuttle_admins, sudo |

### 3.3 Group Structure

#### Owner Groups (Directory ownership)
| Group | Purpose | Owned Directories |
|-------|---------|-------------------|
| shuttle_common_users | Read config, write logs, read ledger | /etc/shuttle (r), /var/log/shuttle (rw), ledger.json (r) |
| shuttle_owners | Own all data directories | /mnt/in, /mnt/quarantine, /mnt/hazard, /mnt/out |
| shuttle_testers | Run tests | /var/tmp/shuttle/test_area |

#### Access Groups (ACL-based access - Optional for future use)
| Group | Purpose | ACL Access To |
|-------|---------|---------------|
| shuttle_samba_in_users | Network inbound access (future use) | /mnt/in (rw), /mnt/out (r) |
| shuttle_out_users | Network outbound access (future use) | /mnt/out (rw) |

#### Administrative Groups
| Group | Purpose | Members |
|-------|---------|---------|
| shuttle_admins | Full administrative access | [ADMIN_USERS] |

---

## 4. Shuttle Configuration

### 4.1 Primary Configuration (shuttle_config.yaml)
```yaml
# Location: [CONFIG_FILE_PATH]

[general]
source_path = [SOURCE_PATH]
destination_path = [DESTINATION_PATH]
quarantine_path = [QUARANTINE_PATH]
hazard_archive_path = [HAZARD_ARCHIVE_PATH]
delete_source_files = [true/false]
save_clean_files = [true/false]

[processing]
max_threads = [NUMBER]
skip_stability_check = [true/false]
symlinks_disabled = [true/false]

[throttling]
warning_threshold_percent = [PERCENT]
error_threshold_percent = [PERCENT]
daily_file_size_limit_gb = [GB_LIMIT]
daily_file_count_limit = [FILE_COUNT]

[notifications]
enabled = [true/false]
smtp_server = [SMTP_SERVER]
smtp_port = [PORT]
sender_email = [SENDER_EMAIL]
recipient_email = [RECIPIENT_EMAIL]
recipient_email_error = [ERROR_EMAIL]
recipient_email_summary = [SUMMARY_EMAIL]
recipient_email_hazard = [HAZARD_EMAIL]

[scanning]
malware_scan_timeout_seconds = [TIMEOUT]
malware_scan_retry_wait_seconds = [WAIT]
malware_scan_retry_count = [COUNT]

[logging]
syslog_enabled = [true/false]
syslog_address = [SYSLOG_SERVER]
syslog_port = [PORT]
syslog_facility = [FACILITY]
```

### 4.2 Processing Paths
| Path Type | Location | Purpose | Permissions |
|-----------|----------|---------|-------------|
| Source | [PATH] | Input files | [PERMS] |
| Quarantine | [PATH] | Temporary isolation | [PERMS] |
| Destination | [PATH] | Clean files | [PERMS] |
| Hazard Archive | [PATH] | Suspect files | [PERMS] |
| Test Config | [PATH] | Test scenario definitions | [PERMS] |
| Test Work | [PATH] | Temporary test execution area | [PERMS] |

---

## 5. Security Configuration

### 5.1 Firewall Rules (UFW)
```bash
# Inbound Rules
[RULE_NUMBER] [ACTION] [PORT/PROTOCOL] from [SOURCE] to [DESTINATION] comment '[DESCRIPTION]'

# Outbound Rules
[RULE_NUMBER] [ACTION] [PORT/PROTOCOL] from [SOURCE] to [DESTINATION] comment '[DESCRIPTION]'

# Example:
# ufw allow from 192.168.1.0/24 to any port 445 comment 'Samba from trusted network'
```

### 5.2 Samba Configuration
```ini
# Location: /etc/samba/smb.conf

[global]
workgroup = [WORKGROUP]
server string = [SERVER_STRING]
security = user
map to guest = never

# Share definitions
[shuttle_source]
path = [SOURCE_PATH]
valid users = [USER_LIST]
read only = no
create mask = 0660
directory mask = 0770

[shuttle_destination]
path = [DESTINATION_PATH]
valid users = [USER_LIST]
read only = yes
```

### 5.3 Access Control Matrix

| User/Group                   | config | key | ledger        | logs | source     | quarantine | hazard | destination | tests | test work |
|------------------------------|--------|-----|---------------|------|------------|------------|--------|-------------|-------|-----------|
| shuttle_runner               | r      | r   | r             | rw   | rw         | rw         | rw     | rw          |       |           |
| shuttle_defender_test_runner | r      | r   | r             | rw   |            |            |        |             |       |           |
| shuttle_samba_in_users       |        |     |               |      | rw via ACL |            |        | r via ACL   |       |           |
| shuttle_out_users            |        |     |               |      |            |            |        | rw via ACL  |       |           |
| shuttle_testers              |        |     |               |      |            |            |        |             | rwx   | rw        |

### 5.4 Directory Ownership and Permissions Model

| Directory   | Path                          | Owner | Group                      | Directory Mode   | File Mode        | Owner Perms           | Group Perms           | Other Perms           | ACL Users                                             | Notes                     |
|-------------|-------------------------------|-------|----------------------------|------------------|------------------|-----------------------|-----------------------|-----------------------|-------------------------------------------------------|---------------------------|
| config      | /etc/shuttle                  | root  | shuttle_common_users       | 2750 (rwxr-s---) | 0640 (rw-r-----) | rwx (dir), rw- (file) | r-x (dir), r-- (file) | ---                   | None                                                  | Config and keys, write via sudo |
| quarantine  | /mnt/quarantine               | root  | shuttle_owners             | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx (dir), rw- (file) | rwx (dir), rw- (file) | ---                   | None                                                  | Service accounts only     |
| hazard      | /mnt/hazard                   | root  | shuttle_owners             | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx (dir), rw- (file) | rwx (dir), rw- (file) | ---                   | None                                                  | Malware isolation         |
| destination | /mnt/out                      | root  | shuttle_owners             | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx (dir), rw- (file) | rwx (dir), rw- (file) | ---                   | shuttle_samba_in_users (r-X), shuttle_out_users (rwX) | Network users via ACL (future) |
| test config | /etc/shuttle/test_config.yaml | root  | shuttle_testers            | 0664 (rw-rw-r--) | -                | rw- (file)            | rw- (file)            | r-- (file)            | None                                                  | Test configuration file   |
| ledger      | /var/log/shuttle/ledger.json  | root  | shuttle_common_users       | 0640 (rw-r-----) | -                | rw- (file)            | r-- (file)            | ---                   | None                                                  | Processing ledger file    |
| logs        | /var/log/shuttle              | root  | shuttle_common_users       | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx (dir), rw- (file) | rwx (dir), rw- (file) | ---                   | None                                                  | Log directory             |
| test work   | /var/tmp/shuttle/test_area    | root  | shuttle_testers            | 2770 (rwxrws---) | 0660 (rw-rw----) | rwx (dir), rw- (file) | rwx (dir), rw- (file) | ---                   | None                                                  | Temporary test area       |
| source      | /mnt/in                       | root  | shuttle_owners             | 2775 (rwxrwsr-x) | 0664 (rw-rw-r--) | rwx (dir), rw- (file) | rwx (dir), rw- (file) | r-x (dir), r-- (file) | shuttle_samba_in_users (rwX)                          | Samba users via ACL (future) |
| venv        | /opt/shuttle/venv             | root  | root                       | 0755 (rwxr-xr-x) | 0644 (rw-r--r--) | rwx (dir), rw- (file) | r-x (dir), r-- (file) | r-x (dir), r-- (file) | None                                                  | Python virtual environment |
| installation| /opt/shuttle                  | root  | root                       | 0755 (rwxr-xr-x) | 0644 (rw-r--r--) | rwx (dir), rw- (file) | r-x (dir), r-- (file) | r-x (dir), r-- (file) | None                                                  | Application source code    |

### 5.5 Permission Mode Explanation

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