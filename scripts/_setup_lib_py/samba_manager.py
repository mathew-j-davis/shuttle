#!/usr/bin/env python3
"""
Samba Manager
Manages Samba configuration from YAML
"""

import yaml
import sys
from typing import Dict, List, Any

# Handle both relative and absolute imports
try:
    from .command_executor import run_command
    from .config_analyzer import analyze_config
except ImportError:
    from command_executor import run_command
    from config_analyzer import analyze_config


class SambaManager:
    """Manages Samba configuration"""
    
    def __init__(self, production_dir: str, dry_run: bool = False, non_interactive: bool = False):
        """
        Initialize the manager
        
        Args:
            production_dir: Path to production scripts directory
            dry_run: If True, only show what would be done
            non_interactive: If True, skip operations requiring user input
        """
        self.production_dir = production_dir
        self.dry_run = dry_run
        self.non_interactive = non_interactive
        self.users_groups_script = f"{production_dir}/12_users_and_groups.sh"
        self.samba_script = f"{production_dir}/13_configure_samba.sh"
    
    def process_config(self, config_file: str) -> bool:
        """
        Process Samba configuration from YAML file
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            True if successful, False otherwise
        """
        # Analyze configuration
        groups, users, settings = analyze_config(config_file)
        
        # Find users with Samba enabled
        samba_users = []
        for user in users:
            if user.get('samba', {}).get('enabled', False):
                samba_users.append(user)
        
        if not samba_users:
            print("No Samba users configured")
            return True
        
        print(f"Configuring {len(samba_users)} Samba users...")
        
        for user in samba_users:
            self._configure_samba_user(user)
        
        print("Samba configuration complete")
        return True
    
    def _configure_samba_user(self, user: Dict[str, Any]) -> bool:
        """Configure Samba for a single user"""
        user_name = user['name']
        print(f"Configuring Samba for user: {user_name}")
        
        # Use the Samba script for Samba user creation
        cmd = [self.samba_script, "add-samba-user", "--user", user_name]
        
        # Handle Samba configuration
        samba_config = user.get('samba', {})
        auth_method = samba_config.get('auth_method', 'smbpasswd')
        
        # Check if password is provided for smbpasswd authentication
        if auth_method == 'smbpasswd':
            if 'password' not in samba_config:
                if self.non_interactive:
                    print(f"  Skipping Samba user '{user_name}' - no password provided in non-interactive mode")
                    print(f"  To configure manually: sudo smbpasswd -a {user_name}")
                    return True
                else:
                    # In interactive mode, let the script prompt for password
                    print(f"  No password provided for '{user_name}' - will prompt interactively")
            else:
                # Password provided, add it to command
                cmd.extend(["--password", samba_config['password']])
        
        # Add force flag to handle existing users
        cmd.append("--force")
        
        # Run command interactively if no password was provided and we're not in non-interactive mode
        interactive_command = (auth_method == 'smbpasswd' and 
                             'password' not in samba_config and 
                             not self.non_interactive)
        
        # Allow retry for interactive password setting
        max_attempts = 2 if interactive_command else 1
        for attempt in range(1, max_attempts + 1):
            if run_command(cmd, f"Configure Samba user '{user_name}'", self.dry_run, interactive=interactive_command):
                return True
            
            if attempt < max_attempts:
                print(f"  Password mismatch. Attempt {attempt} of {max_attempts} failed.")
                print(f"  Retrying password setup for user '{user_name}'...")
            else:
                print(f"Warning: Failed to configure Samba user {user_name} after {max_attempts} attempts")
                if interactive_command:
                    print(f"  To set password manually later: sudo smbpasswd -a {user_name}")
                return False
        
        # Provide additional guidance for domain authentication
        if auth_method == 'domain':
            print(f"  Domain authentication configured for {user_name}")
            print(f"    Domain users authenticate via domain controller")
            print(f"    Ensure machine is joined to domain")
        elif auth_method == 'smbpasswd' and 'password' not in samba_config:
            print(f"  Samba user created for {user_name}")
            print(f"    Set password manually: sudo smbpasswd {user_name}")
        
        return True


def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config_file> <production_dir> [--dry-run] [--non-interactive] [--shuttle-config-path=PATH]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    production_dir = sys.argv[2]
    dry_run = "--dry-run" in sys.argv
    non_interactive = "--non-interactive" in sys.argv
    
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
    
    manager = SambaManager(production_dir, dry_run, non_interactive)
    success = manager.process_config(config_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()