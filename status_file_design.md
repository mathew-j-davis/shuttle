# Status.ini Implementation Design

## Overview

We'll enhance the Shuttle application with a status tracking system that requires certain tests to pass before allowing file operations. This design focuses on implementing a `status.ini` file that will track whether critical system tests (like Defender functionality) have been verified.

## Components

### 1. Status File Structure

Create a `status.ini` file with sections for different system components:

```ini
[defender]
tested=false
last_test_time=
test_result=
version_tested=
current_version=

[system]
ready=false
last_startup=

[throttling]
disk_space_verified=false
```

### 2. Settings.ini Modification

Add a new parameter to `settings.ini` to specify the status file location:

```ini
[paths]
status_file=/path/to/status.ini
```

### 3. Configuration Update

Modify the `ShuttleConfig` class in `config.py` to include the status file path:

```python
@dataclass
class ShuttleConfig:
    # Existing fields...
    
    # Status file configuration
    status_file_path: Optional[str] = None
    require_defender_tested: bool = True  # Whether to enforce defender testing
```

### 4. Status File Manager

Create a new module `status_manager.py` to handle reading and writing to the status file:

```python
import os
import configparser
from datetime import datetime
import logging

class StatusManager:
    def __init__(self, status_file_path):
        self.status_file_path = status_file_path
        self.config = configparser.ConfigParser()
        self.logger = logging.getLogger('shuttle')
        
        # Create status file if it doesn't exist
        if status_file_path and not os.path.exists(status_file_path):
            self._create_default_status_file()
        elif status_file_path:
            self.config.read(status_file_path)
    
    def _create_default_status_file(self):
        """Create a default status file with initial values."""
        # Ensure sections exist
        self.config['defender'] = {
            'tested': 'false',
            'last_test_time': '',
            'test_result': '',
            'version_tested': '',
            'current_version': ''
        }
        
        self.config['system'] = {
            'ready': 'false',
            'last_startup': datetime.now().isoformat()
        }
        
        self.config['throttling'] = {
            'disk_space_verified': 'false'
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.status_file_path), exist_ok=True)
        
        # Write to file
        with open(self.status_file_path, 'w') as configfile:
            self.config.write(configfile)
    
    def get_defender_tested(self):
        """Check if defender has been tested."""
        if not self.status_file_path:
            return False
            
        try:
            # Check if tested flag is set
            if not self.config.getboolean('defender', 'tested', fallback=False):
                return False
                
            # Get current mdatp version
            current_version = self._get_mdatp_version()
            if not current_version:
                self.logger.error("Failed to get current mdatp version")
                return False
                
            # Update current version in status file
            self.config['defender']['current_version'] = current_version
            self._save_config()
                
            # Get version that was tested
            version_tested = self.config.get('defender', 'version_tested', fallback='')
            if not version_tested:
                self.logger.error("No tested version found in status file")
                return False
                
            # Compare versions
            if current_version != version_tested:
                self.logger.error(f"Current mdatp version {current_version} does not match tested version {version_tested}")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error reading defender tested status: {e}")
            return False
            
    def _get_mdatp_version(self):
        """Get the current mdatp version."""
        try:
            import subprocess
            result = subprocess.run(["mdatp", "version"], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"mdatp version command failed: {result.stderr}")
                return None
                
            # Parse the output to extract version number
            output = result.stdout
            import re
            match = re.search(r'Product version: ([\d\.]+)', output)
            if match:
                return match.group(1)
            else:
                self.logger.error(f"Could not parse mdatp version from output: {output}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting mdatp version: {e}")
            return None
            
    def _save_config(self):
        """Save the config to the status file."""
        if not self.status_file_path:
            return
            
        try:
            with open(self.status_file_path, 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            self.logger.error(f"Error saving status file: {e}")
    
    def set_defender_tested(self, tested, result=""):
        """Set the defender tested status."""
        if not self.status_file_path:
            return
            
        try:
            if 'defender' not in self.config:
                self.config['defender'] = {}
                
            self.config['defender']['tested'] = str(tested).lower()
            self.config['defender']['last_test_time'] = datetime.now().isoformat()
            self.config['defender']['test_result'] = result
            
            # Get and store current version if test passed
            if tested:
                version = self._get_mdatp_version()
                if version:
                    self.config['defender']['version_tested'] = version
                    self.config['defender']['current_version'] = version
                else:
                    self.logger.error("Failed to get mdatp version while setting test status")
                    # Don't set tested to true if we can't get version
                    self.config['defender']['tested'] = 'false'
            
            self._save_config()
        except Exception as e:
            self.logger.error(f"Error setting defender tested status: {e}")
```

### 5. Application Integration

Modify `shuttle.py` to check the defender tested status before proceeding:

```python
def main():
    # Existing initialization code...
    
    # Initialize status manager
    status_manager = None
    if config.status_file_path:
        from .status_manager import StatusManager
        status_manager = StatusManager(config.status_file_path)
    
    # Check if defender tests are required and have passed
    if (config.defender_scan and config.require_defender_tested and 
            status_manager and not status_manager.get_defender_tested()):
        # Get current and tested versions for logging
        current_version = "unknown"
        tested_version = "unknown"
        
        if status_manager and status_manager.config.has_section('defender'):
            current_version = status_manager.config.get('defender', 'current_version', fallback="unknown")
            tested_version = status_manager.config.get('defender', 'version_tested', fallback="unknown")
        
        if current_version != tested_version:
            logger.error(f"Microsoft Defender version mismatch. Current: {current_version}, Tested: {tested_version}")
            logger.error("Defender version has changed and requires re-testing.")
        else:
            logger.error("Defender scan is enabled but has not been verified by testing.")
            
        logger.error("Run the defender test script before using Shuttle.")
        return 1
    
    # Continue with normal operation...
```

### 6. Command Line Arguments

Add command line arguments to allow overriding the defender test requirement:

```python
parser.add_argument('-SkipDefenderTest', 
                    action='store_true',
                    help='Skip the defender test requirement (use with caution)')
```

## Implementation Steps

1. **Status Manager Module**:
   - Create `status_manager.py` with the StatusManager class
   - Implement read/write functions for status.ini

2. **Configuration Updates**:
   - Add status_file_path to ShuttleConfig
   - Add parser argument for status file path
   - Add require_defender_tested and override flag

3. **Defender Test Check**:
   - Modify main application entry point to verify defender test status
   - Add early exit if tests haven't been run

4. **Testing**:
   - Create test cases for StatusManager
   - Verify behavior with status file present/missing
   - Test behavior with defender tested true/false

## Security Considerations

- **Status File Access**: Ensure appropriate permissions on the status file
- **Override Protection**: Log when defender test checks are bypassed
- **Tampering Detection**: Consider adding a simple checksum to detect manual edits
- **Version Verification**: Block operation if Microsoft Defender version changes until re-testing occurs
- **Automatic Testing**: Consider automatic re-testing when version changes are detected

## Future Enhancements

1. **Web Dashboard**: Create a simple web interface to view status
2. **Multiple Test Tracking**: Extend to track other system tests
3. **Auto-Recovery**: Add functionality to automatically run tests that fail
4. **Notifications**: Send alerts when status changes or tests fail
