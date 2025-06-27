#!/usr/bin/env python3
"""
Configuration Wizard
Interactive wizard to generate YAML configuration files

ENHANCED WITH THREE-TIER DEPLOYMENT MODES:

1. SIMPLE MODE
   - Single admin user with full access
   - Best for development/testing
   - Minimal security boundaries

2. STANDARD MODE  
   - Production security model
   - Service accounts, network users, proper isolation
   - Based on shuttle_simplified_security_model.md
   - Option to customize after standard setup

3. CUSTOM MODE
   - Full custom permission builder (future implementation)
   - Template assistance and guided setup
   - Import from standard model
   - Complete flexibility

Usage:
- Wizard automatically shows mode selection first
- Standard mode can be customized after initial setup
- All modes generate compatible YAML for permission_manager.py
"""

import yaml
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import configparser
from post_install_config_constants import get_config_filename
from standard_configs import (
    get_standard_groups, get_standard_path_permissions, 
    get_standard_user_templates, get_standard_components
)
from config_converters import convert_standard_to_old_format

# Safety validation constants
SAFE_PREFIXES = [
    '/var/shuttle/',
    '/etc/shuttle/', 
    '/var/log/shuttle/',
    '/opt/shuttle/',
    '/tmp/shuttle/',
    '/usr/local/bin/run-shuttle',
    '/usr/local/bin/run-shuttle-defender-test'
]

DANGEROUS_PATHS = [
    '/etc/passwd', '/etc/shadow', '/etc/group', '/etc/sudoers',
    '/usr/bin/', '/usr/sbin/', '/bin/', '/sbin/', '/lib/', '/boot/',
    '/dev/', '/proc/', '/sys/', '/root/',
    '/etc/systemd/', '/etc/ssh/', '/etc/fstab', '/etc/hosts'
]

DANGEROUS_PREFIXES = [
    '/usr/bin/', '/usr/sbin/', '/bin/', '/sbin/', '/lib/', '/boot/',
    '/dev/', '/proc/', '/sys/', '/etc/systemd/', '/etc/ssh/'
]


class ConfigWizard:
    """Interactive configuration wizard"""
    
    def __init__(self, shuttle_config_path=None, test_work_dir=None, test_config_path=None):
        self.config = {
            'version': '1.0',
            'metadata': {
                'description': 'Shuttle post-install user configuration',
                'environment': 'production',
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'generated_by': 'Configuration Wizard'
            },
            'settings': {
                'create_home_directories': True,
                'backup_existing_users': True,
                'validate_before_apply': True
            },
            'groups': {},
            'components': {
                'install_samba': True,
                'install_acl': True,
                'configure_users_groups': True,
                'configure_samba': True,
                'configure_firewall': True
            }
        }
        self.users = []
        self.shuttle_paths = {}
        
        # Get paths from environment or parameters
        self.shuttle_config_path = shuttle_config_path or os.getenv('SHUTTLE_CONFIG_PATH')
        self.test_work_dir = test_work_dir or os.getenv('SHUTTLE_TEST_WORK_DIR')
        self.test_config_path = test_config_path or os.getenv('SHUTTLE_TEST_CONFIG_PATH')
        
        # Load shuttle configuration to get actual paths
        self._load_shuttle_config()
    
    def _load_shuttle_config(self):
        """Load shuttle configuration to extract actual paths"""
        if not self.shuttle_config_path:
            print("ERROR: SHUTTLE_CONFIG_PATH environment variable not set and no config path provided")
            print("Either set SHUTTLE_CONFIG_PATH or pass --shuttle-config-path parameter")
            sys.exit(1)
        
        if not os.path.exists(self.shuttle_config_path):
            print(f"ERROR: Shuttle config file not found: {self.shuttle_config_path}")
            sys.exit(1)
        
        try:
            config = configparser.ConfigParser()
            config.read(self.shuttle_config_path)
            
            # Extract required paths
            required_paths = [
                'source_path', 'destination_path', 'quarantine_path', 
                'log_path', 'hazard_archive_path', 'hazard_encryption_key_path', 
                'ledger_file_path'
            ]
            
            for path_name in required_paths:
                # Check in main section and paths section
                path_value = None
                for section_name in ['main', 'paths', 'DEFAULT']:
                    if config.has_section(section_name) and config.has_option(section_name, path_name):
                        path_value = config.get(section_name, path_name)
                        break
                    elif section_name == 'DEFAULT' and config.has_option('DEFAULT', path_name):
                        path_value = config.get('DEFAULT', path_name)
                        break
                
                if not path_value:
                    print(f"ERROR: Required path '{path_name}' not found in shuttle config: {self.shuttle_config_path}")
                    sys.exit(1)
                
                self.shuttle_paths[path_name] = path_value
            
            # Add test paths if available
            if self.test_work_dir:
                self.shuttle_paths['test_work_dir'] = self.test_work_dir
            if self.test_config_path:
                self.shuttle_paths['test_config_path'] = self.test_config_path
            
            print(f"✅ Loaded shuttle configuration from: {self.shuttle_config_path}")
            print(f"Found {len(self.shuttle_paths)} path configurations")
            
        except Exception as e:
            print(f"ERROR: Failed to parse shuttle config: {e}")
            sys.exit(1)
        
    def run(self) -> Dict[str, Any]:
        """Run the interactive wizard"""
        print("\n=== Shuttle Configuration Wizard ===")
        print("This wizard will help you create a user setup configuration.")
        print("")
        
        # Select deployment mode first
        mode = self._select_deployment_mode()
        
        if mode == 'simple':
            return self._run_simple_mode()
        elif mode == 'standard':
            config = self._run_standard_mode()
            # Option to customize standard configuration
            if self._offer_customization():
                return self._run_custom_mode(base_config=config)
            return config
        else:  # custom
            return self._run_custom_mode()
    
    def _select_deployment_mode(self) -> str:
        """Select the deployment mode"""
        print("=== Deployment Mode Selection ===")
        print("Choose how you want to configure shuttle permissions:")
        print("")
        print("1) Simple - Single admin user with full access")
        print("   Best for: Development, testing, single-user systems")
        print("   Creates: One user with access to everything")
        print("")
        print("2) Standard - Production roles and security model")
        print("   Best for: Production systems, multiple users")
        print("   Creates: Service accounts, network users, proper isolation")
        print("")
        print("3) Custom - Build your own permission model")
        print("   Best for: Special requirements, complex environments")
        print("   Creates: Whatever you design")
        print("")
        
        choice = self._get_choice("Select deployment mode", ["1", "2", "3"], "2")
        
        mode_map = {
            "1": "simple",
            "2": "standard", 
            "3": "custom"
        }
        selected_mode = mode_map[choice]
        print(f"\n✅ Selected: {selected_mode.title()} Mode")
        return selected_mode
    
    def _run_simple_mode(self) -> Dict[str, Any]:
        """Run simple mode - single admin user"""
        print("\n=== SIMPLE MODE ===")
        print("Creating a single admin user with full shuttle access.")
        print("")
        
        # Basic environment setup
        self.config['metadata']['environment'] = 'development'
        self.config['metadata']['mode'] = 'simple'
        self.config['settings']['interactive_mode'] = 'interactive'
        
        # Component selection first
        self._simple_mode_components()
        
        # Create single admin group
        self.config['groups']['shuttle_admins'] = {
            'description': 'Administrative users with full shuttle access',
            'gid': 5000
        }
        
        # Get admin user details
        print("Admin User Configuration:")
        username = input("Enter admin username [shuttle_admin]: ").strip() or "shuttle_admin"
        
        user_type = self._get_user_type()
        
        # Create admin user with full permissions
        admin_user = {
            'name': username,
            'source': user_type,
            'account_type': 'admin',
            'groups': {
                'primary': 'shuttle_admins',
                'secondary': []
            },
            'permissions': {
                'read_write': [
                    {'path': path_name, 'mode': '755', 'recursive': True}
                    for path_name in self.shuttle_paths.keys()
                ]
            }
        }
        
        # Optional Samba access
        if self._confirm("Enable Samba access for admin user?", False):
            admin_user['samba'] = {
                'enabled': True,
                'auth_method': 'smbpasswd'
            }
            
        self.users.append(admin_user)
        
        print(f"\n✅ Simple mode configuration complete!")
        print(f"   Added user: {username} to instructions")
        print(f"   Access: Full administrative access to all shuttle components")
        
        return self._build_complete_config()
    
    def _run_standard_mode(self) -> Dict[str, Any]:
        """Run standard mode - production security model"""
        print("\n=== STANDARD PRODUCTION MODE ===")
        print("Setting up standard production users and groups.")
        print("")
        
        # Set production defaults
        self.config['metadata']['environment'] = 'production'
        self.config['metadata']['mode'] = 'standard'
        self.config['settings']['interactive_mode'] = 'non-interactive'
        
        # Component selection first
        self._standard_mode_components()
        
        # Create standard groups
        self._create_standard_groups()
        
        # Select and create standard roles
        self._select_and_create_standard_roles()
        
        # Configure path permissions
        self._configure_standard_paths()
            
        print(f"\n✅ Standard mode configuration complete!")
        print(f"   Added {len(self.users)} users to instructions with production security model")
        print(f"   Configured permissions for {len(self.shuttle_paths)} paths in instructions")
        
        return self._build_complete_config()
    
    def _offer_customization(self) -> bool:
        """Ask if user wants to customize standard configuration"""
        print("\n=== Customization Option ===")
        print("Your standard configuration is ready.")
        print("")
        print("Would you like to:")
        print("1) Use this configuration as-is")
        print("2) Customize this configuration")
        print("3) Start over")
        
        choice = self._get_choice("Select option", ["1", "2", "3"], "1")
        print()  # Add spacing between response and next section
        
        if choice == "2":
            print("\n✅ Entering customization mode...")
            return True
        elif choice == "3":
            print("\n↻ Restarting wizard...")
            return self.run()  # Restart
        else:
            print("\n✅ Using standard configuration")
            return False
    
    def _run_custom_mode(self, base_config=None) -> Dict[str, Any]:
        """Run custom mode - interactive builder"""
        if base_config:
            print("\n=== CUSTOM EDIT MODE ===")
            print("Customizing your standard configuration.")
            self.config = base_config[0]  # Load the main config
            self.users = [doc['user'] for doc in base_config[1:] if doc.get('type') == 'user']
            self.config['metadata']['mode'] = 'standard_customized'
        else:
            print("\n=== CUSTOM MODE ===")
            print("Building a custom permission model from scratch.")
            self.config['metadata']['mode'] = 'custom'
            # Set basic defaults
            self.config['metadata']['environment'] = 'custom'
            self.config['settings']['interactive_mode'] = 'interactive'
        
        print("")
        
        # Main custom mode loop
        while True:
            self._show_custom_menu()
            choice = self._get_choice("Select action", ["1", "2", "3", "4", "5", "6", "7", "d", "r", "s"], "1")
            print()  # Add spacing between response and next section
            
            if choice == "1":
                self._custom_manage_groups()
            elif choice == "2":
                self._custom_manage_users()
            elif choice == "3":
                self._custom_configure_path_permissions()
            elif choice == "4":
                self._custom_manage_components()
            elif choice == "5":
                self._custom_import_template()
            elif choice == "6":
                self._custom_show_configuration()
            elif choice == "7":
                self._custom_validate_configuration()
            elif choice == "d":
                # Delete configuration and return to main menu
                if self._confirm("Delete custom configuration and return to main menu?", False):
                    break
            elif choice == "r":
                # Reset configuration
                if self._confirm("Reset all configuration? This cannot be undone.", False):
                    self.config['groups'] = {}
                    self.config['paths'] = {}
                    self.users = []
                    print("✅ Configuration reset")
            elif choice == "s":
                # Save configuration and exit
                break
        
        # Return complete configuration
        return self._build_complete_config()
    
    def _select_environment(self):
        """Select deployment environment"""
        print("\n1. Select Environment")
        print("-------------------")
        print("1) Development - Interactive accounts for debugging")
        print("2) Testing - Mix of service and interactive accounts")
        print("3) Production - Service accounts, no shell access")
        
        choice = self._get_choice("Select environment", ["1", "2", "3"], "1")
        
        env_map = {
            "1": "development",
            "2": "testing",
            "3": "production"
        }
        self.config['metadata']['environment'] = env_map[choice]
    
    def _select_interactive_mode(self):
        """Select interactive mode preference for post-install configuration"""
        print("\n2. Interactive Mode Preference")
        print("-----------------------------")
        print("How would you like to run the post-install configuration?")
        print("")
        print("1) Interactive mode - Answer questions as the script runs")
        print("2) Non-interactive mode - Use defaults from this configuration file")
        print("3) Mixed mode - Interactive for critical decisions, defaults for others")
        
        choice = self._get_choice("Select mode", ["1", "2", "3"], "1")
        
        mode_map = {
            "1": "interactive",
            "2": "non-interactive",
            "3": "mixed"
        }
        self.config['settings']['interactive_mode'] = mode_map[choice]
        
        # Add additional settings based on mode
        if choice == "1":
            print("\nInteractive mode selected:")
            print("- You will be prompted for all configuration decisions")
            print("- Script will pause for your input at each step")
            self.config['settings']['prompt_for_passwords'] = True
            self.config['settings']['confirm_each_step'] = True
        elif choice == "2":
            print("\nNon-interactive mode selected:")
            print("- Script will use defaults from this configuration")
            print("- No prompts during execution (good for automation)")
            self.config['settings']['prompt_for_passwords'] = False
            self.config['settings']['confirm_each_step'] = False
        else:
            print("\nMixed mode selected:")
            print("- Critical decisions will prompt for input")
            print("- Non-critical steps will use defaults")
            self.config['settings']['prompt_for_passwords'] = True
            self.config['settings']['confirm_each_step'] = False
        
        # Ask about dry-run preference
        if self._confirm("\nEnable dry-run by default? (show what would be done without making changes)", False):
            self.config['settings']['dry_run_default'] = True
        else:
            self.config['settings']['dry_run_default'] = False
    
    def _select_components(self):
        """Select which components to install and configure"""
        print("\n3. Component Selection")
        print("--------------------")
        print("Choose which components to install and configure:")
        print("")
        
        # Package installation
        print("Package Installation:")
        self.config['components']['install_samba'] = self._confirm("  Install Samba?", True)
        self.config['components']['install_acl'] = self._confirm("  Install ACL tools?", True)
        print("")
        
        # Configuration steps
        print("Configuration Steps:")
        self.config['components']['configure_users_groups'] = self._confirm("  Configure users and groups?", True)
        
        if self.config['components']['install_samba']:
            self.config['components']['configure_samba'] = self._confirm("  Configure Samba settings?", True)
        else:
            self.config['components']['configure_samba'] = False
            
        self.config['components']['configure_firewall'] = self._confirm("  Configure firewall?", True)
        print("")
    
    def _select_user_approach(self):
        """Select user configuration approach"""
        print("\n4. User Configuration Approach")
        print("-----------------------------")
        print("1) Single user for all functions (simplest)")
        print("2) Separate users by function (most secure)")
        print("3) Custom configuration (advanced)")
        
        choice = self._get_choice("Select approach", ["1", "2", "3"], "1")
        
        if choice == "1":
            self._configure_single_user()
        elif choice == "2":
            self._configure_separate_users()
        else:
            self._configure_custom_users()
    
    def _configure_single_user(self):
        """Configure single user for all functions"""
        print("\n5. Single User Configuration")
        print("---------------------------")
        
        # User source
        user_source = self._select_user_source()
        
        # Username
        if user_source == "domain":
            username = input("Enter domain username (without domain prefix) [shuttle_service]: ").strip() or "shuttle_service"
            if self._confirm_domain_format():
                username = f"DOMAIN\\{username}"
        else:
            username = input("Enter username [shuttle_all]: ").strip() or "shuttle_all"
        
        # Account type (only relevant for new users)
        account_type = "service"
        if self.config['metadata']['environment'] == 'development':
            if user_source != "existing":
                # Only ask for new users where it actually matters
                print("\nAccount Type Selection")
                print("======================")
                print("Service accounts (recommended for Samba):")
                print("  - No shell access (/usr/sbin/nologin)")
                print("  - Can only connect via Samba from other machines")
                print("  - More secure for file sharing only")
                print("")
                print("Interactive accounts:")
                print("  - Full shell access (/bin/bash)")
                print("  - Can log in directly to this server")
                print("  - Needed only if user requires local login")
                print("")
                if self._confirm("Create interactive account with shell access?", False):
                    account_type = "interactive"
                else:
                    print("→ Creating service account (Samba access only)")
        
        # Create groups
        self.config['groups'] = {
            'shuttle_all_users': {
                'description': 'All shuttle functionality'
            },
            'shuttle_config_readers': {
                'description': 'Configuration file readers'
            }
        }
        
        # Create user
        user = {
            'name': username,
            'source': user_source,
            'account_type': account_type,
        }
        
        # Only set shell and home for non-existing users
        if user_source != "existing":
            user['shell'] = '/bin/bash' if account_type == 'interactive' else '/usr/sbin/nologin'
            user['home_directory'] = self._get_home_directory(username, account_type, user_source)
            user['create_home'] = True
        
        # Continue with groups and permissions
        user.update({
            'groups': {
                'primary': 'shuttle_all_users',
                'secondary': ['shuttle_config_readers']
            },
            'permissions': self._configure_path_permissions("Single User")
        })
        
        # Samba configuration
        print("\nEnable Samba Access for User")
        print("============================")
        if self.config['components']['configure_samba'] and self._confirm("Enable Samba access for this user?", True):
            user['samba'] = {'enabled': True}
            
            # Samba authentication method
            print("\nSamba authentication method:")
            print("1) Samba user database (smbpasswd) - separate Samba password")
            print("2) Domain security - use AD/domain authentication")
            print("3) Configure later (enable user, set password manually)")
            print("4) Show other options (PAM sync, Kerberos) - manual setup required")
            
            auth_choice = self._get_choice("Select authentication method", ["1", "2", "3", "4"], "1")
            
            if auth_choice == "1":
                # Traditional smbpasswd approach
                user['samba']['auth_method'] = 'smbpasswd'
                password = self._get_password("Enter Samba password")
                if password:
                    user['samba']['password'] = password
                    
            elif auth_choice == "2":
                # Domain security
                user['samba']['auth_method'] = 'domain'
                print("\nDomain security selected:")
                print("- Requires machine to be joined to domain")
                print("- Users authenticate against domain controller")
                print("- No separate Samba passwords needed")
                
            elif auth_choice == "3":
                # Configure later
                user['samba']['auth_method'] = 'manual'
                print("\nUser will be enabled for Samba but password must be set manually:")
                print("sudo smbpasswd -a {username}")
                
            elif auth_choice == "4":
                # Show other options but don't implement
                self._show_advanced_samba_options()
                # Default to manual configuration
                user['samba']['auth_method'] = 'manual'
        
        self.users.append(user)
    
    def _show_advanced_samba_options(self):
        """Show advanced Samba authentication options for manual setup"""
        print("\n" + "="*60)
        print("ADVANCED SAMBA AUTHENTICATION OPTIONS")
        print("="*60)
        print("These options require manual configuration outside this script:")
        print("")
        
        print("3. UNIX PASSWORD SYNC:")
        print("   - Synchronizes Samba and system passwords")
        print("   - Add to /etc/samba/smb.conf:")
        print("     unix password sync = yes")
        print("     pam password change = yes")
        print("   - Still requires: sudo smbpasswd -a <username>")
        print("")
        
        print("4. PAM AUTHENTICATION:")
        print("   - Uses system PAM stack for authentication")
        print("   - Add to /etc/samba/smb.conf:")
        print("     obey pam restrictions = yes")
        print("     pam password change = yes")
        print("   - Requires PAM configuration in /etc/pam.d/")
        print("")
        
        print("5. KERBEROS/ADS:")
        print("   - Full Active Directory integration with Kerberos")
        print("   - Add to /etc/samba/smb.conf:")
        print("     security = ads")
        print("     realm = YOURDOMAIN.COM")
        print("     kerberos method = secrets and keytab")
        print("   - Requires: kinit, proper DNS, time sync")
        print("")
        
        print("6. LDAP BACKEND:")
        print("   - Use LDAP directory for user/password storage")
        print("   - Requires separate LDAP server setup")
        print("   - Complex but highly scalable")
        print("")
        
        print("For detailed setup instructions, see:")
        print("- Samba Wiki: https://wiki.samba.org/")
        print("- Ubuntu Samba Guide: https://help.ubuntu.com/community/Samba")
        print("="*60)
        
        input("Press Enter to continue...")
    
    def _configure_path_permissions(self, user_role: str) -> Dict[str, List[Dict]]:
        """Configure path permissions for a user role"""
        print(f"\n{user_role} Path Permissions")
        print("=" * (len(user_role) + 17))
        print("Select which paths this user should have access to:")
        print("")
        print("Options:")
        print("  y/yes = Grant access")
        print("  n/no  = Don't grant access")
        print("  s/-   = Skip (don't modify existing permissions)")
        print("  x     = Exit wizard")
        print("")
        
        permissions = {'read_write': [], 'read_only': []}
        
        # Show available paths and ask for each one
        for path_name, path_value in self.shuttle_paths.items():
            print(f"{path_name}: {path_value}")
            
            rw_response = self._get_permission_choice(f"  Grant read/write access to {path_name}?", False)
            
            if rw_response == "yes":
                recursive = False
                if path_name in ['source_path', 'destination_path', 'quarantine_path', 'log_path', 'hazard_archive_path', 'test_work_dir']:
                    recursive = self._confirm(f"    Apply recursively to {path_name}?", True)
                
                mode = '755' if recursive else '644'
                perm_entry = {'path': path_value, 'mode': mode}
                if recursive:
                    perm_entry['recursive'] = True
                permissions['read_write'].append(perm_entry)
            
            elif rw_response == "no":
                # Ask about read-only access
                ro_response = self._get_permission_choice(f"  Grant read-only access to {path_name}?", 
                                                        path_name.endswith(('_config_path', '_key_path', '_file_path')))
                
                if ro_response == "yes":
                    permissions['read_only'].append({'path': path_value, 'mode': '644'})
                # If ro_response is "no" or "skip", we don't add any permissions
            
            # If rw_response is "skip", we don't ask about read-only and don't add any permissions
        
        return permissions
    
    def _configure_separate_users(self):
        """Configure separate users for each function"""
        print("\n5. Separate Users Configuration")
        print("-------------------------------")
        
        # Create groups
        self.config['groups'] = {
            'shuttle_app_users': {'description': 'Users who run shuttle application'},
            'shuttle_test_users': {'description': 'Users who run defender tests'},
            'shuttle_samba_users': {'description': 'Users who access via Samba'},
            'shuttle_config_readers': {'description': 'Users who can read config files'},
            'shuttle_ledger_writers': {'description': 'Users who can write to ledger'}
        }
        
        # Configure each user type
        if self._confirm("Configure Samba user?", True):
            self._add_samba_user()
        
        if self._confirm("Configure Shuttle application user?", True):
            self._add_shuttle_user()
        
        if self._confirm("Configure Defender test user?", True):
            self._add_test_user()
    
    def _add_samba_user(self):
        """Add Samba user configuration"""
        print("\nSamba User Configuration")
        
        user_source = self._select_user_source()
        username = self._get_username("Samba username", "samba_service", user_source)
        
        user = {
            'name': username,
            'source': user_source,
            'account_type': 'service',
            'groups': {
                'primary': 'shuttle_samba_users',
                'secondary': ['shuttle_config_readers']
            },
            'permissions': {
                'read_write': [
                    {'path': 'source_path', 'mode': '755'}
                ],
                'read_only': [
                    {'path': 'shuttle_config_path', 'mode': '644'}
                ]
            },
            'samba': {
                'enabled': True
            }
        }
        
        # Only set shell and home for non-existing users
        if user_source != "existing":
            user['shell'] = '/usr/sbin/nologin'
            user['home_directory'] = '/var/lib/shuttle/samba'
            user['create_home'] = True
        
        if self._confirm("Set Samba password now?", False):
            password = self._get_password("Enter Samba password")
            if password:
                user['samba']['password'] = password
        
        self.users.append(user)
    
    def _add_shuttle_user(self):
        """Add shuttle application user configuration"""
        print("\nShuttle Application User Configuration")
        
        user_source = self._select_user_source()
        username = self._get_username("Shuttle app username", "shuttle_app", user_source)
        
        user = {
            'name': username,
            'source': user_source,
            'account_type': 'service',
            'groups': {
                'primary': 'shuttle_app_users',
                'secondary': ['shuttle_config_readers', 'shuttle_ledger_writers']
            },
            'permissions': {
                'read_write': [
                    {'path': 'source_path', 'mode': '755'},
                    {'path': 'destination_path', 'mode': '755'},
                    {'path': 'quarantine_path', 'mode': '755'},
                    {'path': 'log_path', 'mode': '755'},
                    {'path': 'hazard_archive_path', 'mode': '755'},
                    {'path': 'ledger_file_path', 'mode': '644'}
                ],
                'read_only': [
                    {'path': 'hazard_encryption_key_path', 'mode': '644'},
                    {'path': 'shuttle_config_path', 'mode': '644'}
                ]
            }
        }
        
        # Only set shell and home for non-existing users
        if user_source != "existing":
            user['shell'] = '/usr/sbin/nologin'
            user['home_directory'] = '/var/lib/shuttle/app'
            user['create_home'] = True
        
        self.users.append(user)
    
    def _add_test_user(self):
        """Add defender test user configuration"""
        print("\nDefender Test User Configuration")
        
        user_source = self._select_user_source()
        username = self._get_username("Test user username", "defender_test", user_source)
        
        user = {
            'name': username,
            'source': user_source,
            'account_type': 'service',
            'groups': {
                'primary': 'shuttle_test_users',
                'secondary': ['shuttle_config_readers', 'shuttle_ledger_writers']
            },
            'permissions': {
                'read_write': [
                    {'path': 'test_work_dir', 'mode': '755', 'recursive': True},
                    {'path': 'ledger_file_path', 'mode': '644'}
                ],
                'read_only': [
                    {'path': 'hazard_encryption_key_path', 'mode': '644'},
                    {'path': 'shuttle_config_path', 'mode': '644'},
                    {'path': 'test_config_path', 'mode': '644'}
                ]
            }
        }
        
        # Only set shell and home for non-existing users
        if user_source != "existing":
            user['shell'] = '/usr/sbin/nologin'
            user['home_directory'] = '/var/lib/shuttle/test'
            user['create_home'] = True
        
        self.users.append(user)
    
    def _configure_custom_users(self):
        """Configure custom users"""
        print("\n5. Custom User Configuration")
        print("---------------------------")
        
        # Create default groups
        self.config['groups'] = {
            'shuttle_users': {'description': 'General shuttle users'},
            'shuttle_config_readers': {'description': 'Configuration file readers'}
        }
        
        while True:
            if not self._confirm("\nAdd a user?", True):
                break
            
            self._add_custom_user()
    
    def _add_custom_user(self):
        """Add a custom user interactively"""
        print("\nCustom User Configuration")
        
        # Basic info
        user_source = self._select_user_source()
        username = self._get_username("Username", "user", user_source)
        
        # Account type
        print("\nAccount type:")
        print("1) Service account (no shell)")
        print("2) Interactive account (shell access)")
        account_type_choice = self._get_choice("Select account type", ["1", "2"], "1")
        account_type = "service" if account_type_choice == "1" else "interactive"
        
        # Build user config
        user = {
            'name': username,
            'source': user_source,
            'account_type': account_type,
            'groups': {
                'primary': 'shuttle_users',
                'secondary': []
            },
            'permissions': {
                'read_write': [],
                'read_only': []
            }
        }
        
        # Only set shell and home for non-existing users
        if user_source != "existing":
            user['shell'] = '/bin/bash' if account_type == 'interactive' else '/usr/sbin/nologin'
            user['home_directory'] = self._get_home_directory(username, account_type, user_source)
            user['create_home'] = True
        
        # Groups
        if self._confirm("Add to config readers group?", True):
            user['groups']['secondary'].append('shuttle_config_readers')
        
        
        # Permissions (simplified)
        if self._confirm("Read/write access to source directory?", False):
            user['permissions']['read_write'].append({'path': 'source_path', 'mode': '755'})
        if self._confirm("Read/write access to test directory?", False):
            user['permissions']['read_write'].append({'path': 'test_work_dir', 'mode': '755', 'recursive': True})
        
        # Always add config read access
        user['permissions']['read_only'].append({'path': 'shuttle_config_path', 'mode': '644'})
        
        # Samba
        if self._confirm("Enable Samba access?", False):
            user['samba'] = {'enabled': True}
        
        self.users.append(user)
    
    def _select_user_source(self) -> str:
        """Select user source type"""
        print("\nUser source:")
        print("1) Existing user (any local or domain user already on this system)")
        print("2) New local user (create new local user)")
        print("3) Create new local configuration for a domain user (create reference to AD/LDAP user)")
        
        choice = self._get_choice("Select user source", ["1", "2", "3"], "1")
        source_map = {"1": "existing", "2": "local", "3": "domain"}
        return source_map[choice]
    
    def _get_username(self, prompt: str, default: str, source: str) -> str:
        """Get username with optional domain prefix"""
        username = input(f"{prompt} [{default}]: ").strip() or default
        
        if source == "domain" and self._confirm_domain_format():
            username = f"DOMAIN\\{username}"
        
        return username
    
    def _confirm_domain_format(self) -> bool:
        """Confirm if domain prefix should be added"""
        return self._confirm("Add DOMAIN\\ prefix to username?", True)
    
    def _get_password(self, prompt: str) -> Optional[str]:
        """Get password (with warning)"""
        print(f"\n{prompt}")
        print("WARNING: Password will be stored in YAML file!")
        print("Leave blank to set password later")
        
        import getpass
        password = getpass.getpass("Password: ").strip()
        if password:
            confirm = getpass.getpass("Confirm password: ").strip()
            if password != confirm:
                print("Passwords do not match!")
                return None
        return password if password else None
    
    def _confirm(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no confirmation"""
        # Always add default text for consistency
        default_text = "Yes" if default else "No"
        prompt = f"{prompt} (Default: {default_text})"
        
        default_str = "Y/n/x" if default else "y/N/x"
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        elif response == 'x':
            print("\nExiting wizard...")
            sys.exit(3)  # Exit code 3 for user cancellation
        return response in ['y', 'yes']
    
    # Standard Mode Helper Methods
    def _get_user_type(self) -> str:
        """Get user type for simple mode"""
        print("\nUser account type:")
        print("1) Local account - Create new local user")
        print("2) Existing account - Use existing local user")
        print("3) Domain account - Use domain/LDAP user")
        
        choice = self._get_choice("Select user type", ["1", "2", "3"], "1")
        
        type_map = {
            "1": "local",
            "2": "existing", 
            "3": "domain"
        }
        return type_map[choice]
    
    def _create_standard_groups(self):
        """Create standard production groups"""
        standard_groups = get_standard_groups()
        
        self.config['groups'].update(standard_groups)
        print(f"✅ Added {len(standard_groups)} standard groups to instructions")
    
    def _configure_standard_paths(self):
        """Configure path permissions for standard production mode"""
        print("\n--- Path Configuration ---")
        print("Configuring standard production path permissions...")
        
        # Get standard path permissions and convert to old format
        standard_configs = get_standard_path_permissions()
        path_configs = convert_standard_to_old_format(standard_configs)
        
        # Store path configurations in the global config
        if 'paths' not in self.config:
            self.config['paths'] = {}
        
        for path_config in path_configs:
            path_name = path_config['path']
            if path_name in self.shuttle_paths:
                actual_path = self.shuttle_paths[path_name]
                
                # Store the path configuration
                self.config['paths'][actual_path] = {
                    'description': path_config['description'],
                    'owner': path_config['owner'],
                    'group': path_config['group'],
                    'mode': path_config['mode']
                }
                
                # Add ACLs if specified
                if path_config['acls']:
                    self.config['paths'][actual_path]['acls'] = []
                    for acl in path_config['acls']:
                        acl_entry = f"{acl['type']}:{acl['name']}:{acl['perms']}"
                        self.config['paths'][actual_path]['acls'].append(acl_entry)
                
                print(f"✅ Configured {path_config['description']}")
        
        # Note: Service accounts (shuttle_runner, shuttle_defender_test_runner) get access
        # through group membership and don't need individual path permissions.
        # Only network users (Samba) need individual ACL permissions since they're not
        # in the directory ownership groups.
    
    def _select_and_create_standard_roles(self):
        """Select and create standard roles with integrated flow"""
        print("\nThe standard production pattern uses the following user roles:")
        print("")
        print("- Service accounts (shuttle_runner, defender_test_runner)")
        print("- Network users (samba_in_user, out_user)")
        print("- Test users (shuttle_tester)")
        print("- Admin users (interactive administrators)")
        print("")
        
        # Service Accounts
        if self._confirm("Create service accounts?", True):
            self._create_service_accounts()
        
        # Network Users
        if self._confirm("Create network users?", True):
            self._create_network_users()
        
        # Test Users
        if self._confirm("Create test users?", False):
            self._create_test_users()
        
        # Admin Users
        if self._confirm("Create admin users?", True):
            self._create_admin_users()
    
    def _create_service_accounts(self):
        """Create standard service accounts"""
        print("\n--- Service Accounts ---")
        
        # Shuttle Runner
        if self._confirm("Add shuttle_runner service account?", True):
            self.users.append({
                'name': 'shuttle_runner',
                'source': 'local',
                'account_type': 'service',
                'groups': {
                    'primary': 'shuttle_runners',
                    'secondary': [
                        'shuttle_config_readers',
                        'shuttle_data_owners',
                        'shuttle_log_owners'
                    ]
                },
                'shell': '/usr/sbin/nologin',
                'home_directory': '/var/lib/shuttle/shuttle_runner',
                'create_home': True
            })
            print("✅ Added shuttle_runner to instructions")
        
        # Defender Test Runner  
        if self._confirm("Add shuttle_defender_test_runner?", True):
            self.users.append({
                'name': 'shuttle_defender_test_runner',
                'source': 'local',
                'account_type': 'service', 
                'groups': {
                    'primary': 'shuttle_defender_test_runners',
                    'secondary': [
                        'shuttle_config_readers',
                        'shuttle_log_owners',
                        'shuttle_ledger_owners'
                    ]
                },
                'shell': '/usr/sbin/nologin',
                'home_directory': '/var/lib/shuttle/shuttle_defender_test_runner',
                'create_home': True
            })
            print("✅ Added shuttle_defender_test_runner to instructions")
    
    def _create_network_users(self):
        """Create standard network users"""
        print("\n--- Network Users ---")
        
        # Samba In User
        if self._confirm("Add shuttle_in_user (inbound)?", True):
            user = {
                'name': 'shuttle_in_user',
                'source': 'existing',  # Usually existing account
                'account_type': 'network',
                'groups': {
                    'primary': 'shuttle_samba_in_users',
                    'secondary': []
                },
                'samba': {
                    'enabled': True,
                    'auth_method': 'smbpasswd'
                },
                'shell': '/usr/sbin/nologin',
                'home_directory': '/var/lib/shuttle/samba/shuttle_in_user',
                'create_home': True
            }
            self.users.append(user)
            print("✅ Added shuttle_in_user to instructions")
        
        # Out User
        if self._confirm("Add shuttle_out_user (outbound)?", True):
            self.users.append({
                'name': 'shuttle_out_user',
                'source': 'domain',  # Usually domain account
                'account_type': 'network',
                'groups': {
                    'primary': 'shuttle_samba_out_users',
                    'secondary': []
                },
                'shell': '/usr/sbin/nologin',
                'home_directory': '/var/lib/shuttle/samba/shuttle_out_user',
                'create_home': True
            })
            print("✅ Added shuttle_out_user to instructions")
    
    def _create_test_users(self):
        """Create standard test users"""
        print("\n--- Test Users ---")
        
        if self._confirm("Add shuttle_tester?", True):
            self.users.append({
                'name': 'shuttle_tester',
                'source': 'local',
                'account_type': 'service',
                'groups': {
                    'primary': 'shuttle_testers',
                    'secondary': []
                },
                'shell': '/bin/bash',
                'home_directory': '/home/shuttle_tester',
                'create_home': True
            })
            print("✅ Added shuttle_tester to instructions")
    
    def _create_admin_users(self):
        """Create admin users"""
        print("\n--- Admin Users ---")
        
        username = input("Enter admin username [shuttle_admin]: ").strip() or "shuttle_admin"
        user_type = self._get_user_type()
        
        admin_user = {
            'name': username,
            'source': user_type,
            'account_type': 'admin',
            'groups': {
                'primary': 'shuttle_config_readers',
                'secondary': [
                    'shuttle_data_owners',
                    'shuttle_log_owners',
                    'shuttle_ledger_owners'
                ]
            },
            'shell': '/bin/bash',
            'home_directory': f'/home/{username}',
            'create_home': True
        }
        
        self.users.append(admin_user)
        print(f"✅ Added {username} to instructions")
    
    # Component Selection Methods
    def _simple_mode_components(self):
        """Component selection for simple mode with recommended defaults"""
        print("\n=== Component Selection ===")
        print("Select which components to install and configure:")
        print("")
        
        install_recommended = self._confirm("Install recommended components (Samba + ACL tools + Firewall)?", True)
        
        if install_recommended:
            print("✅ Using recommended component configuration")
            # Keep existing defaults (all True)
        else:
            print("\nCustom component selection:")
            self.config['components']['install_samba'] = self._confirm("  Install Samba (network file sharing)?", False)
            self.config['components']['install_acl'] = self._confirm("  Install ACL tools (advanced permissions)?", True)
            self.config['components']['configure_firewall'] = self._confirm("  Configure firewall settings?", False)
            
            if self.config['components']['install_samba']:
                self.config['components']['configure_samba'] = self._confirm("  Configure Samba settings?", True)
            else:
                self.config['components']['configure_samba'] = False
        
        print("")
    
    def _standard_mode_components(self):
        """Component selection for standard production mode"""
        print("\n=== Production Component Configuration ===")
        print("Configure system components for production environment:")
        print("")
        
        # Samba (network file sharing)
        print("🌐 Network File Sharing:")
        self.config['components']['install_samba'] = self._confirm("  Install Samba for network file access?", True)
        if self.config['components']['install_samba']:
            self.config['components']['configure_samba'] = self._confirm("  Configure Samba users and shares?", True)
        else:
            self.config['components']['configure_samba'] = False
        print("")
        
        # ACL tools (advanced permissions)
        print("🔒 Advanced Permissions:")
        self.config['components']['install_acl'] = self._confirm("  Install ACL tools for fine-grained permissions?", True)
        print("")
        
        # Firewall
        print("🛡️ Security:")
        self.config['components']['configure_firewall'] = self._confirm("  Configure firewall settings?", True)
        print("")
        
        # Always configure users/groups in standard mode
        self.config['components']['configure_users_groups'] = True
        
        if any([self.config['components']['install_samba'], 
                self.config['components']['install_acl'], 
                self.config['components']['configure_firewall']]):
            print("✅ Production components configured")
        else:
            print("⚠️  Minimal configuration - only users and groups will be set up")
    
    # Path Safety Validation Methods
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
        if '/.ssh/' in path or path.endswith('/.ssh'):
            return 'dangerous', f"Path '{path}' contains SSH configuration"
        if '/.bash' in path or '/.zsh' in path or '/.profile' in path:
            return 'dangerous', f"Path '{path}' contains shell configuration"
        
        # Check if path is in safe whitelist
        for safe_prefix in SAFE_PREFIXES:
            if path.startswith(safe_prefix):
                return 'safe', f"Path '{path}' is in shuttle safe zone"
        
        # Outside whitelist but not dangerous
        return 'warning', f"Path '{path}' is outside standard shuttle directories"
    
    def _validate_all_paths(self, users: List[Dict]) -> bool:
        """
        Validate all paths in user configurations and warn user
        
        Returns:
            True if user confirms to proceed, False to abort
        """
        all_paths = []
        dangerous_paths = []
        warning_paths = []
        
        # Extract all paths from the paths configuration section
        # Since we removed path permissions from users, we now validate
        # the actual shuttle paths that have been configured
        all_paths = list(self.shuttle_paths.keys())
        
        # Validate each path (all_paths contains path names, not actual paths)
        for path_name in set(all_paths):  # Remove duplicates
            # Get actual filesystem path from path name
            actual_path = self.shuttle_paths.get(path_name)
            if not actual_path:
                continue  # Skip if we can't find the actual path
                
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
            print("📋 These changes will be REJECTED during installation unless you:")
            print(f"   1. Run the installation normally (will fail safely)")
            print(f"   2. Then manually run with --reckless mode:")
            print(f"      scripts/2_post_install_config_steps/12_users_and_groups.sh --reckless")
            print("")
            print("⚠️  --reckless mode bypasses ALL safety checks!")
            print("   Only use if you know exactly what you're doing.")
            print("")
            
            if not self._confirm("Continue creating this dangerous configuration?", False):
                print("Configuration aborted for safety.")
                return False
        
        # Handle warning paths (outside whitelist but not dangerous)
        if warning_paths:
            print("\n⚠️  WARNING: Paths outside standard shuttle directories:")
            print("=" * 50)
            
            for path, message in warning_paths:
                print(f"  ⚠️  {message}")
            
            print("")
            print("These paths are not dangerous but are outside the standard shuttle")
            print("directory structure. Examples: /mnt/in, /data/shuttle, etc.")
            print("")
            print("This is usually fine for custom installations.")
            print("")
            
            if not self._confirm("Continue with these non-standard paths?", True):
                print("Please modify the paths to use standard shuttle directories.")
                return False
        
        return True
    
    def _get_choice(self, prompt: str, valid_choices: List[str], default: str) -> str:
        """Get a choice from valid options"""
        # Add exit option to the display
        print("x) Exit - Quit the wizard")
        print("")
        
        while True:
            choice = input(f"{prompt} (Default: {default}): ").strip() or default
            if choice.lower() == 'x':
                print("\nExiting wizard...")
                sys.exit(3)  # Exit code 3 for user cancellation
            if choice in valid_choices:
                return choice
            print(f"Invalid choice. Please select from: {', '.join(valid_choices)} or x to exit")
    
    def _get_permission_choice(self, prompt: str, default: bool = True) -> str:
        """Get permission choice with skip and exit options"""
        default_str = "Y/n/s/x" if default else "y/N/s/x"
        
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            
            if not response:
                return "yes" if default else "no"
            elif response in ['y', 'yes']:
                return "yes"
            elif response in ['n', 'no']:
                return "no"
            elif response in ['s', '-', 'skip']:
                return "skip"
            elif response == 'x':
                print("\nExiting wizard...")
                import sys
                sys.exit(3)  # Exit code 3 for user cancellation
            else:
                print("Invalid choice. Please enter: y/yes, n/no, s/-/skip, or x/exit")
    
    def _get_home_directory(self, username: str, account_type: str, user_source: str) -> str:
        """Determine appropriate home directory based on user type and source"""
        if user_source == "existing":
            # For existing users, don't specify home directory - use what exists
            # The configuration system will handle this appropriately
            return ""
        elif account_type == "interactive":
            # Clean username for home directory (remove domain prefix if present)
            clean_username = username.split("\\")[-1] if "\\" in username else username
            return f"/home/{clean_username}"
        else:
            # Service accounts go in /var/lib/shuttle
            return "/var/lib/shuttle"
    
    # Custom Mode Methods
    def _show_custom_menu(self):
        """Show the main custom mode menu"""
        print("\n=== CUSTOM MODE MENU ===")
        print(f"Groups: {len(self.config['groups'])}")
        print(f"Users: {len(self.users)}")
        print(f"Paths: {len(self.config.get('paths', {}))}")
        print("")
        print("1) Manage Groups")
        print("2) Manage Users")
        print("3) Configure Path Permissions")
        print("4) Configure Components")
        print("5) Import from Templates")
        print("6) Show Current Configuration")
        print("7) Validate Configuration")
        print("")
        print("d) Delete Custom Configuration and return to main menu")
        print("r) Reset Custom Configuration")
        print("s) Save Custom Configuration File")
        print("")
    
    def _custom_manage_groups(self):
        """Manage groups in custom mode"""
        while True:
            print("\n=== GROUP MANAGEMENT ===")
            print(f"Current groups in instructions: {len(self.config['groups'])}")
            
            if self.config['groups']:
                print("\nGroups to be created:")
                for name, details in sorted(self.config['groups'].items()):
                    gid_str = str(details.get('gid', 'auto'))
                    desc = details.get('description', 'No description')
                    print(f"  • {name} (GID: {gid_str}) - {desc}")
            
            print("")
            print("0) Add Standard Groups to Instructions")
            print("1) Add Custom Group to Instructions")
            print("2) Remove Group from Instructions")
            print("3) Edit Group in Instructions")
            print("")
            print("b) Back to Main Custom Configuration Menu")
            
            choice = self._get_choice("Select action", ["0", "1", "2", "3", "b"], "b")
            print()  # Add spacing between response and next section
            
            if choice == "0":
                self._custom_add_standard_group()
            elif choice == "1":
                self._custom_add_custom_group()
            elif choice == "2":
                self._custom_remove_group()
            elif choice == "3":
                self._custom_edit_group()
            elif choice == "b":
                break
    
    def _custom_add_custom_group(self):
        """Add a new custom group"""
        print("\n--- Create Custom Group (Add to Instructions) ---")
        group_name = input("Group name: ").strip()
        if not group_name:
            print("❌ Group name cannot be empty")
            return
        
        if group_name in self.config['groups']:
            print(f"❌ Group '{group_name}' already exists")
            return
        
        description = input("Description: ").strip()
        gid_str = input("GID (leave blank for auto): ").strip()
        
        group_data = {
            'description': description or f"Custom group {group_name}"
        }
        
        if gid_str:
            try:
                gid = int(gid_str)
                if gid < 1000:
                    if not self._confirm("GID < 1000 is typically for system groups. Continue?", False):
                        return
                group_data['gid'] = gid
            except ValueError:
                print("❌ Invalid GID")
                return
        
        self.config['groups'][group_name] = group_data
        print(f"✅ Added group '{group_name}' to instructions")
    
    def _custom_add_standard_group(self):
        """Add groups from standard templates"""
        print("\n--- Add from Standard Groups (Add to Instructions) ---")
        
        # Get standard groups from centralized definitions
        standard_groups = get_standard_groups()
        
        # Show available groups to add
        available_groups = []
        print("\nStandard groups available to add:")
        
        # First, collect available groups
        for name, details in standard_groups.items():
            if name not in self.config['groups']:
                available_groups.append((name, details))
        
        if not available_groups:
            print("\n✅ All standard groups are already added!")
            return
        
        # Show "Add All" option first at position 0
        print(f"  0) Add All Available Groups")
        
        # Show individual groups starting at position 1
        for i, (name, details) in enumerate(available_groups, 1):
            print(f"  {i}) {name} - {details['description']}")
        
        # Show already added groups with checkmarks
        for name, details in standard_groups.items():
            if name in self.config['groups']:
                print(f"  ✓) {name} - {details['description']} (already added)")
        
        print("\nb) Back to Group Management")
        
        # Build valid choices list
        valid_choices = ["0"] + [str(i) for i in range(1, len(available_groups) + 1)] + ["b"]
        default_choice = "b"  # Default to "Back"
        
        choice_str = self._get_choice("Select group to add", valid_choices, default_choice)
        
        if choice_str == "b":
            return
        elif choice_str == "0":
            # Add all available groups
            if self._confirm(f"Add all {len(available_groups)} available standard groups?", True):
                for name, details in available_groups:
                    self.config['groups'][name] = details.copy()
                print(f"✅ Added {len(available_groups)} standard groups to instructions")
        else:
            # Add single group
            choice = int(choice_str)
            if 1 <= choice <= len(available_groups):
                name, details = available_groups[choice - 1]
                self.config['groups'][name] = details.copy()
                print(f"✅ Added group '{name}' to instructions")
    
    def _custom_remove_group(self):
        """Remove a group"""
        if not self.config['groups']:
            print("No groups in instructions to remove")
            return
        
        print("\n--- Remove Group from Instructions ---")
        print("Available groups:")
        groups = sorted(self.config['groups'].keys())
        for i, name in enumerate(groups, 1):
            print(f"{i}) {name}")
        
        try:
            valid_choices = [str(i) for i in range(0, len(groups) + 1)]
            choice_str = self._get_choice("Select group number (0 to cancel)", valid_choices, "0")
            idx = int(choice_str)
            if idx == 0:
                return
            if 1 <= idx <= len(groups):
                group_name = groups[idx - 1]
                
                # Check if group is used by any users
                users_using = []
                for user in self.users:
                    if (user.get('groups', {}).get('primary') == group_name or 
                        group_name in user.get('groups', {}).get('secondary', [])):
                        users_using.append(user['name'])
                
                if users_using:
                    print(f"\n⚠️  Group '{group_name}' is used by: {', '.join(users_using)}")
                    if not self._confirm("Remove anyway?", False):
                        return
                
                del self.config['groups'][group_name]
                print(f"✅ Removed group '{group_name}' from instructions")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_edit_group(self):
        """Edit a group"""
        if not self.config['groups']:
            print("No groups in instructions to edit")
            return
        
        print("\n--- Edit Group in Instructions ---")
        print("Available groups:")
        groups = sorted(self.config['groups'].keys())
        for i, name in enumerate(groups, 1):
            print(f"{i}) {name}")
        
        try:
            valid_choices = [str(i) for i in range(0, len(groups) + 1)]
            choice_str = self._get_choice("Select group number (0 to cancel)", valid_choices, "0")
            idx = int(choice_str)
            if idx == 0:
                return
            if 1 <= idx <= len(groups):
                group_name = groups[idx - 1]
                group_data = self.config['groups'][group_name]
                
                print(f"\nEditing group: {group_name}")
                print(f"Current description: {group_data.get('description', 'None')}")
                print(f"Current GID: {group_data.get('gid', 'auto')}")
                
                new_desc = input("New description (blank to keep current): ").strip()
                if new_desc:
                    group_data['description'] = new_desc
                
                new_gid = input("New GID (blank to keep current): ").strip()
                if new_gid:
                    try:
                        gid = int(new_gid)
                        group_data['gid'] = gid
                    except ValueError:
                        print("❌ Invalid GID")
                        return
                
                print(f"✅ Updated group '{group_name}' in instructions")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_manage_users(self):
        """Manage users in custom mode"""
        while True:
            print("\n=== USER MANAGEMENT ===")
            print(f"Users in instructions: {len(self.users)}")
            if self.users:
                print("\nUsers to be created:")
                for user in self.users:
                    print(f"  • {user['name']} ({user['source']}) - {user['account_type']}")
            print("")
            print("0) Add Standard Users to Instructions")
            print("1) Add Custom User to Instructions")
            print("2) Remove User from Instructions")
            print("3) Edit User in Instructions")
            print("")
            print("b) Back to Main Custom Configuration Menu")
            
            choice = self._get_choice("Select action", ["0", "1", "2", "3", "b"], "b")
            print()  # Add spacing between response and next section
            
            if choice == "0":
                self._custom_import_standard_users()
            elif choice == "1":
                self._custom_add_user()
            elif choice == "2":
                self._custom_remove_user()
            elif choice == "3":
                self._custom_edit_user()
            elif choice == "b":
                break
    
    def _custom_add_user(self):
        """Add a new user with full customization"""
        print("\n--- Add New User ---")
        
        # Get basic user info
        username = input("Username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return
        
        # Check if user already exists
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists")
            return
        
        # User source
        print("\nUser source:")
        print("1) Existing - Use existing local user")
        print("2) Local - Create new local user")
        print("3) Domain - Use domain/LDAP user")
        source_choice = self._get_choice("Select source", ["1", "2", "3"], "1")
        source_map = {"1": "existing", "2": "local", "3": "domain"}
        source = source_map[source_choice]
        
        # Account type
        print("\nAccount type:")
        print("1) Service - No shell, application access only")
        print("2) Interactive - Shell access for human users")
        account_type_choice = self._get_choice("Select type", ["1", "2"], "1")
        account_type = "service" if account_type_choice == "1" else "interactive"
        
        # Create user object
        user = {
            'name': username,
            'source': source,
            'account_type': account_type,
            'groups': {
                'primary': None,
                'secondary': []
            },
            'permissions': {
                'read_write': [],
                'read_only': []
            }
        }
        
        # Shell configuration
        if source == "local":
            print("\nShell configuration:")
            if account_type == "service":
                default_shell = '/usr/sbin/nologin'
                default_home = f'/var/lib/shuttle/{username}'
            else:
                default_shell = '/bin/bash'
                default_home = f'/home/{username}'
            
            shell = input(f"Shell [{default_shell}]: ").strip() or default_shell
            user['shell'] = shell
            
            # Home directory
            home_dir = input(f"Home directory [{default_home}]: ").strip() or default_home
            user['home_directory'] = home_dir
            
            # Create home directory?
            if self._confirm("Create home directory?", True):
                user['create_home'] = True
            else:
                user['create_home'] = False
        
        # Primary group
        if self.config['groups']:
            print("\nSelect primary group:")
            groups = sorted(self.config['groups'].keys())
            for i, name in enumerate(groups, 1):
                print(f"{i}) {name}")
            print("0) No primary group")
            
            try:
                valid_choices = [str(i) for i in range(0, len(groups) + 1)]
                choice_str = self._get_choice("Select group number", valid_choices, "0")
                idx = int(choice_str)
                if 1 <= idx <= len(groups):
                    user['groups']['primary'] = groups[idx - 1]
            except ValueError:
                pass
        
        # Secondary groups
        if self.config['groups']:
            print("\nAdd to secondary groups (comma-separated numbers, or blank for none):")
            available_groups = [g for g in sorted(self.config['groups'].keys()) 
                               if g != user['groups']['primary']]
            for i, name in enumerate(available_groups, 1):
                print(f"{i}) {name}")
            
            group_input = input("Groups: ").strip()
            if group_input:
                try:
                    indices = [int(x.strip()) for x in group_input.split(',')]
                    for idx in indices:
                        if 1 <= idx <= len(available_groups):
                            user['groups']['secondary'].append(available_groups[idx - 1])
                except ValueError:
                    print("⚠️  Invalid group selection")
        
        
        # Samba access
        if self._confirm("\nEnable Samba access?", False):
            user['samba'] = {'enabled': True}
        
        self.users.append(user)
        print(f"✅ Added user '{username}' to instructions")
        
        # Offer to add permissions
        if self._confirm("\nAdd permissions for this user now?", True):
            self._custom_edit_user_permissions(user)
    
    def _custom_remove_user(self):
        """Remove a user"""
        if not self.users:
            print("No users in instructions to remove")
            return
        
        print("\n--- Remove User ---")
        print("Available users:")
        for i, user in enumerate(self.users, 1):
            print(f"{i}) {user['name']}")
        
        try:
            valid_choices = [str(i) for i in range(0, len(self.users) + 1)]
            choice_str = self._get_choice("Select user number (0 to cancel)", valid_choices, "0")
            idx = int(choice_str)
            if idx == 0:
                return
            if 1 <= idx <= len(self.users):
                removed_user = self.users.pop(idx - 1)
                print(f"✅ Removed user '{removed_user['name']}' from instructions")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_edit_user(self):
        """Edit a user"""
        if not self.users:
            print("No users in instructions to edit")
            return
        
        print("\n--- Edit User ---")
        print("Available users:")
        for i, user in enumerate(self.users, 1):
            print(f"{i}) {user['name']}")
        
        try:
            valid_choices = [str(i) for i in range(0, len(self.users) + 1)]
            choice_str = self._get_choice("Select user number (0 to cancel)", valid_choices, "0")
            idx = int(choice_str)
            if idx == 0:
                return
            if 1 <= idx <= len(self.users):
                user = self.users[idx - 1]
                self._custom_edit_user_details(user)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_edit_user_details(self, user):
        """Edit user details submenu"""
        while True:
            print(f"\n--- Editing User: {user['name']} ---")
            print(f"Source: {user['source']}")
            print(f"Type: {user['account_type']}")
            print(f"Shell: {user.get('shell', 'Not set')}")
            print(f"Home directory: {user.get('home_directory', 'Not set')}")
            print(f"Create home: {user.get('create_home', False)}")
            print(f"Primary group: {user['groups']['primary'] or 'None'}")
            print(f"Secondary groups: {', '.join(user['groups']['secondary']) or 'None'}")
            print(f"Samba: {'Enabled' if user.get('samba', {}).get('enabled') else 'Disabled'}")
            print("")
            print("1) Edit Groups")
            print("2) Edit Shell/Home Directory")
            print("3) Edit Permissions")
            print("4) Toggle Samba Access")
            print("5) Back to User Menu")
            
            choice = self._get_choice("Select action", ["1", "2", "3", "4", "5"], "5")
            print()  # Add spacing between response and next section
            
            if choice == "1":
                self._custom_edit_user_groups(user)
            elif choice == "2":
                self._custom_edit_user_shell_home(user)
            elif choice == "3":
                self._custom_edit_user_permissions(user)
            elif choice == "4":
                if 'samba' in user and user['samba'].get('enabled'):
                    user['samba']['enabled'] = False
                    print("✅ Samba access disabled")
                else:
                    if 'samba' not in user:
                        user['samba'] = {}
                    user['samba']['enabled'] = True
                    print("✅ Samba access enabled")
            elif choice == "5":
                break
    
    def _custom_edit_user_shell_home(self, user):
        """Edit user shell and home directory"""
        print(f"\n--- Edit Shell/Home for {user['name']} ---")
        
        # Shell
        current_shell = user.get('shell', '/bin/bash')
        shell = input(f"Shell [{current_shell}]: ").strip() or current_shell
        user['shell'] = shell
        
        # Home directory
        current_home = user.get('home_directory', f'/home/{user["name"]}')
        home_dir = input(f"Home directory [{current_home}]: ").strip() or current_home
        user['home_directory'] = home_dir
        
        # Create home directory?
        current_create = user.get('create_home', True)
        if self._confirm("Create home directory?", current_create):
            user['create_home'] = True
        else:
            user['create_home'] = False
        
        print("✅ Updated shell and home directory settings")
    
    def _custom_edit_user_groups(self, user):
        """Edit user group membership"""
        print(f"\n--- Edit Groups for {user['name']} ---")
        
        # Primary group
        if self.config['groups']:
            print("\nSelect new primary group:")
            groups = sorted(self.config['groups'].keys())
            for i, name in enumerate(groups, 1):
                current = " (current)" if name == user['groups']['primary'] else ""
                print(f"{i}) {name}{current}")
            print("0) No primary group")
            
            try:
                valid_choices = [str(i) for i in range(0, len(groups) + 1)] + ["-1"]
                choice_str = self._get_choice("Select group number (blank to keep current)", valid_choices, "-1")
                idx = int(choice_str)
                if idx == 0:
                    user['groups']['primary'] = None
                elif 1 <= idx <= len(groups):
                    user['groups']['primary'] = groups[idx - 1]
            except ValueError:
                pass
        
        # Secondary groups
        if self.config['groups']:
            print("\nSecondary groups (comma-separated numbers):")
            available_groups = [g for g in sorted(self.config['groups'].keys()) 
                               if g != user['groups']['primary']]
            for i, name in enumerate(available_groups, 1):
                current = " (current)" if name in user['groups']['secondary'] else ""
                print(f"{i}) {name}{current}")
            print("0) Clear all secondary groups")
            
            group_input = input("Groups (blank to keep current): ").strip()
            if group_input == "0":
                user['groups']['secondary'] = []
                print("✅ Cleared secondary groups")
            elif group_input:
                try:
                    indices = [int(x.strip()) for x in group_input.split(',')]
                    new_groups = []
                    for idx in indices:
                        if 1 <= idx <= len(available_groups):
                            new_groups.append(available_groups[idx - 1])
                    user['groups']['secondary'] = new_groups
                    print(f"✅ Updated secondary groups")
                except ValueError:
                    print("⚠️  Invalid group selection")
    
    def _custom_edit_user_permissions(self, user):
        """Edit user permissions"""
        print(f"\n--- Edit Permissions for {user['name']} ---")
        
        # Show current permissions
        print("\nCurrent permissions:")
        print("Read/Write:")
        if user['permissions']['read_write']:
            for perm in user['permissions']['read_write']:
                print(f"  • {perm['path']} (mode: {perm.get('mode', '755')})")
        else:
            print("  None")
        
        print("\nRead Only:")
        if user['permissions']['read_only']:
            for perm in user['permissions']['read_only']:
                print(f"  • {perm['path']} (mode: {perm.get('mode', '644')})")
        else:
            print("  None")
        
        print("\n1) Add Read/Write Permission")
        print("2) Add Read-Only Permission")
        print("3) Remove Permission")
        print("4) Back to User Edit Menu")
        
        choice = self._get_choice("Select action", ["1", "2", "3", "4"], "4")
        print()  # Add spacing between response and next section
        
        if choice == "1":
            path = input("\nPath (or shuttle path name): ").strip()
            if path:
                mode = input("Mode [755]: ").strip() or "755"
                recursive = self._confirm("Recursive?", False)
                perm = {'path': path, 'mode': mode}
                if recursive:
                    perm['recursive'] = True
                user['permissions']['read_write'].append(perm)
                print("✅ Added read/write permission")
        
        elif choice == "2":
            path = input("\nPath (or shuttle path name): ").strip()
            if path:
                mode = input("Mode [644]: ").strip() or "644"
                user['permissions']['read_only'].append({'path': path, 'mode': mode})
                print("✅ Added read-only permission")
        
        elif choice == "3":
            all_perms = []
            for perm in user['permissions']['read_write']:
                all_perms.append(('rw', perm))
            for perm in user['permissions']['read_only']:
                all_perms.append(('ro', perm))
            
            if all_perms:
                print("\nSelect permission to remove:")
                for i, (ptype, perm) in enumerate(all_perms, 1):
                    print(f"{i}) [{ptype}] {perm['path']}")
                
                try:
                    valid_choices = [str(i) for i in range(0, len(all_perms) + 1)]
                    choice_str = self._get_choice("Select number (0 to cancel)", valid_choices, "0")
                    idx = int(choice_str)
                    if 1 <= idx <= len(all_perms):
                        ptype, perm = all_perms[idx - 1]
                        if ptype == 'rw':
                            user['permissions']['read_write'].remove(perm)
                        else:
                            user['permissions']['read_only'].remove(perm)
                        print("✅ Removed permission")
                except ValueError:
                    print("❌ Invalid input")
    
    
    def _custom_import_standard_users(self):
        """Import standard user templates"""
        print("\n--- Import Standard Users ---")
        print("Select user template to add to instructions:")
        print("0) Add All Standard Users")
        print("1) Service Account - shuttle_runner")
        print("2) Service Account - defender_test_runner")
        print("3) Network User - in_user")
        print("4) Network User - out_user")
        print("5) Test User - shuttle_tester")
        print("6) Admin User - shuttle_admin")
        print("")
        print("b) Back to User Management")
        
        choice = self._get_choice("Select template", ["0", "1", "2", "3", "4", "5", "6", "b"], "b")
        
        if choice == "0":
            self._import_all_standard_users()
        elif choice == "1":
            self._import_shuttle_runner()
        elif choice == "2":
            self._import_defender_test_runner()
        elif choice == "3":
            self._import_samba_in_user()
        elif choice == "4":
            self._import_samba_out_user()
        elif choice == "5":
            self._import_shuttle_tester()
        elif choice == "6":
            self._import_shuttle_admin()
        # choice == "b" returns automatically (no elif needed)
    
    def _import_all_standard_users(self):
        """Add all standard users"""
        print("")
        print("=== IMPORT ALL STANDARD USERS ===")
        print("This will import all standard user templates with default names.")
        print("")
        
        if not self._confirm("Import all standard user templates?", True):
            return
        
        # Import all standard users
        imported_count = 0
        users_to_import = [
            ("shuttle_runner", self._import_shuttle_runner),
            ("defender_test_runner", self._import_defender_test_runner), 
            ("shuttle_in_user", self._import_samba_in_user),
            ("shuttle_out_user", self._import_samba_out_user),
            ("shuttle_tester", self._import_shuttle_tester),
            ("shuttle_admin", self._import_shuttle_admin)
        ]
        
        for username, import_func in users_to_import:
            # Check if user already exists
            if not any(u['name'] == username for u in self.users):
                try:
                    # Save current state and import
                    print(f"Importing {username}...")
                    import_func()
                    imported_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to import {username}: {e}")
            else:
                print(f"✓ {username} already exists, skipping")
        
        print(f"\\n✅ Imported {imported_count} new standard users to instructions")
        if imported_count < len(users_to_import):
            skipped = len(users_to_import) - imported_count
            print(f"ℹ️  Skipped {skipped} users that already existed")
    
    def _import_shuttle_runner(self):
        """Import shuttle_runner template"""
        username = input("Username [shuttle_runner]: ").strip() or "shuttle_runner"
        
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists")
            return
        
        user = {
            'name': username,
            'source': 'local',
            'account_type': 'service',
            'groups': {
                'primary': 'shuttle_runners',
                'secondary': [
                    'shuttle_config_readers',
                    'shuttle_data_owners',
                    'shuttle_log_owners'
                ]
            },
            'shell': '/usr/sbin/nologin',
            'home_directory': f'/var/lib/shuttle/{username}',
            'create_home': True
        }
        
        self.users.append(user)
        print(f"✅ Imported {username} (shuttle_runner template)")
    
    def _import_defender_test_runner(self):
        """Import defender_test_runner template"""
        username = input("Username [shuttle_defender_test_runner]: ").strip() or "shuttle_defender_test_runner"
        
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists")
            return
        
        user = {
            'name': username,
            'source': 'local',
            'account_type': 'service',
            'groups': {
                'primary': 'shuttle_defender_test_runners',
                'secondary': [
                    'shuttle_config_readers',
                    'shuttle_log_owners',
                    'shuttle_ledger_owners'
                ]
            },
            'shell': '/usr/sbin/nologin',
            'home_directory': f'/var/lib/shuttle/{username}',
            'create_home': True
        }
        
        self.users.append(user)
        print(f"✅ Imported {username} (defender_test_runner template)")
    
    def _import_samba_in_user(self):
        """Import in_user template"""
        username = input("Username [shuttle_in_user]: ").strip() or "shuttle_in_user"
        
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists")
            return
        
        user = {
            'name': username,
            'source': 'local',
            'account_type': 'service',
            'groups': {
                'primary': 'shuttle_samba_in_users',
                'secondary': ['shuttle_config_readers']
            },
            'samba': {
                'enabled': True
            },
            'shell': '/usr/sbin/nologin',
            'home_directory': f'/var/lib/shuttle/samba/{username}',
            'create_home': True
        }
        
        self.users.append(user)
        print(f"✅ Imported {username} (in_user template)")
    
    def _import_samba_out_user(self):
        """Import out_user template"""
        username = input("Username [shuttle_out_user]: ").strip() or "shuttle_out_user"
        
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists")
            return
        
        user = {
            'name': username,
            'source': 'local',
            'account_type': 'service',
            'groups': {
                'primary': 'shuttle_samba_out_users',
                'secondary': ['shuttle_config_readers']
            },
            'samba': {
                'enabled': True
            },
            'shell': '/usr/sbin/nologin',
            'home_directory': f'/var/lib/shuttle/samba/{username}',
            'create_home': True
        }
        
        self.users.append(user)
        print(f"✅ Imported {username} (out_user template)")
    
    def _import_shuttle_tester(self):
        """Import shuttle_tester template"""
        username = input("Username [shuttle_tester]: ").strip() or "shuttle_tester"
        
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists")
            return
        
        user = {
            'name': username,
            'source': 'local',
            'account_type': 'interactive',
            'groups': {
                'primary': 'shuttle_testers',
                'secondary': [
                    'shuttle_runners',
                    'shuttle_config_readers'
                ]
            },
            'shell': '/bin/bash',
            'home_directory': f'/home/{username}',
            'create_home': True
        }
        
        self.users.append(user)
        print(f"✅ Imported {username} (shuttle_tester template)")
    
    def _import_shuttle_admin(self):
        """Import shuttle_admin template"""
        username = input("Username [shuttle_admin]: ").strip() or "shuttle_admin"
        
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists")
            return
        
        # Admin users get permissions through group membership, not individual path assignments
        
        user = {
            'name': username,
            'source': 'local',
            'account_type': 'interactive',
            'groups': {
                'primary': 'shuttle_admins' if 'shuttle_admins' in self.config['groups'] else None,
                'secondary': []
            },
            'shell': '/bin/bash',
            'home_directory': f'/home/{username}',
            'create_home': True
        }
        
        # Add all relevant groups as secondary
        admin_secondary_groups = [
            'shuttle_config_readers',
            'shuttle_data_owners',
            'shuttle_log_owners',
            'shuttle_ledger_owners',
            'shuttle_runners',
            'shuttle_defender_test_runners'
        ]
        
        for group in admin_secondary_groups:
            if group in self.config['groups']:
                user['groups']['secondary'].append(group)
        
        self.users.append(user)
        print(f"✅ Imported {username} (shuttle_admin template)")
    
    def _custom_configure_path_permissions(self):
        """Configure permissions, ownership, and ACLs for shuttle paths"""
        # Ensure paths section exists
        if 'paths' not in self.config:
            self.config['paths'] = {}
        
        while True:
            print("\n=== PATH PERMISSION CONFIGURATION ===")
            print("Configure ownership, permissions, and ACLs for shuttle paths")
            print(f"\nConfigured path permissions: {len(self.config['paths'])}")
            if self.config['paths']:
                print("\nCurrent permission configurations:")
                for path, config in sorted(self.config['paths'].items()):
                    # Find the path name from shuttle_paths
                    path_name = next((name for name, p in self.shuttle_paths.items() if p == path), "custom")
                    owner = config.get('owner', 'not set')
                    group = config.get('group', 'not set')
                    mode = config.get('mode', 'not set')
                    print(f"  • {path_name}: {path}")
                    print(f"    Owner: {owner}:{group}, Mode: {mode}")
                    if 'acls' in config and config['acls']:
                        print(f"    ACLs: {', '.join(config['acls'])}")
                    if 'default_acls' in config:
                        file_acls = config['default_acls'].get('file', [])
                        dir_acls = config['default_acls'].get('directory', [])
                        if file_acls or dir_acls:
                            print(f"    Default ACLs: Files({' '.join(file_acls)}), Dirs({' '.join(dir_acls)})")
                    print()  # Add spacing after each path configuration
            
            print("\nAvailable shuttle paths for configuration:")
            for path_name, actual_path in sorted(self.shuttle_paths.items()):
                configured = " ✓" if actual_path in self.config['paths'] else ""
                print(f"  • {path_name} → {actual_path}{configured}")
            print("")
            
            print("0) Apply Standard Path Permissions to All Paths")
            print("1) Configure Permissions for Shuttle Path")
            print("2) Configure Permissions for Custom Path")
            print("3) Edit Path Permission Configuration")
            print("4) Remove Path Permission Configuration")
            print("5) Import Standard Path Permission Templates")
            print("")
            print("b) Back to Main Custom Configuration Menu")
            
            choice = self._get_choice("Select action", ["0", "1", "2", "3", "4", "5", "b"], "b")
            print()  # Add spacing between response and next section
            
            if choice == "0":
                self._apply_standard_path_permissions()
            elif choice == "1":
                self._custom_configure_shuttle_path_permissions()
            elif choice == "2":
                self._custom_configure_custom_path_permissions()
            elif choice == "3":
                self._custom_edit_path_permissions()
            elif choice == "4":
                self._custom_remove_path_permissions()
            elif choice == "5":
                self._custom_import_standard_path_permissions()
            elif choice == "b":
                break
    
    def _custom_configure_shuttle_path_permissions(self):
        """Configure permissions for a shuttle path"""
        print("\n=== CONFIGURE SHUTTLE PATH PERMISSIONS ===")
        print("Set ownership, permissions, and ACLs for shuttle paths")
        
        if not self.shuttle_paths:
            print("No shuttle paths available")
            return
        
        print("\\nSelect shuttle path to configure permissions for:")
        print("  0) Apply Standard Permissions to All Paths")
        print("")
        
        paths = list(self.shuttle_paths.items())
        for i, (path_name, actual_path) in enumerate(paths, 1):
            configured = " (permissions configured)" if actual_path in self.config['paths'] else " (not configured)"
            print(f"  {i}) {path_name} → {actual_path}{configured}")
        
        try:
            valid_choices = ["0"] + [str(i) for i in range(1, len(paths) + 1)]
            choice_str = self._get_choice("Select option", valid_choices, "0")
            
            if choice_str == "0":
                self._apply_standard_path_permissions()
                return
            
            idx = int(choice_str)
            if 1 <= idx <= len(paths):
                path_name, actual_path = paths[idx - 1]
                self._configure_path_permission_details(actual_path, path_name)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _apply_standard_path_permissions(self):
        """Apply standard permission configurations to all shuttle paths"""
        print("\n=== ADD STANDARD PERMISSIONS TO INSTRUCTIONS ===")
        print("This will add standard production permission configurations to instructions")
        print("including ownership, modes, ACLs, and default ACLs.")
        
        if not self._confirm("\nAdd standard permissions to all shuttle paths in instructions?", True):
            return
        
        # Get standard permissions from centralized definitions
        standard_configs = get_standard_path_permissions()
        
        configured_count = 0
        for path_name, actual_path in self.shuttle_paths.items():
            if path_name in standard_configs:
                config = standard_configs[path_name].copy()
                config['description'] = f"Standard {path_name}"
                self.config['paths'][actual_path] = config
                configured_count += 1
                print(f"✅ Configured {path_name}: {actual_path}")
        
        print(f"\\n✅ Applied standard permissions to {configured_count} paths")
        print("\\nDefault ACLs configured for data directories ensure:")
        print("  • Files created by Samba users: 660 (rw-rw----)")
        print("  • Directories created by Samba users: 770 (rwxrwx---)")
        print("  • Consistent permissions regardless of umask")
    
    def _custom_configure_custom_path_permissions(self):
        """Configure permissions for a custom (non-shuttle) path"""
        print("\n=== CONFIGURE CUSTOM PATH PERMISSIONS ===")
        print("Set permissions for paths outside the standard shuttle paths")
        
        path = input("\nFull path to configure permissions for: ").strip()
        if not path:
            print("❌ Path cannot be empty")
            return
        
        if path in self.config['paths']:
            print(f"❌ Path '{path}' already has permission configuration")
            return
        
        description = input("Description: ").strip()
        self._configure_path_permission_details(path, f"Custom: {description or 'No description'}")
    
    def _configure_path_permission_details(self, path, description):
        """Configure ownership, permissions, and ACLs for a specific path"""
        print(f"\n=== CONFIGURING PERMISSIONS: {description} ===")
        print(f"Path: {path}")
        print("Configure ownership, file permissions, and access control lists")
        
        # Get basic ownership and permissions
        owner = input("Owner [root]: ").strip() or "root"
        
        # Show available groups
        if self.config['groups']:
            print("\nAvailable groups:")
            groups = sorted(self.config['groups'].keys())
            for i, group in enumerate(groups, 1):
                print(f"  {i}) {group}")
            print("  0) Enter custom group name")
            
            try:
                valid_choices = [str(i) for i in range(0, len(groups) + 1)]
                choice_str = self._get_choice("Select group (0 for custom)", valid_choices, "0")
                group_idx = int(choice_str)
                if group_idx == 0:
                    group = input("Group name: ").strip() or "root"
                elif 1 <= group_idx <= len(groups):
                    group = groups[group_idx - 1]
                else:
                    group = "root"
            except ValueError:
                group = input("Group name [root]: ").strip() or "root"
        else:
            group = input("Group [root]: ").strip() or "root"
        
        # Get mode
        print("\nCommon modes:")
        print("  755 - rwxr-xr-x (directories)")
        print("  644 - rw-r--r-- (files)")
        print("  2775 - rwxrwsr-x (setgid directory)")
        print("  2770 - rwxrws--- (setgid directory, group only)")
        print("  640 - rw-r----- (restricted file)")
        mode = input("Mode [755]: ").strip() or "755"
        
        # Create path configuration
        path_config = {
            'description': description,
            'owner': owner,
            'group': group,
            'mode': mode
        }
        
        # Optional ACLs
        if self._confirm("\nAdd ACL entries?", False):
            acls = []
            while True:
                print("\nACL Types:")
                print("1) User ACL (u:username:perms)")
                print("2) Group ACL (g:groupname:perms)")
                print("3) Done adding ACLs")
                
                acl_choice = self._get_choice("Select ACL type", ["1", "2", "3"], "3")
                
                if acl_choice == "3":
                    break
                elif acl_choice == "1":
                    username = input("Username: ").strip()
                    perms = input("Permissions (rwx format) [r-x]: ").strip() or "r-x"
                    if username:
                        acls.append(f"u:{username}:{perms}")
                elif acl_choice == "2":
                    if self.config['groups']:
                        print("Available groups:")
                        groups = sorted(self.config['groups'].keys())
                        for i, g in enumerate(groups, 1):
                            print(f"  {i}) {g}")
                        print("  0) Enter custom group")
                        
                        try:
                            valid_choices = [str(i) for i in range(0, len(groups) + 1)]
                            choice_str = self._get_choice("Select group (0 for custom)", valid_choices, "0")
                            g_idx = int(choice_str)
                            if g_idx == 0:
                                groupname = input("Group name: ").strip()
                            elif 1 <= g_idx <= len(groups):
                                groupname = groups[g_idx - 1]
                            else:
                                continue
                        except ValueError:
                            groupname = input("Group name: ").strip()
                    else:
                        groupname = input("Group name: ").strip()
                    
                    perms = input("Permissions (rwx format) [r-x]: ").strip() or "r-x"
                    if groupname:
                        acls.append(f"g:{groupname}:{perms}")
            
            if acls:
                path_config['acls'] = acls
        
        # Optional Default ACLs (for consistent file/directory permissions)
        if self._confirm("\nConfigure default ACLs for files created in this directory?", False):
            print("\nDefault ACLs ensure consistent permissions regardless of umask")
            print("Recommended for directories where external processes (like Samba) create files")
            
            default_acls = {}
            
            # File defaults
            print("\nDefault permissions for NEW FILES:")
            print("  660 (rw-rw----) - Recommended for data directories")
            print("  640 (rw-r-----) - Recommended for config/log files")
            file_mode = input("Default file permissions [660]: ").strip() or "660"
            
            # Directory defaults  
            print("\nDefault permissions for NEW DIRECTORIES:")
            print("  770 (rwxrwx---) - Recommended for data directories")
            print("  750 (rwxr-x---) - Recommended for restricted directories")
            dir_mode = input("Default directory permissions [770]: ").strip() or "770"
            
            # Convert to ACL format
            if file_mode == "660":
                default_acls['file'] = ["u::rw-", "g::rw-", "o::---"]
            elif file_mode == "640":
                default_acls['file'] = ["u::rw-", "g::r--", "o::---"]
            else:
                # Custom mode - ask for each permission
                print(f"Custom file mode {file_mode} - please specify default ACLs manually")
                default_acls['file'] = []
            
            if dir_mode == "770":
                default_acls['directory'] = ["u::rwx", "g::rwx", "o::---"]
            elif dir_mode == "750":
                default_acls['directory'] = ["u::rwx", "g::r-x", "o::---"]
            else:
                # Custom mode - ask for each permission
                print(f"Custom directory mode {dir_mode} - please specify default ACLs manually")
                default_acls['directory'] = []
            
            if default_acls['file'] or default_acls['directory']:
                path_config['default_acls'] = default_acls
                print(f"✅ Default ACLs configured")
                print(f"   Files: {file_mode} ({' '.join(default_acls.get('file', []))})")
                print(f"   Directories: {dir_mode} ({' '.join(default_acls.get('directory', []))})")
        
        # Store configuration
        self.config['paths'][path] = path_config
        print(f"✅ Configured permissions for path: {path}")
    
    def _custom_edit_path_permissions(self):
        """Edit existing path permission configuration"""
        if not self.config['paths']:
            print("No path permissions configured to edit")
            return
        
        print("\n=== EDIT PATH PERMISSION CONFIGURATION ===")
        print("Select path to modify permissions for:")
        paths = list(self.config['paths'].keys())
        for i, path in enumerate(paths, 1):
            print(f"{i}) {path}")
        
        try:
            valid_choices = [str(i) for i in range(0, len(paths) + 1)]
            choice_str = self._get_choice("Select path number (0 to cancel)", valid_choices, "0")
            idx = int(choice_str)
            if idx == 0:
                return
            if 1 <= idx <= len(paths):
                path = paths[idx - 1]
                config = self.config['paths'][path]
                
                print(f"\nEditing: {path}")
                print(f"Current owner: {config.get('owner', 'unknown')}")
                print(f"Current group: {config.get('group', 'unknown')}")
                print(f"Current mode: {config.get('mode', 'unknown')}")
                if 'acls' in config:
                    print(f"Current ACLs: {', '.join(config['acls'])}")
                
                # Re-configure the path
                description = config.get('description', path)
                self._configure_path_permission_details(path, description)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_remove_path_permissions(self):
        """Remove path permission configuration"""
        if not self.config['paths']:
            print("No path permission configurations to remove")
            return
        
        print("\n=== REMOVE PATH PERMISSION CONFIGURATION ===")
        print("Select path to remove permission configuration for:")
        paths = list(self.config['paths'].keys())
        for i, path in enumerate(paths, 1):
            print(f"{i}) {path}")
        
        try:
            valid_choices = [str(i) for i in range(0, len(paths) + 1)]
            choice_str = self._get_choice("Select path number (0 to cancel)", valid_choices, "0")
            idx = int(choice_str)
            if idx == 0:
                return
            if 1 <= idx <= len(paths):
                path = paths[idx - 1]
                
                if self._confirm(f"Remove permission configuration for '{path}'?", False):
                    del self.config['paths'][path]
                    print(f"✅ Removed permission configuration for path: {path}")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_import_standard_path_permissions(self):
        """Import standard path permission configurations"""
        print("\n=== IMPORT STANDARD PATH PERMISSION TEMPLATES ===")
        print("This will configure all shuttle paths with standard production permission settings.")
        
        if self._confirm("Import standard path permission configurations?", True):
            # Use the same method as standard mode
            original_paths = self.config.get('paths', {}).copy()
            self._configure_standard_paths()
            
            # Count what was added
            new_paths = len(self.config.get('paths', {})) - len(original_paths)
            print(f"✅ Imported standard permission configurations for {new_paths} paths")

    def _custom_manage_components(self):
        """Manage component configuration"""
        print("\n--- Component Configuration ---")
        
        print("\nCurrent settings:")
        print(f"  Install Samba: {self.config['components']['install_samba']}")
        print(f"  Install ACL tools: {self.config['components']['install_acl']}")
        print(f"  Configure firewall: {self.config['components']['configure_firewall']}")
        print(f"  Configure Samba: {self.config['components']['configure_samba']}")
        print(f"  Configure users/groups: {self.config['components']['configure_users_groups']}")
        print("")
        
        self.config['components']['install_samba'] = self._confirm("Install Samba?", 
            self.config['components']['install_samba'])
        self.config['components']['install_acl'] = self._confirm("Install ACL tools?", 
            self.config['components']['install_acl'])
        self.config['components']['configure_firewall'] = self._confirm("Configure firewall?", 
            self.config['components']['configure_firewall'])
        
        if self.config['components']['install_samba']:
            self.config['components']['configure_samba'] = self._confirm("Configure Samba?", 
                self.config['components']['configure_samba'])
        else:
            self.config['components']['configure_samba'] = False
        
        # Always configure users/groups in custom mode
        self.config['components']['configure_users_groups'] = True
        
        print("✅ Component settings updated")
    
    def _custom_import_template(self):
        """Import from predefined templates"""
        print("\n--- Import Templates ---")
        print("1) Import Standard Mode Template (production)")
        print("2) Import Simple Mode Template (single admin)")
        print("3) Import Minimal Template (basic groups only)")
        print("4) Cancel")
        
        choice = self._get_choice("Select template", ["1", "2", "3", "4"], "1")
        
        if choice == "1":
            self._import_standard_template()
        elif choice == "2":
            self._import_simple_template()
        elif choice == "3":
            self._import_minimal_template()
    
    def _import_simple_template(self):
        """Import simple mode template"""
        print("\nImporting Simple Mode template...")
        
        # Add admin group if not exists
        if 'shuttle_admins' not in self.config['groups']:
            self.config['groups']['shuttle_admins'] = {
                'description': 'Administrative users with full shuttle access',
                'gid': 5000
            }
        
        # Set components
        self.config['components']['install_samba'] = True
        self.config['components']['install_acl'] = True
        self.config['components']['configure_firewall'] = True
        self.config['components']['configure_samba'] = True
        
        print("✅ Imported Simple Mode template")
        print("   - Added shuttle_admins group")
        print("   - Enabled all components")
        print("\nUse 'Import Standard Users' > 'Admin User' to add an admin user")
    
    def _import_standard_template(self):
        """Import standard production template"""
        print("\nImporting Standard Production template...")
        
        # Import all standard groups from centralized definitions
        standard_groups = get_standard_groups()
        
        imported = 0
        for name, details in standard_groups.items():
            if name not in self.config['groups']:
                self.config['groups'][name] = details.copy()
                imported += 1
        
        # Set production components from centralized definitions
        standard_components = get_standard_components()
        self.config['components'].update(standard_components)
        
        # Set production environment
        self.config['metadata']['environment'] = 'production'
        self.config['settings']['interactive_mode'] = 'non-interactive'
        
        print("\n✅ Imported Standard Production template")
        print("   - Added all standard groups")
        print("   - Enabled production components")
        print("   - Set production environment")
        print("\nUse 'Import Standard Users' to add standard user accounts")
    
    def _import_minimal_template(self):
        """Import minimal template"""
        print("\nImporting Minimal template...")
        
        # Add only essential groups
        minimal_groups = {
            'shuttle_runners': {
                'description': 'Can execute shuttle applications',
                'gid': 5010
            },
            'shuttle_config_readers': {
                'description': 'Read access to config files',
                'gid': 5001
            }
        }
        
        imported = 0
        for name, details in minimal_groups.items():
            if name not in self.config['groups']:
                self.config['groups'][name] = details.copy()
                imported += 1
        
        # Minimal components
        self.config['components']['install_samba'] = False
        self.config['components']['install_acl'] = False
        self.config['components']['configure_firewall'] = False
        self.config['components']['configure_samba'] = False
        
        print(f"✅ Imported Minimal template")
        print(f"   - Added {imported} essential groups")
        print("   - Disabled optional components")
    
    def _custom_show_configuration(self):
        """Show current configuration summary"""
        print("\n=== Current Configuration ===")
        print(f"\nEnvironment: {self.config['metadata'].get('environment', 'custom')}")
        print(f"Mode: {self.config['metadata'].get('mode', 'custom')}")
        
        print(f"\nGroups ({len(self.config['groups'])}):")
        for name, details in sorted(self.config['groups'].items()):
            print(f"  • {name} (GID: {details.get('gid', 'auto')})")
        
        print(f"\nUsers ({len(self.users)}):")
        for user in self.users:
            groups = []
            if user['groups']['primary']:
                groups.append(f"primary: {user['groups']['primary']}")
            if user['groups']['secondary']:
                groups.append(f"secondary: {', '.join(user['groups']['secondary'])}")
            group_str = f" ({'; '.join(groups)})" if groups else ""
            
            print(f"  • {user['name']} - {user['source']}/{user['account_type']}{group_str}")
        
        print(f"\nPaths ({len(self.config.get('paths', {}))}):")
        if self.config.get('paths'):
            for path, config in sorted(self.config['paths'].items()):
                owner = config.get('owner', 'unknown')
                group = config.get('group', 'unknown')
                mode = config.get('mode', 'unknown')
                print(f"  • {path}")
                print(f"    {owner}:{group} {mode}")
                if 'acls' in config and config['acls']:
                    print(f"    ACLs: {', '.join(config['acls'])}")
        else:
            print("  None configured")
        
        print("\nComponents:")
        for comp, enabled in self.config['components'].items():
            status = "Yes" if enabled else "No"
            print(f"  • {comp}: {status}")
    
    def _custom_validate_configuration(self):
        """Validate the current configuration"""
        print("\n=== Configuration Validation ===")
        
        errors = []
        warnings = []
        
        # Check for groups
        if not self.config['groups']:
            errors.append("No groups defined")
        
        # Check for users
        if not self.users:
            errors.append("No users defined")
        
        # Check each user
        for user in self.users:
            # Check primary group exists
            if user['groups']['primary'] and user['groups']['primary'] not in self.config['groups']:
                errors.append(f"User '{user['name']}': primary group '{user['groups']['primary']}' does not exist")
            
            # Check secondary groups exist
            for group in user['groups']['secondary']:
                if group not in self.config['groups']:
                    errors.append(f"User '{user['name']}': secondary group '{group}' does not exist")
            
            # Check for service accounts with shell access
            if user['account_type'] == 'service' and user.get('shell') == '/bin/bash':
                warnings.append(f"User '{user['name']}': service account has shell access")
            
            # Check for Samba users without Samba component
            if user.get('samba', {}).get('enabled') and not self.config['components']['install_samba']:
                warnings.append(f"User '{user['name']}': has Samba enabled but Samba component is not selected")
        
        # Display results
        if errors:
            print("\n❌ Validation Errors:")
            for error in errors:
                print(f"   • {error}")
        
        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"   • {warning}")
        
        if not errors and not warnings:
            print("\n✅ Configuration is valid")
        
        return len(errors) == 0
    
    def _build_complete_config(self) -> List[Dict[str, Any]]:
        """Build complete configuration documents"""
        # Validate all paths for safety before building config
        print("\n🔍 Validating path safety...")
        if not self._validate_all_paths(self.users):
            print("❌ Configuration cancelled due to path safety concerns.")
            sys.exit(1)
        
        documents = []
        
        # First document: global config
        documents.append(self.config)
        
        # User documents
        for user in self.users:
            documents.append({
                'type': 'user',
                'user': user
            })
        
        print("✅ Path validation complete - configuration is ready")
        return documents


def save_config(config: List[Dict[str, Any]], filename: str):
    """Save configuration to YAML file"""
    with open(filename, 'w') as f:
        yaml.dump_all(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"\nConfiguration saved to: {filename}")


def get_default_filename(config: List[Dict[str, Any]]) -> str:
    """Get default filename based on environment"""
    environment = config[0]['metadata']['environment']
    return get_config_filename(environment)


def ensure_config_dir(filename: str):
    """Ensure the config directory exists for the given filename"""
    config_dir = os.path.dirname(filename)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)


def print_next_steps(filename: str):
    """Print the next steps instructions using the shared shell function"""
    import subprocess
    
    # Get absolute paths - we're in scripts/_setup_lib_py/
    script_dir = os.path.dirname(os.path.abspath(__file__))  # _setup_lib_py
    scripts_dir = os.path.dirname(script_dir)  # scripts
    project_root = os.path.dirname(scripts_dir)  # project root
    config_path = os.path.join(project_root, "config", filename)
    script_path = os.path.join(project_root, "scripts", "2_post_install_config.sh")
    
    # Use the shared shell function for consistency
    # Create a small shell script that sources the common library and calls the function
    shell_cmd = f'''
source "{scripts_dir}/_setup_lib_sh/_common_.source.sh"
show_saved_config_usage "{script_path}" "{config_path}" "configuration" "false"
'''
    
    try:
        subprocess.run(['bash', '-c', shell_cmd], check=True)
    except subprocess.CalledProcessError:
        # Fallback to Python implementation if shell function fails
        print(f"{'='*60}")
        print("NEXT STEPS")
        print("="*60)
        print("You can run these commands from any directory:")
        print("")
        print("To review the configuration:")
        print(f"  cat {config_path}")
        print("")
        print("To test what would be applied (dry run):")
        print(f"  {script_path} --instructions {config_path} --dry-run")
        print("")
        print("To apply the configuration:")
        print(f"  {script_path} --instructions {config_path}")


def validate_yaml_config(filename: str) -> bool:
    """Validate YAML configuration file and print results"""
    print(f"\n{'='*60}")
    print("CONFIGURATION VALIDATION")
    print("="*60)
    
    try:
        # Basic YAML validation
        with open(filename, 'r') as f:
            list(yaml.safe_load_all(f))
        print("✅ YAML syntax is valid")
        
        # Check for required sections
        validation_errors = []
        with open(filename, 'r') as f:
            docs = list(yaml.safe_load_all(f))
        
        # Validate first document (main config)
        if not docs:
            validation_errors.append("No configuration documents found")
        else:
            main_config = docs[0]
            
            # Check required sections
            required_sections = ['metadata', 'settings', 'groups', 'components']
            for section in required_sections:
                if section not in main_config:
                    validation_errors.append(f"Missing required section: {section}")
            
            # Check metadata
            if 'metadata' in main_config:
                metadata = main_config['metadata']
                required_metadata = ['environment', 'created']
                for field in required_metadata:
                    if field not in metadata:
                        validation_errors.append(f"Missing required metadata field: {field}")
        
        # Validate user documents
        user_count = len(docs) - 1
        if user_count == 0:
            validation_errors.append("No users defined")
        else:
            for i, doc in enumerate(docs[1:], 1):
                if doc.get('type') != 'user':
                    validation_errors.append(f"Document {i+1}: Invalid type, expected 'user'")
                elif 'user' not in doc:
                    validation_errors.append(f"Document {i+1}: Missing 'user' section")
                else:
                    user = doc['user']
                    required_user_fields = ['name', 'source', 'account_type', 'groups']
                    for field in required_user_fields:
                        if field not in user:
                            validation_errors.append(f"User {user.get('name', 'unnamed')}: Missing required field '{field}'")
        
        if validation_errors:
            print("❌ Configuration validation errors found:")
            for error in validation_errors:
                print(f"   • {error}")
            print("")
            print("Please review and fix these issues before applying the configuration.")
            print("")
            return False
        else:
            print("✅ Configuration validation passed")
            print("")
            return True
            
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        print("")
        print("Please review and fix the YAML syntax before applying the configuration.")
        print("")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        print("")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Shuttle Post-Install Configuration Wizard')
    parser.add_argument('--shuttle-config-path', help='Path to shuttle configuration file')
    parser.add_argument('--test-work-dir', help='Test work directory path')
    parser.add_argument('--test-config-path', help='Test configuration file path')
    
    args = parser.parse_args()
    
    print("Shuttle Post-Install Configuration Wizard")
    print("======================================")
    
    wizard = ConfigWizard(
        shuttle_config_path=args.shuttle_config_path,
        test_work_dir=args.test_work_dir,
        test_config_path=args.test_config_path
    )
    config = wizard.run()
    
    print("\n=== Configuration Summary ===")
    print(f"Environment: {config[0]['metadata']['environment']}")
    print(f"Groups: {len(config[0]['groups'])}")
    print(f"Users: {len(config) - 1}")
    
    # Save options
    print("\nWhat would you like to do?")
    print("")
    print("1) Save configuration only (exit without applying)")
    print("2) Save configuration and continue") 
    # print("3) Continue with configuration")  # Commented out - require save
    print("x) Exit without saving")
    print("")
    
    choice = input("Select an option [1-2/x] (Default: 1): ").strip() or "1"
    
    if choice == "1":
        # Save configuration only (exit without applying)
        default_filename = get_default_filename(config)
        filename = input(f"Save as [{default_filename}]: ").strip() or default_filename
        
        ensure_config_dir(filename)
        save_config(config, filename)
        
        validate_yaml_config(filename)
        
        print_next_steps(filename)
        print("")
        print("Configuration wizard complete.")
        
        # Exit with code 1 to indicate "save only, don't apply"
        sys.exit(1)
        
    elif choice == "2":
        # Save configuration and continue
        default_filename = get_default_filename(config)
        filename = input(f"Save as [{default_filename}]: ").strip() or default_filename
        
        ensure_config_dir(filename)
        save_config(config, filename)
        
        # Write filename to a temporary file for the shell script to read
        with open('/tmp/wizard_config_filename', 'w') as f:
            f.write(filename)
        
        print("\nConfiguration saved. Continuing to apply configuration...")
        # Exit with code 0 to indicate "continue with apply"
        sys.exit(0)
        
    elif choice.lower() == "x":
        print("\nConfiguration not saved.")
        sys.exit(3)  # Exit code 3 for user cancellation


if __name__ == '__main__':
    main()