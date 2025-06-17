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
        
        # Add Samba user
        cmd = [self.samba_script, "add-samba-user", "--user", user_name]
        if user['source'] == 'domain':
            cmd.append("--domain")
        
        if not run_command(cmd, f"Add Samba user '{user_name}'", self.dry_run):
            print(f"Warning: Failed to add Samba user {user_name}")
            return False
        
        # Handle Samba authentication based on method
        samba_config = user.get('samba', {})
        auth_method = samba_config.get('auth_method', 'smbpasswd')
        
        if auth_method == 'smbpasswd':
            print(f"  Configuring smbpasswd authentication for {user_name}")
            if 'password' in samba_config:
                # Set the provided password
                cmd = [self.samba_script, "set-samba-password", 
                       "--user", user_name, "--password", samba_config['password']]
                if not run_command(cmd, f"Set Samba password for '{user_name}'", self.dry_run):
                    print(f"Warning: Failed to set Samba password for {user_name}")
                    return False
            else:
                print(f"    Password not provided - use: sudo smbpasswd {user_name}")
                
        elif auth_method == 'domain':
            print(f"  Configuring domain authentication for {user_name}")
            print(f"    Domain users authenticate via domain controller")
            print(f"    Ensure machine is joined to domain and smb.conf has:")
            print(f"      security = domain")
            print(f"      workgroup = YOUR_DOMAIN")
            # Domain users don't need smbpasswd - they use domain credentials
            
        elif auth_method == 'manual':
            print(f"  Samba user {user_name} enabled - manual configuration required")
            print(f"    To set password: sudo smbpasswd -a {user_name}")
            
        else:
            print(f"  Unknown auth method '{auth_method}' for {user_name} - skipping password setup")
        
        return True


def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <config_file> <production_dir> [--dry-run]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    production_dir = sys.argv[2]
    dry_run = "--dry-run" in sys.argv
    
    manager = SambaManager(production_dir, dry_run)
    success = manager.process_config(config_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()