#!/usr/bin/env python3
"""
Permission Manager
Manages file and directory permissions from YAML configuration
"""

import yaml
import sys
from typing import Dict, List, Any

# Handle both relative and absolute imports
try:
    from .command_executor import run_command
except ImportError:
    from command_executor import run_command


class PermissionManager:
    """Manages file and directory permissions"""
    
    def __init__(self, production_dir: str, dry_run: bool = False):
        """
        Initialize the manager
        
        Args:
            production_dir: Path to production scripts directory
            dry_run: If True, only show what would be done
        """
        self.production_dir = production_dir
        self.dry_run = dry_run
        self.users_groups_script = f"{production_dir}/12_users_and_groups.sh"
    
    def process_config(self, config_file: str) -> bool:
        """
        Process permission configuration from YAML file
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            True if successful, False otherwise
        """
        users = self._parse_yaml_users(config_file)
        
        # Set permissions for each user
        permission_count = 0
        for user in users:
            count = self._set_user_permissions(user)
            permission_count += count
        
        if permission_count > 0:
            print(f"Processed {permission_count} permission settings")
        else:
            print("No permissions to set")
        
        print("File permissions configuration complete")
        return True
    
    def _parse_yaml_users(self, config_file: str) -> List[Dict[str, Any]]:
        """Parse YAML file and extract user definitions"""
        try:
            with open(config_file, 'r') as f:
                docs = list(yaml.safe_load_all(f))
            
            users = []
            for doc in docs:
                if doc and doc.get('type') == 'user':
                    users.append(doc['user'])
            
            return users
        except Exception as e:
            print(f"Error parsing YAML file {config_file}: {e}")
            return []
    
    def _set_user_permissions(self, user: Dict[str, Any]) -> int:
        """Set permissions for a single user"""
        user_name = user['name']
        permissions = user.get('permissions', {})
        
        if not permissions:
            return 0
        
        print(f"Setting permissions for user: {user_name}")
        permission_count = 0
        
        # Handle read-write permissions
        for perm in permissions.get('read_write', []):
            if self._set_single_permission(perm, user_name, 'read-write', '755'):
                permission_count += 1
        
        # Handle read-only permissions
        for perm in permissions.get('read_only', []):
            if self._set_single_permission(perm, user_name, 'read-only', '644'):
                permission_count += 1
        
        return permission_count
    
    def _set_single_permission(self, perm: Dict[str, Any], user_name: str, 
                              perm_type: str, default_mode: str) -> bool:
        """Set a single permission entry"""
        # Use the path directly from YAML (no resolution needed)
        actual_path = perm['path']
        mode = perm.get('mode', default_mode)
        success = True
        
        # Set ownership first if specified or if this is a user-specific permission
        owner = perm.get('owner', user_name)  # Default to user being configured
        group = perm.get('group', owner)      # Default group to same as owner
        
        if owner or group:
            owner_cmd = [self.users_groups_script, "set-path-owner", "--path", actual_path]
            if owner:
                owner_cmd.extend(["--user", owner])
            if group:
                owner_cmd.extend(["--group", group])
            if perm.get('recursive', False):
                owner_cmd.append("--recursive")
            
            desc = f"Set ownership of {actual_path} to {owner}:{group}"
            if perm.get('recursive', False):
                desc += " (recursive)"
            
            if not run_command(owner_cmd, desc, self.dry_run):
                print(f"Warning: Failed to set ownership on {actual_path}")
                success = False
        
        # Set permissions - handle both single mode and separate directory/file modes
        perm_cmd = [self.users_groups_script, "set-path-permissions", "--path", actual_path]
        
        # Check if this permission config has separate modes
        if perm.get('_has_separate_modes') and 'directory_mode' in perm and 'file_mode' in perm:
            # Use separate directory and file modes (always requires --recursive)
            perm_cmd.extend(["--dir-mode", perm['directory_mode']])
            perm_cmd.extend(["--file-mode", perm['file_mode']])
            perm_cmd.append("--recursive")
        else:
            # Use single mode (backward compatibility)
            perm_cmd.extend(["--mode", mode])
            # Add recursive flag if specified
            if perm.get('recursive', False):
                perm_cmd.append("--recursive")
        
        # Create appropriate description
        if perm.get('_has_separate_modes') and 'directory_mode' in perm and 'file_mode' in perm:
            desc = f"Set dir:{perm['directory_mode']}/file:{perm['file_mode']} permissions on {actual_path} (recursive)"
        else:
            desc = f"Set {mode} permissions on {actual_path}"
            if perm.get('recursive', False):
                desc += " (recursive)"
        
        if not run_command(perm_cmd, desc, self.dry_run):
            print(f"Warning: Failed to set permissions on {actual_path}")
            success = False
        
        return success


def main():
    """Main entry point for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage file and directory permissions from YAML configuration')
    parser.add_argument('config_file', help='Path to YAML configuration file')
    parser.add_argument('production_dir', help='Path to production scripts directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    manager = PermissionManager(args.production_dir, args.dry_run)
    success = manager.process_config(args.config_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()