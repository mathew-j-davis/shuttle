import os
import random
import string

# Define directories
base_dir = os.path.expanduser("~/TestEnvironment")
source_dir = os.path.join(base_dir, "Source")
quarantine_dir = os.path.join(base_dir, "Quarantine")
dest_dir = os.path.join(base_dir, "Destination")
log_dir = os.path.join(base_dir, "Logs")
settings_dir = os.path.join(base_dir, ".shuttle")

settings_file = os.path.join(settings_dir, "settings.txt")

# Create directories if they don't exist
os.makedirs(source_dir, exist_ok=True)
os.makedirs(quarantine_dir, exist_ok=True)
os.makedirs(dest_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)
os.makedirs(settings_dir, exist_ok=True)

# Function to generate random content
def get_random_content(length=1000):
    return ''.join(random.choices(string.ascii_letters, k=length))

# Create text files with random content in the source directory
for filename in ['a.txt', 'b.txt', 'c.txt']:
    file_path = os.path.join(source_dir, filename)
    content = get_random_content()
    with open(file_path, 'w') as file:
        file.write(content)

# Create settings file
settings_content = f"""\
SourcePath={source_dir}
QuarantinePath={quarantine_dir}
DestinationPath={dest_dir}
LogPath={log_dir}
"""

with open(settings_file, 'w') as file:
    file.write(settings_content)

# Output messages
print("Test environment setup complete:")
print(f"Source directory: {source_dir}")
print(f"Quarantine directory: {quarantine_dir}")
print(f"Destination directory: {dest_dir}")
print("Files created: a.txt, b.txt, c.txt in the source directory")
print(f"Settings file created: {settings_file}")