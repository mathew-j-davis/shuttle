import os
import shutil
import sys
import time
from datetime import datetime
from . import (
    ShuttleConfig,
    Notifier,
    parse_config,
    setup_logging,
    process_files
)

def main():
    
    config = parse_config()

    # Lock file handling
    if os.path.exists(config.lock_file):
        print(f"Another instance is running. Lock file {config.lock_file} exists.")
        sys.exit(1)
        
    with open(config.lock_file, 'w') as lock_file:
        lock_file.write(str(os.getpid()))

    try:

        # Create log file name with timestamp and unique ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = os.getpid()  # Using process ID as unique identifier
        log_filename = f"shuttle_{timestamp}_{unique_id}.log"

        # Construct full log path if log directory is specified
        log_file = None

        if config.log_path:
            os.makedirs(config.log_path, exist_ok=True)
            log_file = os.path.join(config.log_path, log_filename)

        # Set up logging with the configured log level
        logger = setup_logging(log_file=log_file, log_level=config.log_level)

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
                logger=logger
            )
        
        logger.info(f"Starting Shuttle Linux file transfer and scanning process (PID: {unique_id})")

        # Check for required external commands
        required_commands = ['lsof', 'mdatp', 'gpg']
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

        # Retrieve other settings

        # Validate required paths
        if not (config.source_path and config.destination_path and config.quarantine_path):
            logger.error("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.")
            sys.exit(1)

        logger.info(f"SourcePath: {config.source_path}")
        logger.info(f"DestinationPath: {config.destination_path}")
        logger.info(f"QuarantinePath: {config.quarantine_path}")

        if not config.on_demand_defender and not config.on_demand_clam_av:
            logger.error("No virus scanner or defender specified. Please specify at least one.")
            logger.error("While a real time virus scanner may make on-demand scanning redundant, this application is for on-demand scanning.")
            sys.exit(1)

        process_files(config, notifier)   

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

    finally:
        if os.path.exists(config.lock_file):
            os.remove(config.lock_file)

if __name__ == '__main__':
    main()
