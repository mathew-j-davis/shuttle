#!/usr/bin/env python3
"""
User and Group Manager
Manages user and group configuration from YAML
"""

import yaml
import sys
from typing import Dict, List, Any, Tuple

# Handle both relative and absolute imports
try:
    from .command_executor import run_command
    from .config_analyzer import analyze_config
except ImportError:
    from command_executor import run_command
    from config_analyzer import analyze_config


class UserGroupManager:
    """Manages user and group configuration"""
    
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
        Process user and group configuration from YAML file
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            True if successful, False otherwise
        """
        # Analyze configuration
        groups, users, settings = analyze_config(config_file)
        
        # Create groups first
        if groups and not self._create_groups(groups):
            return False
        
        # Process users
        if users and not self._process_users(users):
            return False
        
        print("Users and groups configuration complete")
        return True
    
    def _create_groups(self, groups: Dict[str, Any]) -> bool:
        """Create all groups"""
        print("Creating groups...")
        
        for group_name, group_info in groups.items():
            cmd = [self.users_groups_script, "add-group", "--group", group_name]
            if not run_command(cmd, f"Create group '{group_name}'", self.dry_run):
                print(f"Warning: Failed to create group {group_name}")
        
        print()
        return True
    
    def _process_users(self, users: List[Dict[str, Any]]) -> bool:
        """Process all users"""
        print("Processing users...")
        
        for user in users:
            user_name = user['name']
            print(f"Configuring user: {user_name}")
            
            # Create user if source is 'local'
            if user['source'] == 'local':
                if not self._create_local_user(user):
                    print(f"Error: Failed to create user {user_name}")
                    return False
            
            # Configure group memberships
            if not self._configure_user_groups(user):
                print(f"Warning: Failed to configure groups for {user_name}")
            
            print()
        
        return True
    
    def _create_local_user(self, user: Dict[str, Any]) -> bool:
        """Create a local user"""
        user_name = user['name']
        cmd = [self.users_groups_script, "add-user", "--user", user_name]
        
        if 'shell' in user:
            cmd.extend(["--shell", user['shell']])
        if 'home_directory' in user:
            cmd.extend(["--home", user['home_directory']])
        if user.get('create_home', False):
            cmd.append("--create-home")
        
        return run_command(cmd, f"Create local user '{user_name}'", self.dry_run)
    
    def _configure_user_groups(self, user: Dict[str, Any]) -> bool:
        """Configure user group memberships"""
        user_name = user['name']
        groups_config = user.get('groups', {})
        success = True
        
        # Set primary group if specified
        if 'primary' in groups_config:
            cmd = [self.users_groups_script, "add-user-to-group", 
                   "--user", user_name, "--group", groups_config['primary']]
            if user['source'] == 'domain':
                cmd.append("--domain")
            
            if not run_command(cmd, f"Add '{user_name}' to primary group '{groups_config['primary']}'", 
                              self.dry_run):
                print(f"Warning: Failed to add {user_name} to primary group")
                success = False
        
        # Add to secondary groups
        for group in groups_config.get('secondary', []):
            cmd = [self.users_groups_script, "add-user-to-group", 
                   "--user", user_name, "--group", group]
            if user['source'] == 'domain':
                cmd.append("--domain")
            
            if not run_command(cmd, f"Add '{user_name}' to secondary group '{group}'", self.dry_run):
                print(f"Warning: Failed to add {user_name} to group {group}")
                success = False
        
        return success


def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config_file> <production_dir> [--dry-run]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    production_dir = sys.argv[2]
    dry_run = "--dry-run" in sys.argv
    
    manager = UserGroupManager(production_dir, dry_run)
    success = manager.process_config(config_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()