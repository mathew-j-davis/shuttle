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
        
        # Use the secured user management script for Samba user creation
        cmd = [self.users_groups_script, "add-samba-user", "--user", user_name]
        
        # Add domain flag if applicable
        if user['source'] == 'domain':
            cmd.append("--domain")
        
        # Handle Samba configuration
        samba_config = user.get('samba', {})
        auth_method = samba_config.get('auth_method', 'smbpasswd')
        
        # Add password if provided and using smbpasswd method
        if auth_method == 'smbpasswd' and 'password' in samba_config:
            cmd.extend(["--password", samba_config['password']])
        
        # Add authentication method
        if auth_method == 'domain':
            cmd.append("--domain-auth")
        elif auth_method == 'smbpasswd':
            cmd.append("--smbpasswd-auth")
        
        if not run_command(cmd, f"Configure Samba user '{user_name}'", self.dry_run):
            print(f"Warning: Failed to configure Samba user {user_name}")
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
    
    manager = SambaManager(production_dir, dry_run)
    success = manager.process_config(config_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()