from shuttle import ShuttleBase, ShuttleConfig, process_modes

from shuttle import (
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
import json


scan_result_types = types.SimpleNamespace()

scan_result_types.FILE_IS_SUSPECT = 3
scan_result_types.FILE_IS_CLEAN = 0
scan_result_types.FILE_SCAN_FAILED = 100



def check_defender_logs_for_file(file_path, file_hash):
    """
    Check Microsoft Defender logs for a specific file's scan results.
    
    Args:
        file_path (str): Path to the file
        file_hash (str): SHA256 hash of the file to verify
        
    Returns:
        dict: {
            'scanned': bool,  # Whether file has been scanned
            'clean': bool,    # Whether file is clean (if scanned)
            'hash_match': bool # Whether stored hash matches current file
        }
    """
    logger = logging.getLogger('shuttle')
    try:
		# Query defender logs for the file
        result = subprocess.run(
            ["mdatp", "threat", "list", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"Failed to query defender logs: {result.stderr}")
            return {'scanned': False, 'clean': False, 'hash_match': False}
            
        # Parse the JSON output and look for our file
        # You'll need to adjust this based on actual log format
        scan_data = json.loads(result.stdout)

        # For illustration, we just do a simple search. Adjust to match your environment’s log format.
        # We’ll loop through known threats or scanned items and see if file_hash or file_path is found.
        
        scanned = False
        clean = True
        hash_match = False

        # Example structure: 
        #   "threats": [
        #       { "fileName":"...", "sha256":"...", "threatStatus":"active"/"resolved"/... }
        #   ]
        # Adjust based on your real logs.
        threats = scan_data.get("threats", [])
        for item in threats:
            if item.get("sha256") == file_hash:
                # We found the entry
                scanned = True
                hash_match = True
                # If the threat is present or unresolved, not clean. 
                # Adjust logic to your log structure.
                threat_status = item.get("threatStatus","")
                if threat_status not in ["resolved", "cleaned"]:
                    clean = False
                break

        return {
            'scanned': scanned, # If found in logs
            'clean': clean, 	# If no threats found
            'hash_match': hash_match
        }
        
    except Exception as e:
        logger.error(f"Error checking defender logs: {e}")
        return {'scanned': False, 'clean': False, 'hash_match': False}


def passive_check_for_malware(file_path):
    """
    Returns (scan_result, file_hash) tuple where:
    scan_result is:
        FILE_IS_CLEAN if Defender logs show the file is scanned and no threats,
        FILE_IS_SUSPECT if logs show the file is infected,
        FILE_SCAN_FAILED if there's an error or mismatch,
        None if the file has not been scanned yet (skip).
    file_hash is:
        The SHA256 hash of the file if computed successfully,
        None if hash computation failed
    """
    logger = logging.getLogger('shuttle')
    file_hash = get_file_hash(file_path)
    if not file_hash:
        logger.error(f"Could not compute hash for {file_path}")
        return scan_result_types.FILE_SCAN_FAILED, None

    result = check_defender_logs_for_file(file_path, file_hash)
    if not result['scanned']:
        # No logs = not scanned yet
        return None, file_hash

    if not result['hash_match']:
        # Logs found, but our hash was not found or mismatch
        logger.warning(f"Defender logs mismatch. Possibly stale or partial info: {file_path}")
        return scan_result_types.FILE_SCAN_FAILED, file_hash

    # If we reach here, scanned = True and hashes matched
    if result['clean']:
        return scan_result_types.FILE_IS_CLEAN, file_hash
    else:
        return scan_result_types.FILE_IS_SUSPECT, file_hash



def process_file(args):
    """
    Process a file that has already been confirmed clean by Defender.
    Just verify hash still matches before copying to destination.
    
    Args:
        args (tuple): Contains all necessary arguments.
            - quarantine_file_path (str): Full path to the file in quarantine
            - source_file_path (str): Full path to the original source file
            - destination_file_path (str): Full path where the file should be copied in destination
            - hazard_archive_path (str): Path to the hazard archive directory
            - key_file_path (str): Full path to the public encryption key file
            - delete_source_files (bool): Whether to delete source files after processing
            - source_hash (str): The hash value when file was verified clean

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
        delete_source_files,
        source_hash
    ) = args

    logger = logging.getLogger('shuttle')

    # Verify hash still matches
    quarantine_hash = get_file_hash(quarantine_file_path)
    if quarantine_hash == source_hash:
        logger.info(f"Hash verified for {quarantine_file_path}, copying to destination")
        return handle_clean_file(
            quarantine_file_path,
            source_file_path,
            destination_file_path,
            delete_source_files
        )
    else:
        logger.warning(f"Hash mismatch for {quarantine_file_path}, treating as suspect")
        return handle_suspect_file(
            quarantine_file_path,
            source_file_path,
            hazard_archive_path,
            key_file_path,
            delete_source_files
        )


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
 




 
def process_directory(
    source_path,
    destination_path,
    quarantine_path,
    hazard_archive_path,
    hazard_encryption_key_file_path,
    delete_source_files,
    max_scan_threads
):
    """
    Check source files for completed Defender scans before copying to quarantine.
    Only process files that have been scanned and are clean.
    """
    logger = logging.getLogger('shuttle')
    quarantine_files = []

    try:
        # Create quarantine directory if it doesn't exist
        os.makedirs(quarantine_path, exist_ok=True)


        # os.walk traverses the directory tree
        for source_root, dirs, source_files in os.walk(source_path, topdown=False):
            for source_file in source_files:
                source_file_path = os.path.join(source_root, source_file)

                # Skip files that aren't stable or are open
                if not is_file_stable(source_file_path):
                    logger.info(f"Skipping file {source_file_path} (not yet stable).")
                    continue

                # Skip files that are currently open
                if is_file_open(source_file_path):
                    logger.info(f"Skipping file {source_file_path} (currently open).")
                    continue

                # Check if file has been scanned before copying
                source_scan_result, source_hash = passive_check_for_malware(source_file_path)
                if source_scan_result is None:
                    logger.info(f"Skipping file {source_file_path} (not yet scanned by Defender).")
                    continue
                
                # Only proceed with clean files
                if source_scan_result != scan_result_types.FILE_IS_CLEAN:
                    logger.warning(f"Skipping file {source_file_path} (scan result: {source_scan_result}).")
                    continue

                if not source_hash:
                    logger.error(f"Could not compute hash for source file: {source_file_path}")
                    continue

                # Set up paths
                rel_dir = os.path.relpath(source_root, source_path)
                quarantine_subdir = os.path.join(quarantine_path, rel_dir)
                destination_subdir = os.path.join(destination_path, rel_dir)

                # Build final quarantine path
                quarantine_file_path = os.path.join(normalize_path(quarantine_subdir), source_file)
                destination_file_path = os.path.join(normalize_path(destination_subdir), source_file)

                try:
                    # Copy to quarantine
                    copy_temp_then_rename(source_file_path, quarantine_file_path)
                    logger.info(f"Copied {source_file_path} to quarantine: {quarantine_file_path}")

                    # Verify hash after copy
                    quarantine_hash = get_file_hash(quarantine_file_path)
                    if quarantine_hash != source_hash:
                        logger.error(f"Hash mismatch after quarantine copy for {source_file_path}")
                        remove_file_with_logging(quarantine_file_path)
                        continue

                    # Add to processing queue with full paths
                    quarantine_files.append((
                        quarantine_file_path,     # full path to quarantine file
                        source_file_path,         # full path to source file
                        destination_file_path,     # full path to destination file
                        hazard_archive_path,
                        hazard_encryption_key_file_path,
                        delete_source_files,
                        source_hash              # hash to verify later
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to copy to quarantine. Src: {source_file_path}. Err: {e}")

        # Process files in parallel
        with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
            results = list(executor.map(process_file, quarantine_files))

        # Check if all files were processed successfully
        if not all(results):
            logger.warning("Some files were skipped or failed to process completely.")

        # Clean up quarantine directory
        remove_directory_contents(quarantine_path)

        # Optional: remove empty directories in the source if requested
        if delete_source_files:
            directories_to_remove = []
            for index, entry in enumerate(quarantine_files):
                # If the file was processed successfully, we can attempt removing the original folder
                if index < len(results) and results[index]:
                    source_dir = os.path.dirname(entry[1])
                    if normalize_path(source_dir) != normalize_path(source_path):
                        if source_dir not in directories_to_remove and os.path.exists(source_dir):
                            directories_to_remove.append(source_dir)
            
            for directory_to_remove in directories_to_remove:

                # this won't remove directories that contain subdirectories from which no files were tranferred
                # remove_empty_directories() will remove recursively remove subfolders
                if len(os.listdir(directory_to_remove)) == 0:
                    if not remove_directory(directory_to_remove):
                        logger.error(f"Cannot remove directory: {directory_to_remove}")
                    else:
                        logger.info(f"Removed empty directory: {directory_to_remove}")

    except Exception as e:
        logger.error(f"Error processing directory in passive mode: {e}")


class PassiveScanner(ShuttleBase):

    def process_files(self):
        """Implementation for passive scanning"""
        process_directory(
           self.config.source_path,
            self.config.destination_path,
            self.config.quarantine_path,
            self.config.hazard_archive_path,
            self.config.hazard_encryption_key_file_path,
            self.config.delete_source_files,
            self.config.max_scan_threads
        )