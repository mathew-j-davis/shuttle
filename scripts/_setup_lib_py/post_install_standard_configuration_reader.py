#!/usr/bin/env python3
"""
Standard Configuration Definitions for Shuttle
Centralized source of truth for all standard groups, users, and path permissions
Now loads from YAML files with fallback to hardcoded Python dictionaries
"""

import os
import yaml
import copy
from typing import Dict, Any, Optional

# Path to YAML configuration files
YAML_CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'standard_configs')

# Cache for loaded YAML data
_yaml_cache = {}

def _load_yaml_config(filename: str) -> Optional[Dict[str, Any]]:
    """Load YAML configuration file with caching and error handling"""
    if filename in _yaml_cache:
        return _yaml_cache[filename]
    
    yaml_path = os.path.join(YAML_CONFIG_DIR, filename)
    try:
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
                _yaml_cache[filename] = data
                return data
        else:
            print(f"Warning: YAML config file not found: {yaml_path}")
            return None
    except Exception as e:
        print(f"Error loading YAML config {yaml_path}: {e}")
        return None

def _get_groups_from_yaml(environment: str) -> Optional[Dict[str, Any]]:
    """Load groups from YAML file for specified environment"""
    filename = f'standard_groups_{environment}.yaml'
    data = _load_yaml_config(filename)
    return data.get('groups') if data else None

def _get_users_from_yaml(environment: str) -> Optional[Dict[str, Any]]:
    """Load users from YAML file for specified environment"""
    filename = f'standard_users_{environment}.yaml'
    data = _load_yaml_config(filename)
    return data.get('users') if data else None

def _get_paths_from_yaml(environment: str) -> Optional[Dict[str, Any]]:
    """Load path templates from YAML file for specified environment"""
    filename = f'standard_paths_{environment}.yaml'
    data = _load_yaml_config(filename)
    if data and 'path_templates' in data:
        # Convert to the expected format
        path_data = data['path_templates']
        templates = path_data.get('templates', {})
        
        # Normalize templates to support both old and new formats
        normalized_templates = {}
        for template_name, template_config in templates.items():
            normalized_config = template_config.copy()
            
            # Convert new format (directory_mode/file_mode) to include compatibility fields
            if 'directory_mode' in template_config or 'file_mode' in template_config:
                # New format detected - add compatibility for bash script calls
                normalized_config['_has_separate_modes'] = True
                
                # For backward compatibility with existing code that expects 'mode'
                # Use directory_mode as the default 'mode' if no single mode exists
                if 'mode' not in template_config and 'directory_mode' in template_config:
                    normalized_config['mode'] = template_config['directory_mode']
            
            normalized_templates[template_name] = normalized_config
        
        return {
            environment: {
                'name': path_data.get('name', f'{environment.title()} Model'),
                'description': path_data.get('description', f'{environment.title()} permissions'),
                'category': path_data.get('category', 'standard'),
                'recommended': path_data.get('recommended', True),
                'templates': normalized_templates
            }
        }
    return None

def _get_samba_config_from_yaml() -> Optional[Dict[str, Any]]:
    """Load Samba configuration from YAML file"""
    data = _load_yaml_config('standard_samba_config.yaml')
    return data.get('samba') if data else None

def _get_firewall_config_from_yaml() -> Optional[Dict[str, Any]]:
    """Load firewall configuration from YAML file"""
    data = _load_yaml_config('standard_firewall_config.yaml')
    return data.get('firewall') if data else None

# Standard Groups - Simplified 3-group structure
STANDARD_GROUPS = {
    # Core groups (3 groups needed for basic operation)
    'shuttle_common_users': {
        'description': 'Read config, write logs, read ledger',
        'gid': 5001
    },
    'shuttle_owners': {
        'description': 'Own all data directories (source, quarantine, hazard, destination)',
        'gid': 5002
    },
    'shuttle_testers': {
        'description': 'Run tests',
        'gid': 5012
    },
    
    # Administrative group
    'shuttle_admins': {
        'description': 'Administrative users with full shuttle access',
        'gid': 5000
    },
    
    # Optional network access groups (for future use)
    'shuttle_samba_in_users': {
        'description': 'Inbound file submission via Samba (optional - future use)',
        'gid': 5020
    },
    'shuttle_out_users': {
        'description': 'Outbound file retrieval (optional - future use)',
        'gid': 5021
    }
}

# Note: Path permissions are now defined in PATH_PERMISSION_BASE_TEMPLATES below
# This eliminates duplication and provides a single source of truth

# Development User Templates - For development/testing environments
STANDARD_DEVELOPMENT_USER_TEMPLATES = {
    'shuttle_admin': {
        'name': 'shuttle_admin',
        'description': 'Development admin user with full access to all shuttle components',
        'category': 'admin',
        'recommended': True,
        'source': 'local',
        'groups': {
            'primary': 'shuttle_admins',
            'secondary': []
        },
        'shell': '/bin/bash',
        'home_directory': '/home/shuttle_admin',
        'create_home': True,
        'samba': {
            'enabled': False  # Can be enabled via prompt
        }
    }
}

# Production User Templates - Single source of truth
STANDARD_PRODUCTION_USER_TEMPLATES = {
    'shuttle_runner': {
        'name': 'shuttle_runner',
        'description': 'Main application service account - runs shuttle file processing',
        'category': 'core_services',
        'recommended': True,
        'source': 'local',
        'groups': {
            'primary': 'shuttle_owners',
            'secondary': ['shuttle_common_users']
        },
        'shell': '/usr/sbin/nologin',
        'home_directory': '/var/lib/shuttle/shuttle_runner',
        'create_home': True
        # Note: No individual path permissions needed - gets access via group membership
    },
    'shuttle_defender_test_runner': {
        'name': 'shuttle_defender_test_runner',
        'description': 'Defender testing service account - validates antivirus functionality',
        'category': 'core_services',
        'recommended': True,
        'source': 'local',
        'groups': {
            'primary': 'shuttle_common_users',
            'secondary': []
        },
        'shell': '/usr/sbin/nologin',
        'home_directory': '/var/lib/shuttle/shuttle_defender_test_runner',
        'create_home': True
        # Note: No individual path permissions needed - gets access via group membership
    },
    'shuttle_in_user': {
        'name': 'shuttle_in_user',
        'description': 'Samba user for uploading files to shuttle (inbound network access)',
        'category': 'network_services',
        'recommended': True,
        'source': 'local',
        'groups': {
            'primary': 'shuttle_samba_in_users',
            'secondary': []
        },
        'samba': {
            'enabled': True
        },
        'shell': '/usr/sbin/nologin',
        'home_directory': '/var/lib/shuttle/samba/shuttle_in_user',
        'create_home': True
        # Note: ACL permissions are defined in paths section, not here
    },
    'shuttle_out_user': {
        'name': 'shuttle_out_user',
        'description': 'Samba user for downloading processed files (outbound network access)',
        'category': 'network_services',
        'recommended': True,
        'source': 'local',
        'groups': {
            'primary': 'shuttle_out_users',
            'secondary': []
        },
        'samba': {
            'enabled': True
        },
        'shell': '/usr/sbin/nologin',
        'home_directory': '/var/lib/shuttle/samba/shuttle_out_user',
        'create_home': True
        # Note: ACL permissions are defined in paths section, not here
    },
    'shuttle_tester': {
        'name': 'shuttle_tester',
        'description': 'Interactive account for running shuttle test suites and development',
        'category': 'testing',
        'recommended': False,
        'source': 'local',
        'groups': {
            'primary': 'shuttle_testers',
            'secondary': []
        },
        'shell': '/bin/bash',
        'home_directory': '/home/shuttle_tester',
        'create_home': True
    },
    'shuttle_admin': {
        'name': 'shuttle_admin',
        'description': 'Administrative account with full access to all shuttle components',
        'category': 'admin',
        'recommended': False,
        'source': 'local',
        'groups': {
            'primary': None,
            'secondary': [
                'shuttle_common_users', 'shuttle_owners', 'shuttle_testers'
            ]
        },
        'shell': '/bin/bash',
        'home_directory': '/home/shuttle_admin',
        'create_home': True
    }
}

# Base components definition - used only in instruction template
_BASE_COMPONENTS = {
    'install_samba': True,
    'install_acl': True,
    'configure_users_groups': True,
    'configure_samba': True,
    'configure_firewall': True
}

# Standard Samba configuration
STANDARD_SAMBA_CONFIG = {
    'enabled': True,
    'shares': {
        'shuttle_inbound': {
            'path': '/var/shuttle/source',
            'comment': 'Shuttle inbound file submission',
            'read_only': False,
            'valid_users': '@shuttle_samba_in_users',
            'write_list': '@shuttle_samba_in_users',
            'create_mask': '0644',
            'directory_mask': '0755',
            'force_user': 'shuttle_runner',
            'force_group': 'shuttle_owners'
        },
        'shuttle_outbound': {
            'path': '/var/shuttle/destination',
            'comment': 'Shuttle processed file retrieval',
            'read_only': True,
            'valid_users': '@shuttle_out_users',
            'create_mask': '0644',
            'directory_mask': '0755'
        }
    },
    'global_settings': {
        'workgroup': 'WORKGROUP',
        'server_string': 'Shuttle File Transfer Server',
        'security': 'user',
        'map_to_guest': 'Bad User',
        'log_level': '1',
        'max_log_size': '1000',
        'encrypt_passwords': True,
        'unix_password_sync': False
    }
}

# Standard Firewall configuration
STANDARD_FIREWALL_CONFIG = {
    'enabled': True,
    'default_policy': {
        'incoming': 'deny',
        'outgoing': 'allow'
    },
    'logging': 'low',
    'rules': {
        'ssh_access': {
            'service': 'ssh',
            'action': 'allow',
            'sources': ['any'],  # Will be restricted in production
            'comment': 'SSH administrative access'
        },
        'samba_access': {
            'service': 'samba',
            'action': 'allow',
            'sources': [],  # To be configured based on network topology
            'comment': 'Samba file sharing access'
        }
    },
    'network_topology': {
        'management_networks': [],  # e.g., ['10.10.5.0/24', '192.168.100.0/24']
        'client_networks': [],      # e.g., ['192.168.1.0/24']
        'isolated_hosts': []        # e.g., ['10.10.1.100', '10.10.1.101']
    }
}

# Custom User Base Templates - For custom user creation
CUSTOM_USER_BASE_TEMPLATES = {
    'custom_service': {
        'name': '',  # To be filled by user
        'description': 'Custom service account',
        'category': 'custom',
        'recommended': True,
        'source': 'local',
        'groups': {'primary': None, 'secondary': []},
        'shell': '/usr/sbin/nologin',
        'home_directory': '/var/lib/shuttle/custom',
        'create_home': True,
        'samba': {'enabled': False}
    },
    'custom_interactive': {
        'name': '',
        'description': 'Custom interactive user account', 
        'category': 'custom',
        'recommended': True,
        'source': 'local',
        'groups': {'primary': None, 'secondary': []},
        'shell': '/bin/bash',
        'home_directory': '/home/custom',
        'create_home': True,
        'samba': {'enabled': False}
    },
    'custom_existing': {
        'name': '',
        'description': 'Existing user account',
        'category': 'custom', 
        'recommended': True,
        'source': 'existing',
        # Note: shell configuration is not needed for existing users - they already have them
        'groups': {'primary': None, 'secondary': []},
        # No shell/home defaults for existing users - they already have them
        'samba': {'enabled': False}
    }
}

# Standard mode configurations for different deployment types
STANDARD_MODE_CONFIGS = {
    'development': {
        'title': 'DEVELOPMENT MODE',
        'description': 'Creating a single admin user with full shuttle access.',
        'accept_prompt': 'Accept all development defaults? (Recommended for testing)',
        'success_message': 'Using all development defaults',
        'components': {
            'install_samba': True,
            'install_acl': True,
            'configure_users_groups': True,
            'configure_samba': True,
            'configure_firewall': False  # Disabled for development
        },
        'groups_function': 'get_development_admin_group',
        'users_function': '_create_default_admin_user',
        'paths_function': '_configure_development_paths',
        'firewall_default': False,
        'completion_message': 'Development mode configuration complete!',
        'completion_details': 'Added {user_count} user(s) to instructions\n   Access: Full administrative access to all shuttle components'
    },
    'production': {
        'title': 'PRODUCTION MODE',
        'description': 'Setting up standard production security model with standard groups, users and path permissions.',
        'accept_prompt': 'Accept all standard production defaults? (Recommended)',
        'success_message': 'Using all standard production defaults',
        'components': {
            'install_samba': True,
            'install_acl': True,
            'configure_users_groups': True,
            'configure_samba': True,
            'configure_firewall': True  # Enabled for production
        },
        'groups_function': 'get_standard_groups',
        'users_function': '_create_all_standard_roles_with_defaults',
        'paths_function': '_configure_paths_for_environment',
        'firewall_default': True,
        'completion_message': 'Standard mode configuration complete!',
        'completion_details': 'Added {user_count} users to instructions with production security model\n   Configured permissions for {path_count} paths in instructions'
    }
}

# Standard instruction template - base structure for main configuration document
STANDARD_INSTRUCTION_TEMPLATE = {
    'version': '1.0',
    'metadata': {
        'description': 'Shuttle post-install user configuration',
        'environment': 'production',
        'generated_by': 'Configuration Wizard'
        # 'created' will be added dynamically
    },
    'settings': {
        'create_home_directories': True,
        'backup_existing_users': True,
        'validate_before_apply': True
    },
    'components': _BASE_COMPONENTS.copy(),
    'samba': STANDARD_SAMBA_CONFIG.copy(),
    'firewall': STANDARD_FIREWALL_CONFIG.copy()
    # Note: groups, users, paths are separate collections that become separate YAML documents
}

def get_standard_groups(environment='production'):
    """Get a copy of standard groups configuration
    
    Args:
        environment: 'production', 'development', or 'user'
    
    Returns:
        Dictionary of groups configuration
    """
    # Try to load from YAML first
    yaml_groups = _get_groups_from_yaml(environment)
    if yaml_groups:
        return copy.deepcopy(yaml_groups)
    
    # Fallback to hardcoded Python dictionaries
    return STANDARD_GROUPS.copy()

def get_development_admin_group():
    """Get a copy of just the development admin group"""
    return {'shuttle_admins': STANDARD_GROUPS['shuttle_admins'].copy()}

def get_standard_samba_config():
    """Get a copy of standard Samba configuration"""
    # Try to load from YAML first
    yaml_samba = _get_samba_config_from_yaml()
    if yaml_samba:
        return copy.deepcopy(yaml_samba)
    
    # Fallback to hardcoded Python dictionary
    return STANDARD_SAMBA_CONFIG.copy()

def get_standard_firewall_config():
    """Get a copy of standard firewall configuration"""
    # Try to load from YAML first
    yaml_firewall = _get_firewall_config_from_yaml()
    if yaml_firewall:
        return copy.deepcopy(yaml_firewall)
    
    # Fallback to hardcoded Python dictionary
    return STANDARD_FIREWALL_CONFIG.copy()

# Note: get_standard_path_permissions() function removed
# Use get_path_permission_base_templates()[environment]['templates'] instead

def get_standard_user_templates(environment='production'):
    """Get a copy of standard user templates configuration for the specified environment
    
    Args:
        environment: 'production', 'development', or 'user'
        
    Returns:
        Deep copy of the appropriate user templates configuration
    """
    # Try to load from YAML first
    yaml_users = _get_users_from_yaml(environment)
    if yaml_users:
        return copy.deepcopy(yaml_users)
    
    # Fallback to hardcoded Python dictionaries
    if environment == 'development':
        return copy.deepcopy(STANDARD_DEVELOPMENT_USER_TEMPLATES)
    else:
        return copy.deepcopy(STANDARD_PRODUCTION_USER_TEMPLATES)

def get_standard_instruction_template():
    """Get a copy of standard instruction template with current timestamp"""
    import copy
    from datetime import datetime
    
    template = copy.deepcopy(STANDARD_INSTRUCTION_TEMPLATE)
    template['metadata']['created'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return template

def get_standard_mode_configs():
    """Get a copy of standard mode configurations"""
    import copy
    return copy.deepcopy(STANDARD_MODE_CONFIGS)

# Custom Group Base Templates - For custom group creation
CUSTOM_GROUP_BASE_TEMPLATES = {
    'custom_standard': {
        'description': 'Custom group for shuttle operations',
        'category': 'custom',
        'gid': None,  # Auto-assign
        'recommended': True
    },
    'custom_service': {
        'description': 'Service-specific operational group',
        'category': 'service',
        'gid': None,  # Auto-assign
        'recommended': True
    },
    'custom_data': {
        'description': 'Data access and management group',
        'category': 'data',
        'gid': None,  # Auto-assign
        'recommended': True
    },
    'custom_admin': {
        'description': 'Administrative privileges group',
        'category': 'admin',
        'gid': None,  # Auto-assign
        'recommended': False
    }
}

def get_custom_user_base_templates():
    """Get a copy of custom user base templates"""
    import copy
    return copy.deepcopy(CUSTOM_USER_BASE_TEMPLATES)

def get_custom_group_base_templates():
    """Get a copy of custom group base templates"""
    import copy
    return copy.deepcopy(CUSTOM_GROUP_BASE_TEMPLATES)

# Path Permission Base Templates - For template-driven path configuration
PATH_PERMISSION_BASE_TEMPLATES = {
    'production': {
        'name': 'Production Security Model',
        'description': 'Production-ready permissions with role-based access control',
        'category': 'standard',
        'recommended': True,
        'templates': {
            'source_path': {
                'owner': 'root',
                'group': 'shuttle_owners', 
                'mode': '2770',
                'acls': ['g:shuttle_samba_in_users:rwX'],
                'default_acls': {
                    'file': ['u::rw-', 'g::rw-', 'o::---'],
                    'directory': ['u::rwx', 'g::rwx', 'o::---']
                },
                'description': 'Inbound files with Samba upload access'
            },
            'destination_path': {
                'owner': 'root',
                'group': 'shuttle_owners',
                'mode': '2770', 
                'acls': ['g:shuttle_out_users:r-X'],
                'default_acls': {
                    'file': ['u::rw-', 'g::rw-', 'o::---'],
                    'directory': ['u::rwx', 'g::rwx', 'o::---']
                },
                'description': 'Processed files with Samba download access'
            },
            'quarantine_path': {
                'owner': 'root',
                'group': 'shuttle_owners',
                'mode': '2770',
                'default_acls': {
                    'file': ['u::rw-', 'g::rw-', 'o::---'],
                    'directory': ['u::rwx', 'g::rwx', 'o::---']
                },
                'description': 'Quarantine directory (shuttle process only)'
            },
            'hazard_archive_path': {
                'owner': 'root',
                'group': 'shuttle_owners',
                'mode': '2770',
                'default_acls': {
                    'file': ['u::rw-', 'g::rw-', 'o::---'],
                    'directory': ['u::rwx', 'g::rwx', 'o::---']
                },
                'description': 'Encrypted malware archive (restricted access)'
            },
            'log_path': {
                'owner': 'root',
                'group': 'shuttle_common_users',
                'mode': '2770',
                'description': 'Log files (common users write)'
            },
            'hazard_encryption_key_path': {
                'owner': 'root',
                'group': 'shuttle_common_users',
                'mode': '0640',
                'description': 'Encryption key (read-only for authorized users)'
            },
            'ledger_file_path': {
                'owner': 'shuttle_defender_tester',
                'group': 'shuttle_common_users',
                'mode': '0640',
                'description': 'Processing ledger file'
            },
            'test_work_dir': {
                'owner': 'root',
                'group': 'shuttle_testers',
                'mode': '0775',
                'description': 'Test work directory'
            },
            'test_config_path': {
                'owner': 'root',
                'group': 'shuttle_testers',
                'mode': '0664',
                'description': 'Test configuration file'
            }
        }
    },
    'development': {
        'name': 'Development/Testing Model',
        'description': 'Relaxed permissions for development and testing',
        'category': 'standard',
        'recommended': True,
        'templates': {
            '*': {
                'owner': 'root',
                'group': 'shuttle_admins',
                'mode': '2775',
                'acls': ['g:shuttle_admins:rwX'],
                'description': 'Full admin access for development'
            }
        }
    },
    'custom_secure': {
        'name': 'Custom Secure Template',
        'description': 'Starting point for custom secure configurations',
        'category': 'custom',
        'recommended': False,
        'templates': {
            'custom_path': {
                'owner': 'root',
                'group': 'root',
                'mode': '0755',
                'description': 'Basic secure configuration'
            }
        }
    },
    'custom_shared': {
        'name': 'Custom Shared Template',
        'description': 'Starting point for shared directory configurations',
        'category': 'custom', 
        'recommended': False,
        'templates': {
            'custom_path': {
                'owner': 'root',
                'group': 'root',
                'mode': '2775',
                'acls': [],
                'description': 'Shared directory with group write access'
            }
        }
    }
}

def get_path_permission_base_templates():
    """Get a copy of path permission base templates"""
    # Try to load from YAML files first
    result = {}
    
    # Load all three environments
    for env in ['production', 'development', 'user']:
        yaml_paths = _get_paths_from_yaml(env)
        if yaml_paths:
            result.update(yaml_paths)
    
    # If we got any YAML data, return it
    if result:
        return copy.deepcopy(result)
    
    # Fallback to hardcoded Python dictionaries
    return copy.deepcopy(PATH_PERMISSION_BASE_TEMPLATES)