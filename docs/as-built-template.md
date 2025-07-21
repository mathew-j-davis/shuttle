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

This document provides comprehensive as-built documentation for the Shuttle file transfer system installation. Shuttle is a secure, automated file transfer solution that implements a quarantine-first approach with integrated malware scanning capabilities.

### 1.1 Key Features
- Quarantine-first file processing pipeline
- Multi-scanner support (Microsoft Defender, ClamAV)
- Automated file integrity verification
- Configurable throttling and daily processing limits
- Syslog and email notification integration
- Single-instance enforcement to prevent concurrent runs

### 1.2 Architecture Overview
```
Source Directory → Quarantine → Malware Scan → Clean/Suspect → Destination/Hazard Archive
```

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
```

### 3.2 Service Accounts
| Account | Type | Purpose | Shell | Home Directory |
|---------|------|---------|-------|----------------|
| [SERVICE_USER] | Service | Shuttle service account | /usr/sbin/nologin | [HOME_PATH] |
| [ADMIN_USER] | Admin | Administrative access | /bin/bash | [HOME_PATH] |

### 3.3 Group Memberships
| Group | Members | Purpose |
|-------|---------|---------|
| [GROUP_NAME] | [USER1, USER2] | [PURPOSE] |
| shuttle_admins | [ADMIN_USERS] | Administrative access |
| shuttle_users | [STANDARD_USERS] | Standard file transfer access |

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

### 5.3 File System Permissions
| Directory | Owner | Group | Permissions | ACL |
|-----------|-------|-------|-------------|-----|
| [PATH] | [OWNER] | [GROUP] | [PERMS] | [ACL_ENTRIES] |

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
- **Vendor Support**: Anthropic (Claude Code) - https://github.com/anthropics/claude-code/issues

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