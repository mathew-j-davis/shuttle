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



"""
main() [shuttle.py]
├── setup_logging [shuttle_common.logging_setup]
├── parse_shuttle_config [shuttle.shuttle_config]
│   ├── parse_args [shuttle.shuttle_config]
│   └── load_config_file [shuttle.shuttle_config]
│
├── get_mdatp_version [shuttle_common.scan_utils]
│   └── is_using_simulator [shuttle_common.scan_utils]
│
├── Lock file handling [shuttle.py]
│
├── Notifier initialization [shuttle_common.notifier]
│   └── Notifier.is_configured [shuttle_common.notifier]
│
├── scan_and_process_directory [shuttle.scanning]
│   ├── quarantine_files_for_scanning [shuttle.scanning]
│   │   ├── is_file_safe_for_processing [shuttle.scanning]
│   │   ├── normalize_path [shuttle_common.file_utils]
│   │   ├── handle_throttle_check [shuttle.throttle_utils]
│   │   │   └── Throttler methods [shuttle.throttler]
│   │   └── copy_temp_then_rename [shuttle_common.file_utils]
│   │
│   ├── process_scan_tasks [shuttle.scanning]
│   │   ├── setup_logging [shuttle_common.logging_setup]
│   │   ├── PARALLEL MODE (max_scan_threads > 1)
│   │   │   ├── ProcessPoolExecutor [concurrent.futures]
│   │   │   └── process_task [shuttle.scanning]
│   │   │       ├── check_file_safety [shuttle.scanning]
│   │   │       ├── scan_file [shuttle.scanning]
│   │   │       │   ├── scan_with_defender [shuttle_common.scan_utils]
│   │   │       │   └── scan_with_clam_av [shuttle_common.scan_utils]
│   │   │       └── handle_scan_result [shuttle.scanning]
│   │   │           ├── move_clean_file_to_destination [shuttle.post_scan_processing]
│   │   │           │   └── copy_temp_then_rename [shuttle_common.file_utils]
│   │   │           └── handle_suspect_file [shuttle.post_scan_processing]
│   │   │               ├── encrypt_file [shuttle.post_scan_processing]
│   │   │               └── archive_file [shuttle.post_scan_processing]
│   │   │
│   │   └── SINGLE THREAD MODE (max_scan_threads <= 1)
│   │       ├── check_file_safety [shuttle.scanning]
│   │       ├── scan_file [shuttle.scanning]
│   │       │   ├── scan_with_defender [shuttle_common.scan_utils]
│   │       │   └── scan_with_clam_av [shuttle_common.scan_utils]
│   │       └── handle_scan_result [shuttle.scanning]
│   │           ├── move_clean_file_to_destination [shuttle.post_scan_processing]
│   │           │   └── copy_temp_then_rename [shuttle_common.file_utils]
│   │           └── handle_suspect_file [shuttle.post_scan_processing]
│   │               ├── encrypt_file [shuttle.post_scan_processing]
│   │               └── archive_file [shuttle.post_scan_processing]
│   │
│   ├── clean_up_source_files [shuttle.scanning]
│   │   ├── setup_logging [shuttle_common.logging_setup]
│   │   └── remove_empty_directories [shuttle_common.file_utils]
│   │
│   ├── send_summary_notification [shuttle.scanning]
│   │   └── setup_logging [shuttle_common.logging_setup]
│   │
│   └── remove_directory_contents [shuttle_common.file_utils]
│
└── remove_lock_file [shuttle.py]
"""

def main():
    
    logger = None
    
    config = parse_shuttle_config()

    # Lock file handling
    if os.path.exists(config.lock_file):
        print(f"Another instance is running. Lock file {config.lock_file} exists.")
        sys.exit(1)
        
    with open(config.lock_file, 'w') as lock_file:
        lock_file.write(str(os.getpid()))

    try:

        #
        # SET UP LOGGING
        #

        # Create log file name with timestamp and unique ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = os.getpid()  # Using process ID as unique identifier
        log_filename = f"shuttle_{timestamp}_{unique_id}.log"

        # Construct full log path if log directory is specified
        log_file_path = None

        if config.log_path:
            os.makedirs(config.log_path, exist_ok=True)
            log_file_path = os.path.join(config.log_path, log_filename)

        logging_options = LoggingOptions(filePath=log_file_path, level=logging.INFO)

        # Set up logging with the configured log level
        logger = setup_logging('shuttle', logging_options)

        #
        # SIMULATOR CHECK : is defender simulation patch applied?
        #

        # Check if we're using the simulator (patched DEFENDER_COMMAND)
        using_simulator = is_using_simulator()
        
        # Log a warning if we're in simulator mode
        if using_simulator:
            logger.warning("⚠️  RUNNING WITH SIMULATOR - NO REAL MALWARE SCANNING WILL BE PERFORMED ⚠️")

        
        #
        # NOTIFIER INITIALIZATION
        #
        notifier = None;
        
        if config.notify:
            notifier = Notifier(
                recipient_email=config.notify_recipient_email,
                sender_email=config.notify_sender_email,
                smtp_server=config.notify_smtp_server,
                smtp_port=config.notify_smtp_port,
                username=config.notify_username,
                password=config.notify_password,
                use_tls=config.notify_use_tls,
                logging_options=logging_options,
                using_simulator=using_simulator
            )
        
        logger.info(f"Starting Shuttle Linux file transfer and scanning process (PID: {unique_id})")

        #
        # RESOURCE CHECK
        #

        # Check for required external commands
        required_commands = ['lsof', 'gpg']
        if not using_simulator:
            required_commands.append('mdatp')

        if config.on_demand_clam_av:
            required_commands.append('clamdscan')

        missing_commands = []

        for cmd in required_commands:
            if shutil.which(cmd) is None:
                missing_commands.append(cmd)

        if missing_commands:
            for cmd in missing_commands:
                logger.error(f"Required command '{cmd}' not found. Please ensure it is installed and accessible in your PATH.")
            sys.exit(1)

        # Get encryption key file path
        if config.hazard_archive_path:
            
            if not config.hazard_encryption_key_file_path:
                logger.error("Hazard archive path specified but no encryption key file provided")
                sys.exit(1)
            if not os.path.isfile(config.hazard_encryption_key_file_path):
                logger.error(f"Encryption key file not found: {config.hazard_encryption_key_file_path}")
                sys.exit(1)

        else:
            config.hazard_encryption_key_file_path = None

        #
        # ENVIRONMENT CHECK
        #

        # Validate required paths
        if not (config.source_path and config.destination_path and config.quarantine_path):
            logger.error("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.")
            sys.exit(1)

        logger.info(f"SourcePath: {config.source_path}")
        logger.info(f"DestinationPath: {config.destination_path}")
        logger.info(f"QuarantinePath: {config.quarantine_path}")


        # 
        # SCAN CONFIG CHECK
        #

        if not config.on_demand_defender and not config.on_demand_clam_av:
            logger.error("No virus scanner or defender specified. Please specify at least one.")
            logger.error("While a real time virus scanner may make on-demand scanning redundant, this application is for on-demand scanning.")
            sys.exit(1)

        if config.on_demand_defender and config.ledger_path is not None:
            
            # Get current version of Microsoft Defender
            defender_version = get_mdatp_version(logging_options)
            
            if not defender_version:
                logger.error("Could not get Microsoft Defender version")
                sys.exit(1)
            
            # Check status file
            #method to check if the current version of Microsoft Defender 
            # has been tested and this successful testing has been confirmed in the status file.
            # use value of result to check status file
            current_defender_tested = False

            ledger = Ledger(logging_options)    
            
            if not ledger.load(config.ledger_path):
                logger.error("Could not load ledger file")
                sys.exit(1)
            
            if not ledger.is_version_tested(defender_version):
                logger.error("This application requires that the current version Microsoft Defender has been tested and this successful testing has been confirmed in the status file.")
                sys.exit(1)

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
            throttle=config.throttle,
            throttle_free_space=config.throttle_free_space,
            notifier=notifier,
            notify_summary=config.notify_summary,
            skip_stability_check=config.skip_stability_check,
            logging_options=logging_options
        )

    except Exception as e:
        if logger:
            logger.error(f"An error occurred: {e}")
        sys.exit(1)

    finally:
        if os.path.exists(config.lock_file):
            os.remove(config.lock_file)

if __name__ == '__main__':
    main()
