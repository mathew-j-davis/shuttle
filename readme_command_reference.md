# Shuttle Command-Line and Configuration Reference

This document provides detailed information about command-line arguments and configuration file options for the Shuttle application.

## Command-Line Arguments

- `-SourcePath`: Path to the source directory containing files to transfer
- `-DestinationPath`: Path to the destination directory where clean files will be moved
- `-QuarantinePath`: Path to the quarantine directory used for scanning
- `-LogPath`: Path to store log files (optional)
- `-HazardArchivePath`: Path to store encrypted infected files (optional)
- `-HazardEncryptionKeyPath`: Path to the GPG public key file for encrypting hazard files (required if HazardArchivePath is set)
- `-DeleteSourceFiles`: Delete source files after successful transfer (default: False)
- `-MaxScanThreads`: Maximum number of parallel scans (default: 1)
- `-LogLevel`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is INFO
- `-LockFile`: Path to the lock file (default: /tmp/shuttle.lock)
- `-DefenderHandlesSuspectFiles`: Let Defender handle infected files (default: False)
- `-OnDemandDefender`: Use Microsoft Defender for scanning (default: False)
- `-OnDemandClamAV`: Use ClamAV for scanning (default: True)
- `-SettingsPath`: Path to the settings file (default: ~/.shuttle/settings.ini)

**Note:** The application gives priority to command-line arguments over settings file values.

## Settings File Format

The application reads configuration from a settings file in INI format when command-line arguments are not provided. Here's a complete example `settings.ini` with all available options:

```ini
[paths]
# Required path settings
source_path=/path/to/source
destination_path=/path/to/destination
quarantine_path=/path/to/quarantine

# Optional path settings
log_path=/path/to/logs
hazard_archive_path=/path/to/hazard_archive
hazard_encryption_key_path=/path/to/shuttle_public.gpg
ledger_file_path=/path/to/ledger.yaml
lock_file=/tmp/shuttle.lock

[settings]
# Scanning settings
max_scan_threads=1
delete_source_files_after_copying=True
defender_handles_suspect_files=True
on_demand_defender=False
on_demand_clam_av=True

# Throttle settings
throttle=True
throttle_free_space=10000

[logging]
# Logging settings
log_level=INFO
notify=True
notify_summary=True
notify_recipient_email=admin@example.com
notify_sender_email=shuttle@example.com
notify_smtp_server=smtp.example.com
notify_smtp_port=587
notify_smtp_username=username
notify_smtp_password=password
notify_use_tls=True
```

## Configuration Sections

### [paths]
- `source_path` - Directory to copy files from
- `destination_path` - Directory to move clean files to
- `quarantine_path` - Temporary storage for scanning
- `log_path` - Directory to store log files
- `hazard_archive_path` - Directory to store encrypted infected files
- `hazard_encryption_key_path` - Path to GPG public key
- `ledger_file_path` - Path to track tested defender versions
- `lock_file` - Lock file to prevent multiple instances

### [settings]
- `max_scan_threads` - Maximum number of parallel scans (default: 1)
- `delete_source_files_after_copying` - Remove source files after transfer
- `defender_handles_suspect_files` - Let Defender handle infected files
- `on_demand_defender` - Use Microsoft Defender for scanning
- `on_demand_clam_av` - Use ClamAV for scanning
- `throttle` - Enable disk space checking
- `throttle_free_space` - Minimum MB to maintain

### [logging]
- `log_level` - Logging detail level (DEBUG, INFO, WARNING, ERROR)
- `notify` - Enable email notifications
- `notify_summary` - Send summary at completion
- `notify_recipient_email` - Email address to notify
- `notify_sender_email` - Sender email address
- `notify_smtp_*` - SMTP server configuration

## Scanner Configuration Notes

### ClamAV (Primary Scanner)
- Enabled by default (`on_demand_clam_av=True`)
- Uses `clamdscan` which requires the ClamAV daemon to be running
- Update virus definitions with `sudo freshclam`

### Microsoft Defender
- Disabled by default (`on_demand_defender=False`)
- Can be used alongside or instead of ClamAV
- Can be configured to handle infected files (`defender_handles_suspect_files=True`)
- Known to have threading issues - use `max_scan_threads=1` when enabled

When both scanners are enabled, files must pass both scans to be considered clean.
