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
    from .config_analyzer import analyze_config
    from .path_resolver import resolve_path
except ImportError:
    from command_executor import run_command
    from config_analyzer import analyze_config
    from path_resolver import resolve_path


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
        # Analyze configuration
        groups, users, settings = analyze_config(config_file)
        
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
            if self._set_single_permission(perm, 'read-write', '755'):
                permission_count += 1
        
        # Handle read-only permissions
        for perm in permissions.get('read_only', []):
            if self._set_single_permission(perm, 'read-only', '644'):
                permission_count += 1
        
        return permission_count
    
    def _set_single_permission(self, perm: Dict[str, Any], perm_type: str, 
                              default_mode: str) -> bool:
        """Set a single permission entry"""
        # Resolve symbolic path to actual path
        actual_path = resolve_path(perm['path'])
        mode = perm.get('mode', default_mode)
        
        cmd = [self.users_groups_script, "set-path-permissions", 
               "--path", actual_path, "--mode", mode]
        
        if perm.get('recursive', False):
            cmd.append("--recursive")
        
        desc = f"Set {mode} permissions on {actual_path}"
        if perm.get('recursive', False):
            desc += " (recursive)"
        
        if run_command(cmd, desc, self.dry_run):
            return True
        else:
            print(f"Warning: Failed to set permissions on {actual_path}")
            return False


def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config_file> <production_dir> [--dry-run]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    production_dir = sys.argv[2]
    dry_run = "--dry-run" in sys.argv
    
    manager = PermissionManager(production_dir, dry_run)
    success = manager.process_config(config_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()