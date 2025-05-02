import os
import subprocess
import logging
import time
import types
from datetime import datetime
import shutil

from concurrent.futures import ProcessPoolExecutor
from .files import (
    is_filename_safe,
    is_pathname_safe,
    is_file_stable,
    is_file_open,
    normalize_path,
    copy_temp_then_rename,
    remove_directory_contents,
    remove_directory,
    get_file_hash,
)

from .post_scan_processing import (
    handle_clean_file,
    handle_suspect_scan_result
)

scan_result_types = types.SimpleNamespace()

scan_result_types.FILE_IS_SUSPECT = 3
scan_result_types.FILE_IS_CLEAN = 0
scan_result_types.FILE_SCAN_FAILED = 100



def run_malware_scan(cmd, path, result_handler):
    """
    Run a malware scan using the specified command and process the results.
    
    Args:
        cmd (list): Command to run
        path (str): Path to file being scanned
        result_handler (callable): Function to process scan results
        
    Returns:
        int: scan_result_types value
    """
    logger = logging.getLogger('shuttle')
    try:
        logger.info(f"Scanning file {path} for malware...")
        
        child_run = subprocess.Popen(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = ''
        error = ''

        last = time.time()
        while child_run.poll() is None:
            if time.time() - last > 5:
                print('Process is still running')
                last = time.time()

            tmp = child_run.stdout.read(1)
            if tmp:
                output += tmp
            tmp = child_run.stderr.read(1)
            if tmp:
                error += tmp

        output += child_run.stdout.read()
        error += child_run.stderr.read()

        child_run.stdout.close() 
        child_run.stderr.close()

        return result_handler(child_run.returncode, output)

    except FileNotFoundError:
        logger.error(f"Files not found when scanning file: {path}")
    except PermissionError:
        logger.error(f"Permission denied when scanning file: {path}")
    except Exception as e:
        logger.error(f"Failed to perform malware scan on {path}. Error: {e}")

    return scan_result_types.FILE_SCAN_FAILED


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
            - defender_handles_suspect (bool): Whether to let Defender handle suspect files

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
        on_demand_defender,
        on_demand_clam_av,
        defender_handles_suspect
    ) = args

    logger = logging.getLogger('shuttle')

    if not on_demand_defender and not on_demand_clam_av:
        logger.error("No virus scanner or defender specified. Please specify at least one.")
        return False

    logger.info(f"getting file hash: {quarantine_file_path}.")
    quarantine_hash = get_file_hash(quarantine_file_path)

    defender_result = None
    clam_av_result = None

    suspect_file_detected = False
    scanner_handling_suspect_file = False

    if on_demand_defender:
        # Scan the file for malware
        logger.info(f"Scanning file {quarantine_file_path} for malware...")
        defender_result = scan_for_malware_using_defender(quarantine_file_path)


        if defender_result == scan_result_types.FILE_IS_SUSPECT:
            suspect_file_detected = True
            if defender_handles_suspect:
                logger.warning(f"Threats found in {quarantine_file_path}, letting Defender handle it")
                scanner_handling_suspect_file = True

            else:
                logger.warning(f"Threats found in {quarantine_file_path}, handling internally")
             

    if ((not suspect_file_detected) and on_demand_clam_av):
        clam_av_result = scan_for_malware_using_clam_av(quarantine_file_path)

        if clam_av_result == scan_result_types.FILE_IS_SUSPECT:
            suspect_file_detected = True
            logger.warning(f"Threats found in {quarantine_file_path}, handling internally")



    if suspect_file_detected:
        return handle_suspect_scan_result(
            quarantine_file_path,
            source_file_path,
            hazard_archive_path,
            key_file_path,
            delete_source_files,
            scanner_handling_suspect_file,
            quarantine_hash
        )
    

    def is_clean_scan(scanner_enabled, scan_result):
        return (
            not scanner_enabled 
            or (
                scanner_enabled 
                and scan_result == scan_result_types.FILE_IS_CLEAN
            )
        )

    # Check if all enabled scanners report clean
    if (
        is_clean_scan(on_demand_defender, defender_result) 
        and is_clean_scan(on_demand_clam_av, clam_av_result)
    ):
        return handle_clean_file(
            quarantine_file_path,
            source_file_path,
            destination_file_path,
            delete_source_files
        )

    else:
        logger.warning(f"Scan failed on {quarantine_file_path}")
        return False

def scan_and_process_directory(
    source_path,
    destination_path,
    quarantine_path,
    hazard_archive_path,
    hazard_encryption_key_file_path,
    delete_source_files,
    max_scan_threads,
    on_demand_defender,
    on_demand_clam_av,
    defender_handles_suspect_files,
    notifier,
    throttle=True,
    throttle_free_space=10000
    ):
    """
    Process all files in the source directory:
    1. Copy to quarantine
    2. Scan for malware
    3. Move clean files to destination
    4. Handle suspect files according to defender_handles_suspect_files setting

    Args:
        source_path (str): Path to source directory
        destination_path (str): Path to destination directory
        quarantine_path (str): Path to quarantine directory
        hazard_archive_path (str): Path to archive suspect files
        hazard_encryption_key_file_path (str): Path to encryption key
        delete_source_files (bool): Whether to delete source files
        max_scan_threads (int): Maximum number of parallel scans
        defender_handles_suspect_files (bool): Whether to let Defender handle suspect files
        throttle (bool): Whether to enable throttling
        throttle_free_space (int): Minimum free space required in MB
    """
    quarantine_files = []

    logger = logging.getLogger('shuttle')
    
    # Throttling status flags
    quarantine_has_space = False
    destination_has_space = False
    hazard_has_space = False
    disk_error = False

    def check_directory_space(directory_path, file_size_mb, min_free_space_mb, directory_name):
        """
        Check if a directory has enough free space for a file, leaving a minimum amount free after copy.
        
        Args:
            directory_path (str): Path to the directory to check
            file_size_mb (float): Size of the file in MB
            min_free_space_mb (int): Minimum free space to maintain after copy in MB
            directory_name (str): Name of the directory for logging purposes
            
        Returns:
            bool: True if directory has enough space, False otherwise
        """
        logger = logging.getLogger('shuttle')
        
        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path, exist_ok=True)
                
            stats = shutil.disk_usage(directory_path)
            free_mb = stats.free / (1024 * 1024)  # Convert bytes to MB
            
            has_space = (free_mb - file_size_mb) >= min_free_space_mb
            
            if not has_space:
                logger.error(f"{directory_name} is full. Free: {free_mb:.2f} MB, Required: {min_free_space_mb + file_size_mb:.2f} MB")
            
            return has_space
            
        except Exception as e:
            logger.error(f"Error checking space in {directory_name}: {e}")
            return False

    try:
        # Create quarantine directory if it doesn't exist
        os.makedirs(quarantine_path, exist_ok=True)

        # Copy files from source to quarantine directory
        # os.walk traverses the directory tree
        for source_root, dirs, source_files in os.walk(source_path, topdown=False):
            for source_file in source_files:
                if not is_filename_safe(source_file):
                    logger.error(f"Skipping file {source_file} because it contains unsafe characters.")
                    continue

                if not is_pathname_safe(source_root):
                    logger.error(f"Skipping {source_root} because it contains unsafe characters.")
                    continue

                source_file_path = os.path.join(source_root, source_file)

                if not is_pathname_safe(source_file_path):
                    logger.error(f"Skipping path {source_file_path} because it contains unsafe characters.")
                    continue
                

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

                # Check disk space if throttling is enabled 
                if throttle:
                    try:
                        # Get file size in MB
                        file_size_mb = os.path.getsize(source_file_path) / (1024 * 1024)
                        
                        # Check space in all target directories
                        quarantine_has_space = check_directory_space(
                            quarantine_path, 
                            file_size_mb, 
                            throttle_free_space, 
                            "Quarantine directory"
                        )
                        
                        destination_has_space = check_directory_space(
                            destination_path, 
                            file_size_mb, 
                            throttle_free_space, 
                            "Destination directory"
                        )
                        
                        hazard_has_space = check_directory_space(
                            hazard_archive_path, 
                            file_size_mb, 
                            throttle_free_space, 
                            "Hazard archive directory"
                        )
                        
                        # If any directory is full, break out of the inner loop
                        if not quarantine_has_space or not destination_has_space or not hazard_has_space:
                            logger.warning(f"Stopping file processing due to insufficient disk space")
                            break   

                    except Exception as e:
                        logger.error(f"Error checking disk space: {e}")
                        disk_error = True
                        break
                
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
                        delete_source_files,
                        on_demand_defender,
                        on_demand_clam_av,
                        defender_handles_suspect_files   
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to copy file from source: {source_file_path} to quarantine: {quarantine_file_path}. Error: {e}")
            
            # If directories are full, break out of the outer loop too
            if not quarantine_has_space or not destination_has_space or not hazard_has_space or disk_error:
                break

        results = list()
        if max_scan_threads > 1:
        # Process files in parallel using a ProcessPoolExecutor with graceful shutdown
            with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
                try:
                    results = list(executor.map(scan_and_process_file, quarantine_files))
                except Exception as e:
                    logger.error(f"An error occurred during parallel processing: {e}")
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
        else:
            for quarantine_file_parameters in quarantine_files:

                result = scan_and_process_file(
                        quarantine_file_parameters
                    )
                
                results.append(result)  

        # Check if all files were processed successfully
        if not all(results):
            logger.error(f"Some files failed to be processed.")

            if(notifier):
                notifier.notify(
                    subject="Shuttle Error: Some files failed to be processed",
                    body="Some files failed to be processed."
                )

        # Send notifications for disk space issues if applicable
        if throttle and notifier:
            if not quarantine_has_space or not destination_has_space or not hazard_has_space or disk_error:
                full_dirs = []
                if not quarantine_has_space:
                    full_dirs.append("Quarantine directory Space Low    ")
                if not destination_has_space:
                    full_dirs.append("Destination directory Space Low")
                if  not hazard_has_space:
                    full_dirs.append("Hazard archive directory Space Low")
                if disk_error:
                    full_dirs.append("Disk error when checking space")
                notifier.notify(
                    subject="Shuttle Warning: Disk Issue",
                    body=f"File processing was stopped due to insufficient disk space in: {', '.join(full_dirs)}. Please free up space."
                )

        # After processing all files, remove contents of quarantine directory
        remove_directory_contents(quarantine_path)

        # clean up empty subdirectories
        #  this can be made more efficient

        if(delete_source_files):

            directories_to_remove = []

            for counter, file_transfer in enumerate(quarantine_files):
                if counter >= len(results):
                    break

                #transfer was successful, clean up empty directories

                if results[counter]:

                    source_file_dir = os.path.dirname( quarantine_files[counter][1]) ## source_file_path

                    if ( normalize_path(source_file_dir) == normalize_path(source_path) ):
                        continue

                    if not source_file_dir in directories_to_remove:

                        if not os.path.exists(source_file_dir):
                            continue

                        directories_to_remove.append(source_file_dir)
            
            for directory_to_remove in directories_to_remove:

                # this won't remove directories that contain subdirectories from which no files were transferred
                # remove_empty_directories() will remove recursively remove subfolders
                if len(os.listdir(directory_to_remove)) == 0:
                    if not remove_directory(directory_to_remove):
                        logger.error(f"Could not remove directory during cleanup: {directory_to_remove}")
                    else:
                        logger.info(f"Directory removed during cleanup: {directory_to_remove}")


    except Exception as e:
        logger.error(f"Failed to copy files to quarantine: Error: {e}")

def process_files(config, notifier):

    scan_and_process_directory(
        config.source_path,
        config.destination_path,
        config.quarantine_path,
        config.hazard_archive_path,
        config.hazard_encryption_key_file_path,
        config.delete_source_files,
        config.max_scan_threads,
        config.on_demand_defender,
        config.on_demand_clam_av,
        config.defender_handles_suspect_files,
        notifier,
        throttle=config.throttle,
        throttle_free_space=config.throttle_free_space
    )

clamav_parse_response_patterns = types.SimpleNamespace()
clamav_parse_response_patterns.ERROR = "^ERROR"
clamav_parse_response_patterns.TOTAL_ERRORS = "Total errors: "
clamav_parse_response_patterns.THREAT_FOUND = "FOUND\n\n"
clamav_parse_response_patterns.OK = "^OK\n"
clamav_parse_response_patterns.NO_THREATS = "Infected files: 0"

def handle_clamav_scan_result(returncode, output):
    """
    Process ClamAV scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        
    Returns:
        int: scan_result_types value
    """
    logger = logging.getLogger('shuttle')
    
    # RETURN CODES
    #        0 : No virus found.
    #        1 : Virus(es) found.
    #        2 : An error occurred.
    
    if returncode == 1:
        logger.warning("Threats found")
        return scan_result_types.FILE_IS_SUSPECT
        
    if returncode == 2:
        logger.warning("Error while scanning")
        return scan_result_types.FILE_SCAN_FAILED
        
    if returncode == 0:
        logger.info("No threat found")
        return scan_result_types.FILE_IS_CLEAN
        
    logger.warning(f"Unexpected return code: {returncode}")
    return scan_result_types.FILE_SCAN_FAILED


def scan_for_malware_using_clam_av(path):
    """Scan a file using ClamAV."""
    cmd = [
        "clamdscan",
        "--fdpass",  # temp until permissions issues resolved
        path
    ]
    return run_malware_scan(cmd, path, handle_clamav_scan_result)



# # Define scan output patterns
defender_scan_patterns = types.SimpleNamespace()
defender_scan_patterns.THREAT_FOUND = "Threat(s) found"
defender_scan_patterns.NO_THREATS = "0 threat(s) detected"

def handle_defender_scan_result(returncode, output):
    """
    Process Microsoft Defender scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        
    Returns:
        int: scan_result_types value
    """
    logger = logging.getLogger('shuttle')
    
    if returncode == 0:
        # Always check for threat pattern first, otherwise a malicious filename could be used to add clean response text to output
        if defender_scan_patterns.THREAT_FOUND in output:
            logger.warning("Threats found")
            return scan_result_types.FILE_IS_SUSPECT
        
        elif output.rstrip().endswith(defender_scan_patterns.NO_THREATS):
            logger.info("No threat found")
            return scan_result_types.FILE_IS_CLEAN
        
        else:
            logger.warning(f"Unexpected scan output: {output}")
            
    else:
        logger.warning(f"Scan failed with return code {returncode}")
    
    return scan_result_types.FILE_SCAN_FAILED

def scan_for_malware_using_defender(path):
    """Scan a file using Microsoft Defender."""
    cmd = [
        "mdatp",
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path",
        path
    ]
    return run_malware_scan(cmd, path, handle_defender_scan_result)
