#!python3

import os
import configparser
import yaml
import shutil
import subprocess

# Define directories


# Get directory paths from environment variables or use defaults
home_dir = os.path.expanduser("~")
work_dir = os.environ.get("SHUTTLE_WORK_DIR", os.path.join(home_dir, ".local/share/shuttle/work"))
config_path = os.environ.get("SHUTTLE_CONFIG_PATH", os.path.join(home_dir, ".config/shuttle/config.conf"))
config_dir = os.path.dirname(config_path)

# Set up working directories
source_dir = os.path.join(work_dir, "in")
quarantine_dir = os.path.join(work_dir, "quarantine")
dest_dir = os.path.join(work_dir, "out")
log_dir = os.path.join(work_dir, "logs")
ledger_file_dir = os.path.join(work_dir, "ledger")
hazard_archive_dir = os.path.join(work_dir, "hazard")

# Set up config files
settings_file = config_path
hazard_encryption_key_path = os.path.join(config_dir, "public-key.gpg")
ledger_file_path = os.path.join(ledger_file_dir, "ledger.yaml")


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

# Create subdirectory in source for organization
inner_dir = os.path.join(source_dir, 'inner/') 
os.makedirs(inner_dir, exist_ok=True)

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
            'max_scan_threads': '1',
            'delete_source_files_after_copying': 'True',
            'defender_handles_suspect_files': 'True',
            'on_demand_defender': 'False',
            'on_demand_clam_av': 'True',
            'throttle': 'False',
            'throttle_free_space': '10000'
        }

    config['logging'] = {
            'log_level': 'DEBUG'
        }

    config['notification'] = {
            'notify': 'False',
            'notify_summary': 'False',
            'recipient_email': 'admin@example.com',
            'sender_email': 'shuttle@yourdomain.com',
            'smtp_server': 'smtp.yourdomain.com', 
            'smtp_port': '587',
            'username': 'shuttle_notifications',
            'password': 'your_secure_password_here',
            'use_tls': 'True'
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