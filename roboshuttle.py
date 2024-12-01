import os
import sys
import argparse
import subprocess
import configparser
from datetime import datetime

def get_path_value(parameter_value, settings, key):
    if parameter_value:
        print(f"Using provided parameter for {key}: {parameter_value}")
        return parameter_value
    elif key in settings:
        print(f"Using settings file value for {key}: {settings[key]}")
        return settings[key]
    else:
        return None

def test_for_malware(scan_path, delete_files_on_threat):
    try:
        print(f"Scanning files in {scan_path} for malware...")
        scan_command = [
            r"C:\Program Files\Windows Defender\MpCmdRun.exe",
            "-Scan", "-ScanType", "3", "-File", scan_path
        ]
        result = subprocess.run(scan_command, capture_output=True, text=True)
        if result.returncode == 0:
            print("Malware scan completed successfully. No threats detected.")
            return False
        else:
            print(f"Malware scan detected threats or failed with exit code: {result.returncode}")
    except Exception as e:
        print(f"Failed to perform malware scan. Error: {e}")

    if delete_files_on_threat:
        print(f"Deleting all files in {scan_path}")
        subprocess.run(["powershell", "-Command", f"Remove-Item -Path '{scan_path}\\*' -Recurse -Force"])
    return True

def main():
    parser = argparse.ArgumentParser(description='File Transfer Script')
    parser.add_argument('-SourcePath', help='Path to the source network file share')
    parser.add_argument('-DestinationPath', help='Path to the destination directory')
    parser.add_argument('-QuarantinePath', help='Path to the quarantine directory')
    parser.add_argument('-LogPath', help='Path to the log directory')
    parser.add_argument('-SettingsPath', default=r"C:\TestEnvironment\.shuttle\settings.txt",
                        help='Path to the settings file')
    parser.add_argument('-TestSourceWriteAccess', action='store_true', help='Test write access to the source directory')
    parser.add_argument('-DeleteSourceFilesAfterCopying', action='store_true',
                        help='Delete the source files after copying them to the destination')
    args = parser.parse_args()

    # Load settings from file if not provided as arguments
    settings = {}
    if os.path.exists(args.SettingsPath):
        config = configparser.ConfigParser()
        config.read(args.SettingsPath)
        if 'DEFAULT' in config:
            settings = dict(config['DEFAULT'])
        print(f"Loaded settings from {args.SettingsPath}")

    source_path = get_path_value(args.SourcePath, settings, 'SourcePath')
    destination_path = get_path_value(args.DestinationPath, settings, 'DestinationPath')
    quarantine_path = get_path_value(args.QuarantinePath, settings, 'QuarantinePath')
    log_path = get_path_value(args.LogPath, settings, 'LogPath')

    if not (source_path and destination_path and quarantine_path and log_path):
        print("SourcePath, DestinationPath, QuarantinePath, and LogPath must all be provided either as parameters or in the settings file.")
        sys.exit(1)

    log_file = os.path.join(
        log_path,
        f"shuttle-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.log"
    )

    print(f"SourcePath: {source_path}")
    print(f"DestinationPath: {destination_path}")
    print(f"QuarantinePath: {quarantine_path}")
    print(f"LogFile: {log_file}")

    # Scan Source Files for malware
    print("Scanning Source Files for malware...")
    if test_for_malware(source_path, delete_files_on_threat=False):
        print("Malware detected in Source Files. Exiting...")
        sys.exit(1)

    # Prepare robocopy commands
    robocopy_base_params = ["/E", "/DCOPY:DAT", "/R:3", "/W:10", "/J", f"/UNILOG+:{log_file}"]

    robocopy_to_quarantine = ["robocopy", source_path, quarantine_path] + robocopy_base_params

    robocopy_to_destination = ["robocopy", quarantine_path, destination_path] + robocopy_base_params + ["/MOV", "/S"]

    # Copy files from Source to Quarantine
    print("Copying files from Source to Quarantine...")
    result = subprocess.run(robocopy_to_quarantine, capture_output=True, text=True)
    if result.returncode < 8:
        print("Files successfully copied/moved from source to quarantine.")
    else:
        print(f"Robocopy encountered errors. Exit code: {result.returncode}")
        sys.exit(1)

    # Scan Quarantined Files for malware
    print("Scanning Quarantined Files for malware...")
    if test_for_malware(quarantine_path, delete_files_on_threat=True):
        print("Malware detected in Quarantined Files. Exiting...")
        sys.exit(1)

    # Copy files from Quarantine to Destination
    print("Copying files from Quarantine to Destination...")
    result = subprocess.run(robocopy_to_destination, capture_output=True, text=True)
    if result.returncode < 8:
        print("Files successfully moved from quarantine to destination.")
    else:
        print(f"Robocopy encountered errors. Exit code: {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
