# Shuttle Linux - File Transfer and Malware Scanning Script

**Note:** This script is under active development and has not been fully tested. Use at your own risk.

`shuttle-linux.py` is a Python script designed to securely transfer files from a source directory to a destination directory on Linux systems. It includes malware scanning using Microsoft Defender ATP (`mdatp`), handling of infected files, and supports parallel processing for efficiency.

## **Features**

- **File Transfer from Source to Destination:**
  - Copies files from the source directory to a quarantine directory while ensuring files are stable and not being written to.
  - Moves clean files from the quarantine directory to the destination directory after scanning.

- **Malware Scanning:**
  - Utilizes `mdatp` to scan each file individually for malware.
  - Supports parallel scanning with a configurable number of concurrent scans.

- **Handling Infected Files:**
  - If malware is detected, files are compressed and encrypted using a provided password.
  - Encrypted archives are moved to a specified hazard archive directory for further analysis.
  - If hazard archive parameters are not provided, infected files are deleted.

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

## **Usage**

```bash
python shuttle-linux.py \
    -SourcePath /path/to/source \
    -DestinationPath /path/to/destination \
    -QuarantinePath /path/to/quarantine \
    -QuarantineHazardArchive /path/to/hazard_archive \
    -HazardArchivePassword your_secure_password \
    --max-scans 4 \
    -DeleteSourceFilesAfterCopying
```

### **Command-Line Arguments:**

- `-SourcePath`: Path to the source directory containing files to transfer.
- `-DestinationPath`: Path to the destination directory where clean files will be moved.
- `-QuarantinePath`: Path to the quarantine directory used for scanning.
- `-SettingsPath`: Path to the settings file (default: `~/.shuttle/settings.txt`).
- `-TestSourceWriteAccess`: Test write access to the source directory.
- `-DeleteSourceFilesAfterCopying`: Delete the source files after successful transfer.
- `--max-scans`: Maximum number of parallel scans (default: `2`).
- `--lock-file`: Path to the lock file to prevent multiple instances (default: `/tmp/shuttle.lock`).
- `-QuarantineHazardArchive`: Path to the hazard archive directory for infected files.
- `-HazardArchivePassword`: Password for encrypting the hazard archive.

### **Settings File:**

If command-line arguments are not provided, the script will attempt to read from a settings file. An example `settings.txt` might look like:

```
SourcePath=/path/to/source
DestinationPath=/path/to/destination
QuarantinePath=/path/to/quarantine
QuarantineHazardArchive=/path/to/hazard_archive
HazardArchivePassword=your_secure_password
LogPath=/path/to/logs
```

### **Prerequisites:**

- **Python 3** installed on the system.
- **Microsoft Defender ATP (`mdatp`)** installed and configured.
  - [Installation Guide](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually)
- **Required Utilities:**
  - `lsof`: For checking if files are open.
    ```bash
    sudo apt-get install lsof  # For Debian/Ubuntu
    ```
  - `zip`: For compressing and encrypting files.
    ```bash
    sudo apt-get install zip
    ```

### **Example Workflow:**

1. **Set Up Test Environment:**
   - Use the provided `setup_test_environment_linux.py` script to create test directories and files.

2. **Run the Shuttle Script:**
   - Execute `shuttle-linux.py` with the desired parameters.

3. **Script Operations:**
   - The script copies files from the source to the quarantine directory, skipping files that are unstable or open.
   - Files in the quarantine directory are scanned in parallel.
     - Clean files are moved to the destination directory.
     - Infected files are compressed, encrypted, and moved to the hazard archive.
   - Source files are optionally deleted after successful processing.
   - The quarantine directory is cleaned up after processing.

4. **Review Results:**
   - Check the destination directory for transferred files.
   - Examine the hazard archive for any infected files, if applicable.
   - Verify logs and output messages for any errors or issues.

## **Important Notes:**

- **Security Considerations:**
  - Handle passwords securely; avoid exposing them in scripts or command-line arguments when possible.
  - Ensure only authorized users have access to the script and the directories involved.

- **Error Handling:**
  - The script includes basic error handling but may require enhancements for production use.
  - Logs and messages should be reviewed to identify and address any issues.

- **Testing and Validation:**
  - Thoroughly test the script in a controlled environment before deploying it in production.
  - Validate that all operations perform as expected and that files are transferred securely.

- **Limitations:**
  - The script assumes that `mdatp` is installed and operational.
  - The `zip` utility's encryption may not meet all security requirements; consider using stronger encryption methods if necessary.

## **Contributing and Feedback:**

This script is a work in progress. Contributions, suggestions, and feedback are welcome to improve its functionality and reliability.

---

The first version of these scripts were developed for windows using powershell.

These are no longer being developed.


powershell script to move files from a network share, scan for malware, then move to destination location

USE AT OWN RISK, THIS IS STILL UNDER DEVELOPMENT, AND NOT FULLY TESTED.

Roboshuttle.ps1 - Robocopy wrapper script

Usage:
.\roboshuttle.ps1 -SourcePath <network_share_path> -DestinationPath <path> -QuarantinePath <path> -SettingsPath <path> -TestSourceWriteAccess

Ronoshuttle is simpler than shuttle, as it uses robocopy under the hood to move files from source to destination.
However, because of the need to scan the files while they are in the quarantine directory, we cannot rely on robocopy's move feature to delete the source files.

At present the 'delete on successful copy' function is not implemented in roboshuttle.




Shuttle.ps1 - File Transfer Script

Usage:
.\shuttle.ps1 [-SourcePath <network_share_path>] [-DestinationPath <path>] [-QuarantinePath <path>] [-SettingsPath <path>] [-TestSourceWriteAccess]

Description:
This script facilitates file transfer operations from a network file share to a destination.
It requires write access to the source directory for file deletion after successful transfer.

Parameters:
-SourcePath           : (Optional) Path to the source network file share (e.g., \\server\share)
-DestinationPath      : (Optional) Path to the destination directory
-QuarantinePath             : (Optional) Path to the temporary quarantine directory
-SettingsPath         : (Optional) Path to the settings file (default: %USERPROFILE%\.shuttle\settings.txt)
-TestSourceWriteAccess: (Optional) Test write access to the source directory (default: $false)

Settings File:
If not provided as parameters, the script will look for SourcePath, DestinationPath and TempPath
in the settings file. A sample settings file (settings.txt) might look like this:

SourcePath=\\server\share
DestinationPath=C:\Users\YourUsername\Documents\Destination
TempPath=C:\Temp\ShuttleTemp

Note: Command-line parameters take precedence over settings file values.
SourcePath must be a network file share if provided.



```

mdatp health

 mdatp definition update

mdatp threat list


mdatp scan quick



mdatp scan full



mdatp config telemetry --value-enabled | --value-disabled


```