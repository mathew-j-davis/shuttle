from shuttle_common import (
    setup_logging,
    get_file_hash,
    compare_file_hashes,
    remove_file_with_logging,
    test_write_access,
    verify_file_integrity,
    copy_temp_then_rename,
    normalize_path,
    remove_empty_directories,
    remove_directory,
    remove_directory_contents,
    is_file_open,
    is_file_stable
)

import os
import shutil
import hashlib
import argparse
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import configparser  # Added import for configparser
import gnupg
import types


scan_result_types = types.SimpleNamespace()

scan_result_types.FILE_IS_SUSPECT = 3
scan_result_types.FILE_IS_CLEAN = 0
scan_result_types.FILE_SCAN_FAILED = 100


def scan_for_malware(path):
    logger = logging.getLogger('shuttle')
    try:

        # Scan the file for malware
        logger.info(f"Scanning file {path} for malware...")

        child_run = subprocess.run(
            [
                "mdatp",
                "scan",
                "custom",
                "--path",
                path
            ]
        )

        #   piping stout, sterr seems to block subprocess
        #   stdout=subprocess.PIPE,
        #   stderr=subprocess.PIPE

        #  , capture_output=True, text=True)


        match child_run.returncode:
            case 0:
                logger.inf(f"No threat found in {path}")
                return scan_result_types.FILE_IS_CLEAN

            case 2 | 3 :
                logger.warning(f"Threats found in {path}")
                return scan_result_types.FILE_IS_SUSPECT
            
            # case _:
            #        logger.warning(f"Scan failed on  {path}")

    except FileNotFoundError:
        logger.error(f"Files not found when scanning file: {path}")

    except PermissionError:
        logger.error(f"Permission denied when scanning file: {path}")

    except Exception as e:
        logger.error(f"Failed to perform malware scan on {path}. Error: {e}")

    logger.warning(f"Scan failed on  {path}")
    return scan_result_types.FILE_SCAN_FAILED;


def scan_and_process_file(args):
    """
    Scan a file for malware and process it accordingly.

    Args:
        args (tuple): Contains all necessary arguments.
            - quarantine_file_path (str): Full path to the file in quarantine
            - source_file_path (str): Full path to the original source file
            - destination_file_path (str): Full path where the file should be copied in destination
            - hazard_archive_path (str): Path to the hazard archive directory
            - key_file_path (str): Full path to the public encryption key file
            - delete_source_files (bool): Whether to delete source files after processing

    Returns:
        bool: True if the file was processed successfully, False otherwise
    """
    # Unpack arguments
    (
        quarantine_file_path,
        source_file_path,
        destination_file_path,
        hazard_archive_path,
        key_file_path,
        delete_source_files
    ) = args

    logger = logging.getLogger('shuttle')

    # Scan the file for malware
    logger.info(f"Scanning file {quarantine_file_path} for malware...")

    result = scan_for_malware(quarantine_file_path)

    match result:
        case  scan_result_types.FILE_IS_CLEAN:
            logger.info(f"No threats found in {quarantine_file_path}")
            return handle_clean_file(
                quarantine_file_path,
                source_file_path,
                destination_file_path,
                delete_source_files
            )

        case  scan_result_types.FILE_IS_SUSPECT:
            logger.warning(f"Threats found in {quarantine_file_path}")
            return handle_suspect_file(
                quarantine_file_path,
                source_file_path,
                hazard_archive_path,
                key_file_path,
                delete_source_files
            )

        case _:
            logger.warning(f"Scan failed on  {quarantine_file_path}")
            return False



def handle_clean_file(
    quarantine_file_path,
    source_file_path,
    destination_file_path,
    delete_source_files
):
    """
    Handle processing of clean files by moving them to the destination.

    Args:
        quarantine_file_path (str): Full path to the file in quarantine
        source_file_path (str): Full path to the original source file
        destination_file_path (str): Full path where the file should be copied in destination
        delete_source_files (bool): Whether to delete source files after processing

    Returns:
        bool: True if the file was successfully handled, False
          otherwise
    """
    
    logger = logging.getLogger('shuttle')
    try:
        copy_temp_then_rename(quarantine_file_path, destination_file_path)

    except Exception as e:
        logger.error(f"Failed to copy clean file from {quarantine_file_path} to {destination_file_path}: {e}")
        return False
    
    if delete_source_files:
        try:

            # Verify integrity and delete source if requested
            verify = verify_file_integrity(source_file_path, destination_file_path)

            if verify['success']:
                remove_file_with_logging(source_file_path)
            else:
                logger.error(f"Integrity check failed, source file not deleted: {source_file_path}")
                return False
  
        except FileNotFoundError as e:
            logger.error(f"File not found during handling of clean file: {e}")
            return False
        
        except PermissionError as e:
            logger.error(f"Permission denied during handling of clean file: {e}")
            return False
        
        except Exception as e:
            logger.error(f"Failed to handle clean file {quarantine_file_path}: {e}")
            return False
        
    return True


def encrypt_file(file_path, output_path, key_file_path):
    """
    Encrypt a file using GPG with a specified public key file.
    
    Args:
        file_path (str): Path to file to encrypt
        output_path (str): Path for encrypted output
        key_file_path (str): Full path to the public key file (.gpg)
    
    Returns:
        bool: True if encryption successful, False otherwise
    """
    logger = logging.getLogger('shuttle')
    try:
        gpg = gnupg.GPG()
        
        # Import the key from file
        with open(key_file_path, 'rb') as key_file:
            import_result = gpg.import_keys(key_file.read())
            if not import_result.count:
                logger.error(f"Failed to import key from {key_file_path}")
                return False
            
            # Use the fingerprint from the imported key
            key_id = import_result.fingerprints[0]
        
        # Encrypt file
        with open(file_path, 'rb') as f:
            status = gpg.encrypt_file(
                f,
                recipients=[key_id],
                output=output_path,
                always_trust=True
            )
        
        if status.ok:
            logger.info(f"File encrypted successfully: {output_path}")
            return True
        else:
            logger.error(f"Encryption failed: {status.status}")
            return False
            
    except FileNotFoundError:
        logger.error(f"Key file not found: {key_file_path}")
        return False
    except Exception as e:
        logger.error(f"Error during encryption: {e}")
        return False

def handle_suspect_file(
    quarantine_file_path,
    source_file_path,
    hazard_archive_path,
    key_file_path,
    delete_source_files
):
    """
    Handle a file that has been identified as suspicious/infected.
    If hazard archive parameters are provided, encrypt and archive the file.
    Otherwise, delete it.
    
    Args:
        quarantine_file_path (str): Path to the file in quarantine
        source_file_path (str): Original path of the file
        hazard_archive_path (str): Path to archive suspicious files
        key_file_path (str): Path to GPG public key file
        delete_source_files (bool): Whether to delete source files after processing
    
    Returns:
        bool: True if file was handled successfully, False otherwise
    """
    logger = logging.getLogger('shuttle')
    
    try:
        # If hazard archive path and encryption key are provided, archive the file
        if hazard_archive_path and key_file_path:
            # Verify file integrity before archiving

            verify = verify_file_integrity(source_file_path, quarantine_file_path)

            if not verify['success']:
                logger.error(f"Integrity check failed before archiving: {quarantine_file_path}")
                return False

            logger.error(f"Malware detected in : {quarantine_file_path} with hash value {verify['a']}")

            # Create hazard archive directory if it doesn't exist
            try:
                os.makedirs(hazard_archive_path, exist_ok=True)
            except PermissionError as e:
                logger.error(f"Permission denied when creating hazard archive directory {hazard_archive_path}: {e}")
                return False
            except OSError as e:
                logger.error(f"OS error when creating hazard archive directory {hazard_archive_path}: {e}")
                return False

            # Generate encrypted file path with timestamp
            archive_name = f"hazard_{os.path.basename(quarantine_file_path)}_{datetime.now().strftime('%Y%m%d%H%M%S')}.gpg"
            archive_path = os.path.join(hazard_archive_path, archive_name)

            # Attempt to encrypt the file
            if not encrypt_file(quarantine_file_path, archive_path, key_file_path):
                logger.error(f"Failed to encrypt file: {quarantine_file_path}")
            return False 
            
            logger.info(f"Successfully encrypted suspect file to: {archive_path}")

            archive_hash = get_file_hash(archive_path)
           
            logger.info(f"Suspect file archive {archive_path} has hash value : {archive_hash}")

        else:
            # No hazard archive parameters - delete the infected file
            logger.warning(
                f"No hazard archive path or encryption key file provided. "
                f"Deleting infected file: {quarantine_file_path}"
            )

        # Remove the infected file from quarantine
        if not remove_file_with_logging(quarantine_file_path):
            logger.error(f"Failed to remove quarantined file after archiving: {quarantine_file_path}")
            return False
            
        # Delete source file if requested
        if delete_source_files:
            if not remove_file_with_logging(source_file_path):
                logger.error(f"Failed to remove source file after archiving: {source_file_path}")
                return False
        
        return True

    except Exception as e:
        logger.error(f"Unexpected error handling suspect file {quarantine_file_path}: {e}")
        return False
    
def scan_and_process_directory(
    source_path,
    destination_path,
    quarantine_path,
    hazard_archive_path,
    hazard_encryption_key_file_path,
    delete_source_files,
    max_scan_threads
    ):
   
    quarantine_files = []

    logger = logging.getLogger('shuttle')

    try:
        # Create quarantine directory if it doesn't exist
        os.makedirs(quarantine_path, exist_ok=True)

        # Copy files from source to quarantine directory
        # os.walk traverses the directory tree
        for source_root, dirs, source_files in os.walk(source_path, topdown=False):
            for source_file in source_files:
                source_file_path = os.path.join(source_root, source_file)

                # Skip files that are not stable (still being written to)
                if not is_file_stable(source_file_path):
                    print(f"Skipping file {source_file_path} because it may still be written to.")
                    continue  # Skip this file and proceed to the next one

                # Skip files that are currently open
                if is_file_open(source_file_path):
                    print(f"Skipping file {source_file_path} because it is being written to.")
                    continue  # Skip this file and proceed to the next one

                # Determine the relative directory structure
                # Replicate that structure in the quarantine directory
                rel_dir = os.path.relpath(source_root, source_path)
                quarantine_file_copy_dir = os.path.join(normalize_path(os.path.join(quarantine_path, rel_dir)))
                # os.makedirs(quarantine_file_copy_dir, exist_ok=True)

                # Full quarantine path
                quarantine_file_path = os.path.join(normalize_path(os.path.join(quarantine_file_copy_dir, source_file)))

                # Full destination path (but don't create directory yet)
                destination_file_copy_dir = os.path.join(normalize_path(os.path.join(destination_path, rel_dir)))
                destination_file_path = os.path.join(normalize_path(os.path.join(destination_file_copy_dir, source_file)))

                # Copy the file to the appropriate directory in the quarantine directory
                # quarantine_temp_path = os.path.join(quarantine_file_path + '.tmp')

                try:
                    copy_temp_then_rename(source_file_path, quarantine_file_path)

                    logger.info(f"Copied file {source_file_path} to quarantine: {quarantine_file_path}")

                    # Add to processing queue with full paths
                    quarantine_files.append((
                        quarantine_file_path,     # full path to quarantine file
                        source_file_path,         # full path to source file
                        destination_file_path,     # full path to destination file
                        hazard_archive_path,
                        hazard_encryption_key_file_path,
                        delete_source_files
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to copy file from source: {source_file_path} to quarantine: {quarantine_file_path}. Error: {e}")


        # Process files in parallel using a ProcessPoolExecutor with graceful shutdown
        with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
            try:
                results = list(executor.map(scan_and_process_file, quarantine_files))
            except Exception as e:
                logger.error(f"An error occurred during parallel processing: {e}")
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        # Check if all files were processed successfully
        if not all(results):
            logger.error(f"Some files failed to be processed.")

        # After processing all files, remove contents of quarantine directory
        remove_directory_contents(quarantine_path)

        # clean up empty subdirectories
        #  this can be made more efficient

        if(delete_source_files):

            directories_to_remove = []

            for counter, file_transfer in enumerate(quarantine_files):
                if counter >= len(results):
                    break

                #transfer was successful, clean up empty directorues

                if results[counter]:

                    source_file_dir = os.path.dirname( quarantine_files[counter][1]) ## source_file_path

                    if ( normalize_path(source_file_dir) == normalize_path(source_path) ):
                        continue

                    if not source_file_dir in directories_to_remove:

                        if not os.path.exists(source_file_dir):
                            continue

                        directories_to_remove.append(source_file_dir)
            
            for directory_to_remove in directories_to_remove:

                # this won't remove directories that contain subdirectories from which no files were tranferred
                # remove_empty_directories() will remove recursively remove subfolders
                if len(os.listdir(directory_to_remove)) == 0:
                    if not remove_directory(directory_to_remove):
                        logger.error(f"Could not remove directory during cleanup: {directory_to_remove}")
                    else:
                        logger.info(f"Directory removed during cleanup: {directory_to_remove}")


    except Exception as e:
        logger.error(f"Failed to copy files to quarantine: Error: {e}")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='File Transfer Script')
    parser.add_argument('-SourcePath', help='Path to the source directory')
    parser.add_argument('-DestinationPath', help='Path to the destination directory')
    parser.add_argument('-QuarantinePath', help='Path to the quarantine directory')
    parser.add_argument('-LogPath', help='Path to the log directory')
    parser.add_argument('-SettingsPath', default=os.path.join(os.getenv('HOME'), '.shuttle', 'settings.ini'),
                        help='Path to the settings file')
    parser.add_argument('-TestSourceWriteAccess', action='store_true', help='Test write access to the source directory')
    parser.add_argument('-DeleteSourceFilesAfterCopying', action='store_true',
                        help='Delete the source files after copying them to the destination')
    parser.add_argument('--MaxScanThreads', type=int, help='Maximum number of parallel scans')
    parser.add_argument('--lock-file', default='/tmp/shuttle.lock', help='Path to lock file to prevent multiple instances')
    parser.add_argument('-HazardArchivePath', help='Path to the hazard archive directory')
    parser.add_argument('-HazardEncryptionKeyPath', help='Path to the GPG public key file for encrypting hazard files')
    parser.add_argument('-LogLevel', default=None, help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')

    args = parser.parse_args()

    # Prevent multiple instances using a lock file
    if os.path.exists(args.lock_file):
        print(f"Another instance of the script is running. Lock file {args.lock_file} exists.")
        sys.exit(1)

    # Create the lock file
    with open(args.lock_file, 'w') as lock_file:
        lock_file.write(str(os.getpid()))

    try:
        # Load settings from the settings file using configparser
        config = configparser.ConfigParser()
        config.read(args.SettingsPath)

        # Helper function to get settings with priority: CLI args > settings file > default
        def get_setting(arg_value, section, option, default=None):
            if arg_value is not None:
                return arg_value
            elif config.has_option(section, option):
                return config.get(section, option)
            else:
                return default

        # Get paths and parameters from arguments or settings file
        source_path = get_setting(args.SourcePath, 'paths', 'source_path')
        destination_path = get_setting(args.DestinationPath, 'paths', 'destination_path')
        quarantine_path = get_setting(args.QuarantinePath, 'paths', 'quarantine_path')
        log_path = get_setting(args.LogPath, 'paths', 'log_path')
        hazard_archive_path = get_setting(args.HazardArchivePath, 'paths', 'hazard_archive_path')
        log_level_str = get_setting(args.LogLevel, 'logging', 'log_level', 'INFO').upper()

        # Map the log level string to a logging level
        numeric_level = getattr(logging, log_level_str, None)
        if not isinstance(numeric_level, int):
            print(f"Invalid log level: {log_level_str}")
            sys.exit(1)

        # Create log file name with timestamp and unique ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = os.getpid()  # Using process ID as unique identifier
        log_filename = f"shuttle_{timestamp}_{unique_id}.log"

        # Construct full log path if log directory is specified
        log_file = None
        if log_path:
            os.makedirs(log_path, exist_ok=True)
            log_file = os.path.join(log_path, log_filename)

        # Set up logging with the configured log level
        logger = setup_logging(log_file=log_file, log_level=numeric_level)
        logger.info(f"Starting Shuttle Linux file transfer and scanning process (PID: {unique_id})")

        # Check for required external commands
        import shutil

        required_commands = ['lsof', 'mdatp', 'gpg']
        missing_commands = []

        for cmd in required_commands:
            if shutil.which(cmd) is None:
                missing_commands.append(cmd)

        if missing_commands:
            for cmd in missing_commands:
                logger.error(f"Required command '{cmd}' not found. Please ensure it is installed and accessible in your PATH.")
            sys.exit(1)

        # Get encryption key file path
        if hazard_archive_path:
            hazard_encryption_key_file_path = args.HazardEncryptionKeyPath or config.get('paths', 'hazard_encryption_key_path', fallback=None)
            if not hazard_encryption_key_file_path:
                logger.error("Hazard archive path specified but no encryption key file provided")
                sys.exit(1)
            if not os.path.isfile(hazard_encryption_key_file_path):
                logger.error(f"Encryption key file not found: {hazard_encryption_key_file_path}")
                sys.exit(1)

        else:
            hazard_encryption_key_file_path = None

        # Retrieve other settings

        delete_source_files = args.DeleteSourceFilesAfterCopying or config.getboolean('settings', 'delete_source_files_after_copying', fallback=False)

        if args.MaxScanThreads is not None:
            max_scan_threads = args.MaxScanThreads
        else:
            max_scan_threads = config.getint('settings', 'max_scan_threads', fallback=2)

        # Validate required paths
        if not (source_path and destination_path and quarantine_path):
            logger.error("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.")
            sys.exit(1)

        logger.info(f"SourcePath: {source_path}")
        logger.info(f"DestinationPath: {destination_path}")
        logger.info(f"QuarantinePath: {quarantine_path}")

        
        scan_and_process_directory(
            source_path,
            destination_path,
            quarantine_path,
            hazard_archive_path,
            hazard_encryption_key_file_path,
            delete_source_files,
            max_scan_threads
            )

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    finally:
        # Remove the lock file upon script completion or error
        if os.path.exists(args.lock_file):
            os.remove(args.lock_file)

if __name__ == '__main__':
    main()
