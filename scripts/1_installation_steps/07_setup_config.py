#!python3

import os
import argparse
import configparser
import yaml

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
    
    # Path arguments - use work_dir subdirectories as defaults
    parser.add_argument('--source-path', help='Path to the source directory (default: WORK_DIR/in)')
    parser.add_argument('--destination-path', help='Path to the destination directory (default: WORK_DIR/out)')
    parser.add_argument('--quarantine-path', help='Path to the quarantine directory (default: WORK_DIR/quarantine)')
    parser.add_argument('--log-path', help='Path to the log directory (default: WORK_DIR/logs)')
    parser.add_argument('--hazard-archive-path', help='Path to the hazard archive directory (default: WORK_DIR/hazard)')
    parser.add_argument('--ledger-file-path', help='Path to the ledger file (default: WORK_DIR/ledger/ledger.yaml)')
    parser.add_argument('--hazard-encryption-key-path', help='Path to the GPG public key file (default: CONFIG_DIR/public-key.gpg)')
    
    # Scanning configuration
    parser.add_argument('--max-scan-threads', type=int, default=1, help='Maximum number of parallel scans')
    parser.add_argument('--on-demand-defender', action='store_true', default=True, help='Use on-demand scanning for Microsoft Defender')
    parser.add_argument('--no-on-demand-defender', action='store_false', dest='on_demand_defender', help='Disable on-demand Microsoft Defender scanning')
    parser.add_argument('--on-demand-clam-av', action='store_true', default=False, help='Use on-demand scanning for ClamAV')
    parser.add_argument('--defender-handles-suspect-files', action='store_true', default=True, help='Let Microsoft Defender handle suspect files')
    parser.add_argument('--no-defender-handles-suspect-files', action='store_false', dest='defender_handles_suspect_files', help='Don\'t let Defender handle suspect files')
    
    # File processing options
    parser.add_argument('--delete-source-files-after-copying', action='store_true', default=True, help='Delete source files after copying')
    parser.add_argument('--no-delete-source-files-after-copying', action='store_false', dest='delete_source_files_after_copying', help='Keep source files after copying')
    
    # Throttling configuration
    parser.add_argument('--throttle', action='store_true', default=True, help='Enable throttling of file processing')
    parser.add_argument('--no-throttle', action='store_false', dest='throttle', help='Disable throttling')
    parser.add_argument('--throttle-free-space-mb', type=int, default=100, help='Minimum free space (in MB) required')
    
    # Logging configuration
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        help='Logging level')
    
    # Notification configuration
    parser.add_argument('--notify', action='store_true', default=False, help='Enable email notifications for errors')
    parser.add_argument('--notify-summary', action='store_true', default=False, help='Enable email notifications for summaries')
    parser.add_argument('--notify-recipient-email', default='admin@example.com', help='Email address for notifications')
    parser.add_argument('--notify-recipient-email-error', help='Email address for error notifications (defaults to notify-recipient-email)')
    parser.add_argument('--notify-recipient-email-summary', help='Email address for summary notifications (defaults to notify-recipient-email)')
    parser.add_argument('--notify-recipient-email-hazard', help='Email address for hazard notifications (defaults to notify-recipient-email)')
    parser.add_argument('--notify-sender-email', default='shuttle@yourdomain.com', help='Sender email address')
    parser.add_argument('--notify-smtp-server', default='smtp.yourdomain.com', help='SMTP server address')
    parser.add_argument('--notify-smtp-port', type=int, default=587, help='SMTP server port')
    parser.add_argument('--notify-username', default='shuttle_notifications', help='SMTP username')
    parser.add_argument('--notify-password', default='your_secure_password_here', help='SMTP password')
    parser.add_argument('--notify-use-tls', action='store_true', default=True, help='Use TLS for SMTP')
    
    return parser.parse_args()

def create_directories(work_dir, config_dir, args):
    """Create necessary directories for Shuttle operation"""
    source_dir = args.source_path or os.path.join(work_dir, "in")
    dest_dir = args.destination_path or os.path.join(work_dir, "out")
    quarantine_dir = args.quarantine_path or os.path.join(work_dir, "quarantine")
    log_dir = args.log_path or os.path.join(work_dir, "logs")
    hazard_archive_dir = args.hazard_archive_path or os.path.join(work_dir, "hazard")
    ledger_file_path = args.ledger_file_path or os.path.join(work_dir, "ledger", "ledger.yaml")
    ledger_file_dir = os.path.dirname(ledger_file_path)
    
    # Create working directories if they don't exist
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(quarantine_dir, exist_ok=True)
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(ledger_file_dir, exist_ok=True)
    os.makedirs(hazard_archive_dir, exist_ok=True)
    os.makedirs(config_dir, exist_ok=True)
    
    return {
        'source_dir': source_dir,
        'dest_dir': dest_dir,
        'quarantine_dir': quarantine_dir,
        'log_dir': log_dir,
        'hazard_archive_dir': hazard_archive_dir,
        'ledger_file_path': ledger_file_path,
        'ledger_file_dir': ledger_file_dir
    }

def create_config_file(config_path, args, paths, config_dir):
    """Create main Shuttle configuration file"""
    if os.path.exists(config_path):
        print(f"Configuration file already exists: {config_path}")
        return False
        
    print("Creating new config file")
    config = configparser.ConfigParser()
    
    hazard_encryption_key_path = args.hazard_encryption_key_path or os.path.join(config_dir, "public-key.gpg")

    config['paths'] = {
            'source_path': paths['source_dir'],
            'destination_path': paths['dest_dir'],
            'quarantine_path': paths['quarantine_dir'],
            'log_path': paths['log_dir'],
            'hazard_archive_path': paths['hazard_archive_dir'],
            'hazard_encryption_key_path': hazard_encryption_key_path,
            'ledger_file_path': paths['ledger_file_path']
        }

    config['settings'] = {
            'max_scan_threads': str(args.max_scan_threads),
            'delete_source_files_after_copying': str(args.delete_source_files_after_copying),
            'defender_handles_suspect_files': str(args.defender_handles_suspect_files),
            'on_demand_defender': str(args.on_demand_defender),
            'on_demand_clam_av': str(args.on_demand_clam_av),
            'throttle': str(args.throttle),
            'throttle_free_space_mb': str(args.throttle_free_space_mb)
        }

    config['logging'] = {
            'log_level': args.log_level
        }

    config['notification'] = {
            'notify': str(args.notify),
            'notify_summary': str(args.notify_summary),
            'recipient_email': args.notify_recipient_email,
            'recipient_email_error': args.notify_recipient_email_error or args.notify_recipient_email,
            'recipient_email_summary': args.notify_recipient_email_summary or args.notify_recipient_email,
            'recipient_email_hazard': args.notify_recipient_email_hazard or args.notify_recipient_email,
            'sender_email': args.notify_sender_email,
            'smtp_server': args.notify_smtp_server, 
            'smtp_port': str(args.notify_smtp_port),
            'username': args.notify_username,
            'password': args.notify_password,
            'use_tls': str(args.notify_use_tls)
        }

    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    print(f"Created settings file at {config_path}")
    return True

def create_ledger_file(ledger_file_path):
    """Create default ledger.yaml file"""
    if os.path.exists(ledger_file_path):
        print(f"Ledger file already exists: {ledger_file_path}")
        return False
        
    print("Creating default ledger.yaml file...")
    
    # Create YAML structure with empty tested_versions list
    status_data = {
        'defender': {
            'tested_versions': [],
            'current_version': ''
        }
    }

    # Write the ledger.yaml file
    with open(ledger_file_path, 'w') as yaml_file:
        yaml.dump(status_data, yaml_file, default_flow_style=False, sort_keys=False)

    print(f"Created ledger file at {ledger_file_path}")
    return True

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
        
    if os.path.exists(test_config_path):
        print(f"Test config file already exists: {test_config_path}")
        return False
        
    test_config_dir = os.path.dirname(test_config_path)
    os.makedirs(test_config_dir, exist_ok=True)
    
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
    
    # Write test config file
    with open(test_config_path, 'w') as configfile:
        test_config.write(configfile)
    
    print(f"Created test config file at {test_config_path}")
    return True

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
    
    # Create directories first
    paths = create_directories(work_dir, config_dir, args)
    
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