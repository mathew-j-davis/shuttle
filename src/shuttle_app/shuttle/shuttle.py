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

from shuttle_common.logger_injection import (
    configure_logging,
    get_logger
)

from .shuttle_config import (
    parse_shuttle_config
)

from .scanning import (
    scan_and_process_directory
)

from shuttle.daily_processing_tracker import DailyProcessingTracker


"""
CLASS INITIALISATION:

shuttle.shuttle.main
┗━━ shuttle.shuttle.Shuttle.__init__
    ┗━━ shuttle.shuttle_config.parse_shuttle_config
        ┣━━ shuttle.shuttle_config.parse_args
        ┗━━ shuttle.shuttle_config.load_config_file

PROCESS RUN:

shuttle.shuttle.Shuttle.run
┣━━ # LOCK FILE HANDLING
┃   ┗━━ shuttle.shuttle.Shuttle._create_lock_file
┃       ┣━━ if os.path.exists(config.lock_file): → exit(1)
┃       ┗━━ write PID to lock file
┃
┣━━ # SET UP LOGGING  
┃   ┗━━ shuttle.shuttle.Shuttle._setup_logging
┃       ┣━━ if config.log_path: → create directory & set log path
┃       ┗━━ shuttle_common.logger_injection.configure_logging
┃
┣━━ # SIMULATOR CHECK
┃   ┣━━ shuttle_common.scan_utils.is_using_simulator
┃   ┗━━ if using_simulator: → log warning
┃
┣━━ # NOTIFIER INITIALIZATION
┃   ┗━━ shuttle.shuttle.Shuttle._init_notifier
┃       ┗━━ if config.notify: → shuttle_common.notifier.Notifier.__init__
┃
┣━━ # RESOURCE CHECK
┃   ┗━━ shuttle.shuttle.Shuttle._check_resources
┃       ┣━━ if not using_simulator: → check for mdatp
┃       ┣━━ if config.on_demand_clam_av: → check for clamdscan
┃       ┗━━ if missing_commands: → _shutdown_with_error → exit(1)
┃
┣━━ # HAZARD PATH CHECK
┃   ┗━━ shuttle.shuttle.Shuttle._check_hazard_path
┃       ┗━━ if config.hazard_archive_path:
┃           ┣━━ if not config.hazard_encryption_key_file_path: → _shutdown_with_error → exit(1)
┃           ┗━━ if not os.path.isfile(key_file_path): → _shutdown_with_error → exit(1)
┃
┣━━ # PATH VALIDATION
┃   ┗━━ shuttle.shuttle.Shuttle._validate_paths
┃       ┗━━ if not (source & destination & quarantine paths): → _shutdown_with_error → exit(1)
┃
┣━━ # SCAN CONFIG CHECK
┃   ┗━━ shuttle.shuttle.Shuttle._check_scan_config
┃       ┣━━ if not (defender or clam_av): → _shutdown_with_error → exit(1)
┃       ┗━━ if defender and ledger_file_path:
┃           ┣━━ shuttle_common.scan_utils.get_mdatp_version
┃           ┣━━ if not defender_version: → _shutdown_with_error → exit(1)
┃           ┣━━ shuttle_common.ledger.Ledger.load()
┃           ┣━━ if not ledger.load(): → _shutdown_with_error → exit(1)
┃           ┗━━ if not ledger.is_version_tested(): → _shutdown_with_error → exit(1)
┃
┣━━ # MAIN PROCESSING
┃   ┗━━ shuttle.shuttle.Shuttle._process_files
┃       ┣━━ shuttle.daily_processing_tracker.DailyProcessingTracker.__init__  
┃       ┗━━ shuttle.scanning.scan_and_process_directory
┃           ┣━━ shuttle.scanning.quarantine_files_for_scanning
┃           ┃   ┣━━ shuttle.scanning.is_file_safe_for_processing
┃           ┃   ┣━━ shuttle_common.file_utils.normalize_path
┃           ┃   ┣━━ shuttle.throttle_utils.handle_throttle_check
┃           ┃   ┃   ┗━━ shuttle.throttler.Throttler.can_process_file
┃           ┃   ┣━━ shuttle_common.files.get_file_hash 
┃           ┃   ┣━━ daily_processing_tracker.add_pending_file 
┃           ┃   ┗━━ shuttle_common.file_utils.copy_temp_then_rename
┃           ┃
┃           ┣━━ shuttle.scanning.process_scan_tasks
┃           ┃   ┃
┃           ┃   ┣━━ PARALLEL MODE
┃           ┃   ┃   concurrent.futures.ProcessPoolExecutor
┃           ┃   ┃   loop
┃           ┃   ┃   ┣━ call_scan_and_process_file ━━━━━┓
┃           ┃   ┃   ┗━ process_task_result             ┃
┃           ┃   ┃                                      ┃
┃           ┃   ┃                                      ┃
┃           ┃   ┣━━ SINGLE THREAD MODE                 ┃
┃           ┃   ┃    loop                              ┃
┃           ┃   ┃    ┣━━ call_scan_and_process_file ━━━┫
┃           ┃   ┃    ┗━━ process_task_result           ┃
┃           ┃   ┃                                      ┃
┃           ┃   ┃                                      ┃
┃           ┃   ┃                                      ┗━━ scan_and_process_file  
┃           ┃   ┃                                          ┣━━ shuttle.scanning.check_file_safety
┃           ┃   ┃                                          ┣━━ shuttle.scanning.scan_file
┃           ┃   ┃                                          ┃   ┣━━ shuttle_common.scan_utils.scan_with_defender
┃           ┃   ┃                                          ┃   ┗━━ shuttle_common.scan_utils.scan_with_clam_av
┃           ┃   ┃                                          ┗━━ shuttle.scanning.handle_scan_result
┃           ┃   ┃                                              ┣━━ shuttle.post_scan_processing.move_clean_file_to_destination
┃           ┃   ┃                                              ┃   ┗━━ shuttle_common.file_utils.copy_temp_then_rename
┃           ┃   ┃                                              ┗━━ shuttle.post_scan_processing.handle_suspect_file
┃           ┃   ┃                                                  ┣━━ shuttle.post_scan_processing.encrypt_file
┃           ┃   ┃                                                  ┗━━ shuttle.post_scan_processing.archive_file
┃           ┃   ┃  
┃           ┃   ┣━━ daily_processing_tracker.generate_task_summary
┃           ┃   ┗━━ log_final_status
┃           ┃
┃           ┣━━ shuttle.scanning.clean_up_source_files
┃           ┃   ┃
┃           ┃   ┗━━ shuttle_common.file_utils.remove_empty_directories
┃           ┃
┃           ┣━━ shuttle.scanning.send_summary_notification
┃           ┃
┃           ┗━━ shuttle_common.file_utils.remove_directory_contents
┃
┣━━ # EXCEPTION HANDLING
┃   ┗━━ try/except: → log error & return 1
┃
┗━━ # FINALLY BLOCK
    ┣━━ daily_processing_tracker.close() 
    ┗━━ _cleanup_lock_file(config.lock_file)
"""

class Shuttle:
    """Main Shuttle application class that encapsulates the file scanning and transfer functionality."""
    
    def __init__(self):
        """Initialize the Shuttle application with configuration and set up paths."""
        self.config = parse_shuttle_config()
        self.notifier = None
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
        
        # Configure global logging for hierarchy tracking
        configure_logging({
            'log_file_path': log_file_path,
            'log_level': self.config.log_level
        })

        return unique_id
        
    def _init_notifier(self):
        """Initialize the notifier if configured."""
        if self.config.notify:
            self.notifier = Notifier(
                recipient_email=self.config.notify_recipient_email,
                recipient_email_error=self.config.notify_recipient_email_error,
                recipient_email_summary=self.config.notify_recipient_email_summary,
                recipient_email_hazard=self.config.notify_recipient_email_hazard,
                sender_email=self.config.notify_sender_email,
                smtp_server=self.config.notify_smtp_server,
                smtp_port=self.config.notify_smtp_port,
                username=self.config.notify_username,
                password=self.config.notify_password,
                use_tls=self.config.notify_use_tls,
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
            
        logger = get_logger()
        logger.info(f"SourcePath: {self.config.source_path}")
        logger.info(f"DestinationPath: {self.config.destination_path}")
        logger.info(f"QuarantinePath: {self.config.quarantine_path}")
        
    def _check_scan_config(self):
        """Check scan configuration and verify Defender version."""
        if not self.config.on_demand_defender and not self.config.on_demand_clam_av:
            _shutdown_with_error("No virus scanner or defender specified. Please specify at least one.\nWhile a real time virus scanner may make on-demand scanning redundant, this application is for on-demand scanning.", self)
            
        if self.config.on_demand_defender and self.config.ledger_file_path is not None:
            # Get current version of Microsoft Defender
            defender_version = get_mdatp_version()
            
            if not defender_version:
                _shutdown_with_error("Could not get Microsoft Defender version", self)
            
            # Check status file
            ledger = Ledger()    
            
            if not ledger.load(self.config.ledger_file_path):
                _shutdown_with_error("Could not load ledger file", self)
            
            if not ledger.is_version_tested(defender_version):
                _shutdown_with_error("This application requires that the current version Microsoft Defender has been tested and this successful testing has been confirmed in the status file.", self)
                
    def _process_files(self):
        """Process the files using scan_and_process_directory function."""
        # Create the DailyProcessingTracker instance
        self.daily_processing_tracker = DailyProcessingTracker(
            data_directory=self.config.daily_processing_tracker_logs_path
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
            skip_stability_check=self.config.skip_stability_check
        )
    
    def run(self):
        """Run the Shuttle application."""
        try:
            self._create_lock_file()
            
            # Set umask to ensure restrictive file permissions (group writable, no other access)
            os.umask(0o007)
            
            # Set up logging
            unique_id = self._setup_logging()
            
            # Check if we're using the simulator (patched DEFENDER_COMMAND)
            self.using_simulator = is_using_simulator()
            
            # Log a warning if we're in simulator mode
            if self.using_simulator:
                logger = get_logger()
                logger.warning("⚠️  RUNNING WITH SIMULATOR - NO REAL MALWARE SCANNING WILL BE PERFORMED ⚠️")
            
            # Initialize notifier
            self._init_notifier()
            
            logger = get_logger()
            logger.info(f"Starting Shuttle Linux file transfer and scanning process (PID: {unique_id})")
            
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
            try:
                logger = get_logger()
                logger.error(f"An error occurred: {e}")
            except:
                print(f"ERROR: {e}")
            return 1
            
        finally:
            # Close the daily processing tracker if it exists
            if hasattr(self, 'daily_processing_tracker') and self.daily_processing_tracker:
                try:
                    logger = get_logger()
                    logger.info("Closing daily processing tracker...")
                except:
                    pass
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
    try:
        logger = get_logger()
        logger.error(message)
    except:
        print(f"ERROR: {message}")
    sys.exit(1)


if __name__ == '__main__':
    main()


