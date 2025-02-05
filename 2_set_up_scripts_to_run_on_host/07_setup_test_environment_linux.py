#!python3

import os
import random
import string
import configparser  # Added import for configparser
import subprocess

# Define directories

work_dir = os.path.expanduser("~/shuttlework/")
source_dir = os.path.join(work_dir, "source")
quarantine_dir = os.path.join(work_dir, "quarantine")
dest_dir = os.path.join(work_dir, "destination")
log_dir = os.path.join(work_dir, "logs")
hazard_archive_dir = os.path.join(work_dir, "hazard")

settings_dir = os.path.expanduser("~/.shuttle")
settings_file = os.path.join(settings_dir, "settings.ini")
hazard_encryption_key_path = os.path.join(settings_dir, "hazard_public.gpg")

# Create directories if they don't exist
os.makedirs(source_dir, exist_ok=True)
os.makedirs(quarantine_dir, exist_ok=True)
os.makedirs(dest_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)
os.makedirs(settings_dir, exist_ok=True)
os.makedirs(hazard_archive_dir, exist_ok=True)

inner_dir = os.path.join(source_dir, 'inner/') 

# Create quarantine directory if it doesn't exist
os.makedirs(inner_dir, exist_ok=True)

# Function to generate random content
def get_random_content(length=1000):
    return ''.join(random.choices(string.ascii_letters, k=length))

# Create text files with random content in the source directory
for filename in ['a.txt', 'b.txt', 'c.txt']:
    file_path = os.path.join(source_dir, filename)
    content = get_random_content()
    with open(file_path, 'w') as file:
        file.write(content)


for filename in ['d.txt', 'e.txt', 'f.txt', 'FLAG_AS_MALWARE.txt']:
    file_path = os.path.join(inner_dir, filename)
    content = get_random_content()
    with open(file_path, 'w') as file:
        file.write(content)

# Create settings file using configparser
config = configparser.ConfigParser()

config['paths'] = {
    'source_path': source_dir,
    'destination_path': dest_dir,
    'quarantine_path': quarantine_dir,
    'log_path': log_dir,
    'hazard_archive_path': hazard_archive_dir,
    'hazard_encryption_key_path': hazard_encryption_key_path
}

config['settings'] = {
    'max_scan_threads': '1',
    'delete_source_files_after_copying': 'True'
}

config['logging'] = {
    'log_level': 'DEBUG'
}

with open(settings_file, 'w') as configfile:
    config.write(configfile)


    result = subprocess.run(
        [
            "mdatp",
            "exclusion",
            "folder",
            "add",
            "--path",
            source_dir,
            "--scope",
            "global"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

    print(result.stderr)
    print(result.stdout)

    if result.returncode == 0:
        print("Source folder excluded from automatic malware scan: {source_dir}")
    
    result = subprocess.run(
        [
            "mdatp",
            "exclusion",
            "folder",
            "add",
            "--path",
            quarantine_dir,
            "--scope",
            "global"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

    print(result.stderr)
    print(result.stdout)

    if result.returncode == 0:
        print("Quarantine folder excluded from automatic malware scan: {quarantine_dir}")

# Output messages
print("Test environment setup complete:")
print(f"Source directory: {source_dir}")
print(f"Quarantine directory: {quarantine_dir}")
print(f"Destination directory: {dest_dir}")
print(f"Hazard archive directory: {hazard_archive_dir}")
print("Files created: a.txt, b.txt, c.txt in the source directory")
print(f"Settings file created: {settings_file}") 