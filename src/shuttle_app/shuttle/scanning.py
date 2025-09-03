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
    get_file_hash,
    cleanup_empty_directories
)

from .throttler import Throttler
from .throttle_utils import handle_throttle_check
from .post_scan_processing import (
    handle_clean_file,
    handle_suspect_scan_result
)

# Timeout result class
class ScanTimeoutResult:
    """Result object for scan timeout"""
    def __init__(self, quarantine_path, source_path):
        self.quarantine_path = quarantine_path
        self.source_path = source_path
        self.is_timeout = True
        self.is_suspect = False  # Treat timeouts as failures, not suspects

# Import scan utilities from common module
from shuttle_common.scan_utils import (
    scan_for_malware_using_defender,
    run_malware_scan,
    scan_result_types,
    handle_clamav_scan_result,
    ScanTimeoutError,
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
        defender_handles_suspect_files,
        config=None
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
        try:
            defender_result = scan_for_malware_using_defender(quarantine_file_path, config)
            
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
                
        except ScanTimeoutError:
            # Treat timeout as scan failure
            logger.error(f"Defender scan timed out for {quarantine_file_path}")
            return ScanTimeoutResult(quarantine_file_path, source_file_path)

        
    if ((not suspect_file_detected) and on_demand_clam_av):
        try:
            clam_av_result = scan_for_malware_using_clam_av(quarantine_file_path, config)

            if clam_av_result == scan_result_types.FILE_IS_SUSPECT:
                suspect_file_detected = True
                logger.warning(f"Threats found in {quarantine_file_path}, handling internally")
                
        except ScanTimeoutError:
            # Treat timeout as scan failure
            logger.error(f"ClamAV scan timed out for {quarantine_file_path}")
            return ScanTimeoutResult(quarantine_file_path, source_file_path)



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

def call_scan_and_process_file(file_paths, hazard_key_path, hazard_path, delete_source, use_defender, use_clamav, defender_handles_suspect, config=None):
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
            config
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
                
def process_task_result(task_result, file_data, results, processed_count, failed_count, total_files, logger, daily_processing_tracker=None, per_run_tracker=None, timeout_count=0):
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
        per_run_tracker: Optional PerRunTracker to update
    
    Returns:
        tuple: Updated (processed_count, failed_count, timeout_count)
    """

    logger = get_logger()

    # Unpack file_data (now includes 5 elements)
    file_path, source_path, destination_path, file_hash, relative_file_path = file_data
    
    processed_count += 1
    
    # Check for timeout result first
    if hasattr(task_result, 'is_timeout') and task_result.is_timeout:
        timeout_count += 1
        failed_count += 1
        logger.error(f"Scan timeout for file {file_path}")
        results.append(task_result)  # Keep timeout result for cleanup
        
        # Mark as failed in tracker
        if daily_processing_tracker is not None:
            try:
                daily_processing_tracker.complete_pending_file(
                    relative_file_path=relative_file_path,
                    outcome='failed',
                    error='Scan timeout'
                )
                logger.debug(f"Marked timeout file as failed in daily processing tracker: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to mark timeout file as failed in daily tracker: {e}")
        
        # Mark as failed in per-run tracker
        if per_run_tracker is not None:
            try:
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                per_run_tracker.complete_file_processing(file_path, file_size_mb)
                logger.debug(f"Marked timeout file as completed in per-run tracker: {file_path} ({file_size_mb:.2f} MB)")
            except Exception as e:
                logger.warning(f"Failed to mark timeout file as completed in per-run tracker: {e}")
                
    elif isinstance(task_result, Exception):
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
                logger.warning(f"Failed to mark file as failed in daily tracker: {e}")
        
        # Mark as failed in per-run tracker
        if per_run_tracker is not None:
            try:
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                per_run_tracker.complete_file_processing(file_path, file_size_mb)
                logger.debug(f"Marked error file as completed in per-run tracker: {file_path} ({file_size_mb:.2f} MB)")
            except Exception as e:
                logger.warning(f"Failed to mark error file as completed in per-run tracker: {e}")
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
                logger.warning(f"Failed to mark file as completed in daily tracker: {e}")
        
        # Mark file as completed in the per-run tracker
        if per_run_tracker is not None:
            try:
                # Get file size for per-run tracking
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                per_run_tracker.complete_file_processing(file_path, file_size_mb)
                logger.debug(f"Marked file as completed in per-run tracker: {file_path} ({file_size_mb:.2f} MB)")
            except Exception as e:
                logger.warning(f"Failed to mark file as completed in per-run tracker: {e}")
    
    # Log progress periodically
    log_processing_progress(processed_count, total_files)
    
    return processed_count, failed_count, timeout_count

def quarantine_files_for_scanning(source_path, quarantine_path, destination_path, hazard_archive_path, throttle, throttle_free_space_mb, throttle_max_file_count_per_day=0, throttle_max_file_volume_per_day_mb=0, daily_processing_tracker=None, throttle_max_file_count_per_run=0, throttle_max_file_volume_per_run_mb=0, per_run_tracker=None, notifier=None, skip_stability_check=False):
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
        throttle_max_file_count_per_run: Maximum number of files to process per run (0 for no limit)
        throttle_max_file_volume_per_run_mb: Maximum volume of data to process per run in MB (0 for no limit)
        per_run_tracker: PerRunTracker instance for tracking per-run limits
        notifier: Notifier instance for sending notifications
        skip_stability_check: Whether to skip file stability check
        
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
                        max_files_per_run=throttle_max_file_count_per_run,
                        max_volume_per_run=throttle_max_file_volume_per_run_mb,
                        per_run_tracker=per_run_tracker,
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
                    file_size_mb = os.path.getsize(quarantine_file_path) / (1024 * 1024)
                    
                    if daily_processing_tracker:
                        daily_processing_tracker.add_pending_file(
                            file_path=quarantine_file_path,
                            file_size_mb=file_size_mb,
                            file_hash=file_hash,
                            source_path=source_file_path,
                            relative_file_path=relative_file_path
                        )
                        logger.debug(f"Added file to daily pending tracking: {quarantine_file_path} ({file_size_mb:.2f} MB), hash: {file_hash}, key: {relative_file_path}")
                    
                    if per_run_tracker:
                        per_run_tracker.add_pending_file(
                            file_path=quarantine_file_path,
                            file_size_mb=file_size_mb
                        )
                        logger.debug(f"Added file to per-run pending tracking: {quarantine_file_path} ({file_size_mb:.2f} MB)")

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


def cleanup_after_processing(quarantine_files, results, source_path, delete_source_files, quarantine_path, is_timeout_shutdown=False):
    """
    Unified cleanup for both normal completion and timeout shutdown scenarios.
    
    Comprehensive cleanup operations:
    1. Remove source files based on processing results
    2. Clean quarantine directory  
    3. Remove empty source directories
    
    Args:
        quarantine_files: List of file transfer tuples (quarantine_path, source_path, destination_path, hash, rel_path)
        results: List of task results (True/False/result objects for each file)
        source_path: Original source path (root directory)
        delete_source_files: Flag indicating if source cleanup is enabled
        quarantine_path: Path to quarantine directory to clean
        is_timeout_shutdown: Whether this is cleanup after timeout shutdown (affects logging)
    """
    logger = get_logger()
    
    if is_timeout_shutdown:
        logger.info("Starting cleanup after timeout shutdown")
    else:
        logger.debug("Starting normal cleanup after processing")
    
    # 1. Remove source files based on processing results
    if delete_source_files:
        for i, (q_path, s_path, d_path, file_hash, rel_path) in enumerate(quarantine_files):
            if i >= len(results):
                # File was never processed - leave source intact
                logger.debug(f"File never processed: {s_path}")
                continue
                
            result = results[i]
            
            if result is True:
                # Successfully moved to destination
                try:
                    if os.path.exists(s_path):
                        os.remove(s_path)
                        logger.info(f"Removed source file after successful transfer: {s_path}")
                except Exception as e:
                    logger.error(f"Failed to remove source file {s_path}: {e}")
                    
            elif hasattr(result, 'is_suspect') and result.is_suspect:
                # File was moved to hazard - ensure source is removed
                try:
                    if os.path.exists(s_path):
                        os.remove(s_path)
                        logger.info(f"Removed source file after hazard detection: {s_path}")
                except Exception as e:
                    logger.error(f"Failed to remove hazard source {s_path}: {e}")
                    
            elif hasattr(result, 'is_timeout') and result.is_timeout:
                # Timeout occurred - leave source file intact (safe default)
                if is_timeout_shutdown:
                    logger.info(f"Timeout occurred for {s_path}, leaving source file intact")
                else:
                    logger.debug(f"Timeout result for {s_path}, leaving source file intact")
            
            # For other failure cases (result is None, False, etc.), leave source intact
    
    # 2. Clean quarantine directory
    try:
        from shuttle_common.files import remove_directory_contents
        remove_directory_contents(quarantine_path)
        if is_timeout_shutdown:
            logger.info("Cleaned quarantine directory after timeout shutdown")
        else:
            logger.debug("Cleaned quarantine directory after normal processing")
    except Exception as e:
        logger.error(f"Failed to clean quarantine directory: {e}")
    
    # 3. Empty directory cleanup
    if delete_source_files:
        # Clean up ALL empty directories in source that pass safety checks
        # This prevents cleaning up directories that users are actively working with
        stability_seconds = 300  # 5 minutes - configurable in future
        
        # Do full cleanup of all empty dirs
        cleanup_results = cleanup_empty_directories(
            [source_path],  # Only clean source, not quarantine
            stability_seconds
        )
        
        logger.info(f"Source directory cleanup completed: {cleanup_results['directories_removed']} removed, "
                   f"{cleanup_results['directories_failed']} failed")



def process_scan_tasks(scan_tasks, max_scan_threads, daily_processing_tracker=None, per_run_tracker=None, config=None):
    """
    Process a list of scan tasks either sequentially or in parallel based on max_scan_threads.
    
    Args:
        scan_tasks: List of parameter tuples for scan tasks
        max_scan_threads: Number of parallel threads to use (1 for sequential)
        daily_processing_tracker: Optional DailyProcessingTracker to update
        per_run_tracker: Optional PerRunTracker to update
        config: Optional config object
        
    Returns:
        tuple: (results, successful_files, failed_files, timeout_shutdown)
            - results: List of task results (True/False for each file)
            - successful_files: Count of successfully processed files
            - failed_files: Count of files that failed processing
            - timeout_shutdown: Whether processing was stopped due to timeouts
    """
    results = []
    total_files = len(scan_tasks)
    processed_count = 0
    failed_count = 0
    timeout_count = 0
    timeout_shutdown = False
    
    # Get max timeouts from config (0 means unlimited, so set high number)
    max_timeouts = config.malware_scan_retry_count if config else 3
    if max_timeouts == 0:
        max_timeouts = float('inf')  # Unlimited retries means no shutdown
    
    logger = get_logger()
    
    if max_scan_threads > 1:
        # Process files in parallel using a ProcessPoolExecutor
        logger.info(f"Starting parallel processing with {max_scan_threads} workers")
        
        with ProcessPoolExecutor(max_workers=max_scan_threads) as executor:
            try:
                # Submit all tasks and track them with their source file
                futures_to_files = {}
                for task in scan_tasks:
                    future = executor.submit(call_scan_and_process_file, *task, config)
                    futures_to_files[future] = task[0]  # Map future to its source file
                
                # Process results as they complete (not in submission order)
                for future in as_completed(futures_to_files):
                    file_path = futures_to_files[future]
                    
                    try:
                        # Get the result (or raises exception if the task failed)
                        result = future.result()
                        processed_count, failed_count, timeout_count = process_task_result(
                            result, file_path, results, processed_count, failed_count, total_files, logger, daily_processing_tracker, per_run_tracker, timeout_count
                        )
                    except Exception as task_error:
                        # For exceptions from future.result(), pass the exception to the processor
                        processed_count, failed_count, timeout_count = process_task_result(
                            task_error, file_path, results, processed_count, failed_count, total_files, logger, daily_processing_tracker, per_run_tracker, timeout_count
                        )
                    
                    # Check if we should shutdown due to too many timeouts
                    if timeout_count >= max_timeouts:
                        logger.error(f"Reached maximum timeout count ({max_timeouts}), shutting down processing")
                        timeout_shutdown = True
                        
                        # Graceful shutdown: let running scans complete (they're bounded by scan timeout)
                        # but don't submit any new tasks
                        running_count = sum(1 for f in futures_to_files if not f.done())
                        if running_count > 0:
                            scan_timeout = config.malware_scan_timeout_seconds if config else 300
                            # Allow extra time for post-scan processing (file moves, encryption, etc.)
                            max_wait_time = scan_timeout * 2
                            logger.info(f"Waiting for {running_count} running scans to complete (max {max_wait_time}s total)...")
                            
                            # Process remaining completed futures with bounded timeout
                            remaining_futures = [f for f in futures_to_files if not f.done()]
                            completed_count = 0
                            
                            import concurrent.futures
                            try:
                                # Use timeout to prevent infinite hang if worker process gets stuck
                                for future in as_completed(remaining_futures, timeout=max_wait_time):
                                    completed_count += 1
                                    try:
                                        # Get result with short timeout to avoid hanging on result retrieval
                                        result = future.result(timeout=5)
                                        processed_count, failed_count, timeout_count = process_task_result(
                                            result, futures_to_files[future], results, processed_count, failed_count, total_files, logger, daily_processing_tracker, per_run_tracker, timeout_count
                                        )
                                    except concurrent.futures.CancelledError:
                                        # Future was cancelled during shutdown
                                        logger.info(f"Scan was cancelled during shutdown: {futures_to_files[future]}")
                                        failed_count += 1
                                        results.append(None)  # Mark as failed
                                    except concurrent.futures.TimeoutError:
                                        # Result retrieval timed out
                                        logger.warning(f"Scan result retrieval timeout during shutdown: {futures_to_files[future]}")
                                        failed_count += 1
                                        results.append(None)  # Mark as failed
                                    except Exception as task_error:
                                        # Any other exception from the task
                                        logger.error(f"Error processing scan result during shutdown: {task_error}")
                                        processed_count, failed_count, timeout_count = process_task_result(
                                            task_error, futures_to_files[future], results, processed_count, failed_count, total_files, logger, daily_processing_tracker, per_run_tracker, timeout_count
                                        )
                                
                                logger.info(f"Graceful shutdown: {completed_count} running scans completed naturally")
                                
                            except concurrent.futures.TimeoutError:
                                still_running = len(remaining_futures) - completed_count
                                logger.warning(f"Graceful shutdown timeout after {max_wait_time}s, {still_running} scans still running")
                                logger.warning("Proceeding with shutdown - stuck processes will be terminated by executor cleanup")
                        
                        # Only cancel futures that haven't started yet (can't be cancelled once running)
                        cancelled_count = 0
                        for remaining_future in futures_to_files:
                            if not remaining_future.done():
                                if remaining_future.cancel():  # Only succeeds if not yet started
                                    cancelled_count += 1
                        
                        if cancelled_count > 0:
                            logger.info(f"Cancelled {cancelled_count} unstarted scan tasks")
                        
                        break
                
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
                result = call_scan_and_process_file(*task, config)
                processed_count, failed_count, timeout_count = process_task_result(
                    result, task[0], results, processed_count, failed_count, total_files, logger, daily_processing_tracker, per_run_tracker, timeout_count
                )
            except Exception as e:
                # For exceptions from the call itself, pass the exception to the processor
                processed_count, failed_count, timeout_count = process_task_result(
                    e, task[0], results, processed_count, failed_count, total_files, logger, daily_processing_tracker, per_run_tracker, timeout_count
                )
            
            # Check if we should shutdown due to too many timeouts
            if timeout_count >= max_timeouts:
                logger.error(f"Reached maximum timeout count ({max_timeouts}), shutting down processing")
                timeout_shutdown = True
                break
        
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
    
    return results, successful_files, failed_files, timeout_shutdown


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
    throttle_max_file_count_per_run=1000,
    throttle_max_file_volume_per_run_mb=1024,
    per_run_tracker=None,  # Parameter to receive per-run tracker
    
    notifier=None,
    notify_summary=False,
    skip_stability_check=False,
    config=None
    
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
        throttle_max_file_count_per_run (int): Maximum number of files to process per run (default: 1000, 0 for no limit)
        throttle_max_file_volume_per_run_mb (int): Maximum volume of data to process per run in MB (default: 1024, 0 for no limit)
        per_run_tracker (PerRunTracker): Per-run tracker instance to use (required)

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
    
    # The per_run_tracker is also a required parameter
    if per_run_tracker is None:
        logger.error("No per_run_tracker provided to scan_and_process_directory")
        raise ValueError("per_run_tracker is required")
    
    # Log message about throttling configuration if throttling is enabled
    if throttle and (throttle_max_file_volume_per_day_mb > 0 or throttle_max_file_count_per_day > 0):
        logger.info(f"Daily throttling enabled: {throttle_max_file_count_per_day} files, {throttle_max_file_volume_per_day_mb} MB")
    
    if throttle and (throttle_max_file_count_per_run > 0 or throttle_max_file_volume_per_run_mb > 0):
        logger.info(f"Per-run throttling enabled: {throttle_max_file_count_per_run} files, {throttle_max_file_volume_per_run_mb} MB")
    
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
            throttle_max_file_count_per_run,
            throttle_max_file_volume_per_run_mb,
            per_run_tracker,
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
        results, successful_files, failed_files, timeout_shutdown = process_scan_tasks(
            scan_tasks,
            max_scan_threads,
            daily_processing_tracker,
            per_run_tracker,
            config
        )

        # Handle timeout shutdown with proper cleanup
        if timeout_shutdown:
            logger.error("Processing stopped due to excessive scan timeouts")
            
            # CRITICAL: Perform cleanup for processed files
            cleanup_after_processing(
                quarantine_files,
                results,
                source_path,
                delete_source_files,
                quarantine_path,
                is_timeout_shutdown=True
            )
            
            # Send critical error notification
            if notifier:
                notifier.notify_error(
                    "Shuttle: Critical Timeout Error",
                    f"Processing stopped due to excessive malware scanner timeouts.\n"
                    f"Processed {successful_files} files successfully before shutdown.\n"
                    f"Failed files: {failed_files}\n"
                    f"Please check malware scanner service health."
                )
            
            return  # Exit early

        # Normal cleanup continues...
        # Perform comprehensive cleanup after successful processing
        cleanup_after_processing(
            quarantine_files,
            results,
            source_path,
            delete_source_files,
            quarantine_path,
            is_timeout_shutdown=False
        )

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
