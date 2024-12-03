import os
import random
import string
import configparser  # Added import for configparser

# Define directories
base_dir = os.path.expanduser("~/")
work_dir = os.path.expanduser("shuttlework/")
source_dir = os.path.join(base_dir, work_dir, "source")
quarantine_dir = os.path.join(base_dir, work_dir, "quarantine")
dest_dir = os.path.join(base_dir, work_dir, "destination")
log_dir = os.path.join(base_dir, work_dir, "logs")
settings_dir = os.path.join(base_dir, ".shuttle")
hazard_archive_dir = os.path.join(base_dir, work_dir, "HazardArchive")

settings_file = os.path.join(settings_dir, "settings.ini")

# Create directories if they don't exist
os.makedirs(source_dir, exist_ok=True)
os.makedirs(quarantine_dir, exist_ok=True)
os.makedirs(dest_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)
os.makedirs(settings_dir, exist_ok=True)
os.makedirs(hazard_archive_dir, exist_ok=True)

# Function to generate random content
def get_random_content(length=1000):
    return ''.join(random.choices(string.ascii_letters, k=length))

# Create text files with random content in the source directory
for filename in ['a.txt', 'b.txt', 'c.txt']:
    file_path = os.path.join(source_dir, filename)
    content = get_random_content()
    with open(file_path, 'w') as file:
        file.write(content)

# Create settings file using configparser
config = configparser.ConfigParser()

config['Paths'] = {
    'SourcePath': source_dir,
    'DestinationPath': dest_dir,
    'QuarantinePath': quarantine_dir,
    'LogPath': log_dir,
    'QuarantineHazardArchive': hazard_archive_dir
}

config['Settings'] = {
    'MaxScans': '4',
    'DeleteSourceFilesAfterCopying': 'True'
}

config['Logging'] = {
    'LogLevel': 'DEBUG'
}

with open(settings_file, 'w') as configfile:
    config.write(configfile)

# Output messages
print("Test environment setup complete:")
print(f"Source directory: {source_dir}")
print(f"Quarantine directory: {quarantine_dir}")
print(f"Destination directory: {dest_dir}")
print(f"Hazard archive directory: {hazard_archive_dir}")
print("Files created: a.txt, b.txt, c.txt in the source directory")
print(f"Settings file created: {settings_file}") 