#!/usr/bin/env python3
"""
Configuration Wizard Validation Module
Configuration validation and reference checking

This module contains validation functionality:
- User and group reference validation
- Path validation and safety checks
- Configuration consistency checking
- Missing reference detection
"""

import sys
from typing import Dict, List, Any, Optional, Set, Tuple

# Import safety constants from core module
from config_wizard_core import SAFE_PREFIXES, DANGEROUS_PATHS, DANGEROUS_PREFIXES

class ConfigWizardValidation:
    """Configuration validation and safety checking"""
    
    def _validate_group_name(self, group_name: str, check_users: bool = True) -> tuple[bool, str]:
        """Validate group name against rules and existing entities
        
        Returns:
            (is_valid, error_message)
        """
        if not group_name:
            return False, "Group name cannot be empty"
        
        if hasattr(self, 'groups') and group_name in self.groups:
            return False, f"Group '{group_name}' already exists"
        
        if check_users and hasattr(self, 'users'):
            # Check against existing usernames to avoid conflicts
            for user in self.users:
                if user['name'] == group_name:
                    return False, f"Group name '{group_name}' conflicts with existing username"
        
        # Add more validation rules (e.g., valid characters, length)
        if not group_name.replace('_', '').replace('-', '').isalnum():
            return False, "Group name must contain only letters, numbers, underscores, and hyphens"
        
        return True, ""
    
    def _validate_gid(self, gid: int, group_name: str = None) -> tuple[bool, str]:
        """Validate GID value and check for conflicts
        
        Returns:
            (is_valid, error_message)
        """
        if gid < 0:
            return False, "GID must be non-negative"
        
        # Check for GID conflicts
        if hasattr(self, 'groups'):
            for name, data in self.groups.items():
                if name != group_name and data.get('gid') == gid:
                    return False, f"GID {gid} already used by group '{name}'"
        
        # Warning for system GIDs
        if gid < 1000:
            return True, "WARNING: GID < 1000 is typically for system groups"
        
        return True, ""
    
    def _validate_user_name(self, user_name: str, check_groups: bool = True) -> tuple[bool, str]:
        """Validate user name against rules and existing entities
        
        Returns:
            (is_valid, error_message)
        """
        if not user_name:
            return False, "User name cannot be empty"
        
        if hasattr(self, 'users'):
            # Check against existing usernames
            for user in self.users:
                if user['name'] == user_name:
                    return False, f"User '{user_name}' already exists"
        
        if check_groups and hasattr(self, 'groups'):
            # Check against existing group names to avoid conflicts
            if user_name in self.groups:
                return False, f"User name '{user_name}' conflicts with existing group"
        
        # Add more validation rules
        if not user_name.replace('_', '').replace('-', '').isalnum():
            return False, "User name must contain only letters, numbers, underscores, and hyphens"
        
        # Check length
        if len(user_name) > 32:
            return False, "User name must be 32 characters or less"
        
        return True, ""
    
    def _validate_path_safety(self, path: str) -> tuple[str, str]:
        """
        Validate path safety and return status and message
        
        Returns:
            (status, message) where status is 'safe', 'warning', or 'dangerous'
        """
        # Check if path is dangerous
        if path in DANGEROUS_PATHS:
            return 'dangerous', f"Path '{path}' is a critical system path"
        
        for dangerous_prefix in DANGEROUS_PREFIXES:
            if path.startswith(dangerous_prefix):
                return 'dangerous', f"Path '{path}' is in dangerous system area '{dangerous_prefix}'"
        
        # Check for home directory dangers
        if path.startswith('/home/') and '/' in path[6:]:
            return 'warning', f"Path '{path}' modifies user home directory"
        
        # Check if path is in safe shuttle areas
        for safe_prefix in SAFE_PREFIXES:
            if path.startswith(safe_prefix):
                return 'safe', f"Path '{path}' is in safe shuttle area"
        
        # Default: outside shuttle areas but not dangerous
        return 'warning', f"Path '{path}' is outside standard shuttle directories"
    
    def _validate_all_paths(self) -> bool:
        """
        Validate all configured paths for safety
        
        Returns:
            True if all paths are safe to proceed, False if dangerous paths exist
        """
        if not hasattr(self, 'shuttle_paths'):
            return True
        
        dangerous_paths = []
        warning_paths = []
        
        # Check shuttle configuration paths
        for path_name, actual_path in self.shuttle_paths.items():
            status, message = self._validate_path_safety(actual_path)
            
            if status == 'dangerous':
                enhanced_message = f"Path '{path_name}' ({actual_path}) is a critical system path"
                dangerous_paths.append((actual_path, enhanced_message))
            elif status == 'warning':
                enhanced_message = f"Path '{path_name}' ({actual_path}) is outside standard shuttle directories"
                warning_paths.append((actual_path, enhanced_message))
        
        # Handle dangerous paths
        if dangerous_paths:
            print("\n🚨 CRITICAL WARNING: DANGEROUS SYSTEM PATHS DETECTED!")
            print("=" * 60)
            print("The following paths could break your operating system:")
            print("")
            for path, message in dangerous_paths:
                print(f"  ❌ {message}")
            print("")
            print("These paths CANNOT be used for shuttle configuration.")
            print("Please check your shuttle configuration file and fix these paths.")
            print("=" * 60)
            return False
        
        # Handle warning paths
        if warning_paths:
            print("\n⚠️  WARNING: Paths outside standard shuttle directories detected:")
            for path, message in warning_paths:
                print(f"  ⚠️  {message}")
            print("\nThese paths are not inherently dangerous but are outside typical shuttle areas.")
            print("Please ensure these are the correct paths for your installation.")
        
        return True
    
    def _validate_group_references(self) -> Set[str]:
        """Find groups referenced in users but not defined
        
        Returns:
            Set of missing group names
        """
        missing_groups = set()
        
        if not hasattr(self, 'users') or not hasattr(self, 'groups'):
            return missing_groups
        
        defined_groups = set(self.groups.keys())
        
        for user in self.users:
            # Check primary group
            primary_group = user.get('groups', {}).get('primary')
            if primary_group and primary_group not in defined_groups:
                missing_groups.add(primary_group)
            
            # Check secondary groups
            secondary_groups = user.get('groups', {}).get('secondary', [])
            for group in secondary_groups:
                if group not in defined_groups:
                    missing_groups.add(group)
        
        # Cache results for display purposes
        self._last_missing_groups = missing_groups
        return missing_groups
    
    def _validate_user_references(self) -> Set[str]:
        """Find users referenced in paths but not defined
        
        Returns:
            Set of missing user names (excluding standard system users)
        """
        missing_users = set()
        
        if not hasattr(self, 'paths') or not hasattr(self, 'users'):
            return missing_users
        
        # Standard system users that should not be flagged as missing
        standard_system_users = {
            'root', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp', 'mail',
            'news', 'uucp', 'proxy', 'www-data', 'backup', 'list', 'irc', 'gnats',
            'nobody', 'systemd-network', 'systemd-resolve', 'systemd-timesync',
            'messagebus', 'syslog', 'bind', 'avahi', 'colord', 'hplip', 'geoclue',
            'pulse', 'gdm', 'sshd'
        }
        
        defined_users = set(user['name'] for user in self.users)
        # Include standard system users as "defined"
        defined_users.update(standard_system_users)
        
        for path_config in self.paths.values():
            # Check owner
            owner = path_config.get('owner')
            if owner and owner not in defined_users:
                missing_users.add(owner)
            
            # Check ACL users
            acls = path_config.get('acls', [])
            for acl in acls:
                if acl.startswith('u:'):
                    # User ACL format: u:username:permissions
                    parts = acl.split(':')
                    if len(parts) >= 2 and parts[1] and parts[1] not in defined_users:
                        missing_users.add(parts[1])
        
        # Cache results for display purposes
        self._last_missing_users = missing_users
        return missing_users
    
    def _validate_configuration_before_customization(self):
        """Run validation checks and provide helpful guidance"""
        print("\n🔍 Validating configuration...")
        
        # Validate all paths for safety first
        print("🔍 Validating path safety...")
        if not self._validate_all_paths():
            print("❌ Configuration cancelled due to path safety concerns.")
            sys.exit(1)
        print("✅ Path validation complete")
        
        # Validate all referenced groups and users exist
        missing_groups = self._validate_group_references()
        missing_users = self._validate_user_references()
        
        if missing_groups or missing_users:
            print("\n⚠️  Configuration validation found missing references:")
            if missing_groups:
                print(f"   Missing groups: {', '.join(sorted(missing_groups))}")
            if missing_users:
                print(f"   Missing users: {', '.join(sorted(missing_users))}")
            print()
        else:
            print("✅ All user and group references are valid")
    
    def _validate_email_address(self, email: str) -> tuple[bool, str]:
        """Validate email address format
        
        Returns:
            (is_valid, error_message)
        """
        if not email:
            return False, "Email address cannot be empty"
        
        if '@' not in email:
            return False, "Email address must contain @ symbol"
        
        parts = email.split('@')
        if len(parts) != 2:
            return False, "Email address must have exactly one @ symbol"
        
        username, domain = parts
        if not username or not domain:
            return False, "Email address must have both username and domain parts"
        
        if '.' not in domain:
            return False, "Email domain must contain at least one dot"
        
        return True, ""
    
    def _validate_port_number(self, port: int) -> tuple[bool, str]:
        """Validate port number
        
        Returns:
            (is_valid, error_message)
        """
        if port < 1 or port > 65535:
            return False, "Port number must be between 1 and 65535"
        
        if port < 1024:
            return True, "WARNING: Port numbers below 1024 require root privileges"
        
        return True, ""
    
    def _validate_file_mode(self, mode: str) -> tuple[bool, str]:
        """Validate file mode (permissions) string
        
        Returns:
            (is_valid, error_message)
        """
        if not mode:
            return False, "File mode cannot be empty"
        
        # Remove leading '0' if present (octal notation)
        if mode.startswith('0'):
            mode = mode[1:]
        
        # Should be 3 or 4 digits
        if not mode.isdigit() or len(mode) < 3 or len(mode) > 4:
            return False, "File mode must be 3 or 4 octal digits (e.g., 644, 755, 0644)"
        
        # Each digit should be 0-7 (octal)
        for digit in mode:
            if not digit.isdigit() or int(digit) > 7:
                return False, "File mode digits must be 0-7 (octal notation)"
        
        return True, ""
    
    def _validate_acl_entry(self, acl: str) -> tuple[bool, str]:
        """Validate ACL entry format
        
        Returns:
            (is_valid, error_message)
        """
        if not acl:
            return False, "ACL entry cannot be empty"
        
        # Basic ACL format validation: type:name:permissions
        parts = acl.split(':')
        if len(parts) != 3:
            return False, "ACL entry must be in format 'type:name:permissions' (e.g., 'u:username:rwx')"
        
        acl_type, name, permissions = parts
        
        # Validate ACL type
        if acl_type not in ['u', 'g', 'o', 'm']:
            return False, "ACL type must be 'u' (user), 'g' (group), 'o' (other), or 'm' (mask)"
        
        # Validate permissions
        valid_perms = set('rwx-')
        if not all(p in valid_perms for p in permissions):
            return False, "ACL permissions must contain only 'r', 'w', 'x', or '-'"
        
        return True, ""
    
    @staticmethod
    def _validate_user_data(user_data: dict) -> tuple[bool, str]:
        """Validate user data structure and required fields
        
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(user_data, dict) or 'name' not in user_data:
            return False, "Invalid user data: must be dictionary with 'name' field"
        
        username = user_data['name']
        
        # Validate required fields
        required_fields = ['name', 'source', 'groups']
        # Shell is only required for new users (local source), not existing users who chose "no change"
        if user_data.get('source') == 'local':
            required_fields.append('shell')
        
        for field in required_fields:
            if field not in user_data:
                return False, f"User {username}: Missing required field '{field}'"
        
        return True, ""
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of current validation state"""
        missing_groups = self._validate_group_references()
        missing_users = self._validate_user_references()
        
        return {
            'missing_groups': list(missing_groups),
            'missing_users': list(missing_users),
            'has_validation_errors': len(missing_groups) > 0 or len(missing_users) > 0,
            'groups_count': len(getattr(self, 'groups', {})),
            'users_count': len(getattr(self, 'users', [])),
            'paths_count': len(getattr(self, 'paths', {}))
        }