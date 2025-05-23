import os
import logging
from datetime import datetime
from shuttle_common.logging_setup import setup_logging

from concurrent.futures import ProcessPoolExecutor
from shuttle_common.files import (
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

from .throttler import Throttler
from .post_scan_processing import (
    handle_clean_file,
    handle_suspect_scan_result
)


# Import scan utilities from common module
from shuttle_common.scan_utils import (
    scan_for_malware_using_defender,
    run_malware_scan,
    scan_result_types,
    handle_clamav_scan_result,
    scan_for_malware_using_clam_av,
    DefenderScanResult,
    process_defender_result,
)

def scan_and_process_file(
        paths,     
        hazard_encryption_key_file_path, 
        hazard_archive_path,
        delete_source_files, 
        on_demand_defender, 
        on_demand_clam_av, 
        defender_handles_suspect_files, 
        logging_options
    ):
    """
    Scan a file for malware and process it accordingly.

    Args:
        paths (tuple): Contains all necessary paths for the file being processed.
            - quarantine_file_path (str): Full path to the file in quarantine
            - source_file_path (str): Full path to the original source file
            - destination_file_path (str): Full path where the file should be copied in destination

        - hazard_archive_path (str): Path to the hazard archive directory
        - hazard_encryption_key_file_path (str): Full path to the public encryption key file
        - delete_source_files (bool): Whether to delete source files after processing
        - on_demand_defender (bool): Whether to use Defender for on-demand scanning
        - on_demand_clam_av (bool): Whether to use ClamAV for on-demand scanning
        - defender_handles_suspect_files (bool): Whether to let Defender handle suspect files
        - logging_options (tuple): details for logging configuration
    
    Returns:
        bool: True if the file was processed successfully, False otherwise
    """
    # Unpack arguments
    (
        quarantine_file_path,
        source_file_path,
        destination_file_path
    ) = paths

    logger = setup_logging('shuttle.scanning.scan_and_process_file', logging_options)
 
    if not on_demand_defender and not on_demand_clam_av:
        logger.error("No virus scanner or defender specified. Please specify at least one.")
        return False

    logger.info(f"getting file hash: {quarantine_file_path}.")
    quarantine_hash = get_file_hash(quarantine_file_path, logging_options)

    defender_result = None
    clam_av_result = None

    suspect_file_detected = False
    scanner_handling_suspect_file = False

    if on_demand_defender:
        # Scan the file for malware
        logger.info(f"Scanning file {quarantine_file_path} for malware...")
        defender_result = scan_for_malware_using_defender(quarantine_file_path, logging_options)
        
        # Process the scan result with our helper
        scan_result = process_defender_result(
            defender_result,
            quarantine_file_path,
            defender_handles_suspect_files,
            logging_options
        )
        
        # Update our status flags based on the scan result
        suspect_file_detected = scan_result.suspect_detected
        scanner_handling_suspect_file = scan_result.scanner_handles_suspect
        
        # Return early if scan failed (not completed) and no threat detected
        # This happens when file is not found and we're not letting defender handle it
        if not scan_result.scan_completed and not scan_result.suspect_detected:
            return False

        
    if ((not suspect_file_detected) and on_demand_clam_av):
        clam_av_result = scan_for_malware_using_clam_av(quarantine_file_path, logging_options)

        if clam_av_result == scan_result_types.FILE_IS_SUSPECT:
            suspect_file_detected = True
            logger.warning(f"Threats found in {quarantine_file_path}, handling internally")



    if suspect_file_detected:
        return handle_suspect_scan_result(
            quarantine_file_path,
            source_file_path,
            hazard_archive_path,
            hazard_encryption_key_file_path,
            delete_source_files,
            scanner_handling_suspect_file,
            quarantine_hash,
            logging_options
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
            delete_source_files,
            logging_options
        )

    else:
        logger.warning(f"Scan failed on {quarantine_file_path}")
        return False

def parallel_scan_wrapper(file_paths, hazard_key_path, hazard_path, delete_source, use_defender, use_clamav, defender_handles_suspect, logging_opts):
    """
    Wrapper function for parallel scanning to avoid using lambdas which can't be pickled
    """
    return scan_and_process_file(
        file_paths,
        hazard_key_path,
        hazard_path,
        delete_source,
        use_defender,
        use_clamav,
        defender_handles_suspect,
        logging_opts
    )


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

    throttle=True,
    throttle_free_space=10000,
    
    notifier=None,
    notify_summary=False,

    logging_options=None
    
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
        on_demand_defender (bool): Whether to use Microsoft Defender for on-demand scanning
        on_demand_clam_av (bool): Whether to use ClamAV for on-demand scanning
        defender_handles_suspect_files (bool): Whether to let Defender handle suspect files

        throttle (bool): Whether to enable throttling
        throttle_free_space (int): Minimum free space required in MB
        
        notifier (Notifier): Notifier for sending notifications
        notify_summary (bool): Whether to send notification on completion of every run
        logging_options (tuple) : logging setup details
    """
    
    quarantine_files = []

    successful_files = 0
    failed_files = 0
    suspect_files = 0
    
    # Initialize throttling variables with safe defaults
    assume_quarantine_has_space = True  # Assume space is available
    assume_destination_has_space = True
    assume_hazard_has_space = True
    disk_error = False   
    
    logger = setup_logging('shuttle.scanning.scan_and_process_directory', logging_options)
    
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
                if not is_file_stable(source_file_path, logging_options=logging_options):
                    logger.debug(f"Skipping file {source_file_path} because it may still be written to.")
                    continue  # Skip this file and proceed to the next one

                # Skip files that are currently open
                if is_file_open(source_file_path, logging_options=logging_options):
                    logger.debug(f"Skipping file {source_file_path} because it is being written to.")
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
                        # Check if we can process this file based on available space
                        throttle_result = Throttler.can_process_file(
                            source_file_path, 
                            quarantine_path,
                            destination_path,
                            hazard_archive_path,
                            throttle_free_space,
                            logging_options
                        )
                        
                        # Extract results for each directory from the result object
                        assume_quarantine_has_space = throttle_result.quarantine_has_space
                        assume_destination_has_space = throttle_result.destination_has_space
                        assume_hazard_has_space = throttle_result.hazard_has_space
                        disk_error = throttle_result.diskError
                        
                        # If file can't be processed, break out of the loop
                        if (
                            not throttle_result.canProcess or 
                            not assume_quarantine_has_space or 
                            not assume_destination_has_space or 
                            not assume_hazard_has_space or 
                            disk_error
                        ):
                            logger.warning(f"Stopping file processing due to insufficient disk problems")


                            if (not assume_quarantine_has_space):
                                logger.warning(f"Could not validate quarantine directory had enough space. The disk may have run out of space, or may have other issues")

                            if (not assume_destination_has_space):
                                logger.warning(f"Could not validate destination directory had enough space. The disk may have run out of space, or may have other issues")

                            if (not assume_hazard_has_space):
                                logger.warning(f"Could not validate hazard directory had enough space. The disk may have run out of space, or may have other issues")

                            if (disk_error):
                                logger.warning(f"when attempting to check disk space and error occurred.")

                            break
                            
                    except Exception as e:
                        if logger:
                            logger.error(f"Error in throttling checks: {e}")
                        disk_error = True
                        break

                # Copy the file to the appropriate directory in the quarantine directory
                # quarantine_temp_path = os.path.join(quarantine_file_path + '.tmp')

                try:
                    copy_temp_then_rename(source_file_path, quarantine_file_path, logging_options)

                    logger.info(f"Copied file {source_file_path} to quarantine: {quarantine_file_path}")

                    # Add to processing queue with full paths
                    quarantine_files.append((
                        quarantine_file_path,       # Full path to the quarantined file
                        source_file_path,           # Full path to the original source file
                        destination_file_path,      # Full path to the destination file
                    ))
                    
                except Exception as e:
                    if logger:
                        logger.error(f"Failed to copy file from source: {source_file_path} to quarantine: {quarantine_file_path}. Error: {e}")
            
            # If directories are full, break out of the outer loop too
            # Only check throttle_result if it exists (throttle is enabled and the check was performed)
            if throttle and (not assume_quarantine_has_space or not assume_destination_has_space or not assume_hazard_has_space or disk_error):
                break

        results = list()
        if max_scan_threads > 1:
        # Process files in parallel using a ProcessPoolExecutor with graceful shutdown
            with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
                try:
                    #results = list(executor.map(scan_and_process_file, quarantine_files))

                    # Using a properly picklable function instead of a lambda
                    logger.info(f"Starting parallel processing with {max_scan_threads} workers")
                    results = list(
                        executor.map(
                            parallel_scan_wrapper,
                            quarantine_files,
                            [hazard_encryption_key_file_path] * len(quarantine_files),
                            [hazard_archive_path] * len(quarantine_files),
                            [delete_source_files] * len(quarantine_files),
                            [on_demand_defender] * len(quarantine_files),
                            [on_demand_clam_av] * len(quarantine_files),
                            [defender_handles_suspect_files] * len(quarantine_files),
                            [logging_options] * len(quarantine_files)
                        )
                    )
                    logger.info("Parallel processing completed")

                except Exception as e:
                    if logger:
                        logger.error(f"An error occurred during parallel processing: {e}")
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
        else:
            for file_paths in quarantine_files:

                result = scan_and_process_file(
                        file_paths,
                        hazard_encryption_key_file_path, 
                        hazard_archive_path,
                        delete_source_files, 
                        on_demand_defender, 
                        on_demand_clam_av, 
                        defender_handles_suspect_files, 
                        logging_options
                    )
                
                results.append(result)  

        # Process successful results
        for counter in range(len(results)):
            if results[counter]:
                successful_files += 1
            else:
                failed_files += 1

        # After processing all files, remove contents of quarantine directory
        remove_directory_contents(quarantine_path, logging_options)

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
                    if not remove_directory(directory_to_remove, logging_options):
                        logger.error(f"Could not remove directory during cleanup: {directory_to_remove}")
                    else:
                        logger.info(f"Directory removed during cleanup: {directory_to_remove}")

        # Check if all files were processed successfully
        if not all(results):
            logger.error(f"Some files failed to be processed.")

        if notifier:

            summary_title = f"Shuttle Summary: "

            total_files = successful_files + failed_files
            
            # Prepare summary message that may be used for both summary and disk space notifications
            summary_message = f"File processing completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            summary_message += f"Source directory: {source_path}\n"
            summary_message += f"Destination directory: {destination_path}\n\n"
            summary_message += f"Total files processed: {total_files}\n"
            summary_message += f"Successfully processed: {successful_files}\n"
            summary_message += f"Failed to process: {failed_files}\n"
            summary_message += f"Suspect files: {suspect_files}\n"
            
            disk_error = False

            # Add disk space warnings to summary if applicable
            if throttle:
                if not assume_quarantine_has_space or not assume_destination_has_space or not assume_hazard_has_space or disk_error:
                    
                    disk_error = True
                    disk_message = ""
                    summary_title += f" Disk Issue "  
                    
                    if not assume_quarantine_has_space:
                        disk_message += "Quarantine directory space low."
                    if not assume_destination_has_space:
                        disk_message += "Destination directory space low."
                    if not assume_hazard_has_space:
                        disk_message += "Hazard archive directory space low."
                    if disk_error:
                        disk_message += "Disk error when checking space."
                    
                    summary_message += disk_message

                    logger.warning(f"Disk space warning: {disk_message}")
            
            # Send summary notification if configured or if there were failures or disk issues
            if (disk_error) or (notify_summary and total_files > 0) or (failed_files > 0):
                
                if failed_files > 0:
                    summary_title += f"{failed_files} failed"
                if successful_files > 0:
                    if failed_files > 0:
                        summary_title += ", "
                    summary_title += f"{successful_files} successful"

                notifier.notify(summary_title, summary_message)
                logger.info(f"Sent summary notification: {failed_files} failed, {successful_files} successful")

    except Exception as e:
        if logger:
            logger.error(f"Failed to copy files to quarantine: Error: {e}")
        failed_files += 1
        
        # Send notification about the critical error
        if notifier:
            error_message = f"Critical error occurred during file processing: {str(e)}\n\n"
            error_message += f"Source directory: {source_path}\n"
            error_message += f"Destination directory: {destination_path}\n"
            notifier.notify("Shuttle: Critical Processing Error", error_message)
