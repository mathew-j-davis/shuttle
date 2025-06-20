import os
import logging
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from shuttle_common.logger_injection import get_logger

from shuttle_common import (
    is_file_safe_for_processing,
    are_file_and_path_names_safe,
    is_file_ready
)

from shuttle_common.files import (
    normalize_path,
    copy_temp_then_rename,
    encrypt_file,
    remove_file_with_logging,
    remove_directory,
    remove_directory_contents,
    remove_empty_directories,
    get_file_hash
)

from .throttler import Throttler
from .throttle_utils import handle_throttle_check
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
    parse_defender_scan_result
)


def is_clean_scan(scanner_enabled, scan_result):
    """Check if a scanner result indicates a clean file."""
    return (
        not scanner_enabled 
        or (
            scanner_enabled 
            and scan_result == scan_result_types.FILE_IS_CLEAN
        )
    )

def scan_and_process_file(
        paths,     
        hazard_encryption_key_file_path, 
        hazard_archive_path,
        delete_source_files, 
        on_demand_defender, 
        on_demand_clam_av, 
        defender_handles_suspect_files
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
    
    Returns:
        bool: True if the file was processed successfully, False otherwise
    """
    # Unpack arguments
    (
        quarantine_file_path,
        source_file_path,
        destination_file_path,
        file_hash,           # Hash for other checks
        relative_file_path   # relative_file_path for daily processing tracker
    ) = paths

    logger = get_logger()
    
    if not on_demand_defender and not on_demand_clam_av:
        logger.error("No virus scanner or defender specified. Please specify at least one.")
        return False

    # No need to calculate hash again
    logger.debug(f"Using pre-calculated hash for file: {quarantine_file_path}, hash: {file_hash}")
    quarantine_hash = file_hash

    defender_result = None
    clam_av_result = None

    suspect_file_detected = False
    scanner_handling_suspect_file = False

    if on_demand_defender:
        # Scan the file for malware
        logger.info(f"Scanning file {quarantine_file_path} for malware...")
        defender_result = scan_for_malware_using_defender(quarantine_file_path)
        
        # Process the scan result with our helper
        scan_result = process_defender_result(
            defender_result,
            quarantine_file_path,
            defender_handles_suspect_files
        )
        
        # Update our status flags based on the scan result
        suspect_file_detected = scan_result.suspect_detected
        scanner_handling_suspect_file = scan_result.scanner_handles_suspect
        
        # Return early if scan failed (not completed) and no threat detected
        # This happens when file is not found and we're not letting defender handle it
        if not scan_result.scan_completed and not scan_result.suspect_detected:
            return False

        
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
            hazard_encryption_key_file_path,
            delete_source_files,
            scanner_handling_suspect_file,
            quarantine_hash
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

def call_scan_and_process_file(file_paths, hazard_key_path, hazard_path, delete_source, use_defender, use_clamav, defender_handles_suspect):
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
            defender_handles_suspect
        )

def log_processing_progress(processed_count, total_files):
    """
    Log file processing progress at regular intervals
    
    Args:
        processed_count: Number of files processed so far
        total_files: Total number of files to process
        options
    """
    logger = get_logger()
    if processed_count % 5 == 0 or processed_count == total_files:
        logger.info(f"Processed {processed_count}/{total_files} files ({processed_count/total_files:.0%})")

def log_final_status(mode, processed_count, failed_count):
    """
    Log final processing status summary
    
    Args:
        mode: Processing mode ("Parallel" or "Sequential")
        processed_count: Total number of files processed
        failed_count: Number of files that failed processing
        options
    """
    logger = get_logger()
    success_count = processed_count - failed_count
    logger.info(f"{mode} processing completed: {processed_count} files processed, "
                f"{failed_count} failures, {success_count} successes")
                
def process_task_result(task_result, file_data, results, processed_count, failed_count, total_files, logger, daily_processing_tracker=None):
    """
    Process a task result, handle errors, and update counters
    
    Args:
        task_result: Result from task execution or exception if failed
        file_data: Tuple containing (quarantine_path, source_path, destination_path, file_hash)
        results: List to append results to
        processed_count: Counter for processed files
        failed_count: Counter for failed files
        total_files: Total number of files to process
        logger: Logger instance
        daily_processing_tracker: Optional DailyProcessingTracker to update
    
    Returns:
        tuple: Updated (processed_count, failed_count)
    """

    logger = get_logger()

    # Unpack file_data (now includes 5 elements)
    file_path, source_path, destination_path, file_hash, relative_file_path = file_data
    
    processed_count += 1
    
    if isinstance(task_result, Exception):
        # Handle errors for individual tasks without failing everything
        failed_count += 1
        logger.error(f"Error processing file {file_path}: {task_result}")
        results.append(None)
        
        # Mark as failed in tracker
        if daily_processing_tracker is not None:
            try:
                daily_processing_tracker.complete_pending_file(
                    relative_file_path=relative_file_path,
                    outcome='failed',
                    error=str(task_result)
                )
                logger.debug(f"Marked file as failed in daily processing tracker: {file_path}, key: {relative_file_path}")
            except Exception as e:
                logger.warning(f"Failed to mark file as failed in tracker: {e}")
    else:
        # Task succeeded
        results.append(task_result)
        
        # Determine outcome based on task_result (success or suspect)
        outcome = 'success'
        if hasattr(task_result, 'is_suspect') and task_result.is_suspect:
            outcome = 'suspect'
            
        # Mark file as completed in the daily processing tracker
        if daily_processing_tracker is not None:
            try:
                daily_processing_tracker.complete_pending_file(relative_file_path, outcome=outcome)
                logger.debug(f"Marked file as {outcome} in daily processing tracker: {file_path}, key: {relative_file_path}")
            except Exception as e:
                logger.warning(f"Failed to mark file as completed in tracker: {e}")
    
    # Log progress periodically
    log_processing_progress(processed_count, total_files)
    
    return processed_count, failed_count

def quarantine_files_for_scanning(source_path, quarantine_path, destination_path, hazard_archive_path, throttle, throttle_free_space_mb, throttle_max_file_count_per_day=0, throttle_max_file_volume_per_day_mb=0, daily_processing_tracker=None, notifier=None, skip_stability_check=False):
    """
    Find eligible files in source directory, copy them to quarantine, and prepare for scanning.
    
    Args:
        source_path: Path to source directory
        quarantine_path: Path to quarantine directory
        destination_path: Path to destination directory
        hazard_archive_path: Path to hazard archive directory
        throttle: Whether to enable throttling
        throttle_free_space_mb: Minimum free space required in MB
        throttle_max_file_count_per_day: Maximum number of files to process per day (0 for no limit)
        throttle_max_file_volume_per_day_mb: Maximum volume of data to process per day in MB (0 for no limit)
        daily_processing_tracker: DailyProcessingTracker instance for tracking daily limits
        notifier: Notifier instance for sending notifications
        skip_stability_check: Whether to skip file stability check
        options
        
    Returns:
        tuple: (quarantine_files, disk_error_stopped_processing)
            - quarantine_files: List of (quarantine_path, source_path, destination_path) tuples
            - disk_error_stopped_processing: Whether processing was stopped due to disk issues
    """
    quarantine_files = []
    disk_error_stopped_processing = False
    
    logger = get_logger()
    
    try:
        # Create quarantine directory if it doesn't exist
        os.makedirs(quarantine_path, exist_ok=True)

        # Copy files from source to quarantine directory
        # os.walk traverses the directory tree
        for source_root, dirs, source_files in os.walk(source_path, topdown=False):
            for source_file in source_files:
                
                # Check if file is safe to process using our consolidated function
                if not is_file_safe_for_processing(source_file, source_root, skip_stability_check):
                    continue  # Skip this file and proceed to the next one
                
                # Calculate the full path (needed for subsequent operations)
                source_file_path = os.path.join(source_root, source_file)

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
                    if not handle_throttle_check(
                        source_file_path, 
                        quarantine_path,
                        destination_path,
                        hazard_archive_path,
                        throttle_free_space_mb,
                        Throttler(),
                        max_files_per_day=throttle_max_file_count_per_day,
                        max_volume_per_day=throttle_max_file_volume_per_day_mb,
                        daily_processing_tracker=daily_processing_tracker,
                        notifier=notifier
                    ):
                        disk_error_stopped_processing = True
                        break
                    
                # Copy the file to the appropriate directory in the quarantine directory
                try:
                    copy_temp_then_rename(source_file_path, quarantine_file_path)
                    
                    # Calculate file hash
                    file_hash = get_file_hash(quarantine_file_path)
                    logger.debug(f"Calculated hash for file: {quarantine_file_path}, hash: {file_hash}")
                    
                    # Create unique relative path using existing variables
                    relative_file_path = os.path.join(rel_dir, source_file)
                    
                    # Track the file as pending now that it's been copied and hashed
                    if daily_processing_tracker:
                        file_size_mb = os.path.getsize(quarantine_file_path) / (1024 * 1024)
                        daily_processing_tracker.add_pending_file(
                            file_path=quarantine_file_path,
                            file_size_mb=file_size_mb,
                            file_hash=file_hash,
                            source_path=source_file_path,
                            relative_file_path=relative_file_path
                        )
                        logger.debug(f"Added file to pending tracking: {quarantine_file_path} ({file_size_mb:.2f} MB), hash: {file_hash}, key: {relative_file_path}")

                    logger.info(f"Copied file {source_file_path} to quarantine: {quarantine_file_path}")

                    # Add to processing queue with full paths, file hash, and relative file path
                    quarantine_files.append((
                        quarantine_file_path,       # Full path to the quarantined file
                        source_file_path,           # Full path to the original source file
                        destination_file_path,      # Full path to the destination file
                        file_hash,                  # File hash for tracking
                        relative_file_path          # Relative file path for complete_pending_file()
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to copy file from source: {source_file_path} to quarantine: {quarantine_file_path}. Error: {e}")
            
            # If disk error stopped processing, break out of the outer loop too
            if disk_error_stopped_processing:
                break
                
        logger.info(f"Quarantined {len(quarantine_files)} files for scanning")
        return quarantine_files, disk_error_stopped_processing
        
    except Exception as e:
        logger.error(f"Error during file quarantine process: {e}")
        return [], True

def send_summary_notification(notifier, source_path, destination_path, successful_files, failed_files, suspect_files, disk_error_stopped_processing, notify_summary):
    """
    Send a summary notification about the processing results.
    
    Args:
        notifier: Notifier instance to use for sending notifications
        source_path: Source directory path
        destination_path: Destination directory path
        successful_files: Number of successfully processed files
        failed_files: Number of files that failed processing
        suspect_files: Number of suspect files found
        disk_error_stopped_processing: Whether processing was stopped due to disk issues
        notify_summary: Whether summary notification was explicitly requested
        options
    """
    if not notifier:
        return
    
    logger = get_logger()
    total_files = successful_files + failed_files
    
    # Only send notification if configured or if there were failures or disk issues
    if not ((disk_error_stopped_processing) or (notify_summary and total_files > 0) or (failed_files > 0)):
        return
    
    summary_title = "Shuttle Summary: "
    
    # Prepare summary message
    summary_message = f"File processing completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    summary_message += f"Source directory: {source_path}\n"
    summary_message += f"Destination directory: {destination_path}\n\n"
    summary_message += f"Total files processed: {total_files}\n"
    summary_message += f"Successfully processed: {successful_files}\n"
    summary_message += f"Failed to process: {failed_files}\n"
    summary_message += f"Suspect files: {suspect_files}\n"

    # Add disk error information if applicable
    if disk_error_stopped_processing:
        summary_title += "Disk Issue "
        summary_message += "\n\n"
        summary_message += "Disk space was low or an error occurred when checking disk space.\n"
        summary_message += "Some files may not have been processed.\n"

    # Add status counts to title
    if failed_files > 0:
        summary_title += f"{failed_files} failed"
    if successful_files > 0:
        if failed_files > 0:
            summary_title += ", "
        summary_title += f"{successful_files} successful"

    # Send the notification
    notifier.notify_summary(summary_title, summary_message)
    logger.info(f"Sent summary notification: {failed_files} failed, {successful_files} successful")


def clean_up_source_files(quarantine_files, results, source_path, delete_source_files):
    """
    Clean up empty source directories after successful file transfers.
    
    Args:
        quarantine_files: List of file transfer tuples (quarantine_path, source_path, destination_path)
        results: List of task results (True/False for each file)
        source_path: Original source path (root directory)
        delete_source_files: Flag indicating if source cleanup is enabled
        options
    """
    if not delete_source_files:
        return
        
    logger = get_logger()
    directories_to_remove = []

    # Collect directories that might be empty after file transfers
    for counter, file_transfer in enumerate(quarantine_files):
        if counter >= len(results):
            break

        # Only consider successful transfers
        if results[counter]:
            source_file_dir = os.path.dirname(quarantine_files[counter][1])  # source_file_path

            # Skip the root source directory
            if normalize_path(source_file_dir) == normalize_path(source_path):
                continue

            # Add directory to removal list if not already present and it exists
            if not source_file_dir in directories_to_remove and os.path.exists(source_file_dir):
                directories_to_remove.append(source_file_dir)
    
    # Remove empty directories
    for directory_to_remove in directories_to_remove:
        # Only remove if directory is empty
        if len(os.listdir(directory_to_remove)) == 0:
            if not remove_directory(directory_to_remove):
                logger.error(f"Could not remove directory during cleanup: {directory_to_remove}")
            else:
                logger.info(f"Directory removed during cleanup: {directory_to_remove}")


def process_scan_tasks(scan_tasks, max_scan_threads, daily_processing_tracker=None):
    """
    Process a list of scan tasks either sequentially or in parallel based on max_scan_threads.
    
    Args:
        scan_tasks: List of parameter tuples for scan tasks
        max_scan_threads: Number of parallel threads to use (1 for sequential)
        options
        
    Returns:
        tuple: (results, successful_files, failed_files)
            - results: List of task results (True/False for each file)
            - successful_files: Count of successfully processed files
            - failed_files: Count of files that failed processing
    """
    results = []
    total_files = len(scan_tasks)
    processed_count = 0
    failed_count = 0
    
    logger = get_logger()
    
    if max_scan_threads > 1:
        # Process files in parallel using a ProcessPoolExecutor
        logger.info(f"Starting parallel processing with {max_scan_threads} workers")
        
        with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
            try:
                # Submit all tasks and track them with their source file
                futures_to_files = {}
                for task in scan_tasks:
                    future = executor.submit(call_scan_and_process_file, *task)
                    futures_to_files[future] = task[0]  # Map future to its source file
                
                # Process results as they complete (not in submission order)
                for future in as_completed(futures_to_files):
                    file_path = futures_to_files[future]
                    
                    try:
                        # Get the result (or raises exception if the task failed)
                        result = future.result()
                        processed_count, failed_count = process_task_result(
                            result, file_path, results, processed_count, failed_count, total_files, logger, daily_processing_tracker
                        )
                    except Exception as task_error:
                        # For exceptions from future.result(), pass the exception to the processor
                        processed_count, failed_count = process_task_result(
                            task_error, file_path, results, processed_count, failed_count, total_files, logger, daily_processing_tracker
                        )
                
                # Final status report
                log_final_status("Parallel", processed_count, failed_count)
                        
            except Exception as e:
                # This only happens for errors outside the task processing loop
                if logger:
                    logger.error(f"An error occurred in the parallel execution framework: {e}")
                executor.shutdown(wait=False, cancel_futures=True)
                raise
    else:
        # Process files sequentially using the same task parameters
        logger.info(f"Starting sequential processing of {total_files} files")
        
        for i, task in enumerate(scan_tasks):
            try:
                # Call the processing function with unpacked parameters
                result = call_scan_and_process_file(*task)
                processed_count, failed_count = process_task_result(
                    result, task[0], results, processed_count, failed_count, total_files, logger, daily_processing_tracker
                )
            except Exception as e:
                # For exceptions from the call itself, pass the exception to the processor
                processed_count, failed_count = process_task_result(
                    e, task[0], results, processed_count, failed_count, total_files, logger, daily_processing_tracker
                )
        
        # Final status report
        log_final_status("Sequential", processed_count, failed_count)
    
    # Get summary from tracker instead of calculating manually
    if daily_processing_tracker:
        summary = daily_processing_tracker.generate_task_summary()
        successful_files = summary['successful_files']
        failed_files = summary['failed_files']
        suspect_files = summary['suspect_files']
        
        logger.info(f"Scan results: {successful_files} successful, "
                   f"{failed_files} failed, {suspect_files} suspect")
    else:
        # Fallback if no tracker provided
        successful_files = sum(1 for result in results if result)
        failed_files = len(results) - successful_files
        suspect_files = 0
    
    return results, successful_files, failed_files


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
    throttle_free_space_mb=10000,
    throttle_max_file_volume_per_day_mb=0,
    throttle_max_file_count_per_day=0,
    daily_processing_tracker=None,  # Parameter to receive existing tracker
    
    notifier=None,
    notify_summary=False,
    skip_stability_check=False
    
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
        throttle_free_space_mb (int): Minimum free space required in MB
        throttle_max_file_volume_per_day_mb (int): Maximum volume of data to process per day in MB (0 for no limit)
        throttle_max_file_count_per_day (int): Maximum number of files to process per day (0 for no limit)
        daily_processing_tracker (DailyProcessingTracker): Existing tracker instance to use (required)

        notifier (Notifier): Notifier for sending notifications
        notify_summary (bool): Whether to send notification on completion of every run

    """
    
    quarantine_files = []

    successful_files = 0
    failed_files = 0
    suspect_files = 0
    
    logger = get_logger()
    
    # The daily_processing_tracker is now a required parameter and should be initialized
    # by the caller (Shuttle class)
    if daily_processing_tracker is None:
        logger.error("No daily_processing_tracker provided to scan_and_process_directory")
        raise ValueError("daily_processing_tracker is required")
    
    # Log message about throttling configuration if throttling is enabled
    if throttle and (throttle_max_file_volume_per_day_mb > 0 or throttle_max_file_count_per_day > 0):
        logger.info(f"Daily throttling enabled: {throttle_max_file_count_per_day} files, {throttle_max_file_volume_per_day_mb} MB")
    
    try:
        # Phase 1: Copy files from source to quarantine
        quarantine_files, disk_error_stopped_processing = quarantine_files_for_scanning(
            source_path,
            quarantine_path,
            destination_path,
            hazard_archive_path,
            throttle,
            throttle_free_space_mb,
            throttle_max_file_count_per_day,
            throttle_max_file_volume_per_day_mb,
            daily_processing_tracker,
            notifier,
            skip_stability_check
        )
        
        results = list()
        
        # Create all task parameter sets up front
        scan_tasks = []
        for file_path in quarantine_files:
            scan_tasks.append((file_path, 
                             hazard_encryption_key_file_path,
                             hazard_archive_path,
                             delete_source_files,
                             on_demand_defender,
                             on_demand_clam_av,
                             defender_handles_suspect_files
                             ))
        
        total_files = len(scan_tasks)
        processed_count = 0
        failed_count = 0
        
        # Process all scan tasks
        results, successful_files, failed_files = process_scan_tasks(
            scan_tasks,
            max_scan_threads,
            daily_processing_tracker
        )

        # After processing all files, remove contents of quarantine directory
        remove_directory_contents(quarantine_path)

        # Clean up empty source directories if requested
        clean_up_source_files(quarantine_files, results, source_path, delete_source_files)

        # Check if all files were processed successfully
        if not all(results):
            logger.error(f"Some files failed to be processed.")
            
        # Send summary notification
        send_summary_notification(
            notifier,
            source_path,
            destination_path,
            successful_files,
            failed_files,
            suspect_files,
            disk_error_stopped_processing,
            notify_summary
        )

    except Exception as e:
        if logger:
            logger.error(f"Failed to copy files to quarantine: Error: {e}")
        failed_files += 1
        
        # Send notification about the critical error
        if notifier:
            error_message = f"Critical error occurred during file processing: {str(e)}\n\n"
            error_message += f"Source directory: {source_path}\n"
            error_message += f"Destination directory: {destination_path}\n"
            notifier.notify_error("Shuttle: Critical Processing Error", error_message)
