import os
import shutil
import sys
import logging
from datetime import datetime

# Import common modules using relative imports
from shuttle_common.ledger import Ledger
from shuttle_common.notifier import Notifier

from shuttle_common.scan_utils import (
    get_mdatp_version,
    is_using_simulator
)
from shuttle_common.logging_setup import (
    LoggingOptions,
    setup_logging
)
from .shuttle_config import (
    parse_shuttle_config
)

from .scanning import (
    scan_and_process_directory
)

from shuttle.daily_processing_tracker import DailyProcessingTracker

""" 

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
┃   ┗━━ shuttle.scanning.scan_and_process_directory
┃       ┣━━ shuttle.scanning.quarantine_files_for_scanning
┃       ┃   ┣━━ shuttle.scanning.is_file_safe_for_processing
┃       ┃   ┣━━ shuttle_common.file_utils.normalize_path
┃       ┃   ┣━━ shuttle.throttle_utils.handle_throttle_check
┃       ┃   ┃   ┗━━ shuttle.throttler.Throttler.can_process_file
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
┃       ┃   ┃  
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
    ┗━━ if os.path.exists(lock_file): → remove lock file
"""
class Shuttle:
    """Main Shuttle application class that encapsulates the file scanning and transfer functionality."""
    
    def __init__(self):
        """Initialize the Shuttle application with configuration and set up paths."""
        self.logger = None
        self.config = parse_shuttle_config()
        self.notifier = None
        self.logging_options = None
        self.lock_file_created = False
        self.daily_processing_tracker = None
        self.using_simulator = False
    
    def get_config(self):
        """Get the Shuttle configuration object."""
        return self.config
    
    def get_quarantine_path(self):
        """Get the quarantine path from configuration."""
        return self.config.quarantine_path if hasattr(self.config, 'quarantine_path') else None
    
    def get_destination_path(self):
        """Get the destination path from configuration."""
        return self.config.destination_path if hasattr(self.config, 'destination_path') else None
    
    def get_hazard_archive_path(self):
        """Get the hazard archive path from configuration."""
        return self.config.hazard_archive_path if hasattr(self.config, 'hazard_archive_path') else None
    
    def get_source_path(self):
        """Get the source path from configuration."""
        return self.config.source_path if hasattr(self.config, 'source_path') else None
        
    def get_pending_volume(self):
        """Get the pending volume in MB from the daily processing tracker.
        
        Returns:
            float: The pending volume in MB, or 0 if not available
        """
        if self.daily_processing_tracker is not None:
            return self.daily_processing_tracker.pending_volume_mb
        return 0.0
    
    def _create_lock_file(self):
        """Create a lock file to prevent multiple instances from running."""
        if os.path.exists(self.config.lock_file):
            print(f"Another instance is running. Lock file {self.config.lock_file} exists.")
            sys.exit(1)
            
        with open(self.config.lock_file, 'w') as lock_file:
            lock_file.write(str(os.getpid()))
            self.lock_file_created = True
            
    def _setup_logging(self):
        """Set up logging for the application."""
        # Create log file name with timestamp and unique ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = os.getpid()  # Using process ID as unique identifier
        log_filename = f"shuttle_{timestamp}_{unique_id}.log"

        # Construct full log path if log directory is specified
        log_file_path = None

        if self.config.log_path:
            os.makedirs(self.config.log_path, exist_ok=True)
            log_file_path = os.path.join(self.config.log_path, log_filename)

        self.logging_options = LoggingOptions(filePath=log_file_path, level=logging.INFO)

        # Set up logging with the configured log level
        self.logger = setup_logging('shuttle', self.logging_options)
        
        return unique_id
        
    def _init_notifier(self):
        """Initialize the notifier if configured."""
        if self.config.notify:
            self.notifier = Notifier(
                recipient_email=self.config.notify_recipient_email,
                sender_email=self.config.notify_sender_email,
                smtp_server=self.config.notify_smtp_server,
                smtp_port=self.config.notify_smtp_port,
                username=self.config.notify_username,
                password=self.config.notify_password,
                use_tls=self.config.notify_use_tls,
                logging_options=self.logging_options,
                using_simulator=self.using_simulator
            )
            
    def _check_resources(self):
        """Check for required external commands."""
        # Check for required external commands
        required_commands = ['lsof', 'gpg']
        if not self.using_simulator:
            required_commands.append('mdatp')

        if self.config.on_demand_clam_av:
            required_commands.append('clamdscan')

        missing_commands = []

        for cmd in required_commands:
            if shutil.which(cmd) is None:
                missing_commands.append(cmd)

        if missing_commands:
            error_message = "Required commands missing:"
            for cmd in missing_commands:
                error_message += f"\n- '{cmd}' not found. Please ensure it is installed and accessible in your PATH."
            _shutdown_with_error(error_message, self)
            
    def _check_hazard_path(self):
        """Check hazard archive path and encryption key."""
        if self.config.hazard_archive_path:
            if not self.config.hazard_encryption_key_file_path:
                _shutdown_with_error("Hazard archive path specified but no encryption key file provided", self)
                
            if not os.path.isfile(self.config.hazard_encryption_key_file_path):
                _shutdown_with_error(f"Encryption key file not found: {self.config.hazard_encryption_key_file_path}", self)
        else:
            self.config.hazard_encryption_key_file_path = None
            
    def _validate_paths(self):
        """Validate required paths."""
        if not (self.config.source_path and self.config.destination_path and self.config.quarantine_path):
            _shutdown_with_error("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.", self)
            
        self.logger.info(f"SourcePath: {self.config.source_path}")
        self.logger.info(f"DestinationPath: {self.config.destination_path}")
        self.logger.info(f"QuarantinePath: {self.config.quarantine_path}")
        
    def _check_scan_config(self):
        """Check scan configuration and verify Defender version."""
        if not self.config.on_demand_defender and not self.config.on_demand_clam_av:
            _shutdown_with_error("No virus scanner or defender specified. Please specify at least one.\nWhile a real time virus scanner may make on-demand scanning redundant, this application is for on-demand scanning.", self)
            
        if self.config.on_demand_defender and self.config.ledger_path is not None:
            # Get current version of Microsoft Defender
            defender_version = get_mdatp_version(self.logging_options)
            
            if not defender_version:
                _shutdown_with_error("Could not get Microsoft Defender version", self)
            
            # Check status file
            ledger = Ledger(self.logging_options)    
            
            if not ledger.load(self.config.ledger_path):
                _shutdown_with_error("Could not load ledger file", self)
            
            if not ledger.is_version_tested(defender_version):
                _shutdown_with_error("This application requires that the current version Microsoft Defender has been tested and this successful testing has been confirmed in the status file.", self)
                
    def _process_files(self):
        """Process the files using scan_and_process_directory function."""
        # Create the DailyProcessingTracker instance
        self.daily_processing_tracker = DailyProcessingTracker(
            data_directory=self.config.daily_processing_tracker_logs_path,
            logging_options=self.logging_options
        )
        
        # Call scan_and_process_directory with our initialized parameters
        scan_and_process_directory(
            source_path=self.config.source_path,
            destination_path=self.config.destination_path,
            quarantine_path=self.config.quarantine_path,
            hazard_archive_path=self.config.hazard_archive_path,
            hazard_encryption_key_file_path=self.config.hazard_encryption_key_file_path,
            delete_source_files=self.config.delete_source_files,
            max_scan_threads=self.config.max_scan_threads,
            on_demand_defender=self.config.on_demand_defender,
            on_demand_clam_av=self.config.on_demand_clam_av,
            defender_handles_suspect_files=self.config.defender_handles_suspect_files,
            throttle=self.config.throttle,
            throttle_free_space_mb=self.config.throttle_free_space_mb,
            throttle_max_file_count_per_day=self.config.throttle_max_file_count_per_day,
            throttle_max_file_volume_per_day_mb=self.config.throttle_max_file_volume_per_day_mb,
            daily_processing_tracker=self.daily_processing_tracker,  # Pass the tracker directly
            notifier=self.notifier,
            notify_summary=self.config.notify_summary,
            skip_stability_check=self.config.skip_stability_check,
            logging_options=self.logging_options
        )
    
    def run(self):
        """Run the Shuttle application."""
        try:
            self._create_lock_file()
            
            # Set up logging
            unique_id = self._setup_logging()
            
            # Check if we're using the simulator (patched DEFENDER_COMMAND)
            self.using_simulator = is_using_simulator()
            
            # Log a warning if we're in simulator mode
            if self.using_simulator:
                self.logger.warning("⚠️  RUNNING WITH SIMULATOR - NO REAL MALWARE SCANNING WILL BE PERFORMED ⚠️")
            
            # Initialize notifier
            self._init_notifier()
            
            self.logger.info(f"Starting Shuttle Linux file transfer and scanning process (PID: {unique_id})")
            
            # Check resources
            self._check_resources()
            
            # Check hazard path
            self._check_hazard_path()
            
            # Validate paths
            self._validate_paths()
            
            # Check scan config
            self._check_scan_config()
            
            # Process files
            self._process_files()
            
            return 0
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"An error occurred: {e}")
            else:
                print(f"ERROR: {e}")
            return 1
            
        finally:
            # Close the daily processing tracker if it exists
            if hasattr(self, 'daily_processing_tracker') and self.daily_processing_tracker:
                self.logger.info("Closing daily processing tracker...")
                self.daily_processing_tracker.close()
                
            # Existing cleanup code
            if hasattr(self.config, 'lock_file') and os.path.exists(self.config.lock_file):
                _cleanup_lock_file(self.config.lock_file)


def main():
    """Main entry point for Shuttle application."""
    # Create the Shuttle instance
    shuttle = Shuttle()
    
    # Run the Shuttle application
    return shuttle.run()


def _cleanup_lock_file(lock_file):
    """Helper function to remove lock file if it exists"""
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print(f"Removed lock file {lock_file}")
        except Exception as e:
            print(f"Error removing lock file {lock_file}: {e}")
            
            
def _shutdown_with_error(message, shuttle_instance):
    """Helper function to log error and shutdown"""
    if shuttle_instance.logger:
        shuttle_instance.logger.error(message)
    else:
        print(f"ERROR: {message}")
    sys.exit(1)


if __name__ == '__main__':
    main()


