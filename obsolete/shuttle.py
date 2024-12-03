import os
import shutil
import hashlib
import argparse
import subprocess
import win32net
import getpass
import tempfile
import sys

#    pip install pywin32
#   python shuttle.py -SourcePath \\server\share -DestinationPath C:\Destination -QuarantinePath C:\Quarantine

def get_file_hash(file_path, algorithm='sha256'):
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        print(f"Error calculating hash for {file_path}: {e}")
        return None

def compare_file_hashes(hash1, hash2):
    return hash1 == hash2

def remove_file_with_logging(file_path):
    try:
        os.remove(file_path)
        if not os.path.exists(file_path):
            print(f"Delete succeeded: {file_path}")
            return True
    except Exception as e:
        print(f"Delete failed: {file_path}, Error: {e}")
    return False

def test_write_access(path):
    try:
        test_file = os.path.join(path, 'write_test.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print(f"Write access confirmed for {path}")
        return True
    except Exception as e:
        print(f"No write access to {path}. Error: {e}")
        return False

def map_network_drive(network_path, username, password):
    try:
        win32net.NetUseAdd(None, 2, {
            'remote': network_path,
            'username': username,
            'password': password,
            'persistent': False
        })
        print(f"Successfully connected to {network_path}")
    except Exception as e:
        print(f"Failed to connect to {network_path}. Error: {e}")
        sys.exit(1)

def unmap_network_drive(network_path):
    try:
        win32net.NetUseDel(None, network_path, 0)
    except Exception as e:
        print(f"Error disconnecting from {network_path}: {e}")

def scan_for_malware(path):
    try:
        print(f"Scanning files in {path} for malware...")
        result = subprocess.run([
            r"C:\Program Files\Windows Defender\MpCmdRun.exe",
            "-Scan", "-ScanType", "3", "-File", path
        ], capture_output=True, text=True)
        if result.returncode == 0:
            print("Malware scan completed successfully. No threats detected.")
            return True
        elif result.returncode == 2:
            print(f"Malware scan detected threats in {path}")
            return False
        else:
            print(f"Malware scan failed with exit code: {result.returncode}")
            return False
    except Exception as e:
        print(f"Failed to perform malware scan. Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='File Transfer Script')
    parser.add_argument('-SourcePath', help='Path to the source network file share')
    parser.add_argument('-DestinationPath', help='Path to the destination directory')
    parser.add_argument('-QuarantinePath', help='Path to the quarantine directory')
    parser.add_argument('-SettingsPath', default=os.path.join(os.getenv('USERPROFILE'), '.shuttle', 'settings.txt'),
                        help='Path to the settings file')
    parser.add_argument('-TestSourceWriteAccess', action='store_true', help='Test write access to the source directory')
    parser.add_argument('-DeleteSourceFilesAfterCopying', action='store_true',
                        help='Delete the source files after copying them to the destination')
    args = parser.parse_args()

    # Load settings from file if not provided as arguments
    settings = {}
    if os.path.exists(args.SettingsPath):
        with open(args.SettingsPath, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    settings[key.strip()] = value.strip()

    source_path = args.SourcePath or settings.get('SourcePath')
    destination_path = args.DestinationPath or settings.get('DestinationPath')
    quarantine_path = args.QuarantinePath or settings.get('QuarantinePath')

    if not (source_path and destination_path and quarantine_path):
        print("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.")
        sys.exit(1)

    if not source_path.startswith('\\\\'):
        print("SourcePath must be a network file share (e.g., \\\\server\\share).")
        sys.exit(1)

    print(f"SourcePath: {source_path}")
    print(f"DestinationPath: {destination_path}")
    print(f"QuarantinePath: {quarantine_path}")

    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")

    # Map network drive
    map_network_drive(source_path, username, password)

    if args.TestSourceWriteAccess:
        if not test_write_access(source_path):
            unmap_network_drive(source_path)
            sys.exit(1)

    try:
        os.makedirs(quarantine_path, exist_ok=True)
        # Copy files to QuarantinePath
        for root, dirs, files in os.walk(source_path):
            for file in files:
                rel_dir = os.path.relpath(root, source_path)
                dest_dir = os.path.join(quarantine_path, rel_dir)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(os.path.join(root, file), dest_dir)
        print(f"Successfully copied files from {source_path} to {quarantine_path}")
    except Exception as e:
        print(f"Failed to copy files from {source_path} to {quarantine_path}. Error: {e}")
        unmap_network_drive(source_path)
        sys.exit(1)

    # Scan files for malware
    if not scan_for_malware(quarantine_path):
        shutil.rmtree(quarantine_path, ignore_errors=True)
        unmap_network_drive(source_path)
        sys.exit(1)

    # Process files from Quarantine to Destination
    try:
        for root, dirs, files in os.walk(quarantine_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), quarantine_path)
                quarantine_file_path = os.path.join(root, file)
                destination_file_path = os.path.join(destination_path, rel_path)
                source_file_path = os.path.join(source_path, rel_path)

                dest_dir = os.path.dirname(destination_file_path)
                os.makedirs(dest_dir, exist_ok=True)

                shutil.copy2(quarantine_file_path, destination_file_path)

                # Verify files
                destination_file_hash = get_file_hash(destination_file_path)
                source_file_hash = get_file_hash(source_file_path)
                quarantine_file_hash = get_file_hash(quarantine_file_path)

                if not compare_file_hashes(source_file_hash, destination_file_hash):
                    raise Exception(f"Source and destination files do not match: {rel_path}")

                if not compare_file_hashes(destination_file_hash, quarantine_file_hash):
                    raise Exception(f"Quarantine and destination files do not match: {rel_path}")

                print(f"Copied to destination successfully: {destination_file_path}")

                # Remove files from quarantine
                remove_file_with_logging(quarantine_file_path)

                if args.DeleteSourceFilesAfterCopying:
                    # Remove files from source
                    remove_file_with_logging(source_file_path)

        print("All files processed successfully.")
    except Exception as e:
        print(f"Error during file processing: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(quarantine_path, ignore_errors=True)
        unmap_network_drive(source_path)

if __name__ == "__main__":
    main()