---
theme: base
title: "Shuttle Linux - File Transfer and Malware Scanning ScriptRemote Access for Lab Equipment and Systems - CSIRO Energy Siemens CT Scanner Integration"
author: Mat Davis
date: 2024-12-15
version: 0.1
output: word_document

---



# Shuttle Linux - File Transfer and Malware Scanning Script

**Note:** This script is under active development and has not been fully tested. Use at your own risk.

`shuttle.py` is a Python script designed to transfer files from a source directory to a destination directory on Ubuntu Linux systems. It includes malware scanning using ClamAV (preferred) and/or Microsoft Defender ATP (`mdatp`), handling of infected files, and supports parallel processing for efficiency. 

The script primarily uses ClamAV for virus scanning, with Microsoft Defender available as an alternative or additional scanner. When both scanners are enabled, files must pass both scans to be considered clean. This dual-scanning approach provides an extra layer of security when needed.

The recommended configuration is to use ClamAV for on-demand scanning through the script, while disabling the script's Microsoft Defender integration. Instead, configure Microsoft Defender for real-time protection on the filesystem. This setup provides both thorough on-demand scanning via ClamAV and continuous real-time protection via Defender, while avoiding potential conflicts or performance issues that might arise from running both scanners simultaneously in on-demand mode.

The script may work on other Linux distributions; however, the installation scripts were written for Ubuntu. If you plan to use Microsoft Defender as a scanner, you'll need to check that it's supported on your distribution. ClamAV is widely available across Linux distributions.

## **Features**

- **File Transfer from Source to Destination:**
  - Copies files from the source directory to a quarantine directory while ensuring files are stable and not being written to.
  - Moves clean files from the quarantine directory to the destination directory after scanning.

- **Malware Scanning:**
  - Utilizes `clamdscan` and or `mdatp` to scan each file individually for malware.

- **Handling Infected Files:**
  - When a file is identified as suspicious, it will be handled in one of two ways:
    
    1. **Microsoft Defender Handling** (if configured):
       - If Defender is enabled (either for real-time or on-demand scanning) and configured to handle suspect files
       - Defender will automatically quarantine/archive the infected file according to its settings
       - The script will verify that Defender has removed the file.
    
    2. **Manual Script Handling**:
       - Used when Defender is not configured to handle files or is not being used
       - If hazard archive parameters are provided:
         - Files are encrypted using GPG with the provided public key
         - Encrypted files are moved to the specified hazard archive directory
         - Original filenames and timestamps are preserved in the archive
       - If hazard archive parameters are not provided:
         - Infected files are deleted
         
  - **Source File Handling**:
    - When malware is detected in a quarantine copy, the script also checks if the source file.
    - If the source file has not been removed by defender and matches the infected quarantine copy, it will be handled according to the manual handling instructions.
    - This ensures that infected files are not left in the source directory

- **File Integrity Verification:**
  - Verifies that the source and destination files match by comparing their hashes.
  - Ensures data integrity during the transfer process.

- **Concurrency and Performance:**
  - Uses `ProcessPoolExecutor` to scan and process files in parallel.
  - Limits the number of concurrent scans to optimize resource usage.

- **Single Instance Enforcement:**
  - Implements a lock file mechanism to prevent multiple instances of the script from running simultaneously.

- **Configuration via Command-Line Arguments or Settings File:**
  - Supports specifying paths and options through command-line arguments.
  - Can load settings from a configuration file if arguments are not provided.


## **Generate encryption keys**

  This script will generate keys for testing purposes.
  For production use, have the team responsible for managing keys provide you with a public key.

  Run this script on a different machine. 
  It will generate two keys
  - a public key  :   ~/.shuttle/shuttle_public.gpg
  - a private key :   ~/.shuttle/shuttle_private.gpg

  This script can be found in
  ```
  /0_set_up_scripts_to_run_on_other_machine
  ```

  ```bash
  ./00_generate_shuttle_keys.sh
  ```

Keep these keys somewhere secure.

If you lose the private key you will not be able to decrypt files suspected of containing malware.

Copy only the public key ~/.shuttle/shuttle_public.gpg to the server

DO NOT put the private key on the server

CAVEATS:

This script support parallel scanning with a configurable number of concurrent scans,
however either `mdatp` or the parallel libraries seem not to have been stable when used together with reading output from `mdatp`.
Until this is understood, ONLY USE ONE THREAD.


## **Deploy Scripts**

Copy the files in 

```
/1_deployment/shuttle
```

to your host

eg.:

```
~/shuttle/
```

## **Environment Set Up Scripts**

To install all the necessary system packages and Python dependencies, use the provided scripts in:

```
/2_set_up_scripts_to_run_on_host
```

These scripts were tested running from the application root. After setup, they are not required on the host machine. However as the functionality of the virtual environment activation script may be useful on the host machine a separate copy of:

```
/set_up_scripts_to_run_on_host/04_activate_venv_CALL_BY_SOURCE.sh
```

is included in the deployment scripts:

```
1_deployment/shuttle/activate_venv_CALL_BY_SOURCE.sh
```

- **First make the scripts executable:**

   ```bash
   chmod +x ./*.sh
   ```

   ```bash
   chmod +x ./*.py
   ```

- **Run the Scripts:**

- **Install required supporting applications**
  
   ```bash
   ./01_install_dependencies.sh
   ```
   This installs lsof and gnupg.

- **Set up Python Environment**
   ```bash
   ./02_install_python.sh
   ```

- **Create a Virtual Environment:**

   ```bash
   ./03_create_venv.sh
   ```

  This script sets up a python virtual environment

  ```bash
   python3 -m venv venv
   ```


- **Activate virtual environment**
  
   ```bash
   source ./04_activate_venv_CALL_BY_SOURCE.sh
   ```

  The virtual environment must be activated, this is what the script does:

  ```bash
   source venv/bin/activate
   ```
   - **Set up python dependencies**

   ```bash
   ./05_install_python_dependencies.sh
   ```

    After activating the virtual environment, this script installs the Python packages specified in `requirements.txt`:

   ```bash
   pip install -r requirements.txt
   ```

- **Install ClamAV**
   ```bash
   ./06_install_clamav.sh
   ```
   After installation, ClamAV will be enabled and virus definitions will be updated.
   However ClamAV needs to have access to the directory it will scan.
   You may need to use ACL to provide access to the `clamav` user.


   - **Set up working environment config**
  
  This script sets up working files, a settings file and creates a global scope exception for the working folder to stop automatic Microsoft Defender scans interfering with the scripted scanning process.
  If you do not have permission to change exceptions on your machine this process will not work

  ```bash
   python3 ./07_setup_test_environment_linux.py

   ```
   This script:
   - Creates working directories
   - Generates a default settings file
   - If using Defender, creates exclusions for working folders

**Note:** The script will check for the availability of these external commands at runtime. If any are missing, it will log an error and exit.

1. **Run the Shuttle Script:**

Make sure the virtual environment is active.
You do not need to provide parameters if parameters are configured in the settings file
If you do not configure a hazard archive directory and an encryption key, suspect files will be deleted.

Execute `run_shuttle.py` with the desired parameters or ensure the `settings.ini` file is properly configured.

```bash
python3 run_shuttle.py
```

Full parameters:

### **Command-Line Arguments:**

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

**Note:** The script gives priority to command-line arguments over settings file values.

### **Settings File (`settings.ini`):**

If command-line arguments are not provided, the script will attempt to read from a settings file in INI format. An example `settings.ini` might look like:

```ini
[Paths]
source_path=/path/to/source
destination_path=/path/to/destination
quarantine_path=/path/to/quarantine
log_path=/path/to/logs
hazard_archive_path=/path/to/hazard_archive
hazard_encryption_key_path=/path/to/shuttle_public.gpg

[Settings]
max_scan_threads=4
delete_source_files_after_copying=True
on_demand_defender=False
on_demand_clam_av=True
defender_handles_suspect_files=True

[Logging]
log_level=DEBUG

```

**Note:** The script gives priority to command-line arguments over the settings 
file.

**Note:** The `LogLevel` can be set to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` depending on the desired verbosity.

### **Example Workflow:**

- **Script Operations:**

   - The script copies files from the source to the quarantine directory, skipping files that are unstable or open.
   - Files in the quarantine directory are scanned in parallel.
     - Clean files are moved to the destination directory.
     - Infected files are encrypted and moved to the hazard archive.
   - Source files are optionally deleted after successful processing.
   - The quarantine directory is cleaned up after processing.

- **Review Results:**

   - Check the destination directory for transferred files.
   - Examine the hazard archive for any infected files, if applicable.
   - Verify logs and output messages for any errors or issues.

## **Important Notes**

- **Security Considerations:**

  - Ensure only authorized users have access to the script and the directories involved.

- **Error Handling:**

  - The script includes basic error handling but may require enhancements for production use.
  - Logs and messages should be reviewed to identify and address any issues.

- **Testing and Validation:**

  - Thoroughly test the script in a controlled environment before deploying it in production.
  - Validate that all operations perform as expected and that files are transferred securely.

## **Contributing and Feedback**

This script is a work in progress. Contributions, suggestions, and feedback are welcome to improve its functionality and reliability.

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

The script uses GPG encryption for securing hazard files. You'll need to:

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


## Development 

### Adding New Configuration Parameters

When adding new configuration parameters, the following files and code sections need to be updated:

1. **ShuttleConfig Class Definition**
   ```python:1_deployment/shuttle/shuttle.py
   @dataclass
   class ShuttleConfig:
       # Add new parameter with type hint
       # Don't forget Optional[] for optional parameters
   ```

2. **Argument Parser**
   ```python:1_deployment/shuttle/shuttle.py
   def parse_config():
       parser.add_argument('-NewParameter',
                         help='Description of the new parameter',
                         type=type,  # If needed
                         default=default_value)  # If needed
   ```

3. **Settings File Processing**
   ```python:1_deployment/shuttle/shuttle.py
   # In parse_config():
   new_parameter = get_setting(
       args.NewParameter, 
       'section_name',  # Usually 'paths' or 'settings'
       'parameter_name', 
       default=default_value
   )
   ```

4. **ShuttleConfig Object Creation**
   ```python:1_deployment/shuttle/shuttle.py
   settings_file_config = ShuttleConfig(
       # Add new parameter to constructor
       new_parameter=new_parameter
   )
   ```

5. **Example Settings File**
   ```ini:2_set_up_scripts_to_run_on_host/settings.ini.example
   [section_name]
   parameter_name=default_value
   ```

6. **Function Parameters**
   - If the parameter is used in functions like `scan_and_process_directory()`, update their signatures and calls
   - Update any helper functions that need access to the new parameter

7. **Documentation**
   - Update README.md with parameter description
   - Update command-line help text
   - Update any relevant comments in the code

8. **Test Files**
   - Update test configuration files if they exist
   - Add new test cases for the parameter

### Example

Adding a new parameter 'max_retries':

1. **ShuttleConfig**:
   ```python
   @dataclass
   class ShuttleConfig:
       max_retries: int
   ```

2. **Argument Parser**:
   ```python
   parser.add_argument('-MaxRetries', 
                      type=int,
                      help='Maximum number of retry attempts',
                      default=3)
   ```

3. **Settings Processing**:
   ```python
   max_retries = get_setting(
       args.MaxRetries, 
       'settings',
       'max_retries', 
       default=3
   )
   ```

4. **Config Creation**:
   ```python
   settings_file_config = ShuttleConfig(
       max_retries=max_retries,
       # ... other parameters ...
   )
   ```

5. **Settings File**:
   ```ini
   [settings]
   max_retries=3
   ```

### Virus Scanning Options

The script supports two virus scanners:
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
- `-OnDemandDefender`: Enable Microsoft Defender scanning
- `-OnDemandClamAV`: Enable ClamAV scanning
- `-DefenderHandlesSuspectFiles`: Let Defender handle infected files

At least one scanner must be enabled. For maximum security, you can enable both scanners - files must pass both scans to be considered clean.

```

## Setup and Installation

1. **Install Required Supporting Applications**
   ```bash
   ./01_install_dependencies.sh
   ```

   The script ensures these commands are installed and accessible:

   - **lsof**:
     ```bash
     sudo apt-get install lsof
     ```
     
   - **gpg**:
     ```bash
     sudo apt-get install gnupg
     ```

   - **ClamAV** (Primary virus scanner):
     ```bash
     sudo apt-get install clamav clamav-daemon
     ```
     After installation:
     ```bash
     sudo systemctl start clamav-daemon  # Start the daemon
     sudo systemctl enable clamav-daemon # Enable at start-up
     sudo freshclam                      # Update virus definitions
     ```

   - **Microsoft Defender** (Optional):
     If you plan to use Microsoft Defender, follow the [official installation guide](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually)

2. **Set up Python Environment**
   ```bash
   ./02_install_python.sh
   ./03_create_venv.sh
   source ./04_activate_venv_CALL_BY_SOURCE.sh
   ./05_install_python_dependencies.sh
   ```

3. **Configure Working Environment**
   ```bash
   python3 ./06_setup_test_environment_linux.py
   ```
   This script:
   - Creates working directories
   - Generates a default settings file
   - If using Defender, creates exclusions for working folders

The recommended configuration is to:
1. Enable ClamAV for on-demand scanning (`on_demand_clam_av=True`)
2. Disable Defender's on-demand scanning (`on_demand_defender=False`)
3. Configure Microsoft Defender for real-time protection if desired
```
