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
            
            # Add GID if specified
            if isinstance(group_info, dict) and 'gid' in group_info:
                cmd.extend(["--gid", str(group_info['gid'])])
            
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
            
            # Create user only if source is 'local' (new user)
            user_source = user.get('source', 'local')
            if user_source == 'local':
                if not self._create_local_user(user):
                    print(f"Error: Failed to create user {user_name}")
                    return False
            elif user_source == 'existing':
                print(f"  User already exists, skipping creation")
            elif user_source == 'domain':
                print(f"  Domain user reference, skipping local user creation")
            
            # Configure group memberships
            if not self._configure_user_groups(user):
                print(f"Warning: Failed to configure groups for {user_name}")
            
            # Configure user capabilities (executable access)
            if not self._configure_user_capabilities(user):
                print(f"Warning: Failed to configure capabilities for {user_name}")
            
            print()
        
        return True
    
    def _create_local_user(self, user: Dict[str, Any]) -> bool:
        """Create a local user"""
        user_name = user['name']
        cmd = [self.users_groups_script, "add-user", "--user", user_name]
        
        # Add shell configuration
        if 'shell' in user:
            cmd.extend(["--shell", user['shell']])
        
        # Add home directory configuration
        if 'home_directory' in user:
            cmd.extend(["--home", user['home_directory']])
        if user.get('create_home', False):
            cmd.append("--create-home")
        
        # Add user comment/description
        if 'description' in user:
            cmd.extend(["--comment", user['description']])
        
        return run_command(cmd, f"Create local user '{user_name}'", self.dry_run)
    
    def _configure_user_groups(self, user: Dict[str, Any]) -> bool:
        """Configure user group memberships"""
        user_name = user['name']
        groups_config = user.get('groups', {})
        success = True
        
        # Handle null groups config (means no changes)
        if groups_config is None:
            print(f"  Skipping all group changes for '{user_name}' (groups: null)")
            return True
        
        # Set primary group if specified (None means no change)
        primary_group = groups_config.get('primary')
        if primary_group is not None:
            cmd = [self.users_groups_script, "add-user-to-group", 
                   "--user", user_name, "--group", primary_group]
            if user.get('source') == 'domain':
                cmd.append("--domain")
            
            if not run_command(cmd, f"Add '{user_name}' to primary group '{primary_group}'", 
                              self.dry_run):
                print(f"Warning: Failed to add {user_name} to primary group")
                success = False
        else:
            print(f"  Skipping primary group change for '{user_name}' (primary: null)")
        
        # Handle secondary groups with new structured format
        secondary_config = groups_config.get('secondary')
        if secondary_config is None:
            print(f"  Skipping secondary group changes for '{user_name}' (secondary: null)")
        elif isinstance(secondary_config, dict):
            # New structured format - only support 'add' for safety
            if 'add' in secondary_config:
                # Add specific groups without removing existing ones
                groups_to_add = secondary_config['add']
                for group in groups_to_add:
                    cmd = [self.users_groups_script, "add-user-to-group", 
                           "--user", user_name, "--group", group]
                    if user.get('source') == 'domain':
                        cmd.append("--domain")
                    
                    if not run_command(cmd, f"Add '{user_name}' to group '{group}'", self.dry_run):
                        print(f"Warning: Failed to add {user_name} to group {group}")
                        success = False
            else:
                print(f"Warning: Unknown secondary group configuration for {user_name}: {secondary_config}")
        elif isinstance(secondary_config, list):
            # Legacy format - treat as additive for safety (was full replacement)
            if secondary_config:
                # Add groups individually to avoid removing existing groups
                for group in secondary_config:
                    cmd = [self.users_groups_script, "add-user-to-group", 
                           "--user", user_name, "--group", group]
                    if user.get('source') == 'domain':
                        cmd.append("--domain")
                    
                    if not run_command(cmd, f"Add '{user_name}' to group '{group}'", self.dry_run):
                        print(f"Warning: Failed to add {user_name} to group {group}")
                        success = False
        
        return success
    
    def _configure_user_capabilities(self, user: Dict[str, Any]) -> bool:
        """Configure user capabilities (executable access)"""
        user_name = user['name']
        capabilities = user.get('capabilities', {})
        executables = capabilities.get('executables', [])
        
        if not executables:
            return True
        
        print(f"  Configuring executable capabilities for {user_name}")
        
        # For now, we'll just report what executables the user should have access to
        # In a full implementation, this might:
        # 1. Add user to specific groups that have access to these executables
        # 2. Set up sudo rules for specific commands
        # 3. Configure PATH or create symlinks
        
        for executable in executables:
            print(f"    - Access to: {executable}")
        
        # Example: If user needs run-shuttle, add them to shuttle_app_users group
        if 'run-shuttle' in executables:
            if 'shuttle_app_users' not in user.get('groups', {}).get('secondary', []):
                print(f"    Note: Consider adding {user_name} to shuttle_app_users group for run-shuttle access")
        
        # Example: If user needs run-shuttle-defender-test, add them to shuttle_test_users group  
        if 'run-shuttle-defender-test' in executables:
            if 'shuttle_test_users' not in user.get('groups', {}).get('secondary', []):
                print(f"    Note: Consider adding {user_name} to shuttle_test_users group for run-shuttle-defender-test access")
        
        return True


def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config_file> <production_dir> [--dry-run] [--shuttle-config-path=PATH]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    production_dir = sys.argv[2]
    dry_run = "--dry-run" in sys.argv
    
    # Extract shuttle config path if provided
    shuttle_config_path = None
    for arg in sys.argv:
        if arg.startswith("--shuttle-config-path="):
            shuttle_config_path = arg.split("=", 1)[1]
            break
    
    # Set environment variable for path resolution if provided
    if shuttle_config_path:
        import os
        os.environ['SHUTTLE_CONFIG_PATH'] = shuttle_config_path
    
    manager = UserGroupManager(production_dir, dry_run)
    success = manager.process_config(config_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()