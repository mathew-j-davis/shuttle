# Extending Setup Script to Create Default Status File

## Overview

The existing `07_setup_test_environment_linux.py` script already:
1. Creates necessary directories for the Shuttle application
2. Sets up a default `settings.ini` file
3. Creates and defines the path to `status.ini`

We need to extend this script to also initialize a default `status.ini` file with the appropriate sections and default values. This ensures all environments have a consistently structured status file.

## Implementation Plan

### 1. Add Status File Creation Section

After the existing code that creates the `settings.ini` file, add a new section to create the `status.ini` file:

```python
# Create default status.ini file
print("Creating default status.ini file...")
status_config = configparser.ConfigParser()

# Defender section
status_config['defender'] = {
    'tested': 'false',
    'last_test_time': '',
    'test_result': '',
    'version_tested': '',
    'current_version': ''
}

# System section
status_config['system'] = {
    'ready': 'false',
    'last_startup': ''
}

# Throttling section
status_config['throttling'] = {
    'disk_space_verified': 'false'
}

# Write the status.ini file
with open(status_file_path, 'w') as configfile:
    status_config.write(configfile)
print(f"Created status file at {status_file_path}")
```

### 2. Add Version Detection (Optional)

If the system has Microsoft Defender installed, we can attempt to detect and record the current version:

```python
# Try to detect Microsoft Defender version
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '1_deployment', 'shuttle'))
    from defender_utils import get_mdatp_version
    
    version = get_mdatp_version()
    if version:
        print(f"Detected Microsoft Defender version: {version}")
        status_config['defender']['current_version'] = version
        
        # Re-write the status file with updated version
        with open(status_file_path, 'w') as configfile:
            status_config.write(configfile)
    else:
        print("Microsoft Defender not detected or version could not be determined")
except ImportError:
    print("Could not import defender_utils, skipping version detection")
except Exception as e:
    print(f"Error detecting Microsoft Defender version: {e}")
```

### 3. Add Permissions Check

Ensure the status file has appropriate permissions for both the application user and test user:

```python
# Set permissions on the status file
try:
    # Make sure the file is readable and writable by both application and test users
    subprocess.run(['chmod', '666', status_file_path], check=True)
    print(f"Set permissions on {status_file_path}")
except Exception as e:
    print(f"Warning: Could not set permissions on status file: {e}")
```

## Complete Implementation

The full implementation to add to the script would look like:

```python
#----------------------------------------
# Status File Setup
#----------------------------------------
print("\nSetting up status file...")

# Create default status.ini file
status_config = configparser.ConfigParser()

# Defender section
status_config['defender'] = {
    'tested': 'false',
    'last_test_time': '',
    'test_result': '',
    'version_tested': '',
    'current_version': ''
}

# System section
status_config['system'] = {
    'ready': 'false',
    'last_startup': ''
}

# Throttling section
status_config['throttling'] = {
    'disk_space_verified': 'false'
}

# Write the status.ini file
with open(status_file_path, 'w') as configfile:
    status_config.write(configfile)
print(f"Created status file at {status_file_path}")

# Try to detect Microsoft Defender version
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '1_deployment', 'shuttle'))
    from defender_utils import get_mdatp_version
    
    version = get_mdatp_version()
    if version:
        print(f"Detected Microsoft Defender version: {version}")
        status_config['defender']['current_version'] = version
        
        # Re-write the status file with updated version
        with open(status_file_path, 'w') as configfile:
            status_config.write(configfile)
    else:
        print("Microsoft Defender not detected or version could not be determined")
except ImportError:
    print("Could not import defender_utils, skipping version detection")
except Exception as e:
    print(f"Error detecting Microsoft Defender version: {e}")

# Set permissions on the status file
try:
    # Make sure the file is readable and writable by both application and test users
    subprocess.run(['chmod', '666', status_file_path], check=True)
    print(f"Set permissions on {status_file_path}")
except Exception as e:
    print(f"Warning: Could not set permissions on status file: {e}")
```

## Next Steps

After implementing this extension:

1. Test the script on a Linux environment to ensure it creates the status file correctly
2. Verify that both the application user and test user can read and write to the status file
3. Confirm that other components (shuttle application, defender test) can properly read/update the status file
4. Update documentation to reflect the new status file functionality

## Notes on Permission Management

Since the application and test will run under different users, proper permission management is crucial. Some alternatives to consider:

1. Use a group-based approach where both users belong to the same group
2. Consider using ACLs (Access Control Lists) for more fine-grained permission control
3. On production systems, evaluate if a more secure approach than `chmod 666` is needed
