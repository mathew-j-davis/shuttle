#!/usr/bin/env python3
"""
Standard Configuration Definitions for Shuttle
Centralized source of truth for all standard groups, users, and path permissions
"""

# Standard Groups - Single source of truth
STANDARD_GROUPS = {
    'shuttle_config_readers': {
        'description': 'Read access to config, key, and ledger',
        'gid': 5001
    },
    'shuttle_data_owners': {
        'description': 'Owns all data directories',
        'gid': 5002
    },
    'shuttle_log_owners': {
        'description': 'Write access to logs',
        'gid': 5003
    },
    'shuttle_ledger_owners': {
        'description': 'Write access to ledger file',
        'gid': 5004
    },
    'shuttle_runners': {
        'description': 'Can execute shuttle applications',
        'gid': 5010
    },
    'shuttle_defender_test_runners': {
        'description': 'Can run defender testing',
        'gid': 5011
    },
    'shuttle_testers': {
        'description': 'Can run shuttle test suites',
        'gid': 5012
    },
    'shuttle_samba_in_users': {
        'description': 'Inbound file submission via Samba',
        'gid': 5020
    },
    'shuttle_samba_out_users': {
        'description': 'Outbound file retrieval via Samba',
        'gid': 5021
    }
}

# Development Path Permissions - Catch-all pattern for development environments
STANDARD_DEVELOPMENT_PATH_PERMISSIONS = {
    '*': {  # Catch-all pattern for any path
        'owner': 'root',
        'group': 'shuttle_admins',
        'mode': '2775',  # Group writable for development
        'acls': ['g:shuttle_admins:rwX'],  # Full access for admin group
        'description': 'Development access'  # Will be customized per path
    }
}

# Production Path Permissions - Specific configurations per path type
STANDARD_PRODUCTION_PATH_PERMISSIONS = {
    'source_path': {
        'owner': 'root',
        'group': 'shuttle_data_owners',
        'mode': '2770',
        'acls': ['g:shuttle_samba_in_users:rwX'],
        'default_acls': {
            'file': ['u::rw-', 'g::rw-', 'o::---'],
            'directory': ['u::rwx', 'g::rwx', 'o::---']
        },
        'description': 'Source directory (inbound files)'
    },
    'destination_path': {
        'owner': 'root',
        'group': 'shuttle_data_owners',
        'mode': '2770',
        'acls': ['g:shuttle_samba_out_users:r-X'],
        'default_acls': {
            'file': ['u::rw-', 'g::rw-', 'o::---'],
            'directory': ['u::rwx', 'g::rwx', 'o::---']
        },
        'description': 'Destination directory (processed files)'
    },
    'quarantine_path': {
        'owner': 'root',
        'group': 'shuttle_data_owners',
        'mode': '2770',
        'default_acls': {
            'file': ['u::rw-', 'g::rw-', 'o::---'],
            'directory': ['u::rwx', 'g::rwx', 'o::---']
        },
        'description': 'Quarantine directory (files being scanned)'
    },
    'hazard_archive_path': {
        'owner': 'root',
        'group': 'shuttle_data_owners',
        'mode': '2770',
        'default_acls': {
            'file': ['u::rw-', 'g::rw-', 'o::---'],
            'directory': ['u::rwx', 'g::rwx', 'o::---']
        },
        'description': 'Hazard archive (malware/suspect files)'
    },
    'log_path': {
        'owner': 'root',
        'group': 'shuttle_log_owners',
        'mode': '2770',
        'description': 'Log directory'
    },
    'hazard_encryption_key_path': {
        'owner': 'root',
        'group': 'shuttle_config_readers',
        'mode': '0640',
        'description': 'Encryption key'
    },
    'ledger_file_path': {
        'owner': 'root',
        'group': 'shuttle_config_readers',
        'mode': '0640',
        'acls': ['g:shuttle_ledger_owners:rw-'],
        'description': 'Ledger file'
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

# Standard User Templates - Single source of truth
STANDARD_PRODUCTION_USER_TEMPLATES = {
    'shuttle_runner': {
        'name': 'shuttle_runner',
        'source': 'local',
        'account_type': 'service',
        'groups': {
            'primary': 'shuttle_runners',
            'secondary': ['shuttle_config_readers', 'shuttle_data_owners', 'shuttle_log_owners']
        },
        'shell': '/usr/sbin/nologin',
        'home_directory': '/var/lib/shuttle/shuttle_runner',
        'create_home': True
        # Note: No individual path permissions needed - gets access via group membership
    },
    'shuttle_defender_test_runner': {
        'name': 'shuttle_defender_test_runner',
        'source': 'local',
        'account_type': 'service',
        'groups': {
            'primary': 'shuttle_defender_test_runners',
            'secondary': ['shuttle_config_readers', 'shuttle_log_owners', 'shuttle_ledger_owners']
        },
        'shell': '/usr/sbin/nologin',
        'home_directory': '/var/lib/shuttle/shuttle_defender_test_runner',
        'create_home': True
        # Note: No individual path permissions needed - gets access via group membership
    },
    'shuttle_in_user': {
        'name': 'shuttle_in_user',
        'source': 'local',
        'account_type': 'service',
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
        'source': 'local',
        'account_type': 'service',
        'groups': {
            'primary': 'shuttle_samba_out_users',
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
        'source': 'local',
        'account_type': 'interactive',
        'groups': {
            'primary': 'shuttle_testers',
            'secondary': ['shuttle_runners', 'shuttle_config_readers']
        },
        'shell': '/bin/bash',
        'home_directory': '/home/shuttle_tester',
        'create_home': True
    },
    'shuttle_admin': {
        'name': 'shuttle_admin',
        'source': 'local',
        'account_type': 'interactive',
        'groups': {
            'primary': None,
            'secondary': [
                'shuttle_config_readers', 'shuttle_data_owners', 'shuttle_log_owners',
                'shuttle_ledger_owners', 'shuttle_runners', 'shuttle_defender_test_runners'
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
    'enabled': True
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
        'description': 'Setting up standard production users and groups.',
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
    'components': _BASE_COMPONENTS.copy()
    # Note: groups, users, paths are separate collections that become separate YAML documents
}

def get_standard_groups():
    """Get a copy of standard groups configuration"""
    return STANDARD_GROUPS.copy()

def get_standard_path_permissions(environment='production'):
    """Get a copy of standard path permissions configuration for the specified environment
    
    Args:
        environment: 'production' or 'development'
        
    Returns:
        Deep copy of the appropriate path permissions configuration
    """
    import copy
    if environment == 'development':
        return copy.deepcopy(STANDARD_DEVELOPMENT_PATH_PERMISSIONS)
    else:
        return copy.deepcopy(STANDARD_PRODUCTION_PATH_PERMISSIONS)

def get_standard_user_templates():
    """Get a copy of standard user templates configuration"""
    import copy
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