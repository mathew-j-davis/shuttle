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

# Standard Path Permissions - Single source of truth
# Uses the format from _apply_standard_path_permissions() which is more complete
STANDARD_PATH_PERMISSIONS = {
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
STANDARD_USER_TEMPLATES = {
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

# Standard Components Configuration
STANDARD_COMPONENTS = {
    'install_samba': True,
    'install_acl': True,
    'configure_users_groups': True,
    'configure_samba': True,
    'configure_firewall': True
}

def get_standard_groups():
    """Get a copy of standard groups configuration"""
    return STANDARD_GROUPS.copy()

def get_standard_path_permissions():
    """Get a copy of standard path permissions configuration"""
    import copy
    return copy.deepcopy(STANDARD_PATH_PERMISSIONS)

def get_standard_user_templates():
    """Get a copy of standard user templates configuration"""
    import copy
    return copy.deepcopy(STANDARD_USER_TEMPLATES)

def get_standard_components():
    """Get a copy of standard components configuration"""
    return STANDARD_COMPONENTS.copy()