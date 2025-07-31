#!python3
"""
Setup Shuttle configuration files

Note: This script only creates configuration-related directories.
Data directories (source, destination, quarantine, etc.) are created
by the main installer based on user preferences.
"""

import os
import argparse
import configparser
import yaml
import tempfile
import subprocess

def write_file_with_sudo_fallback(file_path, write_func):
    """
    Common function to write files with sudo fallback using bash helper
    
    Args:
        file_path: Target file path
        write_func: Function that takes a file path and writes content to it
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Try writing directly first
        write_func(file_path)
        print(f"Created file at {file_path}")
        return True
    except PermissionError:
        print(f"Permission denied, attempting with sudo: {file_path}")
        
        # Write to a temporary file first
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            # Write content to temp file
            write_func(tmp_path)
            
            # Use bash helper to copy with sudo fallback
            script_dir = os.path.dirname(os.path.dirname(__file__))
            bash_helper = os.path.join(script_dir, '_setup_lib_sh', 'sudo_helpers.source.sh')
            
            result = subprocess.run([
                'bash', '-c', 
                f'source "{bash_helper}" && write_temp_file_with_sudo_fallback "{tmp_path}" "{file_path}"'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Created file with sudo at {file_path}")
                return True
            else:
                print(f"ERROR: Failed to create file even with sudo: {file_path}")
                print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to write to temp file: {e}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
    except Exception as e:
        print(f"ERROR: Failed to create file: {file_path}")
        print(f"Error: {e}")
        return False

def get_required_env_var(var_name, description):
    """Get an environment variable or exit with error if not set"""
    value = os.environ.get(var_name)
    if not value:
        print(f"ERROR: {var_name} environment variable is not set.")
        print(f"This variable should contain the path to the {description}.")
        print(f"Please run the environment setup script first:")
        print(f"  ./scripts/1_installation_steps/00_set_env.sh -e    # For development")
        print(f"  ./scripts/1_installation_steps/00_set_env.sh -u    # For user production")
        print(f"  ./scripts/1_installation_steps/00_set_env.sh       # For system production")
        print(f"Then source the generated environment file before running this script.")
        exit(1)
    return value

def parse_arguments():
    """Parse command line arguments for configuration setup"""
    parser = argparse.ArgumentParser(description='Setup Shuttle configuration and directories')
    
    # Operation mode selection
    parser.add_argument('--create-config', action='store_true', help='Create main configuration file')
    parser.add_argument('--create-test-config', action='store_true', help='Create test configuration file')
    parser.add_argument('--create-ledger', action='store_true', help='Create ledger file')
    parser.add_argument('--create-test-keys', action='store_true', help='Create test encryption keys')
    parser.add_argument('--all', action='store_true', help='Create all files (default behavior)')
    parser.add_argument('--append-config', action='store_true', help='Append to existing configuration file instead of overwriting')
    
    # Staging mode support
    parser.add_argument('--staging-mode', action='store_true', help='Staging mode: use final paths in config content but create files at env var locations')
    parser.add_argument('--final-config-path', help='Final config path for staging mode (used in config content)')
    parser.add_argument('--final-test-work-dir', help='Final test work directory for staging mode (used in config content)')
    parser.add_argument('--final-test-config-path', help='Final test config path for staging mode (used in config content)')
    
    # Path arguments - use work_dir subdirectories as defaults
    parser.add_argument('--source-path', help='Path to the source directory (default: WORK_DIR/in)')
    parser.add_argument('--destination-path', help='Path to the destination directory (default: WORK_DIR/out)')
    parser.add_argument('--quarantine-path', help='Path to the quarantine directory (default: WORK_DIR/quarantine)')
    parser.add_argument('--log-path', help='Path to the log directory (default: WORK_DIR/logs)')
    parser.add_argument('--hazard-archive-path', help='Path to the hazard archive directory (default: WORK_DIR/hazard)')
    parser.add_argument('--ledger-file-path', help='Path to the ledger file (default: WORK_DIR/ledger/ledger.yaml)')
    parser.add_argument('--hazard-encryption-key-path', help='Path to the GPG public key file (default: CONFIG_DIR/public-key.gpg)')
    
    # Scanning configuration
    parser.add_argument('--max-scan-threads', type=int, help='Maximum number of parallel scans')
    parser.add_argument('--on-demand-defender', action='store_true', help='Use on-demand scanning for Microsoft Defender')
    parser.add_argument('--no-on-demand-defender', action='store_false', dest='on_demand_defender', help='Disable on-demand Microsoft Defender scanning')
    parser.add_argument('--on-demand-clam-av', action='store_true', help='Use on-demand scanning for ClamAV')
    parser.add_argument('--defender-handles-suspect-files', action='store_true', help='Let Microsoft Defender handle suspect files')
    parser.add_argument('--no-defender-handles-suspect-files', action='store_false', dest='defender_handles_suspect_files', help='Don\'t let Defender handle suspect files')
    
    # Malware scan timeout configuration
    parser.add_argument('--malware-scan-timeout-seconds', type=int, 
                        help='Timeout for malware scans in seconds (0 = no timeout)')
    parser.add_argument('--malware-scan-timeout-ms-per-byte', type=float,
                        help='Additional timeout per byte in milliseconds (0 = no per-byte timeout)')
    parser.add_argument('--malware-scan-retry-wait-seconds', type=int,
                        help='Wait time between scan retries in seconds (0 = no wait)')
    parser.add_argument('--malware-scan-retry-count', type=int,
                        help='Maximum scan timeouts before shutdown (0 = unlimited)')
    
    # File processing options
    parser.add_argument('--delete-source-files-after-copying', action='store_true', help='Delete source files after copying')
    parser.add_argument('--no-delete-source-files-after-copying', action='store_false', dest='delete_source_files_after_copying', help='Keep source files after copying')
    
    # Throttling configuration
    parser.add_argument('--throttle', action='store_true', help='Enable throttling of file processing')
    parser.add_argument('--no-throttle', action='store_false', dest='throttle', help='Disable throttling')
    parser.add_argument('--throttle-free-space-mb', type=int, help='Minimum free space (in MB) required')
    parser.add_argument('--throttle-max-file-count-per-run', type=int, 
                        help='Maximum files to process per run (0 = unlimited)')
    parser.add_argument('--throttle-max-file-volume-per-run-mb', type=int,
                        help='Maximum volume to process per run in MB (0 = unlimited)')
    parser.add_argument('--throttle-max-file-volume-per-day-mb', type=int,
                        help='Maximum volume to process per day in MB (0 = unlimited)')
    parser.add_argument('--throttle-max-file-count-per-day', type=int,
                        help='Maximum files to process per day (0 = unlimited)')
    
    # Logging configuration
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        help='Logging level')
    
    # Notification configuration
    parser.add_argument('--notify', action='store_true', help='Enable email notifications for errors')
    parser.add_argument('--notify-summary', action='store_true', help='Enable email notifications for summaries')
    parser.add_argument('--notify-recipient-email', help='Email address for notifications')
    parser.add_argument('--notify-recipient-email-error', help='Email address for error notifications (defaults to notify-recipient-email)')
    parser.add_argument('--notify-recipient-email-summary', help='Email address for summary notifications (defaults to notify-recipient-email)')
    parser.add_argument('--notify-recipient-email-hazard', help='Email address for hazard notifications (defaults to notify-recipient-email)')
    parser.add_argument('--notify-sender-email', help='Sender email address')
    parser.add_argument('--notify-smtp-server', help='SMTP server address')
    parser.add_argument('--notify-smtp-port', type=int, help='SMTP server port')
    parser.add_argument('--notify-username', help='SMTP username')
    parser.add_argument('--notify-password', help='SMTP password')
    parser.add_argument('--notify-use-tls', action='store_true', help='Use TLS for SMTP')
    
    return parser.parse_args()

# Helper function to create directory with sudo if needed (global scope)
def create_directory_with_sudo_if_needed(dir_path, description):
    if os.path.exists(dir_path):
        return True
        
    try:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created {description}: {dir_path}")
        return True
    except PermissionError:
        print(f"Creating directory with sudo: {dir_path}")
        
        # Use bash helper for directory creation with sudo
        script_dir = os.path.dirname(os.path.dirname(__file__))
        bash_helper = os.path.join(script_dir, '_setup_lib_sh', 'sudo_helpers.source.sh')
        
        result = subprocess.run([
            'bash', '-c', 
            f'source "{bash_helper}" && create_directory_with_auto_sudo "{dir_path}" "{description}" "true"'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Created {description} with sudo: {dir_path}")
            return True
        else:
            print(f"ERROR: Failed to create {description} even with sudo: {dir_path}")
            print(f"Error: {result.stderr}")
            return False

def prepare_directory_paths(work_dir, config_dir, args):
    """Prepare directory paths for configuration (without creating them)"""
    
    # In staging mode, use final paths for config content but current env vars for file creation
    if args.staging_mode:
        # Use final paths for writing into config files
        final_work_dir = args.final_test_work_dir or work_dir
        source_dir = args.source_path or os.path.join(final_work_dir, "in")
        dest_dir = args.destination_path or os.path.join(final_work_dir, "out")
        quarantine_dir = args.quarantine_path or os.path.join(final_work_dir, "quarantine")
        log_dir = args.log_path or os.path.join(final_work_dir, "logs")
        hazard_archive_dir = args.hazard_archive_path or os.path.join(final_work_dir, "hazard")
        ledger_file_path = args.ledger_file_path or os.path.join(final_work_dir, "ledger", "ledger.yaml")
    else:
        # Normal mode: use current work_dir for both file creation and config content
        source_dir = args.source_path or os.path.join(work_dir, "in")
        dest_dir = args.destination_path or os.path.join(work_dir, "out")
        quarantine_dir = args.quarantine_path or os.path.join(work_dir, "quarantine")
        log_dir = args.log_path or os.path.join(work_dir, "logs")
        hazard_archive_dir = args.hazard_archive_path or os.path.join(work_dir, "hazard")
        ledger_file_path = args.ledger_file_path or os.path.join(work_dir, "ledger", "ledger.yaml")
    
    ledger_file_dir = os.path.dirname(ledger_file_path)
    
    # Only create config-related directories that are needed for config file creation
    # The main installer handles creation of data directories based on user preferences
    if not create_directory_with_sudo_if_needed(config_dir, "config directory"):
        print(f"Failed to create config directory: {config_dir}")
        return None
    
    # Create ledger directory only if ledger creation is requested
    if args.create_ledger and ledger_file_dir:
        if not create_directory_with_sudo_if_needed(ledger_file_dir, "ledger directory"):
            print(f"Failed to create ledger directory: {ledger_file_dir}")
            return None
    
    return {
        'source_dir': source_dir,
        'dest_dir': dest_dir,
        'quarantine_dir': quarantine_dir,
        'log_dir': log_dir,
        'hazard_archive_dir': hazard_archive_dir,
        'ledger_file_path': ledger_file_path,
        'ledger_file_dir': ledger_file_dir
    }

def add_config_value_if_not_none(section_dict, key, value):
    """Add a value to the config section dictionary only if it's not None"""
    if value is not None:
        section_dict[key] = str(value)

def create_config_file(config_path, args, paths, config_dir):
    """Create main Shuttle configuration file"""
    # Check for append mode
    if args.append_config and os.path.exists(config_path):
        print(f"Appending to existing configuration file: {config_path}")
        config = configparser.ConfigParser()
        config.read(config_path)
    else:
        if os.path.exists(config_path):
            print(f"Overwriting existing configuration file: {config_path}")
        else:
            print("Creating new config file")
        config = configparser.ConfigParser()
    
    # Prepare config data - only set hazard key if not provided
    hazard_encryption_key_path = args.hazard_encryption_key_path
    if not hazard_encryption_key_path and paths:
        hazard_encryption_key_path = os.path.join(config_dir, "public-key.gpg")

    # Create or update paths section
    if 'paths' not in config:
        config.add_section('paths')
    paths_section = {}
    
    # Only add path values that are provided
    if paths and paths.get('source_dir'):
        add_config_value_if_not_none(paths_section, 'source_path', paths['source_dir'])
    if paths and paths.get('dest_dir'):
        add_config_value_if_not_none(paths_section, 'destination_path', paths['dest_dir'])
    if paths and paths.get('quarantine_dir'):
        add_config_value_if_not_none(paths_section, 'quarantine_path', paths['quarantine_dir'])
    if paths and paths.get('log_dir'):
        add_config_value_if_not_none(paths_section, 'log_path', paths['log_dir'])
        add_config_value_if_not_none(paths_section, 'daily_processing_tracker_logs_path', paths['log_dir'])
    if paths and paths.get('hazard_archive_dir'):
        add_config_value_if_not_none(paths_section, 'hazard_archive_path', paths['hazard_archive_dir'])
    if hazard_encryption_key_path:
        add_config_value_if_not_none(paths_section, 'hazard_encryption_key_path', hazard_encryption_key_path)
    if paths and paths.get('ledger_file_path'):
        add_config_value_if_not_none(paths_section, 'ledger_file_path', paths['ledger_file_path'])
    
    # Update the config section with new values
    for key, value in paths_section.items():
        config['paths'][key] = value

    # Create or update settings section
    if 'settings' not in config:
        config.add_section('settings')
    settings_section = {}
    
    # Only add settings values that are provided
    add_config_value_if_not_none(settings_section, 'max_scan_threads', args.max_scan_threads)
    add_config_value_if_not_none(settings_section, 'delete_source_files_after_copying', args.delete_source_files_after_copying)
    add_config_value_if_not_none(settings_section, 'defender_handles_suspect_files', args.defender_handles_suspect_files)
    add_config_value_if_not_none(settings_section, 'on_demand_defender', args.on_demand_defender)
    add_config_value_if_not_none(settings_section, 'on_demand_clam_av', args.on_demand_clam_av)
    add_config_value_if_not_none(settings_section, 'throttle', args.throttle)
    add_config_value_if_not_none(settings_section, 'throttle_free_space_mb', args.throttle_free_space_mb)
    add_config_value_if_not_none(settings_section, 'throttle_max_file_count_per_run', args.throttle_max_file_count_per_run)
    add_config_value_if_not_none(settings_section, 'throttle_max_file_volume_per_run_mb', args.throttle_max_file_volume_per_run_mb)
    add_config_value_if_not_none(settings_section, 'throttle_max_file_volume_per_day_mb', args.throttle_max_file_volume_per_day_mb)
    add_config_value_if_not_none(settings_section, 'throttle_max_file_count_per_day', args.throttle_max_file_count_per_day)
    
    # Update the config section with new values
    for key, value in settings_section.items():
        config['settings'][key] = value

    # Create or update logging section
    if 'logging' not in config:
        config.add_section('logging')
    logging_section = {}
    
    add_config_value_if_not_none(logging_section, 'log_level', args.log_level)
    
    # Update the config section with new values
    for key, value in logging_section.items():
        config['logging'][key] = value

    # Create or update scanning section
    if 'scanning' not in config:
        config.add_section('scanning')
    scanning_section = {}
    
    add_config_value_if_not_none(scanning_section, 'malware_scan_timeout_seconds', args.malware_scan_timeout_seconds)
    add_config_value_if_not_none(scanning_section, 'malware_scan_timeout_ms_per_byte', args.malware_scan_timeout_ms_per_byte)
    add_config_value_if_not_none(scanning_section, 'malware_scan_retry_wait_seconds', args.malware_scan_retry_wait_seconds)
    add_config_value_if_not_none(scanning_section, 'malware_scan_retry_count', args.malware_scan_retry_count)
    
    # Update the config section with new values
    for key, value in scanning_section.items():
        config['scanning'][key] = value

    # Create or update notifications section
    if 'notifications' not in config:
        config.add_section('notifications')
    notifications_section = {}
    
    add_config_value_if_not_none(notifications_section, 'notify', args.notify)
    add_config_value_if_not_none(notifications_section, 'notify_summary', args.notify_summary)
    add_config_value_if_not_none(notifications_section, 'recipient_email', args.notify_recipient_email)
    
    # Only add fallback emails if there's a primary email or specific email provided
    if args.notify_recipient_email_error:
        add_config_value_if_not_none(notifications_section, 'recipient_email_error', args.notify_recipient_email_error)
    elif args.notify_recipient_email:
        add_config_value_if_not_none(notifications_section, 'recipient_email_error', args.notify_recipient_email)
        
    if args.notify_recipient_email_summary:
        add_config_value_if_not_none(notifications_section, 'recipient_email_summary', args.notify_recipient_email_summary)
    elif args.notify_recipient_email:
        add_config_value_if_not_none(notifications_section, 'recipient_email_summary', args.notify_recipient_email)
        
    if args.notify_recipient_email_hazard:
        add_config_value_if_not_none(notifications_section, 'recipient_email_hazard', args.notify_recipient_email_hazard)
    elif args.notify_recipient_email:
        add_config_value_if_not_none(notifications_section, 'recipient_email_hazard', args.notify_recipient_email)
    add_config_value_if_not_none(notifications_section, 'sender_email', args.notify_sender_email)
    add_config_value_if_not_none(notifications_section, 'smtp_server', args.notify_smtp_server)
    add_config_value_if_not_none(notifications_section, 'smtp_port', args.notify_smtp_port)
    add_config_value_if_not_none(notifications_section, 'username', args.notify_username)
    add_config_value_if_not_none(notifications_section, 'password', args.notify_password)
    add_config_value_if_not_none(notifications_section, 'use_tls', args.notify_use_tls)
    
    # Update the config section with new values
    for key, value in notifications_section.items():
        config['notifications'][key] = value

    # Define write function for the shared helper
    def write_config(file_path):
        with open(file_path, 'w') as configfile:
            config.write(configfile)
    
    # Use shared helper for file creation with sudo fallback
    return write_file_with_sudo_fallback(config_path, write_config)

def create_ledger_file(ledger_file_path):
    """Create default ledger.yaml file"""
    if os.path.exists(ledger_file_path):
        print(f"Overwriting existing ledger file: {ledger_file_path}")
    else:
        print("Creating default ledger.yaml file...")
    
    # Create YAML structure with empty tested_versions list
    status_data = {
        'defender': {
            'tested_versions': [],
            'current_version': ''
        }
    }

    # Define write function for the shared helper
    def write_ledger(file_path):
        with open(file_path, 'w') as yaml_file:
            yaml.dump(status_data, yaml_file, default_flow_style=False, sort_keys=False)
    
    # Use shared helper for file creation with sudo fallback
    return write_file_with_sudo_fallback(ledger_file_path, write_ledger)

def create_test_keys(test_area_dir):
    """Generate test encryption keys"""
    test_key_public_path = os.path.join(test_area_dir, 'shuttle_test_key_public.gpg')
    
    if os.path.exists(test_key_public_path):
        print(f"Test keys already exist: {test_key_public_path}")
        return False
        
    print("Generating test encryption keys...")
    import subprocess
    key_generation_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), '0_key_generation', '00_generate_shuttle_keys.sh')
    
    # Call key generation script with test parameters
    result = subprocess.run([
        key_generation_script,
        '--key-name', 'shuttle_test_hazard_encryption_key',
        '--key-comment', 'Shuttle Test Hazard Archive Encryption Key',
        '--output-dir', test_area_dir,
        '--public-filename', 'shuttle_test_key_public.gpg',
        '--private-filename', 'shuttle_test_key_private.gpg'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Test encryption keys generated successfully")
        print(f"Public key: {test_key_public_path}")
        return True
    else:
        print(f"Warning: Failed to generate test keys: {result.stderr}")
        return False

def create_test_config_file(test_config_path, config_dir):
    """Create test configuration file"""
    if not test_config_path:
        print("SHUTTLE_TEST_CONFIG_PATH not set, skipping test config creation")
        return False
        
    test_config_dir = os.path.dirname(test_config_path)
    
    # Use the same helper function as above
    if not create_directory_with_sudo_if_needed(test_config_dir, "test config directory"):
        return False
    
    if os.path.exists(test_config_path):
        print(f"Overwriting existing test config file: {test_config_path}")
    else:
        print("Creating test configuration file...")
    
    # Generate test keys for encryption
    test_area_dir = os.path.dirname(test_config_path)  # Should be test_area
    test_key_public_path = os.path.join(test_area_dir, 'shuttle_test_key_public.gpg')
    
    # Generate test keys if they don't exist
    if not create_test_keys(test_area_dir):
        # Fall back to pointing to main config key if test key generation fails
        test_key_public_path = os.path.join(config_dir, 'shuttle_public.gpg')
    
    # Create test config with all booleans false
    # NOTE: Minimal paths section - only encryption key needed
    test_config = configparser.ConfigParser()
    
    # Settings with all booleans false
    test_config['settings'] = {
        'max_scan_threads': '1',
        'delete_source_files_after_copying': 'false',
        'defender_handles_suspect_files': 'false', 
        'on_demand_defender': 'false',
        'on_demand_clam_av': 'false',
        'throttle': 'false',
        'throttle_free_space_mb': '0'
    }
    
    # Logging settings
    test_config['logging'] = {
        'log_level': 'INFO'
    }
    
    # Scanning settings for tests - shorter timeouts
    test_config['scanning'] = {
        'malware_scan_timeout_seconds': '30',  # Shorter timeout for tests
        'malware_scan_timeout_ms_per_byte': '0.0',  # No per-byte timeout for tests
        'malware_scan_retry_wait_seconds': '5',  # Quick retries for tests
        'malware_scan_retry_count': '2'  # Fewer retries for tests
    }
    
    # Notifications disabled
    test_config['notifications'] = {
        'notify': 'false',
        'notify_summary': 'false',
        'use_tls': 'false'
    }
    
    # Minimal paths - only encryption key
    test_config['paths'] = {
        'hazard_encryption_key_path': test_key_public_path
    }
    
    # Define write function for the shared helper
    def write_test_config(file_path):
        with open(file_path, 'w') as configfile:
            test_config.write(configfile)
    
    # Use shared helper for file creation with sudo fallback
    return write_file_with_sudo_fallback(test_config_path, write_test_config)

def main():
    """Main function to handle modular configuration creation"""
    # Get required environment variables
    work_dir = get_required_env_var("SHUTTLE_TEST_WORK_DIR", "shuttle working directory")
    config_path = get_required_env_var("SHUTTLE_CONFIG_PATH", "shuttle configuration file")
    config_dir = os.path.dirname(config_path)

    # Parse command line arguments
    args = parse_arguments()
    
    # Check what operations to perform
    if not any([args.create_config, args.create_test_config, args.create_ledger, args.create_test_keys, args.all]):
        # Default behavior - create all
        args.all = True
    
    # Prepare directory paths (without creating them - installer handles that)
    paths = prepare_directory_paths(work_dir, config_dir, args)
    
    # Track what was created
    created_files = []
    
    # Perform requested operations
    if args.all or args.create_config:
        if create_config_file(config_path, args, paths, config_dir):
            created_files.append(f"Configuration: {config_path}")
    
    if args.all or args.create_ledger:
        if create_ledger_file(paths['ledger_file_path']):
            created_files.append(f"Ledger: {paths['ledger_file_path']}")
    
    if args.all or args.create_test_config:
        test_config_path = os.environ.get('SHUTTLE_TEST_CONFIG_PATH')
        if create_test_config_file(test_config_path, config_dir):
            created_files.append(f"Test config: {test_config_path}")
    
    if args.all or args.create_test_keys:
        test_config_path = os.environ.get('SHUTTLE_TEST_CONFIG_PATH')
        if test_config_path:
            test_area_dir = os.path.dirname(test_config_path)
            if create_test_keys(test_area_dir):
                created_files.append(f"Test keys: {test_area_dir}/shuttle_test_key_*.gpg")
    
    # Show summary
    if created_files:
        print("\nSetup complete!")
        print("\nFiles created:")
        for file_info in created_files:
            print(f"  {file_info}")
    else:
        print("\nNo new files created (all files already exist)")
    
    # Show directory summary (only if --all or no specific flags)
    if args.all:
        print("\nDirectories created:")
        print(f"  Work: {work_dir}")
        print(f"  Source: {paths['source_dir']}")
        print(f"  Quarantine: {paths['quarantine_dir']}")
        print(f"  Destination: {paths['dest_dir']}")
        print(f"  Hazard archive: {paths['hazard_archive_dir']}")
        print(f"  Logs: {paths['log_dir']}")

if __name__ == "__main__":
    main()