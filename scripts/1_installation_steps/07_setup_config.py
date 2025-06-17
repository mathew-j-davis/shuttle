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

# Get required environment variables
work_dir = get_required_env_var("SHUTTLE_TEST_WORK_DIR", "shuttle working directory")
config_path = get_required_env_var("SHUTTLE_CONFIG_PATH", "shuttle configuration file")
config_dir = os.path.dirname(config_path)

# Parse command line arguments
args = parse_arguments()

# Set up paths with defaults based on work_dir and config_dir
source_dir = args.source_path or os.path.join(work_dir, "in")
dest_dir = args.destination_path or os.path.join(work_dir, "out")
quarantine_dir = args.quarantine_path or os.path.join(work_dir, "quarantine")
log_dir = args.log_path or os.path.join(work_dir, "logs")
hazard_archive_dir = args.hazard_archive_path or os.path.join(work_dir, "hazard")
ledger_file_path = args.ledger_file_path or os.path.join(work_dir, "ledger", "ledger.yaml")
hazard_encryption_key_path = args.hazard_encryption_key_path or os.path.join(config_dir, "public-key.gpg")

# Derived paths
settings_file = config_path
ledger_file_dir = os.path.dirname(ledger_file_path)


# Create working directories if they don't exist
os.makedirs(work_dir, exist_ok=True)
os.makedirs(source_dir, exist_ok=True)
os.makedirs(quarantine_dir, exist_ok=True)
os.makedirs(dest_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)
os.makedirs(ledger_file_dir, exist_ok=True)
os.makedirs(hazard_archive_dir, exist_ok=True)

# Create config directory if it doesn't exist
os.makedirs(config_dir, exist_ok=True)

# Create config file if it doesn't exist
if not os.path.exists(settings_file):
    # Create new config file
    print("Creating new config file")
    config = configparser.ConfigParser()

    config['paths'] = {
            'source_path': source_dir,
            'destination_path': dest_dir,
            'quarantine_path': quarantine_dir,
            'log_path': log_dir,
            'hazard_archive_path': hazard_archive_dir,
            'hazard_encryption_key_path': hazard_encryption_key_path,
            'ledger_file_path': ledger_file_path
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

    with open(settings_file, 'w') as configfile:
        config.write(configfile)

print(f"Created settings file at {settings_file}")

# Create default ledger.yaml file
print("Creating default ledger.yaml file...")



# defender:
#   tested_versions:
#     - version: "101.12345.123"
#       test_time: "2025-05-09T10:30:00"
#       test_result: "pass"
#       test_details: "All detection tests passed"
#     - version: "101.12345.456"
#       test_time: "2025-05-01T14:22:00"
#       test_result: "pass" 
#       test_details: "All detection tests passed"

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

# Create test configuration file
test_config_path = os.environ.get('SHUTTLE_TEST_CONFIG_PATH')
if test_config_path:
    test_config_dir = os.path.dirname(test_config_path)
    os.makedirs(test_config_dir, exist_ok=True)
    
    print("Creating test configuration file...")
    
    # Generate test keys for encryption
    test_area_dir = os.path.dirname(test_config_path)  # Should be test_area
    test_key_public_path = os.path.join(test_area_dir, 'shuttle_test_key_public.gpg')
    
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
    else:
        print(f"Warning: Failed to generate test keys: {result.stderr}")
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
else:
    print("SHUTTLE_TEST_CONFIG_PATH not set, skipping test config creation")


# Setup complete
print("\nSetup complete!")

# Summary of setup
print("\nDirectories created:")
print(f"  Work: {work_dir}")
print(f"  Source: {source_dir}")
print(f"  Quarantine: {quarantine_dir}")
print(f"  Destination: {dest_dir}")
print(f"  Hazard archive: {hazard_archive_dir}")
print(f"  Logs: {log_dir}")
print(f"\nConfiguration: {settings_file}")
print(f"Ledger: {ledger_file_path}")