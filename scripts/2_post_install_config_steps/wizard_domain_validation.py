#!/usr/bin/env python3

"""
Domain User Validation for Shuttle Configuration Wizard
Validates domain user requirements and guides configuration setup
"""

import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of domain user validation"""
    valid: bool
    error_type: Optional[str] = None
    message: Optional[str] = None
    required_action: Optional[str] = None


class WizardDomainUserValidator:
    """Validates domain user configuration requirements"""
    
    def __init__(self, config):
        self.config = config
        self.has_domain_users = False
        self.domain_config_exists = False
        self.domain_config_path = None
        
        # Patterns that indicate domain users
        self.domain_patterns = [
            r'.*\..*',      # Contains dot (alice.domain)
            r'.*@.*',       # Contains @ (alice@domain.com)
            r'.*\\.*',      # Contains backslash (DOMAIN\alice)
        ]
    
    def validate_domain_user_requirements(self):
        """Check if configuration requires domain users and if setup is ready"""
        
        # Check if any users are domain users
        self.has_domain_users, domain_users = self._detect_domain_users()
        
        if self.has_domain_users:
            print(f"🔍 Detected {len(domain_users)} potential domain users:")
            for user in domain_users:
                print(f"   • {user}")
            
            # Check for existing domain configuration
            self.domain_config_exists, self.domain_config_path = self._check_domain_config()
            
            if not self.domain_config_exists:
                return ValidationResult(
                    valid=False,
                    error_type="DOMAIN_CONFIG_MISSING",
                    message="Domain users configured but no domain import configuration found",
                    required_action="CONFIGURE_DOMAIN_IMPORT"
                )
            else:
                # Validate existing configuration
                if not self._validate_domain_config_file(self.domain_config_path):
                    return ValidationResult(
                        valid=False,
                        error_type="DOMAIN_CONFIG_INVALID",
                        message=f"Domain configuration file exists but is invalid: {self.domain_config_path}",
                        required_action="FIX_DOMAIN_CONFIG"
                    )
        
        return ValidationResult(valid=True)
    
    def _detect_domain_users(self) -> Tuple[bool, List[str]]:
        """Detect if any configured users appear to be domain users"""
        domain_users = []
        
        # Check users_to_create if it exists
        if hasattr(self.config, 'users') and hasattr(self.config.users, 'users_to_create'):
            for user in self.config.users.users_to_create:
                username = user.username if hasattr(user, 'username') else str(user)
                if self._is_domain_user(username):
                    domain_users.append(username)
        
        return len(domain_users) > 0, domain_users
    
    def _is_domain_user(self, username: str) -> bool:
        """Check if a username appears to be a domain user"""
        for pattern in self.domain_patterns:
            if re.match(pattern, username):
                return True
        return False
    
    def _check_domain_config(self) -> Tuple[bool, Optional[str]]:
        """Check for existing domain import configuration"""
        # Determine config base path
        config_base = getattr(self.config, 'config_base_path', '/etc/shuttle')
        
        config_paths = [
            f"{config_base}/domain_config.yaml",
            f"{config_base}/domain_import.conf",
            "/etc/shuttle/domain_config.yaml",
            "/etc/shuttle/domain_import.conf",
            f"{os.path.expanduser('~')}/.config/shuttle/domain_config.yaml",
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                return True, path
        
        return False, None
    
    def _validate_domain_config_file(self, config_path: str) -> bool:
        """Validate that domain config file contains required fields"""
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Check for required 'command' field
            # Support both key=value and key: value formats
            if re.search(r'^command\s*[=:]\s*\S+', content, re.MULTILINE):
                # Make sure it's not just 'cat' (template placeholder)
                command_match = re.search(r'^command\s*[=:]\s*(.+)$', content, re.MULTILINE)
                if command_match:
                    command = command_match.group(1).strip().strip('"\'')
                    if command == 'cat':
                        print(f"⚠️  Domain config uses 'cat' placeholder: {config_path}")
                        return False
                    return True
            
            return False
        except Exception as e:
            print(f"❌ Error reading domain config {config_path}: {e}")
            return False
    
    def get_domain_users(self) -> List[str]:
        """Get list of detected domain users"""
        _, domain_users = self._detect_domain_users()
        return domain_users


class DomainConfigurationHelper:
    """Helper for domain configuration management"""
    
    def __init__(self, config):
        self.config = config
    
    def create_domain_config_template(self, output_dir: str, config_name: str = "domain_import.conf") -> str:
        """Create domain configuration template with cat placeholder"""
        
        template_content = '''# Domain User Import Configuration Template
# 
# ⚠️  IMPORTANT: This is a template that must be configured before use!
# 
# INSTRUCTIONS:
# 1. Replace the 'cat' command below with your actual domain import command
# 2. Adjust the args_template for your environment
# 3. Test with: ./test_domain_import.sh
#
# EXAMPLES:
# command=sudo /opt/corporate/bin/import-domain-user
# command=sudo /usr/local/bin/ad-import-user
# command=python3 /opt/scripts/domain_import.py

# TODO: Replace 'cat' with your actual domain import command
command=cat

# TODO: Adjust arguments template for your domain import tool
# Available variables: {username}, {uid}, {home}, {shell}, {primary_group}, {groups}
args_template=--username {username} --home {home} --shell {shell} --primary-group {primary_group}

# Default settings (adjust as needed)
default_shell=/bin/bash
default_home_pattern=/home/{username}

# UID range (optional - remove if domain determines UIDs)
# uid_range_start=70000
# uid_range_end=99999

# NOTE: The 'cat' command above will simply echo the arguments passed to it.
# This allows testing the argument construction without actually importing users.
# Replace it with your real domain import command when ready.
'''
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        config_path = os.path.join(output_dir, config_name)
        with open(config_path, 'w') as f:
            f.write(template_content)
        
        return config_path
    
    def generate_domain_config_interactive(self, output_dir: str) -> str:
        """Generate domain configuration using the generate-domain-config command"""
        
        # Find the user management script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_script = os.path.join(script_dir, "12_users_and_groups.sh")
        
        if not os.path.exists(user_script):
            # Try relative path
            user_script = "./scripts/2_post_install_config_steps/12_users_and_groups.sh"
        
        cmd = [
            user_script,
            "generate-domain-config",
            "--output-dir", output_dir,
            "--interactive"
        ]
        
        try:
            print(f"🔧 Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, text=True, capture_output=True)
            
            # Domain config should be created at output_dir/domain_import.conf
            config_path = os.path.join(output_dir, "domain_import.conf")
            if os.path.exists(config_path):
                return config_path
            else:
                # Try other possible names
                for name in ["domain_config.yaml", "domain_import.conf"]:
                    path = os.path.join(output_dir, name)
                    if os.path.exists(path):
                        return path
                
                raise FileNotFoundError("Generated config file not found")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate domain configuration: {e}")
            print(f"   stderr: {e.stderr}")
            # Fallback to simple template
            return self.create_domain_config_template(output_dir)
        except FileNotFoundError:
            print(f"❌ Could not find user management script: {user_script}")
            # Fallback to simple template
            return self.create_domain_config_template(output_dir)
    
    def test_domain_configuration(self, config_path: str) -> bool:
        """Test domain configuration with a dry run"""
        
        # Find the user management script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_script = os.path.join(script_dir, "12_users_and_groups.sh")
        
        if not os.path.exists(user_script):
            user_script = "./scripts/2_post_install_config_steps/12_users_and_groups.sh"
        
        cmd = [
            user_script,
            "import-domain-user",
            "--username", "test.domain",
            "--command-config", config_path,
            "--dry-run", "--verbose"
        ]
        
        try:
            print(f"🧪 Testing configuration: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, text=True, capture_output=True)
            print("✅ Domain configuration test passed")
            print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Domain configuration test failed: {e}")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            return False
        except FileNotFoundError:
            print(f"❌ Could not find user management script: {user_script}")
            return False


def get_input(prompt: str, default: str = "", validator=None) -> str:
    """Get user input with validation"""
    while True:
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            if not response:
                response = default
        else:
            response = input(f"{prompt}: ").strip()
        
        if validator:
            error = validator(response)
            if error:
                print(f"❌ {error}")
                continue
        
        return response


def get_yes_no(prompt: str, default: bool = False) -> bool:
    """Get yes/no input from user"""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")


def get_choice(prompt: str, choices: List[Tuple[str, str]], default: str = None) -> str:
    """Get choice from user with list of options"""
    print(f"\n{prompt}")
    for i, (key, description) in enumerate(choices, 1):
        marker = " (default)" if key == default else ""
        print(f"  {i}. {description}{marker}")
    
    while True:
        try:
            response = input(f"\nEnter choice [1-{len(choices)}]: ").strip()
            if not response and default:
                return default
            
            choice_num = int(response) - 1
            if 0 <= choice_num < len(choices):
                return choices[choice_num][0]
            else:
                print(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("Please enter a valid number")


if __name__ == "__main__":
    # Test the domain validation
    print("Domain User Validation Test")
    
    # Mock config for testing
    class MockUser:
        def __init__(self, username):
            self.username = username
    
    class MockUsers:
        def __init__(self):
            self.users_to_create = [
                MockUser("alice.domain"),
                MockUser("bob"),
                MockUser("charlie@company.com"),
                MockUser("localuser")
            ]
    
    class MockConfig:
        def __init__(self):
            self.users = MockUsers()
            self.config_base_path = "/tmp/shuttle_test"
    
    config = MockConfig()
    validator = WizardDomainUserValidator(config)
    result = validator.validate_domain_user_requirements()
    
    print(f"Validation result: {result}")
    print(f"Domain users found: {validator.get_domain_users()}")