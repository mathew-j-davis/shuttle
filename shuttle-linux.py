import os
import shutil
import hashlib
import argparse
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import keyring
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_file=None, log_level=logging.INFO):
    """
    Set up logging configuration for the application.
    
    Args:
        log_file (str): Path to the log file. If None, logs only to console.
        log_level (int): Logging level (default: logging.INFO)
    """
    # Create logger
    logger = logging.getLogger('shuttle')
    logger.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if log_file is specified
    if log_file:
        try:
            # Ensure log directory exists
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            # Create rotating file handler (10MB per file, keep 5 backup files)
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to set up file logging: {e}")

    return logger





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
    logger = logging.getLogger('shuttle')
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            # Read the file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        hash_value = hash_func.hexdigest()
        logger.debug(f"Successfully calculated {algorithm} hash for {file_path}")
        return hash_value
    except FileNotFoundError:
        logger.error(f"File not found while calculating hash: {file_path}")
        return None
    except PermissionError:
        logger.error(f"Permission denied while calculating hash: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
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
    logger = logging.getLogger('shuttle')
    try:
        os.remove(file_path)
        if not os.path.exists(file_path):
            logger.info(f"Successfully deleted file: {file_path}")
            return True
    except PermissionError:
        logger.error(f"Permission denied while deleting file: {file_path}")
    except FileNotFoundError:
        logger.warning(f"File not found while attempting deletion: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
    return False

def test_write_access(path):
    """
    Test if the script has write access to a given directory.
    
    Args:
        path (str): Path to the directory to test.
    
    Returns:
        bool: True if write access is confirmed, False otherwise.
    """
    logger = logging.getLogger('shuttle')
    try:
        test_file = os.path.join(path, 'write_test.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info(f"Write access confirmed for {path}")
        return True
    except Exception as e:
        logger.error(f"No write access to {path}. Error: {e}")
        return False

def scan_for_malware(path):
    logger = logging.getLogger('shuttle')
    try:
        logger.info(f"Scanning files in {path} for malware...")
        result = subprocess.run([
            "mdatp",
            "scan",
            "custom",
            "--path",
            path
        ], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Malware scan completed successfully. No threats detected.")
            return True
        elif result.returncode == 2:
            logger.warning(f"Malware scan detected threats in {path}")
            return False
        else:
            logger.error(f"Malware scan failed with exit code: {result.returncode}")
            return False
    except Exception as e:
        logger.error(f"Failed to perform malware scan. Error: {e}")
        return False

def is_file_open(file_path):
    """
    Check if a file is currently open by any process.
    
    Args:
        file_path (str): Path to the file to check.
    
    Returns:
        bool: True if the file is open, False otherwise.
    """
    logger = logging.getLogger('shuttle')
    try:
        result = subprocess.run(
            ['lsof', '--', file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        is_open = result.returncode == 0
        if is_open:
            logger.debug(f"File is currently open: {file_path}")
        return is_open
    except Exception as e:
        logger.error(f"Error checking if file is open: {e}")
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
    logger = logging.getLogger('shuttle')
    try:
        last_modified_time = os.path.getmtime(file_path)
        current_time = time.time()
        is_stable = (current_time - last_modified_time) > stability_time
        if not is_stable:
            logger.debug(f"File is not yet stable: {file_path}")
        return is_stable
    except Exception as e:
        logger.error(f"Error checking file stability for {file_path}: {e}")
        return False

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
    logger = logging.getLogger('shuttle')
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
        logger.info(f"Scanning file {file_path} for malware...")
        result = subprocess.run([
            "mdatp",
            "scan",
            "file",
            "--path",
            file_path
        ], capture_output=True, text=True)

        if result.returncode == 0:
            # No threats detected
            logger.info(f"No threats detected in {file_path}.")
            return handle_clean_file(file_path, quarantine_path, destination_path, source_path, delete_source_files)

        else:
            # Threats detected in the file
            logger.warning(f"Threats detected in {file_path}.")
            return handle_suspect_file(file_path, hazard_archive_path, hazard_archive_password)

        return True
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return False

def handle_clean_file(file_path, quarantine_path, destination_path, source_path, delete_source_files):
    """Handle processing of clean files."""
    logger = logging.getLogger('shuttle')
    try:
        rel_path = os.path.relpath(file_path, quarantine_path)
        destination_file_path = os.path.join(destination_path, rel_path)
        dest_dir = os.path.dirname(destination_file_path)
        
        logger.debug(f"Moving clean file to destination: {destination_file_path}")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(file_path, destination_file_path)

        # Verify file integrity
        if not verify_file_integrity(source_path, destination_file_path, rel_path):
            return False

        if delete_source_files:
            source_file_path = os.path.join(source_path, rel_path)
            remove_file_with_logging(source_file_path)
        
        return True
    except Exception as e:
        logger.error(f"Error handling clean file {file_path}: {e}")
        return False

def verify_file_integrity(source_path, destination_file_path, rel_path):
    """Verify file integrity between source and destination."""
    logger = logging.getLogger('shuttle')
    destination_file_hash = get_file_hash(destination_file_path)
    source_file_path = os.path.join(source_path, rel_path)
    source_file_hash = get_file_hash(source_file_path)

    if not compare_file_hashes(source_file_hash, destination_file_hash):
        logger.error(f"Source and destination files do not match: {rel_path}")
        return False
    
    logger.info(f"File integrity verified for: {destination_file_path}")
    return True

def handle_suspect_file(file_path, hazard_archive_path, hazard_archive_password):
    """
    Handle processing of suspect files by compressing and encrypting them.
    
    Args:
        file_path (str): Path to the suspect file.
        hazard_archive_path (str): Path to the hazard archive directory.
        hazard_archive_password (str): Password for the encrypted archive.
    
    Returns:
        bool: True if the file was successfully handled, False otherwise.
    """
    logger = logging.getLogger('shuttle')
    try:
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
                logger.info(f"File archived and encrypted to {archive_path}")
            else:
                logger.error(f"Failed to create encrypted archive for {file_path}. Error: {result.stderr}")
                return False
        else:
            logger.warning(f"No hazard archive path or password provided. Deleting file {file_path}.")

        # Remove the infected file from quarantine
        os.remove(file_path)
        return True
    except Exception as e:
        logger.error(f"Error handling suspect file {file_path}: {e}")
        return False
    
def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='File Transfer Script')
    parser.add_argument('-SourcePath', help='Path to the source directory')
    parser.add_argument('-DestinationPath', help='Path to the destination directory')
    parser.add_argument('-QuarantinePath', help='Path to the quarantine directory')
    parser.add_argument('-LogPath', help='Path to the log directory')
    parser.add_argument('-SettingsPath', default=os.path.join(os.getenv('USERPROFILE') or os.getenv('HOME'), '.shuttle', 'settings.txt'),
                        help='Path to the settings file')
    parser.add_argument('-TestSourceWriteAccess', action='store_true', help='Test write access to the source directory')
    parser.add_argument('-DeleteSourceFilesAfterCopying', action='store_true',
                        help='Delete the source files after copying them to the destination')
    parser.add_argument('--max-scans', type=int, help='Maximum number of parallel scans')   
    parser.add_argument('--lock-file', default='/tmp/shuttle.lock', help='Path to lock file to prevent multiple instances')
    parser.add_argument('-QuarantineHazardArchive', help='Path to the hazard archive directory')
    parser.add_argument('-HazardArchivePassword', help='Password for the encrypted hazard archive')

    args = parser.parse_args()


    # Retrieve the hazard archive password
    if args.HazardArchivePassword:
        hazard_archive_password = args.HazardArchivePassword
    else:
        service_name = "shuttle_linux"
        username = "hazard_archive"
        hazard_archive_password = keyring.get_password(service_name, username)

        if not hazard_archive_password:
            logger.warning("Hazard archive password not found. Suspect files will be deleted without archiving.")
            hazard_archive_password = None

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

    # Get paths and parameters from arguments or settings file
    source_path = args.SourcePath or settings.get('SourcePath')
    destination_path = args.DestinationPath or settings.get('DestinationPath')
    quarantine_path = args.QuarantinePath or settings.get('QuarantinePath')
    log_path = args.LogPath or settings.get('LogPath')
    hazard_archive_path = args.QuarantineHazardArchive or settings.get('QuarantineHazardArchive')


    # Create log file name with timestamp and unique ID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = os.getpid()  # Using process ID as unique identifier
    log_filename = f"shuttle_{timestamp}_{unique_id}.log"

    # Construct full log path if log directory is specified
    log_file = None
    if log_path:
        os.makedirs(log_path, exist_ok=True)
        log_file = os.path.join(log_path, log_filename)
    
    # Set up logging
    logger = setup_logging(log_file=log_file)
    logger.info(f"Starting Shuttle Linux file transfer and scanning process (PID: {unique_id})")

    # Convert DeleteSourceFilesAfterCopying to boolean, giving priority to the command-line argument
    if args.DeleteSourceFilesAfterCopying:
        delete_source_files = True
    else:
        delete_source_files = settings.get('DeleteSourceFilesAfterCopying', 'False').lower() == 'true'
    # Determine max_scans, giving priority to the command-line argument
    if args.max_scans is not None:
        max_scans = args.max_scans
    else:
        max_scans = int(settings.get('MaxScans', 2))


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
                    continue  # Skip this file and proceed to the next one

                # Skip files that are currently open
                if is_file_open(file_path):
                    print(f"Skipping file {file_path} because it is being written to.")
                    continue  # Skip this file and proceed to the next one

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
    with ProcessPoolExecutor(max_workers=max_scans) as executor:
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