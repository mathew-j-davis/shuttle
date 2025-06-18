#!/usr/bin/env python3
"""
Configuration Wizard
Interactive wizard to generate YAML configuration files
"""

import yaml
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import configparser
from post_install_config_constants import get_config_filename


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
        
        # Environment selection
        self._select_environment()
        
        # Component selection
        self._select_components()
        
        # User type selection
        self._select_user_approach()
        
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
    
    def _select_components(self):
        """Select which components to install and configure"""
        print("\n2. Component Selection")
        print("--------------------")
        print("Choose which components to install and configure:")
        print("")
        
        # Package installation
        print("Package Installation:")
        self.config['components']['install_samba'] = self._confirm("  Install Samba? (Default: Yes)", True)
        self.config['components']['install_acl'] = self._confirm("  Install ACL tools? (Default: Yes)", True)
        print("")
        
        # Configuration steps
        print("Configuration Steps:")
        self.config['components']['configure_users_groups'] = self._confirm("  Configure users and groups? (Default: Yes)", True)
        
        if self.config['components']['install_samba']:
            self.config['components']['configure_samba'] = self._confirm("  Configure Samba settings? (Default: Yes)", True)
        else:
            self.config['components']['configure_samba'] = False
            
        self.config['components']['configure_firewall'] = self._confirm("  Configure firewall? (Default: Yes)", True)
        print("")
    
    def _select_user_approach(self):
        """Select user configuration approach"""
        print("\n3. User Configuration Approach")
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
        print("\n4. Single User Configuration")
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
        
        # Account type 
        account_type = "service"
        if self.config['metadata']['environment'] == 'development':
            if user_source == "existing":
                print(f"\nFor existing user '{username}', how will they use Samba?")
                print("1) Interactive user - desktop/human file sharing")
                print("2) Service account - programmatic/automated file access")
                type_choice = self._get_choice("Select usage type", ["1", "2"], "1")
                account_type = "interactive" if type_choice == "1" else "service"
            else:
                if self._confirm("Create interactive account with shell access?", False):
                    account_type = "interactive"
        
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
            'capabilities': {
                'executables': ['run-shuttle', 'run-defender-test']
            },
            'permissions': self._configure_path_permissions("Single User")
        })
        
        # Samba configuration
        print("\nEnable Samba Access for User")
        print("============================")
        if self.config['components']['configure_samba'] and self._confirm("Enable Samba access for this user? (Default: Yes)", True):
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
        print("Options: y/yes = grant access, n/no = don't grant, x/- = skip (don't modify existing permissions)")
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
        print("\n3. Separate Users Configuration")
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
            'capabilities': {
                'executables': []
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
            'capabilities': {
                'executables': ['run-shuttle']
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
            'capabilities': {
                'executables': ['run-defender-test']
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
        print("\n3. Custom User Configuration")
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
            'capabilities': {
                'executables': []
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
        
        # Capabilities
        if self._confirm("Can run shuttle?", False):
            user['capabilities']['executables'].append('run-shuttle')
        if self._confirm("Can run defender tests?", False):
            user['capabilities']['executables'].append('run-defender-test')
        
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
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        return response in ['y', 'yes']
    
    def _get_choice(self, prompt: str, valid_choices: List[str], default: str) -> str:
        """Get a choice from valid options"""
        while True:
            choice = input(f"{prompt} [{default}]: ").strip() or default
            if choice in valid_choices:
                return choice
            print(f"Invalid choice. Please select from: {', '.join(valid_choices)}")
    
    def _get_permission_choice(self, prompt: str, default: bool = True) -> str:
        """Get permission choice with skip option"""
        default_str = "Y/n/x" if default else "y/N/x"
        
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            
            if not response:
                return "yes" if default else "no"
            elif response in ['y', 'yes']:
                return "yes"
            elif response in ['n', 'no']:
                return "no"
            elif response in ['x', '-', 'skip']:
                return "skip"
            else:
                print("Invalid choice. Please enter: y/yes, n/no, or x/-/skip")
    
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
    
    def _build_complete_config(self) -> List[Dict[str, Any]]:
        """Build complete configuration documents"""
        documents = []
        
        # First document: global config
        documents.append(self.config)
        
        # User documents
        for user in self.users:
            documents.append({
                'type': 'user',
                'user': user
            })
        
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
    """Print the next steps instructions"""
    print(f"{'='*60}")
    print("NEXT STEPS")
    print("="*60)
    print("From the project root directory, you can:")
    print("")
    print("To review the configuration:")
    print(f"  cat config/{filename}")
    print("")
    print("To test what would be applied (dry run):")
    print(f"  ./scripts/2_post_install_config.sh --config config/{filename} --dry-run")
    print("")
    print("To apply the configuration:")
    print(f"  ./scripts/2_post_install_config.sh --config config/{filename}")


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
    print("1) Save configuration to file (review before applying)")
    print("2) Apply configuration now")
    print("3) Save and apply configuration")
    print("4) Exit without saving")
    
    choice = input("Select option [1]: ").strip() or "1"
    
    if choice == "1":
        # Save only - show commands and exit with special code
        default_filename = get_default_filename(config)
        filename = input(f"Save as [{default_filename}]: ").strip() or default_filename
        
        ensure_config_dir(filename)
        save_config(config, filename)
        
        validate_yaml_config(filename)
        
        print_next_steps(filename)
        print("")
        print("Configuration wizard complete.")
        sys.exit(2)  # Exit with code 2 to indicate "save only, don't continue"
        
    elif choice == "2":
        # Apply now without saving to permanent location
        import tempfile
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, 
                                       dir='/tmp', prefix='wizard_temp_config_') as f:
            temp_filename = f.name
            yaml.dump_all(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Write just the filename (not full path) for consistency
        temp_basename = os.path.basename(temp_filename)
        with open('/tmp/wizard_config_filename', 'w') as f:
            f.write(f"../../../{temp_filename}")  # Relative path from config dir
        
        print(f"\nTemporary configuration created: {temp_filename}")
        print("Configuration will be applied without saving to config directory.")
        print("Note: Temporary file will be deleted after use.")
        
        # Exit with code 0 to indicate "continue with apply"
        sys.exit(0)
        
    elif choice == "3":
        # Save and apply
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
        
    elif choice == "4":
        print("\nConfiguration not saved.")


if __name__ == '__main__':
    main()