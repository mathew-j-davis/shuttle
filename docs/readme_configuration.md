# Shuttle Configuration

## Configuration Files

Shuttle looks for configuration files in several locations, following standard Linux conventions:

1. Command-line specified path (`--settings-path`)
2. Environment variable: `SHUTTLE_CONFIG_PATH`
3. User-specific locations:
   - `~/.config/shuttle/config.conf`
   - `~/.shuttle/config.conf`
   - `~/.shuttle/settings.ini`
4. System-wide locations:
   - `/etc/shuttle/config.conf`
   - `/usr/local/etc/shuttle/config.conf`

## Settings Format

Configuration files use INI format with sections and key-value pairs:

```ini
[paths]
source_path = /path/to/source
destination_path = /path/to/destination
quarantine_path = /path/to/quarantine
hazard_archive_path = /path/to/hazard

[settings]
delete_source_files = false
max_scan_threads = 4
on_demand_defender = true
on_demand_clam_av = true
throttle = true
throttle_free_space = 10000

[logging]
log_path = /var/log/shuttle
log_level = INFO

[notifications]
notify = false
notify_summary = true
notify_recipient_email = admin@example.com
notify_sender_email = shuttle@example.com
notify_smtp_server = smtp.example.com
notify_smtp_port = 587
```

## Configuration Classes

### CommonConfig

Base configuration class with shared settings:

- `log_path`: Path for log files
- `log_level`: Logging level (INFO, DEBUG, etc.)
- `notify`: Enable/disable notifications
- `notify_summary`: Send summary notifications after each run
- `notify_*`: SMTP settings for notifications
- `ledger_path`: Path to Defender version ledger
- `defender_handles_suspect_files`: Let Defender handle suspect files

### ShuttleConfig

Extended configuration for the main application:

- `source_path`: Directory to process files from
- `destination_path`: Directory to move clean files to
- `quarantine_path`: Temporary directory for scanning
- `hazard_archive_path`: Directory for encrypted suspect files
- `hazard_encryption_key_file_path`: Public key for encrypting suspect files
- `lock_file`: Path to the lock file to prevent concurrent runs
- `delete_source_files`: Whether to delete source files after processing
- `max_scan_threads`: Number of parallel scan threads
- `on_demand_defender`: Use Microsoft Defender
- `on_demand_clam_av`: Use ClamAV
- `throttle`: Enable disk space throttling
- `throttle_free_space`: Minimum free space to maintain (MB)

## Command Line Arguments

The same settings can be provided via command line arguments:

```
--source-path /path/to/source
--destination-path /path/to/destination
--quarantine-path /path/to/quarantine
--hazard-archive-path /path/to/hazard
--delete-source-files-after-copying
--max-scan-threads 4
--on-demand-defender
--on-demand-clam-av
--throttle
--throttle-free-space 10000
--log-path /var/log/shuttle
--log-level INFO
--skip-stability-check
```

## Setting Precedence

Settings are applied with the following priority:
1. Command line arguments (highest)
2. Configuration file
3. Default values (lowest)

## Configuration Best Practices

### File Permissions
- Set appropriate permissions to prevent unauthorized access or modification
- For system-wide configurations in `/etc/shuttle/`, use restricted permissions

### Backups
- Regularly back up configuration files, especially before making changes
- Include configuration files in system backup routines

### Environment Variables
- `SHUTTLE_CONFIG_PATH` can be set in the environment to specify a custom location
- Consider setting this in a system startup script for consistent configuration
