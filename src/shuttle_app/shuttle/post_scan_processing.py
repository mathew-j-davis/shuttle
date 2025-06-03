import os
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from shuttle_common.logging_setup import setup_logging
from shuttle_common.logger_injection import with_logger
from shuttle_common.files import (
    copy_temp_then_rename,
    get_file_hash,
    verify_file_integrity,
    remove_file_with_logging,
    encrypt_file
)

@with_logger
def handle_suspect_source_file(
    source_file_path,
    quarantine_hash,
    hazard_archive_path,
    key_file_path,
    logging_options=None,
    logger=None
):
    """
    Handle a source file when its quarantine copy is found to be suspect.
    
    Args:
        source_file_path (str): Path to the source file
        quarantine_hash (str): Hash of the quarantine file for comparison
        hazard_archive_path (str): Path to archive suspicious files
        key_file_path (str): Path to GPG public key file
        delete_source_files (bool): Whether to delete source files
        logging_options: Optional logging configuration options
    
    Returns:
        bool: True if handled successfully, False otherwise
    """
    
    if not os.path.exists(source_file_path):
        return True
        
    source_hash = get_file_hash(source_file_path, logging_options)
    
    if source_hash == quarantine_hash:
        logger.error(f"Hash match for source file {source_file_path}")
        logger.error(f"Archiving source file")
        
        if not handle_suspect_file(
            source_file_path,
            hazard_archive_path,
            key_file_path,
            logging_options
        ):
            logger.error(f"Failed to archive source file: {source_file_path}")
            return False
    else:
        logger.error(f"Hash mismatch for source file {source_file_path}")
        logger.error(f"Not archiving source file")
        
    return True

@with_logger
def handle_suspect_scan_result(
    quarantine_file_path,
    source_file_path,
    hazard_archive_path,
    key_file_path,
    delete_source_files,
    scanner_handling_suspect_file,
    quarantine_hash,
    logging_options=None,
    logger=None
):
    """
    Handle the result of a malware scan that found a suspect file.
    
    Args:
        quarantine_file_path (str): Path to the file in quarantine
        source_file_path (str): Path to the original source file
        hazard_archive_path (str): Path to archive suspicious files
        key_file_path (str): Path to GPG public key file
        delete_source_files (bool): Whether to delete source files
        scanner_handling_suspect_file (bool): Whether virus scanner removes suspect files
        quarantine_hash (str): Hash of the quarantine file for comparison
    
    Returns:
        bool: True if handled successfully, False otherwise
    """
    scanner_handled_suspect_file = False

    if scanner_handling_suspect_file:
        logger.warning(f"Threats found in {quarantine_file_path}, letting Scanner handle it")
        
        # Give Scanner time to handle the file and verify it's been removed
        time.sleep(0.5)  # 500ms pause
        if not os.path.exists(quarantine_file_path):
            logger.info(f"Scanner has removed the suspect file: {quarantine_file_path}")
            scanner_handled_suspect_file = True
        else:
            logger.warning(f"Scanner did not remove the suspect file: {quarantine_file_path}, handling internally")

    if scanner_handled_suspect_file:
        return handle_suspect_source_file(
            source_file_path,
            quarantine_hash,
            hazard_archive_path,
            key_file_path,
            logging_options
        )
    else:
        logger.warning(f"Threats found in {quarantine_file_path}, handling internally")
        return handle_suspect_quarantine_file_and_delete_source(
            quarantine_file_path,
            source_file_path,
            hazard_archive_path,
            key_file_path,
            delete_source_files,
            logging_options
        )

@with_logger
def handle_clean_file(
    quarantine_file_path,
    source_file_path,
    destination_file_path,
    delete_source_files,
    logging_options=None,
    logger=None
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
    
    try:
        copy_temp_then_rename(quarantine_file_path, destination_file_path, logging_options)

    except Exception as e:
        if logger:
            logger.error(f"Failed to copy clean file from {quarantine_file_path} to {destination_file_path}: {e}")
        return False
    
    if delete_source_files:
        try:

            # Verify integrity and delete source if requested
            verify = verify_file_integrity(source_file_path, destination_file_path, logging_options)

            if verify['success']:
                remove_file_with_logging(source_file_path, logging_options)
            else:
                logger.error(f"Integrity check failed, source file not deleted: {source_file_path}")
                return False
  
        except FileNotFoundError as e:
            if logger:
                logger.error(f"File not found during handling of clean file: {e}")
            return False
        
        except PermissionError as e:
            if logger:
                logger.error(f"Permission denied during handling of clean file: {e}")
            return False
        
        except Exception as e:
            if logger:
                logger.error(f"Failed to handle clean file {quarantine_file_path}: {e}")
            return False
        
    return True


@with_logger
def handle_suspect_quarantine_file_and_delete_source(
    quarantine_file_path,
    source_file_path,
    hazard_archive_path,
    key_file_path,
    delete_source_files,
    logging_options=None,
    logger=None
):
    """
    Handle a file that has been identified as suspicious/infected.
    Archives the quarantine file and optionally deletes the source.
    
    Args:
        quarantine_file_path (str): Path to the file in quarantine
        source_file_path (str): Original path of the file
        hazard_archive_path (str): Path to archive suspicious files
        key_file_path (str): Path to GPG public key file
        delete_source_files (bool): Whether to delete source files after processing
    
    Returns:
        bool: True if file was handled successfully, False otherwise
    """
    
    try:
        # If hazard archive path and encryption key are provided, archive the file
        if hazard_archive_path and key_file_path:
            # Verify file integrity before archiving
            verify = verify_file_integrity(source_file_path, quarantine_file_path, logging_options)

            if not verify['success']:
                logger.error(f"Integrity check failed before archiving: {quarantine_file_path}")
                return False

            logger.error(f"Malware detected in : {quarantine_file_path} with hash value {verify['a']}")

            # Archive and remove the quarantine file
            if not handle_suspect_file(
                quarantine_file_path,
                hazard_archive_path,
                key_file_path,
                logging_options
            ):
                logger.error(f"Failed to handle suspect quarantine file: {quarantine_file_path}")
                return False

            # Delete source file if requested
            if delete_source_files:
                if not remove_file_with_logging(source_file_path, logging_options):
                    logger.error(f"Failed to remove source file after archiving: {source_file_path}")
                    return False

            return True
        else:
            # No hazard archive parameters - delete the infected file
            logger.warning(
                f"No hazard archive path or encryption key file provided. "
                f"Deleting infected file: {quarantine_file_path}"
            )

            # Remove the infected file from quarantine
            if not remove_file_with_logging(quarantine_file_path, logging_options):
                logger.error(f"Failed to remove quarantined file: {quarantine_file_path}")
                return False
            
            # Delete source file if requested
            if delete_source_files:
                if not remove_file_with_logging(source_file_path, logging_options):
                    logger.error(f"Failed to remove source file: {source_file_path}")
                    return False
        
        return True

    except Exception as e:
        if logger:
            logger.error(f"Unexpected error handling suspect file {quarantine_file_path}: {e}")
        return False
    
@with_logger
def handle_suspect_file(
    suspect_file_path,
    hazard_archive_path,
    key_file_path,
    logging_options=None,
    logger=None
):
    """
    Archive a suspect file by encrypting it and then remove the original.
    
    Args:
        suspect_file_path (str): Path to the suspect file
        hazard_archive_path (str): Path to archive suspicious files
        key_file_path (str): Path to GPG public key file
    
    Returns:
        bool: True if file was archived successfully and removed, False otherwise
    """

    if not os.path.exists(suspect_file_path):
        logger.error(f"Cannot archive non-existent file: {suspect_file_path}")
        return False

    if not (hazard_archive_path and key_file_path):
        logger.warning(
            f"No hazard archive path or encryption key file provided. "
            f"Cannot archive suspect file: {suspect_file_path}"
        )
        return False

    # Create hazard archive directory if it doesn't exist
    try:
        os.makedirs(hazard_archive_path, exist_ok=True)
    except PermissionError as e:
        if logger:
            logger.error(f"Permission denied when creating hazard archive directory {hazard_archive_path}: {e}")
        return False
    except OSError as e:
        if logger:
            logger.error(f"OS error when creating hazard archive directory {hazard_archive_path}: {e}")
        return False

    # Generate encrypted file path with timestamp
    archive_name = f"hazard_{os.path.basename(suspect_file_path)}_{datetime.now().strftime('%Y%m%d%H%M%S')}.gpg"
    archive_path = os.path.join(hazard_archive_path, archive_name)

    # Attempt to encrypt the file
    if not encrypt_file(suspect_file_path, archive_path, key_file_path, logging_options):
        logger.error(f"Failed to encrypt file: {suspect_file_path}")
        return False

    logger.info(f"Successfully encrypted suspect file to: {archive_path}")

    archive_hash = get_file_hash(archive_path, logging_options)
    logger.info(f"Suspect file archive {archive_path} has hash value : {archive_hash}")

    # Remove the original file after successful archiving
    if not remove_file_with_logging(suspect_file_path, logging_options):
        logger.error(f"Failed to remove file after archiving: {suspect_file_path}")
        return False

    return True
