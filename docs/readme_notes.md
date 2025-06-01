# Shuttle Linux - File Transfer and Malware Scanning System

**Note:** This system is under active development. Use at your own risk.

`shuttle.py` is a Python application designed to transfer files from a source directory to a destination directory on Ubuntu Linux systems. It includes malware scanning using ClamAV (preferred) and/or Microsoft Defender ATP (`mdatp`), comprehensive file tracking, handling of infected files, and supports parallel processing for efficiency.

The system primarily uses ClamAV for virus scanning, with Microsoft Defender available as an alternative or additional scanner. When both scanners are enabled, files must pass both scans to be considered clean. This dual-scanning approach provides an extra layer of security when needed.

The recommended configuration is to use ClamAV for on-demand scanning through the application, while disabling the application's Microsoft Defender integration. Instead, configure Microsoft Defender for real-time protection on the filesystem. This setup provides both thorough on-demand scanning via ClamAV and continuous real-time protection via Defender, while avoiding potential conflicts or performance issues that might arise from running both scanners simultaneously in on-demand mode.

The application may work on other Linux distributions; however, the installation scripts were written for Ubuntu. If you plan to use Microsoft Defender as a scanner, you'll need to check that it's supported on your distribution. ClamAV is widely available across Linux distributions.

## **Features**

- **File Transfer from Source to Destination:**
  - Copies files from the source directory to a quarantine directory while ensuring files are stable and not being written to.
  - Moves clean files from the quarantine directory to the destination directory after scanning.

- **Comprehensive File Tracking:**
  - Tracks every file using unique hash identifiers
  - Maintains detailed metrics by outcome (success/failure/suspect)
  - Provides summary reports and processing statistics
  - Ensures data persistence with transaction safety

- **Malware Scanning:**
  - Utilizes `clamdscan` and/or `mdatp` to scan each file individually for malware.

- **Handling Infected Files:**
  - When a file is identified as suspicious, it will be handled in one of two ways:
    
    1. **Microsoft Defender Handling** (if configured):
       - If Defender is enabled (either for real-time or on-demand scanning) and configured to handle suspect files
       - Defender will automatically quarantine/archive the infected file according to its settings
       - The application will verify that Defender has removed the file.
    
    2. **Manual Application Handling**:
       - Used when Defender is not configured to handle files or is not being used
       - If hazard archive parameters are provided:
         - Files are encrypted using GPG with the provided public key
         - Encrypted files are moved to the specified hazard archive directory
         - Original filenames and timestamps are preserved in the archive
       - If hazard archive parameters are not provided:
         - Infected files are deleted
         
  - **Source File Handling**:
    - When malware is detected in a quarantine copy, the application also checks the source file
    - If the source file has not been removed by defender and matches the infected quarantine copy, it will be handled according to the manual handling instructions
    - This ensures that infected files are not left in the source directory

- **File Integrity Verification:**
  - Verifies that the source and destination files match by comparing their hashes
  - Ensures data integrity during the transfer process

- **Concurrency and Performance:**
  - Uses `ProcessPoolExecutor` to scan and process files in parallel
  - Limits the number of concurrent scans to optimize resource usage

- **Single Instance Enforcement:**
  - Implements a lock file mechanism to prevent multiple instances of the application from running simultaneously

- **Configuration via Command-Line Arguments or Settings File:**
  - Supports specifying paths and options through command-line arguments
  - Can load settings from a configuration file if arguments are not provided


## **GPG Key Management**

The Shuttle application uses GPG encryption to securely handle potential malware. When a file is flagged as suspicious and cannot be automatically handled by the malware detection tool, Shuttle encrypts it using a public GPG key.

### Generate Encryption Keys

This script will generate keys for testing purposes. For production use, have the team responsible for managing keys provide you with a public key.

```bash
# Run this on a DIFFERENT machine (not the server):
./scripts/0_key_generation/00_generate_shuttle_keys.sh
```

This creates:
- A public key: `shuttle_public.gpg` - Deploy this on the target machine
- A private key: `shuttle_private.gpg` - Keep this secure elsewhere

**IMPORTANT SECURITY NOTES:**
- Only the public key should be deployed on the target machine
- The private key should NEVER be deployed on the server
- If you lose the private key, you will not be able to decrypt files suspected of containing malware

### Configure the Public Key Path

After generating the key pair, configure Shuttle to use the public key by adding the path to your `settings.ini` file:

```ini
[paths]
hazard_encryption_key_path = /path/to/shuttle_public.gpg
```

CAVEATS:

The application supports parallel scanning with a configurable number of concurrent scans,
however either `mdatp` or the parallel libraries seem not to have been stable when used together with reading output from `mdatp`.
Until this is understood, ONLY USE ONE THREAD.


## **Documentation**

This project includes several documentation files for different aspects of the system:

### [Deployment Documentation](readme_deployment.md)
- Complete project structure
- Step-by-step installation instructions
- Virtual environment setup and troubleshooting
- GPG key management for secure file handling
- Disk space throttling configuration

### [Configuration Guide](readme_configuration.md)
- Detailed explanations of all configuration options
- Sample configuration files

### [Cron Job Setup](readme_cron_notes.md)
- Instructions for setting up scheduled tasks
- Example crontab entries

### [VS Code Remote Debugging](readme_vscode_remote_python_debugging.md)
- Setting up VS Code for remote Python debugging
- Working with virtual environments

## **Running the Shuttle Application**

1. **Activate the virtual environment:**

   ```bash
   source ./activate_venv_CALL_BY_SOURCE.sh
   ```

2. **Run the Shuttle Application:**

   Make sure the virtual environment is active.
   You do not need to provide parameters if they are configured in the settings file.
   If you do not configure a hazard archive directory and an encryption key, suspect files will be deleted.

   ```bash
   python3 -m shuttle.shuttle
   ```
   
   When installed via pip, you can also use the console script entry point:
   
   ```bash
   run-shuttle
   ```
   
   Alternatively, if you've set up a bin directory with the shuttle Python script:
   
   ```bash
   python3 /path/to/bin/run_shuttle.py
   ```

Full parameters:

### **Command-Line Arguments:**

- `--source-path`: Path to the source directory containing files to transfer
- `--destination-path`: Path to the destination directory where clean files will be moved
- `--quarantine-path`: Path to the quarantine directory used for scanning
- `--log-path`: Path to store log files (optional)
- `--hazard-archive-path`: Path to store encrypted infected files (optional)
- `--hazard-encryption-key-path`: Path to the GPG public key file for encrypting hazard files (required if hazard-archive-path is set)
- `--delete-source-files-after-copying`: Delete source files after successful transfer (default: False)
- `--max-scan-threads`: Maximum number of parallel scans (default: 1)
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is INFO
- `--lock-file`: Path to the lock file (default: /tmp/shuttle.lock)
- `--defender-handles-suspect-files`: Let Defender handle infected files (default: False)
- `--on-demand-defender`: Use Microsoft Defender for scanning (default: False)
- `--on-demand-clam-av`: Use ClamAV for scanning (default: True)
- `--settings-path`: Path to the settings file (default: ~/.shuttle/settings.ini)
- `--skip-stability-check`: Skip file stability check (testing only, default: False)

**Note:** The application gives priority to command-line arguments over settings file values.

### **Settings File (`settings.ini`):**

If command-line arguments are not provided, the application reads configuration from a settings file in INI format. A complete example `settings.ini` with all available options:

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
throttle=False
throttle_free_space=10000

# Notification settings
notify=False
notify_summary=False
notify_recipient_email=recipient@example.com
notify_sender_email=sender@example.com
notify_smtp_server=smtp.example.com
notify_smtp_port=587
notify_username=username
notify_password=password
notify_use_tls=True

[logging]
log_level=INFO
```

#### Configuration Sections Explained:

**[paths]**
- `source_path` - Directory to scan for files to transfer
- `destination_path` - Directory for clean files after scanning
- `quarantine_path` - Temporary directory for scanning files
- `log_path` - Directory for log files
- `hazard_archive_path` - Directory for encrypted potentially malicious files
- `hazard_encryption_key_path` - Path to GPG public key for encrypting hazard files
- `ledger_file_path` - Path to track tested defender versions
- `lock_file` - Lock file to prevent multiple application instances

**[settings]**
- `max_scan_threads` - Maximum number of parallel scans (default: 1)
- `delete_source_files_after_copying` - Remove source files after successful transfer
- `defender_handles_suspect_files` - Let Defender handle infected files
- `on_demand_defender` - Use Microsoft Defender for scanning
- `on_demand_clam_av` - Use ClamAV for scanning
- `throttle` - Enable disk space throttling
- `throttle_free_space` - Minimum MB of free space required

**[logging]**
- `log_level` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Note:** Command-line arguments override settings file values.

**Note:** The `LogLevel` can be set to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` depending on the desired verbosity.

### **Example Workflow:**

- **Application Operations:**

   - The application performs file hash calculation during the quarantine copy phase
   - Each file is registered with the DailyProcessingTracker for metrics tracking
   - Files in the quarantine directory are scanned in parallel
     - Clean files are moved to the destination directory
     - Infected files are encrypted and moved to the hazard archive
   - The tracker updates file status and metrics based on scan outcomes
   - Source files are optionally deleted after successful processing
   - The quarantine directory is cleaned up after processing
   - On shutdown, the tracker ensures all pending files are properly accounted for

- **Review Results:**

   - Check the destination directory for transferred files
   - Examine the hazard archive for any infected files, if applicable
   - Verify logs and output messages for any errors or issues
   - Review metrics summary for processing statistics

## **Important Notes**

- **Security Considerations:**

  - Ensure only authorized users have access to the application and the directories involved.

- **Error Handling:**

  - The application includes improved error handling with proper lifecycle management
  - Logs and messages should be reviewed to identify and address any issues

- **Testing and Validation:**

  - Thoroughly test the application in a controlled environment before deploying it in production
  - Validate that all operations perform as expected and that files are transferred securely

## **Contributing and Feedback**

This application is a work in progress. Contributions, suggestions, and feedback are welcome to improve its functionality and reliability.

---

## **Additional Commands and Tips**

Here are some additional ClamAV commands that may be useful:

```bash
# Check virus definitions
sudo systemctl stop clamav-freshclam
sudo -u clamav freshclam
sudo systemctl start clamav-freshclam

# Scan a specific file
sudo clamscan -r /path/to/file

# check if freshclam is running
sudo systemctl status clamav-freshclam

# check if clamav is running
sudo systemctl status clamav-daemon

# check if clamav is enabled at startup
sudo systemctl is-enabled clamav-daemon

# check if freshclam is enabled at startup
sudo systemctl is-enabled clamav-freshclam

# check if freshclam is scheduled to run as a cron job
sudo crontab -u clamav -l

# edit the cron job for freshclam
sudo crontab -u clamav -e

```

Here are some additional Microsoft Defender : `mdatp` commands that may be useful:

```bash
# Check health status
mdatp health

# Update definitions
mdatp definition update

# List detected threats
mdatp threat list

# Perform a quick scan
mdatp scan quick

# Perform a full scan
mdatp scan full

# Configure telemetry settings
mdatp config telemetry --value-enabled  # Enable telemetry
mdatp config telemetry --value-disabled # Disable telemetry
```
crontab configuration

```crontab
0 0 * * * /usr/bin/freshclam
```

Feel free to explore the `mdatp` command-line options to better understand its capabilities.



### **Key Management**

The application uses GPG encryption for securing hazard files. You'll need to:

1. **Generate Key Pair**:
   ```bash
   ./generate_keys.sh
   ```
   This will create:
   - `shuttle_public.gpg`: Public key for encrypting hazard files
   - `shuttle_private.gpg`: Private key for decryption (keep secure!)

2. **Key Deployment**:
   - Deploy ONLY the public key (`shuttle_public.gpg`) to production machines
   - Keep the private key secure and OFF the production machine
   - Store the private key securely for later decryption of hazard files

3. **Security Considerations**:
   - Never deploy the private key to production environments
   - Keep the private key backed up securely
   - Only systems that need to decrypt hazard files should have access to the private key
   - The production system only needs the public key for encryption

4. **Configuration**:
   Update your settings.ini with the path to the public key:
   ```ini
   [Settings]
   hazard_encryption_key_path = /path/to/shuttle_public.gpg
   ```

**Note:** The separation of public and private keys ensures that even if the production system is compromised, encrypted hazard files cannot be decrypted without access to the private key stored elsewhere.



### Virus Scanning Options

The application supports two virus scanners:
- **ClamAV** (Default and preferred scanner)
- **Microsoft Defender** (Alternative or additional scanner)

You can configure which scanners to use through these parameters:

```ini
[settings]
on_demand_defender=False  # Use Microsoft Defender for scanning
on_demand_clam_av=True   # Use ClamAV for scanning (recommended)
defender_handles_suspect_files=True  # Let Defender handle infected files
```

These can also be set via command line arguments:
- `--on-demand-defender`: Enable Microsoft Defender scanning
- `--on-demand-clam-av`: Enable ClamAV scanning
- `--defender-handles-suspect-files`: Let Defender handle infected files

At least one scanner must be enabled. For maximum security, you can enable both scanners - files must pass both scans to be considered clean.

## **Shuttle Defender Test**

The `shuttle_defender_test` component is a critical part of maintaining compatibility with Microsoft Defender as it receives updates.

### Purpose

Microsoft Defender receives automatic updates that can change its behavior or command-line interface. The Shuttle application is designed to work with specific known versions of Defender. When an unknown version is encountered, Shuttle will stop processing files to prevent potential issues.

### How It Works

The defender test:
1. Tests compatibility with the currently installed version of Microsoft Defender
2. Updates a ledger file with information about tested versions
3. Allows Shuttle to verify it's working with a compatible Defender version

### Running the Test

```bash
python3 -m shuttle_defender.shuttle_defender_test
```

### Scheduling

Because Defender updates automatically, it's important to schedule this test to run regularly:

```bash
# Example crontab entry to run the test daily
0 2 * * * cd /opt/shuttle && source ./activate_venv_CALL_BY_SOURCE.sh && python3 -m shuttle_defender.shuttle_defender_test
```

### Configuration

The test requires a path to the ledger file where tested versions are recorded:

```ini
[paths]
ledger_file_path=/path/to/ledger.yaml
```

**IMPORTANT:** Without regular testing, Shuttle may stop processing files after a Defender update. Include this test in your maintenance routine.