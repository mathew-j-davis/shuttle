#!/usr/bin/env python3
"""
Configuration Wizard Core Module
Core state management and configuration orchestration

This module contains the ConfigWizard class with core functionality:
- Initialization and state management
- Shuttle configuration loading
- Main orchestration methods
- YAML configuration generation and saving
"""

import yaml
import sys
import os
import datetime
from typing import Dict, List, Any, Optional, Set
import configparser
from post_install_config_constants import get_config_filename
from post_install_standard_configuration_reader import get_standard_instruction_template

# Safety validation constants
SAFE_PREFIXES = [
    '/var/shuttle/',
    '/etc/shuttle/', 
    '/var/log/shuttle/',
    '/opt/shuttle/',
    '/tmp/shuttle/',
    '/usr/local/bin/run-shuttle',
    '/usr/local/bin/run-shuttle-defender-test'
]

DANGEROUS_PATHS = [
    '/etc/passwd', '/etc/shadow', '/etc/group', '/etc/sudoers',
    '/usr/bin/', '/usr/sbin/', '/bin/', '/sbin/', '/lib/', '/boot/',
    '/dev/', '/proc/', '/sys/', '/root/',
    '/etc/systemd/', '/etc/ssh/', '/etc/fstab', '/etc/hosts'
]

DANGEROUS_PREFIXES = [
    '/usr/bin/', '/usr/sbin/', '/bin/', '/sbin/', '/lib/', '/boot/',
    '/dev/', '/proc/', '/sys/', '/etc/systemd/', '/etc/ssh/'
]

class ConfigWizardCore:
    """Core configuration wizard state and orchestration"""
    
    def __init__(self, shuttle_config_path=None, test_work_dir=None, test_config_path=None):
        """Initialize the configuration wizard with core state"""
        # Use standard instruction template as base for main document
        self.instructions = get_standard_instruction_template()
        
        # Remove nested collections - they should be separate documents
        self.groups = self.instructions.pop('groups', {})
        self.users = self.instructions.pop('users', [])
        self.paths = self.instructions.pop('paths', {})
        # Keep shuttle_paths separate - it's for path discovery/input
        self.shuttle_paths = {}
        
        # Get paths from environment or parameters
        self.shuttle_config_path = shuttle_config_path or os.getenv('SHUTTLE_CONFIG_PATH')
        self.test_work_dir = test_work_dir or os.getenv('SHUTTLE_TEST_WORK_DIR')
        self.test_config_path = test_config_path or os.getenv('SHUTTLE_TEST_CONFIG_PATH')
        
        # Load shuttle configuration to get actual paths
        self._load_shuttle_config()
    
    def _load_shuttle_config(self):
        """Load shuttle configuration to extract actual paths"""
        if not self.shuttle_config_path:
            print("ERROR: SHUTTLE_CONFIG_PATH environment variable not set and no config path provided")
            print("Either set SHUTTLE_CONFIG_PATH or pass --shuttle-config-path parameter")
            sys.exit(1)
        
        if not os.path.exists(self.shuttle_config_path):
            print(f"ERROR: Shuttle config file not found: {self.shuttle_config_path}")
            sys.exit(1)
        
        try:
            config = configparser.ConfigParser()
            config.read(self.shuttle_config_path)
            
            # Extract required paths
            required_paths = [
                'source_path', 'destination_path', 'quarantine_path', 
                'log_path', 'hazard_archive_path', 'hazard_encryption_key_path', 
                'ledger_file_path'
            ]
            
            for path_name in required_paths:
                # Check in main section and paths section
                path_value = None
                for section_name in ['main', 'paths', 'DEFAULT']:
                    if config.has_section(section_name) and config.has_option(section_name, path_name):
                        path_value = config.get(section_name, path_name)
                        break
                    elif section_name == 'DEFAULT' and config.has_option('DEFAULT', path_name):
                        path_value = config.get('DEFAULT', path_name)
                        break
                
                if not path_value:
                    print(f"ERROR: Required path '{path_name}' not found in shuttle config: {self.shuttle_config_path}")
                    sys.exit(1)
                
                self.shuttle_paths[path_name] = path_value
            
            # Add test paths if available
            if self.test_work_dir:
                self.shuttle_paths['test_work_dir'] = self.test_work_dir
            if self.test_config_path:
                self.shuttle_paths['test_config_path'] = self.test_config_path
            
            print(f"✅ Loaded shuttle configuration from: {self.shuttle_config_path}")
            print(f"Found {len(self.shuttle_paths)} path configurations")
            
        except Exception as e:
            print(f"ERROR: Failed to parse shuttle config: {e}")
            sys.exit(1)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get current wizard state summary"""
        return {
            'users_count': len(self.users),
            'groups_count': len(self.groups),
            'paths_count': len(self.paths),
            'shuttle_paths_count': len(self.shuttle_paths),
            'shuttle_config_path': self.shuttle_config_path,
            'test_work_dir': self.test_work_dir,
            'test_config_path': self.test_config_path
        }
    
    def _save_configuration(self) -> str:
        """Save the current configuration to a YAML file
        
        Returns:
            Path to the saved configuration file
        """
        # Generate configuration filename
        config_filename = get_config_filename()
        
        try:
            # Generate multi-document YAML
            yaml_content = self._generate_yaml_config()
            
            # Write to file
            with open(config_filename, 'w') as f:
                f.write(yaml_content)
            
            # Save filename for reference
            with open('/tmp/wizard_config_filename', 'w') as f:
                f.write(config_filename)
            
            print(f"✅ Configuration saved to: {config_filename}")
            return config_filename
            
        except Exception as e:
            print(f"❌ ERROR: Failed to save configuration: {e}")
            sys.exit(1)
    
    def _generate_yaml_config(self) -> str:
        """Generate multi-document YAML configuration"""
        documents = []
        
        # Document 1: Main configuration and metadata
        main_doc = self.instructions.copy()
        main_doc['metadata'] = {
            'description': f"{main_doc.get('metadata', {}).get('description', 'Shuttle Configuration')}",
            'environment': main_doc.get('metadata', {}).get('environment', 'production'),
            'created': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'generated_by': 'Configuration Wizard'
        }
        
        # Add groups to main document
        if self.groups:
            main_doc['groups'] = self.groups
        
        documents.append(main_doc)
        
        # Document N: Individual user configurations
        for user in self.users:
            user_doc = {
                'type': 'user',
                'user': user
            }
            documents.append(user_doc)
        
        # Final Document: Path permissions
        if self.paths:
            path_doc = {
                'type': 'paths',
                'paths': self.paths
            }
            documents.append(path_doc)
        
        # Generate YAML with document separators
        yaml_parts = []
        for i, doc in enumerate(documents):
            if i > 0:
                yaml_parts.append('---')
            yaml_parts.append(yaml.dump(doc, default_flow_style=False, sort_keys=False))
        
        return '\n'.join(yaml_parts)
    
    def validate_configuration(self) -> tuple[bool, List[str]]:
        """Validate the current configuration
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Basic validation
        if not self.groups and not self.users:
            errors.append("Configuration must have at least one group or user")
        
        # Validate paths exist
        for path_name, path_value in self.shuttle_paths.items():
            if not path_value:
                errors.append(f"Path '{path_name}' is empty")
        
        # Additional validation can be added here
        
        return len(errors) == 0, errors
    
    def get_configuration_counts(self) -> Dict[str, int]:
        """Get counts of configured items"""
        service_users = sum(1 for user in self.users if user.get('account_type') == 'service')
        interactive_users = sum(1 for user in self.users if user.get('account_type') == 'interactive')
        
        return {
            'groups': len(self.groups),
            'users': len(self.users),
            'service_users': service_users,
            'interactive_users': interactive_users,
            'paths': len(self.paths),
            'shuttle_paths': len(self.shuttle_paths)
        }
    
    def reset_configuration(self):
        """Reset the configuration to initial state"""
        self.instructions = get_standard_instruction_template()
        self.groups = self.instructions.pop('groups', {})
        self.users = self.instructions.pop('users', [])
        self.paths = self.instructions.pop('paths', {})
        print("✅ Configuration reset to initial state")
    
    def is_configuration_empty(self) -> bool:
        """Check if configuration is in initial/empty state"""
        return len(self.groups) == 0 and len(self.users) == 0 and len(self.paths) == 0