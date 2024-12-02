import os
import shutil
import hashlib
import argparse
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

#    sudo apt-get install lsof 
#    python shuttle-linux.py -SourcePath /path/to/source -DestinationPath /path/to/destination -QuarantinePath /path/to/quarantine

def get_file_hash(file_path, algorithm='sha256'):
    """
    Calculate the hash of a file using the specified algorithm.
    
    Args:
        file_path (str): Path to the file.
        algorithm (str): Hash algorithm to use (default is 'sha256').
    
    Returns:
        str: The hexadecimal hash string of the file.
    """
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            # Read the file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        print(f"Error calculating hash for {file_path}: {e}")
        return None

def compare_file_hashes(hash1, hash2):
    """
    Compare two hash strings.
    
    Args:
        hash1 (str): First hash string.
        hash2 (str): Second hash string.
    
    Returns:
        bool: True if hashes match, False otherwise.
    """
    return hash1 == hash2

def remove_file_with_logging(file_path):
    """
    Remove a file and log the result.
    
    Args:
        file_path (str): Path to the file to remove.
    
    Returns:
        bool: True if file was successfully deleted, False otherwise.
    """
    try:
        os.remove(file_path)
        if not os.path.exists(file_path):
            print(f"Delete succeeded: {file_path}")
            return True
    except Exception as e:
        print(f"Delete failed: {file_path}, Error: {e}")
    return False

def test_write_access(path):
    """
    Test if the script has write access to a given directory.
    
    Args:
        path (str): Path to the directory to test.
    
    Returns:
        bool: True if write access is confirmed, False otherwise.
    """
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

def is_file_open(file_path):
    """
    Check if a file is currently open by any process.
    
    Args:
        file_path (str): Path to the file to check.
    
    Returns:
        bool: True if the file is open, False otherwise.
    """
    try:
        result = subprocess.run(
            ['lsof', '--', file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        # If returncode is 0, the file is open by some process
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking if file is open: {e}")
        return False



def is_file_stable(file_path, stability_time=5):
    """
    Check if a file has not been modified in the last 'stability_time' seconds.
    
    Args:
        file_path (str): Path to the file to check.
        stability_time (int): Time in seconds to consider the file stable (default is 5).
    
    Returns:
        bool: True if the file is stable, False otherwise.
    """
    last_modified_time = os.path.getmtime(file_path)
    current_time = time.time()
    return (current_time - last_modified_time) > stability_time

def scan_and_process_file(args):
    """
    Scan and process a single file.
    If no threats detected, move to destination.
    If threats detected, archive and encrypt, then move to hazard archive.
    
    Args:
        args (tuple): Tuple containing the arguments required for processing.
    
    Returns:
        bool: True if processing was successful, False otherwise.
    """
    (
        file_path,
        quarantine_path,
        destination_path,
        source_path,
        hazard_archive_path,
        hazard_archive_password,
        delete_source_files
    ) = args

    try:
        # Scan the file
        print(f"Scanning file {file_path} for malware...")
        result = subprocess.run([
            "mdatp",
            "scan",
            "file",
            "--path",
            file_path
        ], capture_output=True, text=True)

        if result.returncode == 0:
            # No threats detected
            print(f"No threats detected in {file_path}.")

            # Move the file from quarantine to destination
            rel_path = os.path.relpath(file_path, quarantine_path)
            destination_file_path = os.path.join(destination_path, rel_path)
            dest_dir = os.path.dirname(destination_file_path)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(file_path, destination_file_path)

            # Verify the file hashes between source and destination
            destination_file_hash = get_file_hash(destination_file_path)
            source_file_path = os.path.join(source_path, rel_path)
            source_file_hash = get_file_hash(source_file_path)

            if not compare_file_hashes(source_file_hash, destination_file_hash):
                print(f"Source and destination files do not match: {rel_path}")
                return False

            print(f"Copied to destination successfully: {destination_file_path}")

            # Remove the source file if required
            if delete_source_files:
                remove_file_with_logging(source_file_path)

        else:
            # Threats detected in the file
            print(f"Threats detected in {file_path}.")

            if hazard_archive_path and hazard_archive_password:
                # Compress and encrypt the file
                os.makedirs(hazard_archive_path, exist_ok=True)
                archive_name = 'hazard_' + os.path.basename(file_path) + '_' + datetime.now().strftime('%Y%m%d%H%M%S') + '.zip'
                archive_path = os.path.join(hazard_archive_path, archive_name)

                # Use zip with password to encrypt the file
                zip_command = [
                    'zip', '--password', hazard_archive_password, archive_path, file_path
                ]

                # Execute the zip command
                result = subprocess.run(zip_command, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"File archived and encrypted to {archive_path}")
                else:
                    print(f"Failed to create encrypted archive for {file_path}. Error: {result.stderr}")
                    return False
            else:
                print(f"No hazard archive path or password provided. Deleting file {file_path}.")

            # Remove the infected file from quarantine
            os.remove(file_path)

        return True
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return False

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='File Transfer Script')
    parser.add_argument('-SourcePath', help='Path to the source directory')
    parser.add_argument('-DestinationPath', help='Path to the destination directory')
    parser.add_argument('-QuarantinePath', help='Path to the quarantine directory')
    parser.add_argument('-SettingsPath', default=os.path.join(os.getenv('USERPROFILE') or os.getenv('HOME'), '.shuttle', 'settings.txt'),
                        help='Path to the settings file')
    parser.add_argument('-TestSourceWriteAccess', action='store_true', help='Test write access to the source directory')
    parser.add_argument('-DeleteSourceFilesAfterCopying', action='store_true',
                        help='Delete the source files after copying them to the destination')
    parser.add_argument('--max-scans', type=int, default=2, help='Maximum number of parallel scans')
    parser.add_argument('--lock-file', default='/tmp/shuttle.lock', help='Path to lock file to prevent multiple instances')
    parser.add_argument('-QuarantineHazardArchive', help='Path to the hazard archive directory')
    parser.add_argument('-HazardArchivePassword', help='Password for the encrypted hazard archive')
    args = parser.parse_args()

    # Prevent multiple instances using a lock file
    if os.path.exists(args.lock_file):
        print(f"Another instance of the script is running. Lock file {args.lock_file} exists.")
        sys.exit(1)
    else:
        # Create the lock file
        with open(args.lock_file, 'w') as lock_file:
            lock_file.write(str(os.getpid()))

    # Load settings from the settings file if parameters are not provided
    settings = {}
    if os.path.exists(args.SettingsPath):
        with open(args.SettingsPath, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    settings[key.strip()] = value.strip()

    # Get paths from arguments or settings file
    source_path = args.SourcePath or settings.get('SourcePath')
    destination_path = args.DestinationPath or settings.get('DestinationPath')
    quarantine_path = args.QuarantinePath or settings.get('QuarantinePath')
    hazard_archive_path = args.QuarantineHazardArchive
    hazard_archive_password = args.HazardArchivePassword
    delete_source_files = args.DeleteSourceFilesAfterCopying

    # Validate required paths
    if not (source_path and destination_path and quarantine_path):
        print("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.")
        sys.exit(1)

    print(f"SourcePath: {source_path}")
    print(f"DestinationPath: {destination_path}")
    print(f"QuarantinePath: {quarantine_path}")

    try:
        # Create quarantine directory if it doesn't exist
        os.makedirs(quarantine_path, exist_ok=True)

        # Copy files from source to quarantine directory
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = os.path.join(root, file)

                # Skip files that are not stable (still being written to)
                if not is_file_stable(file_path):
                    print(f"Skipping file {file_path} because it may still be written to.")
                    continue

                # Skip files that are currently open
                if is_file_open(file_path):
                    print(f"Skipping file {file_path} because it is being written to.")
                    continue

                # Determine the relative directory structure
                rel_dir = os.path.relpath(root, source_path)
                dest_dir = os.path.join(quarantine_path, rel_dir)
                os.makedirs(dest_dir, exist_ok=True)

                # Copy the file to the quarantine directory
                shutil.copy2(file_path, dest_dir)
        print(f"Successfully copied files from {source_path} to {quarantine_path}")
    except Exception as e:
        print(f"Failed to copy files from {source_path} to {quarantine_path}. Error: {e}")
        sys.exit(1)

    # Prepare arguments for scanning and processing files
    quarantine_files = []
    for root, _, files in os.walk(quarantine_path):
        for file in files:
            file_path = os.path.join(root, file)
            quarantine_files.append((
                file_path,
                quarantine_path,
                destination_path,
                source_path,
                hazard_archive_path,
                hazard_archive_password,
                delete_source_files
            ))

    # Process files in parallel using a ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=args.max_scans) as executor:
        results = list(executor.map(scan_and_process_file, quarantine_files))

    # Check if all files were processed successfully
    if not all(results):
        print("Some files failed to be processed.")

    # After processing all files, remove the quarantine directory
    shutil.rmtree(quarantine_path, ignore_errors=True)

    # Remove the lock file upon script completion
    if os.path.exists(args.lock_file):
        os.remove(args.lock_file)

if __name__ == "__main__":
    main()