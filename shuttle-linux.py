  #!/usr/bin/env python3
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
import configparser  # Added import for configparser

def setup_logging(log_file=None, log_level=logging.INFO):
    """
    Set up logging for the script.

    Args:
        log_file (str): Path to the log file.
        log_level (int): Logging level (e.g., logging.DEBUG, logging.INFO).
    """
    # Create logger
    logger = logging.getLogger('shuttle')
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler if log_file is specified
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger





#    sudo apt-get install lsof 
#    python shuttle-linux.py -SourcePath /path/to/source -DestinationPath /path/to/destination -QuarantinePath /path/to/quarantine

def get_file_hash(file_path):
    """
    Compute the SHA-256 hash of a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: The computed hash or None if an error occurred.
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            # Read the file in chunks to avoid memory issues with large files
            for chunk in iter(lambda: f.read(4096), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except FileNotFoundError:
        logging.getLogger('shuttle').error(f"File not found: {file_path}")
        return None
    except PermissionError:
        logging.getLogger('shuttle').error(f"Permission denied when accessing file: {file_path}")
        return None
    except Exception as e:
        logging.getLogger('shuttle').error(f"Error computing hash for {file_path}: {e}")
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
            ['lsof', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
        elif result.returncode == 1:
            # lsof returns 1 if no processes are using the file
            return False
        else:
            if result.stderr:
                logger.error(f"Error checking if file is open: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        logger.error(f"'lsof' command not found. Please ensure it is installed.")
        return False
    except PermissionError:
        logger.error(f"Permission denied when accessing 'lsof' or file: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Exception occurred while checking if file is open: {e}")
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
    except FileNotFoundError:
        logger.error(f"File not found when checking if file is stable: {file_path}")
        return False
    except PermissionError:
        logger.error(f"Permission denied when accessing file size: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Error checking if file is stable {file_path}: {e}")
        return False
def scan_and_process_file(args):
    """
    Scan a file for malware and process it accordingly.

    Args:
        args (tuple): Contains all necessary arguments.
            - quarantine_file_path (str): Full path to the file in quarantine
            - source_file_path (str): Full path to the original source file
            - destination_file_path (str): Full path where the file should be copied in destination
            - hazard_archive_path (str): Path to the hazard archive directory
            - hazard_archive_password (str): Password for the encrypted archive
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
        hazard_archive_password,
        delete_source_files
    ) = args

    logger = logging.getLogger('shuttle')

    try:
        # Scan the file for malware
        logger.info(f"Scanning file {quarantine_file_path} for malware...")
        result = subprocess.run(
            [
                "mdatp",
                "scan",
                "file",
                "--path",
                quarantine_file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

        if result.returncode == 0:
            logger.info(f"No threats found in {quarantine_file_path}")
            return handle_clean_file(
                quarantine_file_path,
                source_file_path,
                destination_file_path,
                delete_source_files
            )
        elif result.returncode == 3:
            logger.warning(f"Threats found in {quarantine_file_path}")
            return handle_suspect_file(
                quarantine_file_path,
                source_file_path,
                hazard_archive_path,
                hazard_archive_password,
                delete_source_files
            )
        else:
            logger.error(f"Failed to scan {quarantine_file_path}. Error: {result.stderr.strip()}")
            return False

    except FileNotFoundError:
        logger.error(f"'mdatp' command not found. Please ensure it is installed.")
        return False
    except PermissionError:
        logger.error(f"Permission denied when scanning file: {quarantine_file_path}")
        return False
    except Exception as e:
        logger.error(f"An exception occurred while scanning {quarantine_file_path}: {e}")
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
        bool: True if the file was successfully handled, False otherwise
    """
    logger = logging.getLogger('shuttle')
    try:
        # Create destination directory if it doesn't exist
        dest_dir = os.path.dirname(destination_file_path)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except PermissionError:
            logger.error(f"Permission denied creating directory: {dest_dir}")
            return False
        except OSError as e:
            logger.error(f"Failed to create directory {dest_dir}: {e}")
            return False

        # Move file to destination
        shutil.move(quarantine_file_path, destination_file_path)
        logger.info(f"Moved clean file to destination: {destination_file_path}")

        # Verify integrity and delete source if requested
        if delete_source_files:
            if verify_file_integrity(source_file_path, destination_file_path):
                remove_file_with_logging(source_file_path)
            else:
                logger.error(f"Integrity check failed, source file not deleted: {source_file_path}")
                return False

        return True
    except FileNotFoundError as e:
        logger.error(f"File not found during handling of clean file: {e}")
        return False
    except PermissionError as e:
        logger.error(f"Permission denied during handling of clean file: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to handle clean file {quarantine_file_path}: {e}")
        return False

def verify_file_integrity(source_file_path, comparison_file_path):
    """Verify file integrity between source and destination."""
    logger = logging.getLogger('shuttle')

    if os.path.getsize(source_file_path) == 0 or os.path.getsize(comparison_file_path) == 0:
        logger.error("One of the files is empty")
        return False

    source_hash = get_file_hash(source_file_path)
    comparison_hash = get_file_hash(comparison_file_path)

    if source_hash is None:
        logger.error(f"Failed to compute hash for source file: {source_file_path}")
        return False
    if comparison_hash is None:
        logger.error(f"Failed to compute hash for comparison file: {comparison_file_path}")
        return False

    if compare_file_hashes(source_hash, comparison_hash):
        logger.info(f"File integrity verified between {source_file_path} and {comparison_file_path}")
        return True
    else:
        logger.error(f"File integrity check failed between {source_file_path} and {comparison_file_path}")
        return False

def handle_suspect_file(
    quarantine_file_path,
    source_file_path,
    hazard_archive_path,
    hazard_archive_password,
    delete_source_files
):
    """
    Handle processing of suspect files by compressing and encrypting them.

    Args:
        quarantine_file_path (str): Full path to the file in quarantine
        source_file_path (str): Full path to the original source file
        hazard_archive_path (str): Path to the hazard archive directory
        hazard_archive_password (str): Password for the encrypted archive
        delete_source_files (bool): Whether to delete source files after processing

    Returns:
        bool: True if the file was successfully handled, False otherwise
    """
    logger = logging.getLogger('shuttle')
    try:
        if hazard_archive_path and hazard_archive_password:
            # Verify integrity with source before archiving
            if not verify_file_integrity(source_file_path, quarantine_file_path):
                logger.error(f"Integrity check failed before archiving: {quarantine_file_path}")
                return False

            # Create hazard archive directory
            try:
                os.makedirs(hazard_archive_path, exist_ok=True)
            except PermissionError:
                logger.error(f"Permission denied creating hazard archive directory: {hazard_archive_path}")
                return False
            except OSError as e:
                logger.error(f"Failed to create hazard archive directory {hazard_archive_path}: {e}")
                return False

            archive_name = 'hazard_' + os.path.basename(quarantine_file_path) + '_' + datetime.now().strftime('%Y%m%d%H%M%S') + '.zip'
            archive_path = os.path.join(hazard_archive_path, archive_name)

            # Use zip with password from stdin
            zip_command = [
                'zip', '-e', archive_path, quarantine_file_path
            ]

            # Execute the zip command, passing password via stdin
            result = subprocess.run(
                zip_command,
                input=hazard_archive_password + '\n' + hazard_archive_password + '\n',  # zip asks for password twice
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )

            if result.returncode == 0:
                logger.info(f"File archived and encrypted to {archive_path}")
                # Remove the infected file from quarantine
                remove_file_with_logging(quarantine_file_path)
                
                # Delete source file if requested and integrity check passed
                if delete_source_files:
                    remove_file_with_logging(source_file_path)
                
                return True
            else:
                logger.error(f"Failed to create encrypted archive for {quarantine_file_path}. Error: {result.stderr.strip()}")
                return False
        else:
            logger.warning(f"No hazard archive path or password provided. Deleting file {quarantine_file_path}.")
            # Remove the infected file from quarantine
            remove_file_with_logging(quarantine_file_path)
            
            # Delete source file if requested
            if delete_source_files:
                remove_file_with_logging(source_file_path)
            
            return True

    except FileNotFoundError:
        logger.error(f"'zip' command not found. Please ensure it is installed.")
        return False
    except PermissionError:
        logger.error(f"Permission denied when handling suspect file: {quarantine_file_path}")
        return False
    except Exception as e:
        logger.error(f"Error handling suspect file {quarantine_file_path}: {e}")
        return False
    
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
    parser.add_argument('--max-scans', type=int, help='Maximum number of parallel scans')
    parser.add_argument('--lock-file', default='/tmp/shuttle.lock', help='Path to lock file to prevent multiple instances')
    parser.add_argument('-QuarantineHazardArchive', help='Path to the hazard archive directory')
    parser.add_argument('-HazardArchivePassword', help='Password for the encrypted hazard archive')
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
        source_path = get_setting(args.SourcePath, 'Paths', 'SourcePath')
        destination_path = get_setting(args.DestinationPath, 'Paths', 'DestinationPath')
        quarantine_path = get_setting(args.QuarantinePath, 'Paths', 'QuarantinePath')
        log_path = get_setting(args.LogPath, 'Paths', 'LogPath')
        hazard_archive_path = get_setting(args.QuarantineHazardArchive, 'Paths', 'QuarantineHazardArchive')
        log_level_str = get_setting(args.LogLevel, 'Logging', 'LogLevel', 'INFO').upper()

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

        required_commands = ['lsof', 'mdatp', 'zip']
        missing_commands = []

        for cmd in required_commands:
            if shutil.which(cmd) is None:
                missing_commands.append(cmd)

        if missing_commands:
            for cmd in missing_commands:
                logger.error(f"Required command '{cmd}' not found. Please ensure it is installed and accessible in your PATH.")
            sys.exit(1)

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

        # Retrieve other settings
        delete_source_files = args.DeleteSourceFilesAfterCopying or config.getboolean('Settings', 'DeleteSourceFilesAfterCopying', fallback=False)

        if args.max_scans is not None:
            max_scans = args.max_scans
        else:
            max_scans = config.getint('Settings', 'MaxScans', fallback=2)

        # Validate required paths
        if not (source_path and destination_path and quarantine_path):
            logger.error("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.")
            sys.exit(1)

        logger.info(f"SourcePath: {source_path}")
        logger.info(f"DestinationPath: {destination_path}")
        logger.info(f"QuarantinePath: {quarantine_path}")

        try:
            # Create quarantine directory if it doesn't exist
            os.makedirs(quarantine_path, exist_ok=True)

            # Copy files from source to quarantine directory
            # os.walk traverses the directory tree
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
                    # Replicate that structure in the quarantine directory
                    rel_dir = os.path.relpath(root, source_path)
                    quarantine_file_copy_dir = os.path.join(quarantine_path, rel_dir)
                    os.makedirs(quarantine_file_copy_dir, exist_ok=True)

                    # Copy the file to the appropriate directory in the quarantine directory
                    quarantine_temp_path = os.path.join(quarantine_file_copy_dir, file + '.tmp')
                    try:
                        shutil.copy2(file_path, quarantine_temp_path)
                        os.rename(quarantine_temp_path, os.path.join(quarantine_file_copy_dir, file))
                    except:
                        if os.path.exists(quarantine_temp_path):
                            os.remove(quarantine_temp_path)
                        raise

                    try:
                        ##shutil.copy2(file_path, quarantine_file_path)
                        shutil.copy2(file_path, quarantine_file_copy_dir)
                        logger.info(f"Copied file {file_path} to quarantine: {quarantine_file_copy_dir}")
                    except FileNotFoundError as e:
                        logger.error(f"File not found during copying: {file_path} to quarantine: {quarantine_file_copy_dir}. Error: {e}")
                    except PermissionError as e:
                        logger.error(f"Permission denied when copying file: {file_path} to quarantine: {quarantine_file_copy_dir}. Error: {e}")
                    except Exception as e:
                        logger.error(f"Failed to copy file to quarantine: {file_path} to quarantine: {quarantine_file_copy_dir}. Error: {e}")

            print(f"Successfully copied files from {source_path} to {quarantine_path}")
        except Exception as e:
            print(f"Failed to copy files from {source_path} to {quarantine_path}. Error: {e}")
            sys.exit(1)

        # Prepare arguments for scanning and processing files
        quarantine_files = []
        for root, dirs, files in os.walk(source_path):
            for file in files:
                # Full paths
                source_file_path = os.path.join(root, file)
                
                # Get relative path to maintain structure
                rel_dir = os.path.relpath(root, source_path)
                
                # Create quarantine directory structure
                quarantine_dir = os.path.join(quarantine_path, rel_dir)
                os.makedirs(quarantine_dir, exist_ok=True)
                
                # Full quarantine path
                quarantine_file_path = os.path.join(quarantine_dir, file)
                
                # Full destination path (but don't create directory yet)
                destination_dir = os.path.join(destination_path, rel_dir)
                destination_file_path = os.path.join(destination_dir, file)

                # Copy to quarantine
                try:
                    shutil.copy2(source_file_path, quarantine_file_path)
                    logger.info(f"Copied file {source_file_path} to quarantine: {quarantine_file_path}")
                    
                    # Add to processing queue with full paths
                    quarantine_files.append((
                        quarantine_file_path,     # full path to quarantine file
                        source_file_path,         # full path to source file
                        destination_file_path,     # full path to destination file
                        hazard_archive_path,
                        hazard_archive_password,
                        delete_source_files
                    ))
                except FileNotFoundError as e:
                    logger.error(f"File not found during copying: {source_file_path}. Error: {e}")
                except PermissionError as e:
                    logger.error(f"Permission denied when copying file: {source_file_path}. Error: {e}")
                except Exception as e:
                    logger.error(f"Failed to copy file to quarantine: {source_file_path}. Error: {e}")

        # Process files in parallel using a ProcessPoolExecutor with graceful shutdown
        with ProcessPoolExecutor(max_workers=max_scans) as executor:
            try:
                results = list(executor.map(scan_and_process_file, quarantine_files))
            except Exception as e:
                logger.error(f"An error occurred during parallel processing: {e}")
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        # Check if all files were processed successfully
        if not all(results):
            print("Some files failed to be processed.")

        # After processing all files, remove the quarantine directory
        shutil.rmtree(quarantine_path, ignore_errors=True)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Remove the lock file upon script completion or error
        if os.path.exists(args.lock_file):
            os.remove(args.lock_file)

if __name__ == '__main__':
    main()