# Updated Shuttle Process Diagram

The process diagram in shuttle.py needs to be updated to reflect recent changes, particularly the refactoring of the DailyProcessingTracker component. Here's an updated version:

```
PROCESS OVERVIEW:

shuttle.shuttle.main
┣━━ shuttle.shuttle_config.parse_shuttle_config
┃   ┣━━ shuttle.shuttle_config.parse_args
┃   ┗━━ shuttle.shuttle_config.load_config_file
┃
┣━━ # LOCK FILE HANDLING
┃   ┣━━ if os.path.exists(config.lock_file): → exit(1)
┃   ┗━━ write PID to lock file
┃
┣━━ # SET UP LOGGING
┃   ┣━━ if config.log_path: → create directory & set log path
┃   ┗━━ shuttle_common.logging_setup.setup_logging
┃
┣━━ # SIMULATOR CHECK
┃   ┣━━ shuttle_common.scan_utils.is_using_simulator
┃   ┗━━ if using_simulator: → log warning
┃
┣━━ # NOTIFIER INITIALIZATION
┃   ┗━━ if config.notify: → shuttle_common.notifier.Notifier.__init__
┃
┣━━ # RESOURCE CHECK
┃   ┣━━ if not using_simulator: → check for mdatp
┃   ┣━━ if config.on_demand_clam_av: → check for clamdscan
┃   ┗━━ if missing_commands: → log error & exit(1)
┃
┣━━ # HAZARD PATH CHECK
┃   ┗━━ if config.hazard_archive_path:
┃       ┣━━ if not config.hazard_encryption_key_file_path: → exit(1)
┃       ┗━━ if not os.path.isfile(key_file_path): → exit(1)
┃
┣━━ # PATH VALIDATION
┃   ┗━━ if not (source & destination & quarantine paths): → exit(1)
┃
┣━━ # SCAN CONFIG CHECK
┃   ┣━━ if not (defender or clam_av): → exit(1)
┃   ┗━━ if defender and ledger_path:
┃       ┣━━ shuttle_common.scan_utils.get_mdatp_version
┃       ┣━━ if not defender_version: → exit(1)
┃       ┣━━ if not ledger.load(): → exit(1)
┃       ┗━━ if not ledger.is_version_tested(): → exit(1)
┃
┣━━ # MAIN PROCESSING
┃   ┣━━ shuttle.daily_processing_tracker.DailyProcessingTracker.__init__  
┃   ┗━━ shuttle.scanning.scan_and_process_directory
┃       ┣━━ shuttle.scanning.quarantine_files_for_scanning
┃       ┃   ┣━━ shuttle.scanning.is_file_safe_for_processing
┃       ┃   ┣━━ shuttle_common.file_utils.normalize_path
┃       ┃   ┣━━ shuttle.throttle_utils.handle_throttle_check
┃       ┃   ┃   ┗━━ shuttle.throttler.Throttler.can_process_file
┃       ┃   ┣━━ shuttle_common.files.get_file_hash 
┃       ┃   ┣━━ daily_processing_tracker.add_pending_file 
┃       ┃   ┗━━ shuttle_common.file_utils.copy_temp_then_rename
┃       ┃
┃       ┣━━ shuttle.scanning.process_scan_tasks
┃       ┃   ┃
┃       ┃   ┣━━ PARALLEL MODE
┃       ┃   ┃   concurrent.futures.ProcessPoolExecutor
┃       ┃   ┃   loop
┃       ┃   ┃   ┣━ call_scan_and_process_file ━━━━━┓
┃       ┃   ┃   ┗━ process_task_result             ┃
┃       ┃   ┃                                      ┃
┃       ┃   ┃                                      ┃
┃       ┃   ┣━━ SINGLE THREAD MODE                 ┃
┃       ┃   ┃    loop                              ┃
┃       ┃   ┃    ┣━━ call_scan_and_process_file ━━━┫
┃       ┃   ┃    ┗━━ process_task_result           ┃
┃       ┃   ┃                                      ┃
┃       ┃   ┃                                      ┃
┃       ┃   ┃                                      ┗━━ scan_and_process_file  
┃       ┃   ┃                                          ┣━━ shuttle.scanning.check_file_safety
┃       ┃   ┃                                          ┣━━ shuttle.scanning.scan_file
┃       ┃   ┃                                          ┃   ┣━━ shuttle_common.scan_utils.scan_with_defender
┃       ┃   ┃                                          ┃   ┗━━ shuttle_common.scan_utils.scan_with_clam_av
┃       ┃   ┃                                          ┗━━ shuttle.scanning.handle_scan_result
┃       ┃   ┃                                              ┣━━ shuttle.post_scan_processing.move_clean_file_to_destination
┃       ┃   ┃                                              ┃   ┗━━ shuttle_common.file_utils.copy_temp_then_rename
┃       ┃   ┃                                              ┗━━ shuttle.post_scan_processing.handle_suspect_file
┃       ┃   ┃                                                  ┣━━ shuttle.post_scan_processing.encrypt_file
┃       ┃   ┃                                                  ┗━━ shuttle.post_scan_processing.archive_file
┃       ┃   ┃  
┃       ┃   ┣━━ daily_processing_tracker.generate_task_summary  [NEW]
┃       ┃   ┗━━ log_final_status
┃       ┃
┃       ┣━━ shuttle.scanning.clean_up_source_files
┃       ┃   ┃
┃       ┃   ┗━━ shuttle_common.file_utils.remove_empty_directories
┃       ┃
┃       ┣━━ shuttle.scanning.send_summary_notification
┃       ┃
┃       ┗━━ shuttle_common.file_utils.remove_directory_contents
┃
┣━━ # EXCEPTION HANDLING
┃   ┗━━ if exception: → log error & exit(1)
┃
┗━━ # FINALLY BLOCK
    ┣━━ daily_processing_tracker.close() 
    ┗━━ if os.path.exists(lock_file): → remove lock file
```

## Key Changes in the Process Flow

1. **DailyProcessingTracker Initialization**
   - Added creation of DailyProcessingTracker in the main processing block
   - This happens in `_process_files()` method

2. **File Hash Calculation**
   - Moved file hash calculation from `scan_and_process_file` to `quarantine_files_for_scanning`
   - Hash is now calculated once and passed along with the file throughout processing

3. **Updated Tracking API**
   - `add_pending_file` now requires file path, size, hash, and source path
   - `complete_pending_file` now requires file hash and outcome information

4. **Results Tracking**
   - Added `generate_task_summary` in process_scan_tasks to use the tracker as the source of truth for results
   - Results are now categorized as successful, failed, or suspect

5. **Proper Shutdown**
   - Added call to `daily_processing_tracker.close()` in the finally block
   - This ensures pending files are properly tracked and summary data is saved

## Process Improvements from Refactoring

1. **Complete Traceability**
   - Each file is now tracked by its hash from quarantine to completion
   - File statuses and outcomes are recorded throughout processing

2. **Accurate Metrics**
   - Detailed metrics are now collected by outcome type
   - Processing rates and volumes are available for reporting

3. **Data Persistence**
   - Transaction-safe file writing prevents data corruption
   - Proper shutdown ensures all data is saved even on interruption

4. **Single Source of Truth**
   - The DailyProcessingTracker is now the authoritative source for processing results
   - No more duplicate counting in different components