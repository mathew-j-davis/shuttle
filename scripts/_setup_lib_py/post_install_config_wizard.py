#!/usr/bin/env python3
"""
Configuration Wizard
Interactive wizard to generate YAML configuration files

ENHANCED WITH THREE-TIER DEPLOYMENT MODES:

1. DEVELOPMENT MODE
   - Single admin user with full access
   - Best for development/testing
   - Minimal security boundaries

2. STANDARD MODE  
   - Production security model
   - Service accounts, network users, proper isolation
   - Based on shuttle_simplified_security_model.md
   - Option to customize after standard setup

3. CUSTOM MODE
   - Full custom permission builder 
   - Template assistance and guided setup
   - Complete flexibility

Usage:
- Wizard automatically shows mode selection first
- Standard mode can be customized after initial setup
- All modes generate compatible YAML for permission_manager.py
"""

import yaml
import sys
import os
from typing import Dict, List, Any, Optional, Set
import configparser
from post_install_config_constants import get_config_filename
from post_install_standard_configuration_reader import (
    get_standard_groups, get_standard_user_templates, get_standard_instruction_template,
    get_custom_user_base_templates, get_custom_group_base_templates,
    get_path_permission_base_templates, get_development_admin_group, 
    STANDARD_MODE_CONFIGS, STANDARD_SAMBA_CONFIG
)

# Import domain user validation and integration
import subprocess
import re
from pathlib import Path

# Domain user integration imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '2_post_install_config_steps'))
try:
    from wizard_domain_integration import WizardDomainIntegration
    DOMAIN_INTEGRATION_AVAILABLE = True
except ImportError:
    print("ℹ️  Domain user integration not available (wizard_domain_integration.py not found)")
    DOMAIN_INTEGRATION_AVAILABLE = False

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
        # Use standard instruction template as base for main document
        self.instructions = get_standard_instruction_template()
        
        # Remove nested collections - they should be separate
        self.groups = self.instructions.pop('groups', {})
        self.users = self.instructions.pop('users', [])
        self.paths = self.instructions.pop('paths', {})
        # Keep shuttle_paths separate - it's for path discovery/input
        self.shuttle_paths = {}
        
        # Get paths from environment or parameters
        self.shuttle_config_path = shuttle_config_path or os.getenv('SHUTTLE_CONFIG_PATH')
        self.test_work_dir = test_work_dir or os.getenv('SHUTTLE_TEST_WORK_DIR')
        self.test_config_path = test_config_path or os.getenv('SHUTTLE_TEST_CONFIG_PATH')
        
        # Load shuttle configuration to get actual paths
        self._load_shuttle_config()
        
        # Set config base path for domain integration
        self.config_base_path = self._get_config_base_path()
        
        # Initialize domain user integration if available
        self.domain_integration = None
        if DOMAIN_INTEGRATION_AVAILABLE:
            try:
                self.domain_integration = WizardDomainIntegration(self)
            except Exception as e:
                print(f"⚠️  Failed to initialize domain integration: {e}")
                self.domain_integration = None
    
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
    
    def _get_config_base_path(self):
        """Get the base directory where shuttle config is stored"""
        if self.shuttle_config_path:
            # Extract directory from shuttle config file path
            return os.path.dirname(os.path.abspath(self.shuttle_config_path))
        else:
            # Fallback to default if no shuttle config path
            return '/etc/shuttle'
    
    # =============================================
    # UTILITY METHODS
    # =============================================
    
    def _wrap_title(self, title: str) -> str:
        """Wrap a title with decorative borders for consistent formatting"""
        return f"\n=== {title} ===\n"
    
    # =============================================
    # GROUP HELPER METHODS
    # =============================================
    
    def _get_sorted_groups(self) -> List[str]:
        """Get sorted list of group names"""
        return sorted(self.groups.keys())
    
    def _validate_group_name(self, group_name: str, check_users: bool = True) -> tuple[bool, str]:
        """Validate group name against rules and existing entities
        
        Returns:
            (is_valid, error_message)
        """
        if not group_name:
            return False, "Group name cannot be empty"
        
        if group_name in self.groups:
            return False, f"Group '{group_name}' already exists"
        
        if check_users:
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
        for name, data in self.groups.items():
            if name != group_name and data.get('gid') == gid:
                return False, f"GID {gid} already used by group '{name}'"
        
        # Warning for system GIDs
        if gid < 1000:
            return True, "WARNING: GID < 1000 is typically for system groups"
        
        return True, ""
    
    def _find_users_using_group(self, group_name: str) -> List[str]:
        """Find all users that reference a group
        
        Returns:
            List of usernames using the group
        """
        users_using = []
        for user in self.users:
            if (user.get('groups', {}).get('primary') == group_name or 
                group_name in user.get('groups', {}).get('secondary', [])):
                users_using.append(user['name'])
        return users_using
    
    def _get_next_available_gid(self, start_gid: int = 5000) -> int:
        """Find next available GID starting from start_gid"""
        used_gids = set()
        for group_data in self.groups.values():
            if 'gid' in group_data:
                used_gids.add(group_data['gid'])
        
        gid = start_gid
        while gid in used_gids:
            gid += 1
        return gid
    
    def _edit_group_template_interactively(self, group_name: str, template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Context-aware interactive group template editing
        
        Similar to user template editing but for groups - provides unified editing
        experience with validation, preview, and confirmation.
        
        Args:
            group_name: Name of the group being edited
            template_data: Original template data
            
        Returns:
            Modified template data or None if cancelled
        """
        print(f"\n=== Editing Group: {group_name} ===")
        
        # Start with a copy
        edited_data = template_data.copy()
        
        # 1. Edit description
        current_desc = edited_data.get('description', '')
        print(f"\nCurrent description: {current_desc}")
        new_desc = input(f"New description [{current_desc}]: ").strip()
        if new_desc:
            edited_data['description'] = new_desc
        
        # 2. Edit GID with validation
        current_gid = edited_data.get('gid')
        if current_gid is None:
            print(f"\nCurrent GID: auto-assign")
        else:
            print(f"\nCurrent GID: {current_gid}")
        
        if self._confirm("Change GID?", False):
            gid_input = input("New GID (blank for auto-assign): ").strip()
            if gid_input:
                try:
                    new_gid = int(gid_input)
                    # Use existing validation
                    is_valid, msg = self._validate_gid(new_gid, group_name)
                    if not is_valid:
                        print(f"❌ {msg}")
                        print("Keeping current GID")
                    elif msg.startswith("WARNING"):
                        if self._confirm(f"{msg} Continue?", False):
                            edited_data['gid'] = new_gid
                        else:
                            print("Keeping current GID")
                    else:
                        edited_data['gid'] = new_gid
                except ValueError:
                    print("❌ Invalid GID - must be a number. Keeping current GID")
            else:
                # Auto-assign requested
                edited_data['gid'] = self._get_next_available_gid()
                print(f"Auto-assigned GID: {edited_data['gid']}")
        
        # 3. Show final configuration preview
        print(self._wrap_title('Final Group Configuration'))
        self._display_group_template(group_name, edited_data)
        
        if self._confirm("\nApply these changes?", True):
            return edited_data
        else:
            return None
    
    def _display_group_template(self, group_name: str, template_data: Dict[str, Any]):
        """Display complete group template information for review"""
        category = template_data.get('category', 'custom')
        description = template_data.get('description', 'No description')
        gid = template_data.get('gid')
        
        print(f"\n{group_name} ({category}):")
        print(f"   Description: {description}")
        if gid is None:
            print(f"   GID: auto-assign")
        else:
            print(f"   GID: {gid}")
    
    def _get_all_available_groups(self) -> Dict[str, Dict[str, Any]]:
        """Get all available groups (standard + instruction groups) with status"""
        from post_install_standard_configuration_reader import get_standard_groups
        
        # Start with standard groups
        standard_groups = get_standard_groups()
        all_groups = {}
        
        # Add standard groups with status
        for name, data in standard_groups.items():
            all_groups[name] = {
                'description': data.get('description', ''),
                'gid': data.get('gid', 'auto'),
                'source': 'standard',
                'in_instructions': name in self.groups
            }
        
        # Add any custom groups from instructions that aren't in standard
        for name, data in self.groups.items():
            if name not in all_groups:
                all_groups[name] = {
                    'description': data.get('description', 'Custom group'),
                    'gid': data.get('gid', 'auto'),
                    'source': 'custom',
                    'in_instructions': True
                }
        
        return all_groups
    
    def _select_group_from_list(self, prompt: str, include_none: bool = False, 
                               none_label: str = "None", current_group: str = None,
                               exclude_groups: List[str] = None, include_back: bool = True) -> Optional[str]:
        """
        Enhanced group selection menu showing all available groups with status
        
        Returns:
            Selected group name, None if cancelled/none selected
        """
        all_groups = self._get_all_available_groups()
        
        # Apply exclusions
        if exclude_groups:
            available_groups = {k: v for k, v in all_groups.items() if k not in exclude_groups}
        else:
            available_groups = all_groups
        
        # Build menu items
        menu_items = []
        
        if include_none:
            menu_items.append({
                'key': '1',
                'label': none_label,
                'value': None
            })
        
        # Sort groups: standard first, then custom
        standard_groups = [(k, v) for k, v in available_groups.items() if v['source'] == 'standard']
        custom_groups = [(k, v) for k, v in available_groups.items() if v['source'] == 'custom']
        
        all_sorted = sorted(standard_groups) + sorted(custom_groups)
        
        # Start enumeration based on whether we already added a none option
        start_index = 2 if include_none else 1
        for i, (group_name, group_data) in enumerate(all_sorted, start_index):
            # Build label with status indicators
            label = group_name
            if group_name == current_group:
                label += " (current)"
            
            # Add status indicator
            if group_data['in_instructions']:
                label += " ✓"  # In instructions
            else:
                label += " ○"  # Available but not in instructions
            
            # Add description
            if group_data['description']:
                label += f" - {group_data['description']}"
            
            menu_items.append({
                'key': str(i),
                'label': label,
                'value': group_name
            })
        
        # Add custom group input option
        custom_key = str(len(menu_items) + 1)
        menu_items.append({
            'key': custom_key,
            'label': "Enter custom group name",
            'value': '__custom__'
        })
        
        print(f"\n{prompt}")
        print("Legend: ✓ = In instructions, ○ = Standard group available")
        
        # Use existing menu system
        default_key = self._find_default_key(menu_items)
        choice = self._get_menu_choice(
            "",  # Empty prompt since we already printed it
            menu_items,
            default_key,
            include_back=include_back
        )
        
        # Handle back option first
        if choice == 'b':
            return None
            
        # Convert choice key to value
        choice_value = self._get_choice_value(choice, menu_items)
        
        # Handle custom group input
        if choice_value == '__custom__':
            custom_name = input("Enter group name: ").strip()
            if custom_name:
                return custom_name
            else:
                return None
        
        return choice_value
    
    def _get_config_counts(self, config_data=None, format_output=False):
        """
        Get counts of groups, users, and paths from configuration data
        
        Args:
            config_data: Either a list of documents (with 'type' field) or None to use wizard state
            format_output: If True, return formatted string; if False, return dict with counts
            
        Returns:
            Dict with counts or formatted string
        """
        if config_data is None:
            # Count from wizard state
            group_count = len(self.groups)
            user_count = len(self.users)
            path_count = len(self.instructions.get('paths', {}))
        else:
            # Count from document list (config_data is list of documents with 'type' field)
            group_count = sum(1 for doc in config_data if doc.get('type') == 'group')
            user_count = sum(1 for doc in config_data if doc.get('type') == 'user')
            path_count = sum(1 for doc in config_data if doc.get('type') == 'path')
        
        counts = {
            'groups': group_count,
            'users': user_count,
            'paths': path_count
        }
        
        if format_output:
            return f"Groups: {group_count}\nUsers: {user_count}\nPaths: {path_count}"
        else:
            return counts
    
    def _display_path_template(self, template: dict, path_name: str):
        """Display path permission template information"""
        print(f"\nPath: {path_name}")
        print(f"Description: {template.get('description', 'No description')}")
        print(f"Owner: {template.get('owner', 'unset')}")
        print(f"Group: {template.get('group', 'unset')}")
        print(f"Mode: {template.get('mode', 'unset')}")
        
        acls = template.get('acls', [])
        if acls:
            print(f"ACLs: {', '.join(acls)}")
        else:
            print("ACLs: None")
            
        default_acls = template.get('default_acls', {})
        if default_acls:
            print("Default ACLs:")
            for acl_type, acl_entries in default_acls.items():
                print(f"  {acl_type}: {', '.join(acl_entries)}")
        else:
            print("Default ACLs: None")
    
    def _edit_path_template_interactively(self, path_name: str, template: dict) -> Optional[dict]:
        """Edit path permission template interactively"""
        print(f"\n{self._wrap_title('Edit Path Template')}")
        print(f"Editing permissions for: {path_name}")
        
        edited_template = template.copy()
        
        while True:
            print(f"\nCurrent configuration:")
            self._display_path_template(edited_template, path_name)
            
            # Build edit menu
            edit_choices = [
                {'key': '1', 'label': 'Edit Description', 'value': 'description'},
                {'key': '2', 'label': 'Edit Owner', 'value': 'owner'},
                {'key': '3', 'label': 'Edit Group', 'value': 'group'},
                {'key': '4', 'label': 'Edit Mode (Permissions)', 'value': 'mode'},
                {'key': '5', 'label': 'Edit ACLs', 'value': 'acls'},
                {'key': '6', 'label': 'Edit Default ACLs', 'value': 'default_acls'},
                {'key': 's', 'label': 'Save Changes', 'value': 'save'},
                {'key': 'c', 'label': 'Cancel (Discard Changes)', 'value': 'cancel'}
            ]
            
            choice_key = self._get_menu_choice("Select field to edit", edit_choices, 's', include_back=False)
            choice_value = self._get_choice_value(choice_key, edit_choices, 'save')
            
            if choice_value == 'save':
                return edited_template
            elif choice_value == 'cancel':
                return None
            elif choice_value == 'description':
                new_desc = input(f"Description [{edited_template.get('description', '')}]: ").strip()
                if new_desc:
                    edited_template['description'] = new_desc
            elif choice_value == 'owner':
                new_owner = input(f"Owner [{edited_template.get('owner', 'root')}]: ").strip()
                if new_owner:
                    edited_template['owner'] = new_owner
            elif choice_value == 'group':
                # Use group selection menu for group editing
                if self.groups:
                    selected_group = self._select_group_from_list(
                        f"Select group (current: {edited_template.get('group', 'root')}):",
                        include_none=True,
                        none_label="Enter custom group name",
                        current_group=edited_template.get('group'),
                        include_back=True
                    )
                    if selected_group is not None:
                        edited_template['group'] = selected_group
                else:
                    new_group = input(f"Group [{edited_template.get('group', 'root')}]: ").strip()
                    if new_group:
                        edited_template['group'] = new_group
            elif choice_value == 'mode':
                print("\nCommon modes:")
                print("  755 - rwxr-xr-x (directories)")
                print("  644 - rw-r--r-- (files)")
                print("  2775 - rwxrwsr-x (setgid directory)")
                print("  2770 - rwxrws--- (setgid directory, group only)")
                print("  640 - rw-r----- (restricted file)")
                new_mode = input(f"Mode [{edited_template.get('mode', '755')}]: ").strip()
                if new_mode:
                    edited_template['mode'] = new_mode
            elif choice_value == 'acls':
                self._edit_template_acls(edited_template)
            elif choice_value == 'default_acls':
                self._edit_template_default_acls(edited_template)
    
    def _edit_template_acls(self, template: dict):
        """Edit ACLs in path template"""
        acls = template.get('acls', [])
        
        while True:
            print(f"\nCurrent ACLs: {acls if acls else 'None'}")
            print("\n1) Add ACL entry")
            print("2) Remove ACL entry") 
            print("3) Clear all ACLs")
            print("d) Done editing ACLs")
            
            choice = input("Select option [d]: ").strip() or 'd'
            
            if choice == 'd':
                template['acls'] = acls
                break
            elif choice == '1':
                print("\nACL Examples:")
                print("  g:groupname:rwX - Group read/write/execute")
                print("  u:username:r-- - User read-only")
                print("  g:shuttle_admins:rwX - Full access for admin group")
                new_acl = input("Enter ACL entry: ").strip()
                if new_acl and new_acl not in acls:
                    acls.append(new_acl)
                    print(f"✅ Added ACL: {new_acl}")
            elif choice == '2':
                if acls:
                    print("Select ACL to remove:")
                    for i, acl in enumerate(acls, 1):
                        print(f"  {i}) {acl}")
                    try:
                        idx = int(input("Enter number: "))
                        if 1 <= idx <= len(acls):
                            removed = acls.pop(idx - 1)
                            print(f"✅ Removed ACL: {removed}")
                    except ValueError:
                        print("❌ Invalid selection")
                else:
                    print("No ACLs to remove")
            elif choice == '3':
                acls.clear()
                print("✅ Cleared all ACLs")
    
    def _edit_template_default_acls(self, template: dict):
        """Edit default ACLs in path template"""
        default_acls = template.get('default_acls', {})
        
        while True:
            print(f"\nCurrent Default ACLs:")
            if default_acls:
                for acl_type, entries in default_acls.items():
                    print(f"  {acl_type}: {', '.join(entries)}")
            else:
                print("  None")
            
            print("\n1) Edit file default ACLs")
            print("2) Edit directory default ACLs")
            print("3) Clear all default ACLs")
            print("d) Done editing default ACLs")
            
            choice = input("Select option [d]: ").strip() or 'd'
            
            if choice == 'd':
                template['default_acls'] = default_acls
                break
            elif choice == '1':
                self._edit_acl_entries('file', default_acls)
            elif choice == '2':
                self._edit_acl_entries('directory', default_acls)
            elif choice == '3':
                default_acls.clear()
                print("✅ Cleared all default ACLs")
    
    def _edit_acl_entries(self, acl_type: str, default_acls: dict):
        """Edit specific ACL type entries"""
        entries = default_acls.get(acl_type, [])
        
        print(f"\nCurrent {acl_type} default ACLs: {', '.join(entries) if entries else 'None'}")
        print(f"\nCommon {acl_type} ACL patterns:")
        if acl_type == 'file':
            print("  u::rw- (owner read/write)")
            print("  g::rw- (group read/write)")
            print("  o::--- (others no access)")
        else:
            print("  u::rwx (owner read/write/execute)")
            print("  g::rwx (group read/write/execute)")
            print("  o::--- (others no access)")
        
        new_entries = input(f"Enter {acl_type} ACLs (comma-separated): ").strip()
        if new_entries:
            entries_list = [e.strip() for e in new_entries.split(',') if e.strip()]
            default_acls[acl_type] = entries_list
            print(f"✅ Updated {acl_type} default ACLs")
    
    def _select_multiple_groups(self, prompt: str, already_selected: List[str] = None,
                               exclude_groups: List[str] = None, primary_group: str = None) -> List[str]:
        """
        Enhanced multiple group selection with add/remove capability
        
        Returns:
            List of selected group names
        """
        selected = already_selected.copy() if already_selected else []
        
        while True:
            # Build combined menu with selected groups (removable) and available groups (addable)
            all_groups = self._get_all_available_groups()
            
            # Apply exclusions
            excluded_set = set(exclude_groups) if exclude_groups else set()
            
            # Build menu items
            menu_items = []
            
            # First section: Currently selected groups (removable)
            if selected:
                print(f"\nCurrently selected:")
                for i, group_name in enumerate(selected):
                    group_info = all_groups.get(group_name, {'description': 'Custom group'})
                    description = group_info.get('description', '')
                    label = f"{group_name} - Remove from selection"
                    if description:
                        label += f" ({description})"
                    
                    menu_items.append({
                        'key': f"-{i+1}",
                        'label': label,
                        'value': f"REMOVE:{group_name}"
                    })
            
            # Add "Done" option
            menu_items.append({
                'key': 'd',
                'label': "Done selecting groups",
                'value': 'DONE'
            })
            
            # Second section: Available groups to add (excluding selected and excluded)
            available_groups = {k: v for k, v in all_groups.items() 
                              if k not in selected and k not in excluded_set}
            
            # Add special action for selecting all available groups
            if len(available_groups) > 1:  # Only show if there are multiple groups to select
                menu_items.append({
                    'key': '0',
                    'label': "Select All Available Groups (Special Action)",
                    'value': 'SELECT_ALL'
                })
            
            # Sort: standard first, then custom
            standard_groups = [(k, v) for k, v in available_groups.items() if v['source'] == 'standard']
            custom_groups = [(k, v) for k, v in available_groups.items() if v['source'] == 'custom']
            all_sorted = sorted(standard_groups) + sorted(custom_groups)
            
            # Add available groups
            for i, (group_name, group_data) in enumerate(all_sorted, 1):
                # Build label with status indicator
                label = group_name
                if group_data['in_instructions']:
                    label += " ✓"  # In instructions
                else:
                    label += " ○"  # Available but not in instructions
                
                # Add description
                if group_data['description']:
                    label += f" - {group_data['description']}"
                
                menu_items.append({
                    'key': str(i),
                    'label': label,
                    'value': f"ADD:{group_name}"
                })
            
            # Add custom group input option
            custom_key = str(len([item for item in menu_items if not item['value'].startswith('REMOVE:')]))
            menu_items.append({
                'key': custom_key,
                'label': "Enter custom group name",
                'value': 'CUSTOM'
            })
            
            # Display prompt
            print(f"\n{prompt}")
            if primary_group:
                print(f"Primary group: {primary_group} (not available for secondary groups)")
            if selected:
                print("Legend: ✓ = In instructions, ○ = Standard group available")
            
            # Use menu system
            default_key = 'd'  # Default to "Done"
            choice = self._get_menu_choice(
                "",  # Empty since we already printed the prompt
                menu_items,
                default_key,
                include_back=False
            )
            
            # Convert choice key to value
            choice_value = self._get_choice_value(choice, menu_items)
            
            # Handle choice
            if choice_value == 'DONE':
                break
            elif choice_value == 'SELECT_ALL':
                # Add all available groups to selection
                added_count = 0
                for group_name in available_groups.keys():
                    if group_name not in selected:
                        selected.append(group_name)
                        added_count += 1
                print(f"✅ Added {added_count} groups to selection")
            elif choice_value == 'CUSTOM':
                custom_name = input("Enter group name: ").strip()
                if custom_name and custom_name not in selected:
                    selected.append(custom_name)
                    print(f"✅ Added {custom_name}")
                elif custom_name in selected:
                    print(f"⚠️  {custom_name} already selected")
            elif choice_value.startswith('REMOVE:'):
                group_to_remove = choice_value[7:]  # Remove "REMOVE:" prefix
                if group_to_remove in selected:
                    selected.remove(group_to_remove)
                    print(f"✅ Removed {group_to_remove}")
            elif choice_value.startswith('ADD:'):
                group_to_add = choice_value[4:]  # Remove "ADD:" prefix
                if group_to_add not in selected:
                    selected.append(group_to_add)
                    print(f"✅ Added {group_to_add}")
        
        return selected
    
    # ============================================================================
    # User Builder Helper Methods
    # ============================================================================

    def _add_user_from_template_data(self, template_data: Dict[str, Any], 
                                    name: str = None, source: str = None, 
                                    account_type: str = None, primary_group: str = None, 
                                    secondary_groups: List[str] = None, shell: str = None, 
                                    home_directory: str = None, create_home: bool = None,
                                    auth_method: str = None) -> None:
        """
        Add user from direct template data (no template name lookup)
        
        Same override behavior as _add_templated_user but works with template_data directly.
        This enables data-driven user creation without hardcoded template names.
        
        Args:
            template_data: Complete user template dictionary
            name: Override username (optional)
            source: Override user source (optional) 
            account_type: Override account type (optional)
            primary_group: Override primary group (optional)
            secondary_groups: Override secondary groups (optional)
            shell: Override shell (optional)
            home_directory: Override home directory (optional)
            create_home: Override create_home flag (optional)
            auth_method: Samba auth method if applicable (optional)
        """
        # Start with a copy of the template data
        user_template = template_data.copy()
        
        # Apply simple overrides
        if name is not None:
            user_template['name'] = name
        if source is not None:
            user_template['source'] = source
        if account_type is not None:
            user_template['account_type'] = account_type
        if shell is not None:
            user_template['shell'] = shell
        if home_directory is not None:
            user_template['home_directory'] = home_directory
        if create_home is not None:
            user_template['create_home'] = create_home
            
        # Handle groups structure (nested dictionary)
        if primary_group is not None or secondary_groups is not None:
            if 'groups' not in user_template:
                user_template['groups'] = {}
            if primary_group is not None:
                user_template['groups']['primary'] = primary_group
            if secondary_groups is not None:
                user_template['groups']['secondary'] = secondary_groups
                
        # Handle samba auth method if provided and samba is enabled
        if auth_method is not None and user_template.get('samba', {}).get('enabled', False):
            user_template['samba']['auth_method'] = auth_method
            
        # Add to instructions
        self._add_user_to_instructions(user_template)
    
    def _process_user_templates(self, templates: Dict[str, Dict], accept_defaults: bool = False, 
                               allow_edit: bool = True) -> int:
        """
        Process a set of user templates - either all or with interactive prompts
        
        Unified template processor that enables data-driven user creation for both
        accept-defaults mode and interactive mode.
        
        Args:
            templates: Dictionary of template_name -> template_data
            accept_defaults: If True, auto-add recommended templates; if False, prompt for each
            allow_edit: If True, allow editing template values in interactive mode
            
        Returns:
            Number of users added
        """
        added_count = 0
        
        if accept_defaults:
            # Auto-add all recommended templates
            for template_name, template_data in templates.items():
                if template_data.get('recommended', True):
                    self._add_user_from_template_data(template_data.copy())
                    added_count += 1
                    print(f"   ✓ Added {template_data['name']}")
        else:
            # Interactive mode - offer "add all" option first
            print(f"\n{self._wrap_title('USER CONFIGURATION')}")
            print(f"Found {len(templates)} standard user templates")
            
            # Show summary of available users
            recommended_users = [name for name, data in templates.items() if data.get('recommended', True)]
            optional_users = [name for name, data in templates.items() if not data.get('recommended', True)]
            
            if recommended_users:
                print(f"Recommended users: {', '.join(recommended_users)}")
            if optional_users:
                print(f"Optional users: {', '.join(optional_users)}")
            
            print()
            
            # Ask if user wants to add all recommended users
            if recommended_users and self._confirm("Add all recommended standard users?", True):
                # Add all recommended users
                for template_name, template_data in templates.items():
                    if template_data.get('recommended', True):
                        self._add_user_from_template_data(template_data.copy())
                        added_count += 1
                        print(f"   ✓ Added {template_data['name']}")
                
                # Ask how to handle optional users (same pattern as recommended users)
                if optional_users:
                    print()
                    if self._confirm("Add all optional users with defaults?", True):
                        # Add all optional users with defaults (no individual review)
                        for template_name, template_data in templates.items():
                            if not template_data.get('recommended', True):
                                self._add_user_from_template_data(template_data.copy())
                                added_count += 1
                                print(f"   ✓ Added {template_data['name']}")
                    else:
                        # Ask if they want to review individually instead
                        if self._confirm("Review optional users individually instead?", False):
                            # Process only optional users individually
                            optional_templates = {name: data for name, data in templates.items() 
                                                if not data.get('recommended', True)}
                            added_count += self._process_templates_individually(optional_templates, allow_edit)
            else:
                # Process all templates individually
                added_count = self._process_templates_individually(templates, allow_edit)
                    
        return added_count
    
    def _process_templates_individually(self, templates: Dict[str, Dict], allow_edit: bool = True) -> int:
        """Process user templates one by one with individual prompts"""
        added_count = 0
        
        for template_name, template_data in templates.items():
            should_add = False
            user_data = None
            
            # Display full template details
            self._display_full_template(template_name, template_data)
            
            # Three-way choice: yes, no, or edit
            if allow_edit:
                choice = self._get_template_action()
                
                if choice == 'y':
                    should_add = True
                    user_data = template_data.copy()
                elif choice == 'e':
                    # Edit the template
                    edited_data = self._edit_template_interactively(template_name, template_data)
                    if edited_data:
                        should_add = True
                        user_data = edited_data
                # 'n' means skip (should_add remains False)
            else:
                # Simple yes/no without edit option
                prompt = f"Add {template_name}?"
                default = template_data.get('recommended', True)
                if self._confirm(prompt, default):
                    should_add = True
                    user_data = template_data.copy()
            
            # Core action - single point of user creation
            if should_add and user_data:
                self._add_user_from_template_data(user_data)
                added_count += 1
                print(f"   ✓ Added {user_data['name']}")
        
        return added_count
    
    def _get_user_templates_for_environment(self, environment: str = 'production') -> Dict[str, Dict]:
        """Get user templates for specified environment"""
        return get_standard_user_templates(environment)
    
    def _get_current_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get current system information for an existing user"""
        try:
            import pwd
            import grp
            
            # Get user info
            user_info = pwd.getpwnam(username)
            
            # Get primary group name
            primary_group = grp.getgrgid(user_info.pw_gid).gr_name
            
            # Get secondary groups
            secondary_groups = []
            for group in grp.getgrall():
                if username in group.gr_mem:
                    secondary_groups.append(group.gr_name)
            
            return {
                'name': user_info.pw_name,
                'uid': user_info.pw_uid,
                'gid': user_info.pw_gid,
                'shell': user_info.pw_shell,
                'home_directory': user_info.pw_dir,
                'groups': {
                    'primary': primary_group,
                    'secondary': secondary_groups
                }
            }
        except (KeyError, ImportError):
            # User doesn't exist or can't access system info
            return None
    
    def _edit_groups_with_context(self, edited_data: Dict[str, Any], current_user_info: Optional[Dict[str, Any]]):
        """Context-aware group editing with 4-option reconciliation"""
        template_groups = edited_data.get('groups', {})
        template_primary = template_groups.get('primary')
        template_secondary = template_groups.get('secondary', [])
        
        if current_user_info:
            current_primary = current_user_info['groups']['primary']
            current_secondary = current_user_info['groups']['secondary']
            
            print(f"\n=== Group Configuration ===")
            print(f"Current system primary group: {current_primary}")
            print(f"Current system secondary groups: {', '.join(current_secondary) if current_secondary else 'None'}")
            print(f"Template primary group: {template_primary}")
            print(f"Template secondary groups: {', '.join(template_secondary) if template_secondary else 'None'}")
            
            # Primary group reconciliation
            if current_primary != template_primary:
                print(f"\n⚠️  Primary group mismatch!")
                choice = self._get_choice(
                    "How to handle primary group:",
                    [
                        ("1", "Keep current system group", current_primary),
                        ("2", "Use template group", template_primary),
                        ("3", "Copy current to instructions", current_primary),
                        ("4", "Choose new group", None)
                    ],
                    "1"
                )
                
                if choice == "1":
                    # Remove from instructions (keep current)
                    template_groups['primary'] = None
                elif choice == "2":
                    # Keep template value (no change)
                    pass
                elif choice == "3":
                    # Copy current to instructions
                    template_groups['primary'] = current_primary
                elif choice == "4":
                    # Choose new value
                    new_primary = self._select_group_from_list("Select new primary group:")
                    template_groups['primary'] = new_primary
            
            # Secondary groups reconciliation
            current_set = set(current_secondary)
            template_set = set(template_secondary)
            if current_set != template_set:
                print(f"\n⚠️  Secondary groups differ!")
                choice = self._get_choice(
                    "How to handle secondary groups:",
                    [
                        ("1", "Keep current system groups", current_secondary),
                        ("2", "Use template groups", template_secondary),
                        ("3", "Copy current to instructions", current_secondary),
                        ("4", "Choose new groups", None)
                    ],
                    "1"
                )
                
                if choice == "1":
                    template_groups['secondary'] = []
                elif choice == "2":
                    pass
                elif choice == "3":
                    template_groups['secondary'] = current_secondary
                elif choice == "4":
                    new_secondary = self._select_multiple_groups(
                        "Select secondary groups:",
                        already_selected=template_secondary,
                        exclude_groups=[template_primary] if template_primary else [],
                        primary_group=template_primary
                    )
                    template_groups['secondary'] = new_secondary
        else:
            # No current user info - standard template editing
            print(f"\n=== Group Configuration ===")
            print(f"Primary group: {template_primary or 'None'}")
            print(f"Secondary groups: {', '.join(template_secondary) if template_secondary else 'None'}")
            
            if self._confirm("Edit group configuration?", False):
                # Edit primary group
                if self._confirm("Change primary group?", False):
                    new_primary = self._select_group_from_list("Select primary group:")
                    template_groups['primary'] = new_primary
                
                # Edit secondary groups
                if self._confirm("Edit secondary groups?", False):
                    new_secondary = self._select_multiple_groups(
                        "Select secondary groups:",
                        already_selected=template_secondary,
                        exclude_groups=[template_primary] if template_primary else [],
                        primary_group=template_primary
                    )
                    template_groups['secondary'] = new_secondary
        
        edited_data['groups'] = template_groups

    def _edit_shell_with_context(self, edited_data: Dict[str, Any], current_user_info: Optional[Dict[str, Any]]):
        """Context-aware shell editing with 4-option reconciliation"""
        template_shell = edited_data.get('shell', '/bin/bash')
        
        if current_user_info:
            current_shell = current_user_info['shell']
            
            print(f"\n=== Shell Configuration ===")
            print(f"Current system shell: {current_shell}")
            print(f"Template shell: {template_shell}")
            
            if current_shell != template_shell:
                print(f"\n⚠️  Shell mismatch!")
                choice = self._get_choice(
                    "How to handle shell:",
                    [
                        ("1", "Keep current system shell", current_shell),
                        ("2", "Use template shell", template_shell),
                        ("3", "Copy current to instructions", current_shell),
                        ("4", "Choose new shell", None)
                    ],
                    "1"
                )
                
                if choice == "1":
                    # Remove from instructions (keep current)
                    if 'shell' in edited_data:
                        del edited_data['shell']
                elif choice == "2":
                    # Keep template value (no change)
                    pass
                elif choice == "3":
                    # Copy current to instructions
                    edited_data['shell'] = current_shell
                elif choice == "4":
                    # Choose new value
                    common_shells = ['/bin/bash', '/bin/sh', '/usr/sbin/nologin', '/bin/zsh']
                    print("Common shells:")
                    for i, shell in enumerate(common_shells, 1):
                        print(f"  {i}) {shell}")
                    print(f"  {len(common_shells) + 1}) Custom")
                    
                    shell_choice = self._get_choice("Select shell:", 
                                                   [str(i) for i in range(1, len(common_shells) + 2)], "1")
                    
                    if shell_choice == str(len(common_shells) + 1):
                        new_shell = input("Enter shell path: ").strip()
                    else:
                        new_shell = common_shells[int(shell_choice) - 1]
                    
                    if new_shell:
                        edited_data['shell'] = new_shell
        else:
            # No current user info - standard template editing
            print(f"\n=== Shell Configuration ===")
            print(f"Current shell: {template_shell}")
            if self._confirm("Change shell?", False):
                common_shells = ['/bin/bash', '/bin/sh', '/usr/sbin/nologin', '/bin/zsh']
                print("Common shells:")
                for i, shell in enumerate(common_shells, 1):
                    print(f"  {i}) {shell}")
                print(f"  {len(common_shells) + 1}) Custom")
                
                shell_choice = self._get_choice("Select shell:", 
                                               [str(i) for i in range(1, len(common_shells) + 2)], "1")
                
                if shell_choice == str(len(common_shells) + 1):
                    new_shell = input("Enter shell path: ").strip()
                else:
                    new_shell = common_shells[int(shell_choice) - 1]
                
                if new_shell:
                    edited_data['shell'] = new_shell
    
    def _display_full_template(self, template_name: str, template_data: Dict[str, Any]):
        """Display complete template information for user review"""
        category = template_data.get('category', 'unknown')
        description = template_data.get('description', 'No description available')
        
        print(f"\n{template_name} ({category}):")
        print(f"   {description}")
        
        # Show key template details
        source = template_data.get('source', 'local')
        account_type = template_data.get('account_type', 'unknown')
        print(f"   Source: {source}, Type: {account_type}")
        
        # Show groups
        groups = template_data.get('groups', {})
        primary_group = groups.get('primary', 'None')
        secondary_groups = groups.get('secondary', [])
        print(f"   Primary group: {primary_group}")
        if secondary_groups:
            print(f"   Secondary groups: {', '.join(secondary_groups)}")
        else:
            print(f"   Secondary groups: None")
        
        # Show shell (for interactive accounts)
        if account_type in ['interactive', 'admin']:
            shell = template_data.get('shell', '/bin/bash')
            print(f"   Shell: {shell}")
        
        # Show home directory (for local accounts)
        if source == 'local':
            home_dir = template_data.get('home_directory', 'Not specified')
            create_home = template_data.get('create_home', False)
            print(f"   Home directory: {home_dir} ({'will create' if create_home else 'no creation'})")
        elif source == 'existing':
            print(f"   Home directory: Using existing user's home directory")
        
        # Show Samba access (default to disabled if not specified)
        samba_enabled = template_data.get('samba', {}).get('enabled', False)
        print(f"   Samba access: {'Enabled' if samba_enabled else 'Disabled'}")
        
        # Show password setup guidance
        if account_type in ['interactive', 'admin']:
            print(f"   ⚠️  Password setup: Manual setup required after installation")
            print(f"        sudo passwd {template_name}")
            if samba_enabled:
                print(f"        sudo smbpasswd -a {template_name}")
        elif account_type == 'service':
            print(f"   🔒 Password: None (service account uses nologin shell)")
        else:
            print(f"   ℹ️  Password: Manual setup may be required after installation")

    def _get_template_action(self) -> str:
        """Get user's choice for template action (yes/no/edit)"""
        template_action_choices = [
            {'key': 'y', 'label': 'Yes, add with defaults', 'value': 'y'},
            {'key': 'n', 'label': 'No, skip this user', 'value': 'n'},
            {'key': 'e', 'label': 'Edit template values', 'value': 'e'}
        ]
        
        choice = self._get_menu_choice(
            "",  # Empty title since template info was already displayed above
            template_action_choices,
            "y",  # Default to yes
            include_back=False  # No back option for this choice
        )
        
        return self._get_choice_value(choice, template_action_choices, "y")
    
    def _edit_template_interactively(self, template_name: str, template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Context-aware interactive template editing
        
        Shows current system state for existing users and provides 4-option reconciliation
        for each configurable field.
        
        Args:
            template_name: Name of the template being edited
            template_data: Original template data
            
        Returns:
            Modified template data or None if cancelled
        """
        print(f"\n=== Editing {template_name} ===")
        
        # Start with a copy
        edited_data = template_data.copy()
        
        # 1. Edit name (always allow)
        current_name = edited_data.get('name', template_name)
        new_name = input(f"Username [{current_name}]: ").strip()
        if new_name:
            edited_data['name'] = new_name
        
        # 2. Edit source type
        current_source = edited_data.get('source', 'local')
        print(f"\nCurrent source: {current_source}")
        if self._confirm("Change source type?", False):
            edited_data['source'] = self._get_user_type()
        
        # Get current system info if this is an existing user
        current_user_info = None
        if edited_data.get('source') == 'existing':
            current_user_info = self._get_current_user_info(edited_data['name'])
        
        # 3. Edit account type (for local accounts)
        if edited_data.get('source') == 'local':
            current_account_type = edited_data.get('account_type', 'service')
            print(f"\n=== Account Type ===")
            print(f"Current account type: {current_account_type}")
            if self._confirm("Change account type?", False):
                choices = [
                    {'key': '1', 'label': 'Service - No shell, application access only'},
                    {'key': '2', 'label': 'Interactive - Shell access for human users'}
                ]
                type_choice = self._get_menu_choice(
                    "Select account type",
                    choices,
                    default_key='1',
                    include_back=False
                )
                edited_data['account_type'] = "service" if type_choice == "1" else "interactive"
        
        # 4. Edit home directory (for local accounts)
        if edited_data.get('source') == 'local':
            current_home = edited_data.get('home_directory', '/home/user')
            print(f"\n=== Home Directory ===")
            print(f"Current home directory: {current_home}")
            if self._confirm("Change home directory?", False):
                new_home = input(f"Home directory [{current_home}]: ").strip()
                if new_home:
                    edited_data['home_directory'] = new_home
            
            # Create home directory flag
            current_create_home = edited_data.get('create_home', True)
            print(f"Create home directory: {'Yes' if current_create_home else 'No'}")
            if self._confirm("Toggle create home directory?", False):
                edited_data['create_home'] = not current_create_home
        
        # 5. Context-aware group configuration
        self._edit_groups_with_context(edited_data, current_user_info)
        
        # 6. Context-aware shell configuration (for interactive accounts)
        if edited_data.get('account_type') in ['interactive', 'admin']:
            self._edit_shell_with_context(edited_data, current_user_info)
        
        # 5. Samba configuration (always available)
        samba_config = edited_data.get('samba', {'enabled': False})
        samba_enabled = samba_config.get('enabled', False)
        print(f"\n=== Samba Configuration ===")
        print(f"Samba access: {'Enabled' if samba_enabled else 'Disabled'}")
        if self._confirm("Toggle Samba access?", False):
            if 'samba' not in edited_data:
                edited_data['samba'] = {}
            edited_data['samba']['enabled'] = not samba_enabled
        
        # Show full template preview again for confirmation
        print(f"\n{self._wrap_title('Final Configuration')}")
        self._display_full_template(edited_data.get('name', template_name), edited_data)
        
        if self._confirm("\nApply these changes?", True):
            return edited_data
        else:
            return None
    
    def _add_samba_to_user(self, user: Dict[str, Any], enabled: bool = True, 
                          auth_method: str = 'smbpasswd') -> Dict[str, Any]:
        """Add samba configuration to user object
        
        Args:
            user: User dictionary to modify
            enabled: Whether samba is enabled
            auth_method: Authentication method ('smbpasswd', 'domain')
            
        Returns:
            Modified user dictionary
        """
        user['samba'] = {
            'enabled': enabled,
            'auth_method': auth_method
        }
        return user
    
    def _toggle_samba_access(self, user: Dict[str, Any]) -> bool:
        """Toggle Samba access for a user
        
        Returns:
            bool: True if Samba is now enabled, False if disabled
        """
        if 'samba' in user and user['samba'].get('enabled'):
            user['samba']['enabled'] = False
            return False
        else:
            user['samba'] = STANDARD_SAMBA_CONFIG.copy()
            return True
    
    def _enable_samba_access(self, user: Dict[str, Any]) -> None:
        """Enable Samba access for a user"""
        user['samba'] = STANDARD_SAMBA_CONFIG.copy()
        
    def _disable_samba_access(self, user: Dict[str, Any]) -> None:
        """Disable Samba access for a user"""
        if 'samba' in user:
            user['samba']['enabled'] = False
        else:
            user['samba'] = {'enabled': False}
    
    def _is_samba_enabled(self, user: Dict[str, Any]) -> bool:
        """Check if Samba is enabled for a user"""
        return user.get('samba', {}).get('enabled', False)
    
    def run(self) -> Dict[str, Any]:
        """Run the interactive wizard"""
        print(f"\n{self._wrap_title('Shuttle Configuration Wizard')}")
        print("This wizard will help you create a user setup configuration.")
        print("")
        
        # Select deployment mode first
        mode = self._select_deployment_mode()
        
        if mode in ['development', 'production']:
            config = self._run_standard_mode(mode)
            
            # Validate configuration before offering customization
            self._validate_configuration_before_customization()
            
            # Option to customize standard configuration
            if self._offer_customization():
                return self._run_custom_mode(base_config=config)
            return config
        else:  # custom
            return self._run_custom_mode()
    
    def _select_deployment_mode(self) -> str:
        """Select the deployment mode using generic menu system"""
        description = self._wrap_title("Deployment Mode Selection")
        
        deployment_choices = [
            {'key': '1', 'label': 'Development - For Development and Testing - Single admin user with full access', 'value': 'development'},
            {'key': '2', 'label': 'Production - Production roles and security model', 'value': 'production'},
            {'key': '3', 'label': 'Custom - Build your own permission model', 'value': 'custom'}
        ]
        
        choice = self._get_menu_choice(
            description, 
            deployment_choices,
            "2",  # Default to production mode
            include_back=False  # No back option for main mode selection
        )
        
        selected_mode = self._get_choice_value(choice, deployment_choices, "production")
        print(f"\n✅ Selected: {selected_mode.title()} Mode")
        return selected_mode
    
    def _run_standard_mode(self, standard: str) -> Dict[str, Any]:
        """Run standard mode for development or production standards"""

        # accept only development mode or production mode
        # default to production

        if standard not in ['development', 'production']:
            standard = 'production'

        config = STANDARD_MODE_CONFIGS[standard]
        
        print(self._wrap_title(config['title']))
        print(f"\n{config['description']}")


        
        # Apply mode-specific defaults using shared method
        self._apply_mode_specific_defaults(standard)
        
        # Ask if user wants to accept all defaults
        accept_defaults = self._confirm(config['accept_prompt'], True)
        
        if accept_defaults:
            print(f"✅ {config['success_message']}")
            # Set all components to recommended defaults
            self._add_components_to_instructions(config['components'])
            
            # Add groups based on mode
            if standard == 'development':
                self._add_groups_to_instructions(get_development_admin_group())
            else:  # production
                self._add_groups_to_instructions(get_standard_groups())
            
        else:
            print("📋 Step-by-step configuration...")
            # Component selection using unified method
            self._configure_components_interactive(firewall_default=config['firewall_default'])
            
            # Add groups based on mode - interactive selection
            if standard == 'development':
                self._select_standard_groups_interactive(get_development_admin_group(), "development")
            else:  # production
                self._select_standard_groups_interactive(get_standard_groups(), "production")

        # Create users with unified approach - works for both accept_defaults and interactive modes
        self._create_standard_users(standard, accept_defaults=accept_defaults, allow_edit=(not accept_defaults))

        # Configure path permissions
        self._configure_paths_for_environment(standard, accept_defaults)
        
        print(f"\n✅ {config['completion_message']}")
        
        if standard == 'development':
            print(f"   {config['completion_details'].format(user_count=len(self.users))}")
        else:
            print(f"   {config['completion_details'].format(user_count=len(self.users), path_count=len(self.shuttle_paths))}")
        
        return self._build_complete_config()
    
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
            print(f"\n⚠️  WARNING: Configuration has missing references:")
            
            if missing_groups:
                print(f"   Missing groups:")
                for group in sorted(missing_groups):
                    print(f"      - {group}")
            
            if missing_users:
                print(f"   Missing users:")
                for user in sorted(missing_users):
                    print(f"      - {user}")
            
            print("\n💡 These references are used in your configuration but are not defined.")
            print("   This will cause issues during installation unless these groups/users")
            print("   already exist on the target system.")
            print("\n📝 You can fix this by:")
            print("   • Choose 'Customize this configuration' to add the missing items")
            print("   • Or ensure these groups/users exist on the target system before installation")
            
            if not self._confirm("\nContinue with missing references?", False):
                print("❌ Configuration cancelled. Please fix the missing references.")
                sys.exit(1)
        else:
            print("✅ All references are properly defined")
    
    def _offer_customization(self) -> bool:
        """Ask if user wants to customize standard configuration"""
        print(f"\n{self._wrap_title('Customization Option')}")
        print("Your standard configuration is ready.")
        print("")
        
        print("📋 Customization Options:")
        print("  1) Use as-is: Deploy this configuration immediately")
        print("  2) Customize: Enter advanced mode to:")
        print("     • Add missing groups or users that were referenced")
        print("     • Modify existing users, groups, or path permissions")
        print("     • Add new users or groups")
        print("     • Fine-tune security settings")
        print("  3) Start over: Return to the beginning and choose a different approach")
        print("")
        
        choices = [
            {'key': '1', 'label': 'Use this configuration as-is'},
            {'key': '2', 'label': 'Customize this configuration'},
            {'key': '3', 'label': 'Start over'}
        ]
        
        choice = self._get_menu_choice(
            "Select an option:",
            choices,
            default_key='1',
            include_back=False
        )
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
    
    #good
    def _run_custom_mode(self, base_config=None) -> Dict[str, Any]:
        """Run custom mode - interactive builder"""
        if base_config:
            print(f"\n{self._wrap_title('CUSTOM EDIT MODE')}")
            print("Customizing your standard configuration.")
            self.instructions = base_config[0]  # Load the main config
            self.users = [doc['user'] for doc in base_config[1:] if doc.get('type') == 'user']
            self.instructions['metadata']['mode'] = 'standard_customized'
        else:
            print(f"\n{self._wrap_title('CUSTOM MODE')}")
            print("Building a custom permission model from scratch.")
            self.instructions['metadata']['mode'] = 'custom'
            # Set basic defaults
            self.instructions['metadata']['environment'] = 'custom'
            self.instructions['settings']['interactive_mode'] = 'interactive'
        
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
                self._custom_show_configuration()
            elif choice == "6":
                self._custom_validate_configuration()
            elif choice == "7":
                self._custom_manage_domain_users()
            elif choice == "d":
                # Delete configuration and return to main menu
                if self._confirm("Delete custom configuration and return to main menu?", False):
                    break
            elif choice == "r":
                # Reset configuration
                if self._confirm("Reset all configuration? This cannot be undone.", False):
                    self.groups = {}
                    self.paths = {}
                    self.users = []
                    print("✅ Configuration reset")
            elif choice == "s":
                # Save configuration and exit
                break
        
        # Return complete configuration
        return self._build_complete_config()
   
    
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
   
    def _select_user_source(self) -> str:
        """Select user source type using universal menu system"""
        user_source_choices = [
            {'key': '1', 'label': 'Existing user (any local or domain user already on this system)', 'value': 'existing'},
            {'key': '2', 'label': 'New local user (create new local user)', 'value': 'local'},
            {'key': '3', 'label': 'Create new local configuration for a domain user (create reference to AD/LDAP user)', 'value': 'domain'}
        ]
        
        # Find default key (will be '1' - lowest numbered)
        default_key = self._find_default_key(user_source_choices)
        
        # Use universal menu system
        selected_key = self._get_menu_choice(
            "User source:",
            user_source_choices,
            default_key,
            include_back=False  # No back option for this utility function
        )
        
        # Extract and return the value
        return self._get_choice_value(selected_key, user_source_choices, 'existing')
    
    def _get_username(self, prompt: str, default: str, source: str) -> str:
        """Get username with optional domain prefix"""
        username = input(f"{prompt} [{default}]: ").strip() or default
        
        if source == "domain" and self._confirm_domain_format():
            username = f"DOMAIN\\{username}"
        
        return username
    
    def _confirm_domain_format(self) -> bool:
        """Confirm if domain prefix should be added"""
        return self._confirm("Add DOMAIN\\ prefix to username?", True)
    
    # NOTE: Password handling is intentionally excluded from this wizard
    # - Service accounts (most users) don't need passwords and use nologin shells
    # - Interactive accounts require manual password setup after installation
    # - Storing passwords in YAML config files would be a security risk
    # - Use 'sudo passwd username' or 'sudo smbpasswd -a username' after installation
    
    def _confirm(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no confirmation with input validation"""
        # Always add default text for consistency
        default_text = "Yes" if default else "No"
        prompt = f"{prompt} (Default: {default_text})"
        
        default_str = "Y/n/x" if default else "y/N/x"
        
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            
            if not response:
                return default
            elif response == 'x':
                print("\nExiting wizard...")
                sys.exit(3)  # Exit code 3 for user cancellation
            elif response in ['y', 'yes', 'n', 'no']:
                return response in ['y', 'yes']
            else:
                print(f"❌ Invalid input '{response}'. Please enter 'y' for yes, 'n' for no, or 'x' to exit.")
    
    # Generic Helper Methods
    def _get_user_type(self, default_type: str = "local") -> str:
        """
        Get user type interactively - used across all modes (development, production, custom)
        
        Usage examples:
            # Development mode (typically local accounts)
            user_type = self._get_user_type("local")
            
            # Production mode (might prefer existing/domain)  
            user_type = self._get_user_type("existing")
            
            # Custom mode (let user decide)
            user_type = self._get_user_type()
        
        Args:
            default_type: Default user type ('local', 'existing', 'domain')
        
        Returns:
            Selected user type string
        """
        # Universal user type options - same for all modes
        user_type_choices = [
            {'key': '1', 'label': 'Local account - Create new local user', 'value': 'local'},
            {'key': '2', 'label': 'Existing account - Use existing local user', 'value': 'existing'},
            {'key': '3', 'label': 'Domain account - Use domain/LDAP user', 'value': 'domain'}
        ]
        
        # Find default key using generic function
        default_key = self._find_default_key(user_type_choices, default_type)
        
        # Use generic menu choice function
        selected_key = self._get_menu_choice(
            "User account type:",
            user_type_choices,
            default_key,
            include_back=False  # No back option for this utility function
        )
        
        # Extract and return the value
        return self._get_choice_value(selected_key, user_type_choices, default_type)
    
    def _create_standard_users(self, standard: str, accept_defaults: bool = False, allow_edit: bool = True) -> int:
        """
        Create standard users for the specified environment using template processor
        
        Unified user creation for both development and production standard modes.
        Replaces both _create_all_standard_roles_with_defaults and #_create_default_admin_user.
        
        Args:
            standard: Environment type - 'development' or 'production'
            accept_defaults: If True, auto-add recommended users; if False, prompt for each
            allow_edit: If True, allow editing template values in interactive mode
            
        Returns:
            Number of users added
        """
        templates = self._get_user_templates_for_environment(standard)
        users_added = self._process_user_templates(templates, accept_defaults, allow_edit)
        
        # NEW: Domain user validation and configuration
        if self.domain_integration and not accept_defaults:
            print("\n🔍 Checking for domain user requirements...")
            try:
                domain_success = self.domain_integration.validate_and_configure_domain_users()
                if not domain_success:
                    print("⚠️  Domain user configuration incomplete")
                    print("   Domain users may not be importable until configuration is completed")
            except Exception as e:
                print(f"⚠️  Domain validation failed: {e}")
        
        return users_added
    
    def _apply_mode_specific_defaults(self, mode):
        """
        Apply mode-specific default configurations.
        Consolidates common setup patterns across all modes.
        """
        if mode == 'development':
            self.instructions['metadata']['environment'] = 'development'
            self.instructions['settings']['interactive_mode'] = 'interactive'
        elif mode == 'production':
            self.instructions['metadata']['environment'] = 'production'
            self.instructions['settings']['interactive_mode'] = 'non-interactive'
        elif mode == 'custom':
            # Custom mode lets user choose these
            pass
        
        # Common defaults for all modes
        self.instructions['metadata']['mode'] = mode
        self.instructions['settings']['create_home_directories'] = True
        self.instructions['settings']['backup_existing_users'] = True
        self.instructions['settings']['validate_before_apply'] = True
    
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
    
    def _validate_all_paths(self) -> bool:
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
    
    def _validate_group_references(self) -> Set[str]:
        """Check for groups referenced in users/paths that don't exist in group configuration
        
        Returns:
            Set of missing group names
        """
        referenced_groups = set()
        configured_groups = set(self.groups.keys())
        
        # Check groups referenced by users
        for user in self.users:
            # Check primary group
            primary_group = user.get('groups', {}).get('primary')
            if primary_group:
                referenced_groups.add(primary_group)
            
            # Check secondary groups
            secondary_groups = user.get('groups', {}).get('secondary', [])
            for group in secondary_groups:
                referenced_groups.add(group)
        
        # Check groups referenced by paths
        for path, config in self.paths.items():
            # Check owner group
            if 'group' in config:
                referenced_groups.add(config['group'])
            
            # Check ACL entries
            for acl in config.get('acls', []):
                if acl.startswith('g:'):
                    # Extract group name from ACL entry (g:groupname:perms)
                    parts = acl.split(':')
                    if len(parts) >= 2:
                        referenced_groups.add(parts[1])
            
            # Check default ACL entries
            default_acls = config.get('default_acls', {})
            for acl_list in [default_acls.get('files', []), default_acls.get('directories', [])]:
                for acl in acl_list:
                    if acl.startswith('g:'):
                        parts = acl.split(':')
                        if len(parts) >= 2:
                            referenced_groups.add(parts[1])
        
        # Return groups that are referenced but not configured
        return referenced_groups - configured_groups
    
    def _validate_user_references(self) -> Set[str]:
        """Check for users referenced in path configs that don't exist in user configuration
        
        Returns:
            Set of missing user names (excluding standard system users)
        """
        referenced_users = set()
        configured_users = {user['name'] for user in self.users}
        
        # Standard system users that should not be flagged as missing
        standard_system_users = {
            'root', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp', 'mail',
            'news', 'uucp', 'proxy', 'www-data', 'backup', 'list', 'irc', 'gnats',
            'nobody', 'systemd-network', 'systemd-resolve', 'systemd-timesync',
            'messagebus', 'syslog', 'bind', 'avahi', 'colord', 'hplip', 'geoclue',
            'pulse', 'gdm', 'sshd'
        }
        
        # Include standard system users as "configured"
        configured_users.update(standard_system_users)
        
        # Check users referenced by paths
        for path, config in self.paths.items():
            # Check owner user
            if 'owner' in config:
                referenced_users.add(config['owner'])
            
            # Check ACL entries
            for acl in config.get('acls', []):
                if acl.startswith('u:'):
                    # Extract user name from ACL entry (u:username:perms)
                    parts = acl.split(':')
                    if len(parts) >= 2:
                        referenced_users.add(parts[1])
            
            # Check default ACL entries
            default_acls = config.get('default_acls', {})
            for acl_list in [default_acls.get('files', []), default_acls.get('directories', [])]:
                for acl in acl_list:
                    if acl.startswith('u:'):
                        parts = acl.split(':')
                        if len(parts) >= 2:
                            referenced_users.add(parts[1])
        
        # Return users that are referenced but not configured (excluding standard system users)
        return referenced_users - configured_users
    
    def _display_missing_references(self, context: str = ""):
        """Display missing group and user references with context"""
        missing_groups = self._validate_group_references()
        missing_users = self._validate_user_references()
        
        if missing_groups or missing_users:
            print(f"\n⚠️  WARNING: Missing references detected{' in ' + context if context else ''}:")
            
            if missing_groups:
                print(f"   📁 Missing groups: {', '.join(sorted(missing_groups))}")
            
            if missing_users:
                print(f"   👤 Missing users: {', '.join(sorted(missing_users))}")
            
            print("   💡 These are referenced in your configuration but not defined.")
            print("      Add them or they must exist on the target system.")
            print()
    
    def _get_choice(self, prompt: str, valid_choices: List[str], default: str) -> str:
        """Get a choice from valid options"""
        # Add exit option to the display
        print("x) Exit - Quit the wizard")
        print()
        
        while True:
            choice = input(f"{prompt} (Default: {default}): ").strip() or default
            if choice.lower() == 'x':
                print("\nExiting wizard...")
                sys.exit(3)  # Exit code 3 for user cancellation
            if choice in valid_choices:
                print()
                return choice
            print(f"Invalid choice. Please select from: {', '.join(valid_choices)} or x to exit")
    
    def _get_menu_choice(self, title: str, choices: List[Dict[str, Any]], 
                        default_key: str, include_back: bool = True, 
                        back_label: str = "parent menu") -> str:
        """
        Universal menu choice function - works for any menu pattern
        
        This is the core reusable function that replaces all hardcoded menu patterns.
        Any menu in the application can use this by defining a data structure.
        
        Args:
            title: Menu title/header text
            choices: List of choice dictionaries with required keys:
                    - 'key': choice key (e.g., '1', '2', 'a')
                    - 'label': display text for the choice
                    Optional keys:
                    - 'value': return value (if different from key)
                    - 'action': action to execute (for action-based menus)
            default_key: Default choice key
            include_back: Whether to add back option
            back_label: Label for back option context
        
        Returns:
            Selected choice key
            
        Pattern Examples:
        
        1) Simple value selection (like user types):
            choices = [
                {'key': '1', 'label': 'Local account', 'value': 'local'},
                {'key': '2', 'label': 'Domain account', 'value': 'domain'}
            ]
            key = self._get_menu_choice("User Type:", choices, '1', False)
            value = self._get_choice_value(key, choices, 'local')
            
        2) Action-based menus (like management menus):
            choices = [
                {'key': '1', 'label': 'Add User', 'action': self._add_user},
                {'key': '2', 'label': 'Delete User', 'action': self._delete_user}
            ]
            key = self._get_menu_choice("User Management:", choices, '1')
            self._execute_menu_choice(key, choices)
            
        3) Complex nested menus (with multi-line labels):
            choices = [
                {'key': '1', 'label': 'Option 1 - Description\n   Details: More info', 'value': 'opt1'}
            ]
            
        This pattern eliminates all hardcoded print statements and if/elif chains.
        """
        print(f"\n{title}")
        
        # Display all choices
        for choice in choices:
            print(f"{choice['key']}) {choice['label']}")
        
        # Add back option if requested
        valid_keys = [choice['key'] for choice in choices]
        if include_back:
            print("")
            print(f"b) Back to {back_label}")
            valid_keys.append('b')
            
        return self._get_choice("Select option", valid_keys, default_key)
    
    def _show_dynamic_menu(self, title: str, menu_items: List[Dict[str, Any]], 
                          parent_menu_name: str = "parent menu") -> str:
        """
        Generic menu system for dynamic content (legacy wrapper - use _get_menu_choice instead)
        
        Args:
            title: Menu title/header
            menu_items: List of menu item dictionaries with keys:
                       - 'key': menu choice key (e.g., '1', '2')  
                       - 'label': display text for menu item
                       - 'action': callable or special action name
            parent_menu_name: Name of parent menu for back option
        
        Returns:
            Selected choice key or 'b' for back
        """
        return self._get_menu_choice(title, menu_items, "b", True, parent_menu_name)
    
    def _get_choice_value(self, selected_key: str, choices: List[Dict[str, Any]], 
                         fallback_value: Any = None) -> Any:
        """
        Extract value from choice data structure based on selected key
        
        Args:
            selected_key: The key that was selected
            choices: List of choice dictionaries 
            fallback_value: Value to return if key not found
            
        Returns:
            The 'value' field from matching choice, or the 'key' if no 'value' field exists,
            or fallback_value if no match found
        """
        for choice in choices:
            if choice['key'] == selected_key:
                return choice.get('value', choice['key'])
        return fallback_value
    
    def _find_default_key(self, choices: List[Dict[str, Any]], target_value: Any = None) -> str:
        """
        Find the appropriate default key from choices list
        
        Args:
            choices: List of choice dictionaries with 'key' and optional 'value' fields
            target_value: Value to search for in 'value' fields, or None for lowest key
            
        Returns:
            Key that matches target_value, or the lowest numbered key if no match/target
            
        Examples:
            # Find key for specific value
            choices = [
                {'key': '1', 'value': 'local'}, 
                {'key': '2', 'value': 'domain'}
            ]
            key = self._find_default_key(choices, 'domain')  # Returns '2'
            
            # Get lowest numbered key (no target specified)
            key = self._find_default_key(choices)  # Returns '1'
            
            # Works with mixed key types
            choices = [
                {'key': '3', 'label': 'Option 3'},
                {'key': '1', 'label': 'Option 1'}, 
                {'key': 'a', 'label': 'Option A'}
            ]
            key = self._find_default_key(choices)  # Returns '1' (lowest numeric)
            
            # Template menu with '0' option
            choices = [
                {'key': '0', 'label': 'Add All'},
                {'key': '1', 'label': 'Template 1'}
            ]
            key = self._find_default_key(choices)  # Returns '0'
        """
        if not choices:
            return "1"  # Ultimate fallback
            
        # If target_value specified, try to find matching choice
        if target_value is not None:
            for choice in choices:
                if choice.get('value') == target_value:
                    return choice['key']
        
        # Fallback: find lowest numbered key
        numeric_keys = []
        non_numeric_keys = []
        
        for choice in choices:
            key = choice['key']
            try:
                numeric_keys.append((int(key), key))
            except ValueError:
                non_numeric_keys.append(key)
        
        # Return lowest numeric key if any exist
        if numeric_keys:
            numeric_keys.sort()
            return numeric_keys[0][1]  # Return the key string of lowest number
            
        # Return first non-numeric key if no numeric keys  
        if non_numeric_keys:
            return non_numeric_keys[0]
            
        # Ultimate fallback
        return choices[0]['key']
    
    def _execute_menu_choice(self, choice: str, menu_items: List[Dict[str, Any]]) -> bool:
        """
        Execute the action for a selected menu choice
        
        Args:
            choice: Selected choice key
            menu_items: Menu items list with action definitions
        
        Returns:
            True if action was executed, False if choice was 'b' (back)
        """
        if choice == 'b':
            return False
            
        # Find matching menu item
        for item in menu_items:
            if item['key'] == choice:
                action = item['action']
                
                # Handle different action types
                if callable(action):
                    action()
                elif isinstance(action, str):
                    # Handle special action strings
                    if hasattr(self, action):
                        getattr(self, action)()
                    else:
                        print(f"❌ Unknown action: {action}")
                else:
                    print(f"❌ Invalid action type for choice {choice}")
                return True
        
        print(f"❌ No action found for choice {choice}")
        return True
    
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
        counts = self._get_config_counts()
        description = f"""
{self._wrap_title("CUSTOM MODE MENU")}

Current configuration:
  Groups: {counts['groups']}
  Users: {counts['users']}
  Paths: {counts['paths']}

1) Manage Groups
2) Manage Users
3) Configure Path Permissions
4) Configure Components
5) Show Current Configuration
6) Validate Configuration
7) Domain User Configuration

d) Delete Custom Configuration and return to main menu
r) Reset Custom Configuration
s) Use this configuration and continue.
        """
        print(description)
        
        # Show validation warnings at the top level
        self._display_missing_references("current configuration")
    
    def _custom_manage_groups(self):
        """Manage groups in custom mode"""
        while True:
            # Build groups list dynamically
            groups_list = ""
            if self.groups:
                groups_list = "\nGroups to be created:\n"
                for name, details in sorted(self.groups.items()):
                    gid_str = str(details.get('gid', 'auto'))
                    desc = details.get('description', 'No description')
                    groups_list += f"  • {name} (GID: {gid_str}) - {desc}\n"
            
            description = f"""
{self._wrap_title("GROUP MANAGEMENT")}

Current groups in instructions: {len(self.groups)}
{groups_list}
1) Add Standard Groups to Instructions
2) Add Custom Group to Instructions
3) Remove Group from Instructions
4) Edit Group in Instructions

b) Back to Main Custom Configuration Menu
            """
            print(description)
            
            # Show missing groups validation specific to groups
            missing_groups = self._validate_group_references()
            if missing_groups:
                print(f"⚠️  Missing groups referenced in configuration: {', '.join(sorted(missing_groups))}")
                print("   💡 Add these groups to fix configuration issues")
                print()
            
            choice = self._get_choice("Select action", ["1", "2", "3", "4", "b"], "b")
            print()  # Add spacing between response and next section
            
            if choice == "1":
                self._custom_add_standard_group()
            elif choice == "2":
                self._custom_add_custom_group()
            elif choice == "3":
                self._custom_remove_group()
            elif choice == "4":
                self._custom_edit_group()
            elif choice == "b":
                break
    
    def _custom_add_custom_group(self):
        """Add a new group with template-based creation and full editing"""
        print("\n--- Add New Group ---")
        print("Select a base template, then customize all details in the editor.")
        
        # 1. Select template type first using universal menu system
        base_templates = get_custom_group_base_templates()
        
        template_choices = [
            {
                'key': '1', 
                'label': 'Standard Operations Group\n   General shuttle operations and tasks\n   Default: auto-assign GID',
                'value': 'custom_standard'
            },
            {
                'key': '2', 
                'label': 'Service-Specific Group\n   For specific services or applications\n   Default: auto-assign GID',
                'value': 'custom_service'
            },
            {
                'key': '3', 
                'label': 'Data Access Group\n   For data management and access control\n   Default: auto-assign GID',
                'value': 'custom_data'
            },
            {
                'key': '4', 
                'label': 'Administrative Group\n   For administrative privileges and tasks\n   Default: auto-assign GID',
                'value': 'custom_admin'
            }
        ]
        
        selected_key = self._get_menu_choice(
            "Select group template type:",
            template_choices,
            "1",  # Default to standard
            include_back=True,
            back_label="group management menu"
        )
        
        if selected_key == 'b':
            return
        
        template_key = self._get_choice_value(selected_key, template_choices, 'custom_standard')
        
        # 2. Load base template
        template_data = base_templates[template_key].copy()
        
        # 3. Get group name
        group_name = input("\nGroup name: ").strip()
        if not group_name:
            print("❌ Group name cannot be empty")
            return
        
        # Validate group name
        is_valid, error_msg = self._validate_group_name(group_name)
        if not is_valid:
            print(f"❌ {error_msg}")
            return
        
        # 4. Set auto-assign GID for template (will be editable in template editor)
        if template_data.get('gid') is None:
            template_data['gid'] = self._get_next_available_gid()
        
        print(f"\n✓ Loaded {template_key.replace('custom_', '')} template for '{group_name}'")
        
        # Show the template with defaults before editing
        self._display_group_template(group_name, template_data)
        
        print("\n✓ Going into template editor - you can customize all fields...")
        
        # 5. Go directly into comprehensive template editing
        edited_template = self._edit_group_template_interactively(group_name, template_data)
        if edited_template is None:
            print("❌ Group creation cancelled")
            return
        
        # 6. Add to instructions
        self._add_group_to_instructions(group_name, edited_template)
        print(f"✅ Added {group_name} to instructions")
    
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
            if name not in self.groups:
                available_groups.append((name, details))
        
        if not available_groups:
            print("\n✅ All standard groups are already added!")
            return
        
        # Build menu choices using universal menu system
        menu_choices = []
        
        # Add special action at position 0
        menu_choices.append({
            'key': '0', 
            'label': 'Add All Available Groups (Special Action)', 
            'value': 'add_all'
        })
        
        # Add individual groups starting at 1
        for i, (name, details) in enumerate(available_groups, 1):
            menu_choices.append({
                'key': str(i), 
                'label': f"{name}\n   {details['description']}", 
                'value': name
            })
        
        # Show already added groups with checkmarks (display only)
        added_display = []
        for name, details in standard_groups.items():
            if name in self.groups:
                added_display.append(f"  ✓) {name} - {details['description']} (already added)")
        
        if added_display:
            print("\nAlready Added:")
            for item in added_display:
                print(item)
        
        menu_choices.append({'key': 'b', 'label': 'Back to Group Management', 'value': 'back'})
        
        choice_key = self._get_menu_choice("Select group to add", menu_choices, 'back')
        choice_value = self._get_choice_value(choice_key, menu_choices, 'back')
        
        if choice_value == 'back':
            return
        elif choice_value == 'add_all':
            # Add all available groups
            if self._confirm(f"Add all {len(available_groups)} available standard groups?", True):
                groups_to_add = {name: details for name, details in available_groups}
                added_count = self._add_groups_to_instructions(groups_to_add)
                print(f"✅ Added {added_count} standard groups to instructions")
        else:
            # Add single group by name (choice_value is the group name)
            group_details = standard_groups[choice_value]
            self._add_group_to_instructions(choice_value, group_details)
    
    def _custom_remove_group(self):
        """Remove a group"""
        if not self.groups:
            print("No groups in instructions to remove")
            return
        
        print("\n--- Remove Group from Instructions ---")
        
        # Use the new group selection helper
        group_name = self._select_group_from_list("Select group to remove")
        
        if not group_name:  # User cancelled
            return
        
        # Use the new helper to find users using this group
        users_using = self._find_users_using_group(group_name)
        
        if users_using:
            print(f"\n⚠️  Group '{group_name}' is used by: {', '.join(users_using)}")
            if not self._confirm("Remove anyway?", False):
                return
        
        del self.groups[group_name]
        print(f"✅ Removed group '{group_name}' from instructions")
    
    def _custom_edit_group(self):
        """Edit a group using unified template editing approach"""
        if not self.groups:
            print("No groups in instructions to edit")
            return
        
        print("\n--- Edit Group in Instructions ---")
        
        # Use the new group selection helper
        group_name = self._select_group_from_list("Select group to edit")
        
        if not group_name:  # User cancelled
            return
        
        print(f"\n--- Editing Group: {group_name} ---")
        print("Using current group configuration as template for editing...")
        
        # Use existing group data as template
        template_data = self.groups[group_name].copy()
        
        # Run through unified template editor
        edited_template = self._edit_group_template_interactively(group_name, template_data)
        
        if edited_template is not None:
            # Update the group in place
            self.groups[group_name] = edited_template
            print(f"✅ Updated {group_name} in instructions")
        else:
            print("❌ Group editing cancelled")
    
    def _custom_manage_users(self):
        """Manage users in custom mode"""
        while True:
            # Build users list dynamically
            users_list = ""
            if self.users:
                users_list = "\nUsers to be created:\n"
                for user in self.users:
                    users_list += f"  • {user['name']} ({user['source']}) - {user['account_type']}\n"
            
            description = f"""
{self._wrap_title("USER MANAGEMENT")}

Users in instructions: {len(self.users)}
{users_list}
1) Add Standard Production Users
2) Add Standard Development Users
3) Add Custom User to Instructions
4) Remove User from Instructions
5) Edit User in Instructions

b) Back to Main Custom Configuration Menu
            """
            print(description)
            
            # Show missing users validation specific to users
            missing_users = self._validate_user_references()
            if missing_users:
                print(f"⚠️  Missing users referenced in path configurations: {', '.join(sorted(missing_users))}")
                print("   💡 Add these users to fix configuration issues")
                print()
            
            choice = self._get_choice("Select action", ["1", "2", "3", "4", "5", "b"], "b")
            print()  # Add spacing between response and next section
            
            if choice == "1":
                self._custom_select_individual_users('production')
            elif choice == "2":
                self._custom_select_individual_users('development')
            elif choice == "3":
                self._custom_add_user()
            elif choice == "4":
                self._custom_remove_user()
            elif choice == "5":
                self._custom_edit_user()
            elif choice == "b":
                break
    
    def _custom_add_user(self):
        """Add a new user with template-based creation and full editing"""
        print("\n--- Add New User ---")
        print("Select a base template, then customize all details in the editor.")
        
        # 1. Select template type first using universal menu system
        base_templates = get_custom_user_base_templates()
        
        template_choices = [
            {
                'key': '1', 
                'label': 'Service Account Template\n   For applications and automated processes\n   Default: /usr/sbin/nologin shell, service home directory',
                'value': 'custom_service'
            },
            {
                'key': '2', 
                'label': 'Interactive User Template\n   For human users who need shell access\n   Default: /bin/bash shell, /home directory',
                'value': 'custom_interactive'
            },
            {
                'key': '3', 
                'label': 'Existing User Template\n   For users already on the system\n   No shell/home changes, groups only',
                'value': 'custom_existing'
            }
        ]
        
        selected_key = self._get_menu_choice(
            "Select user template type:",
            template_choices,
            "1",  # Default to service account
            include_back=True,
            back_label="user management menu"
        )
        
        if selected_key == 'b':
            return
        
        template_key = self._get_choice_value(selected_key, template_choices, 'custom_service')
        
        # 2. Load base template
        template_data = base_templates[template_key].copy()
        
        # 3. Get username for template
        username = input("\nUsername: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return
        
        # Check if user already exists in instructions
        if any(u['name'] == username for u in self.users):
            print(f"❌ User '{username}' already exists in instructions")
            return
        
        # 4. Set username and basic description in template
        template_data['name'] = username
        template_data['description'] = f"Custom {template_data['category']} user - {username}"
        
        # 5. Default primary group to username if not set (do this early!)
        if 'groups' not in template_data:
            template_data['groups'] = {}
        if template_data.get('groups', {}).get('primary') is None:
            template_data['groups']['primary'] = username
        
        # 6. Customize paths for non-existing users
        if template_key != 'custom_existing':
            if template_data.get('account_type') == 'service':
                template_data['home_directory'] = f'/var/lib/shuttle/{username}'
            else:
                template_data['home_directory'] = f'/home/{username}'
        
        print(f"\n✓ Loaded {template_key.replace('custom_', '')} template for '{username}'")
        
        # Show the template with defaults before editing
        self._display_full_template(username, template_data)
        
        print("\n✓ Going into template editor - you can customize all fields...")
        
        # 7. Go directly into comprehensive template editing
        edited_template = self._edit_template_interactively(username, template_data)
        if edited_template is None:
            print("❌ User creation cancelled")
            return
        
        # 7. Add to instructions
        self._add_user_to_instructions(edited_template)
        print(f"✅ Added {username} to instructions")
        
    
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
        """Edit user details using unified template editing approach"""
        print(f"\n--- Editing User: {user['name']} ---")
        print("Using current user configuration as template for editing...")
        
        # Use existing user data as template
        template_data = user.copy()
        
        # Run through unified template editor
        edited_template = self._edit_template_interactively(user['name'], template_data)
        
        if edited_template is not None:
            # Update the user in place (careful to preserve list reference)
            user.clear()
            user.update(edited_template)
            
            # Update the user in the instructions list as well
            for i, instruction_user in enumerate(self.users):
                if instruction_user['name'] == edited_template['name']:
                    self.users[i] = edited_template
                    break
            
            print(f"✅ Updated {edited_template['name']} in instructions")
        else:
            print("❌ User editing cancelled")
    
    def _toggle_samba_for_user(self, user: Dict[str, Any]) -> None:
        """Toggle Samba access for user - UI handling"""
        is_enabled = self._toggle_samba_access(user)
        if is_enabled:
            print("✅ Samba access enabled")
        else:
            print("✅ Samba access disabled")
    
    # good
    def _custom_select_individual_users(self, environment='production'):
        """Let user pick individual users from templates with rich descriptions"""
        templates = self._get_user_templates_for_environment(environment)
        
        while True:
            # Display menu fresh each time
            print(f"\n=== {environment.title()} User Templates ===")
            
            # Build choice mapping for both removal and addition
            choice_map = {}
            
            # First section: Currently added users (removable)
            added_users = [u for u in self.users if u.get('name') in templates]
            if added_users:
                print("Currently added users:")
                for i, user in enumerate(added_users):
                    user_name = user.get('name', 'Unknown')
                    template = templates.get(user_name, {})
                    desc = template.get('description', 'No description')
                    
                    print(f"-{i+1}) {user_name} - Remove from instructions ({desc})")
                    choice_map[f"-{i+1}"] = f"REMOVE:{user_name}"
                print()
            
            print("Select users to add (you can select multiple or add all):")
            print()
            
            # Add "All" option
            print(f"0) Add All {environment.title()} Users")
            choice_map['0'] = 'all'
            counter = 1
            
            # Group by category for better organization
            by_category = {}
            for name, template in templates.items():
                category = template.get('category', 'other')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append((name, template))
            
            # Display by category - only show users not already added
            for category, users in sorted(by_category.items()):
                category_users = [(name, template) for name, template in users 
                                if not any(u['name'] == name for u in self.users)]
                
                if category_users:  # Only show category if it has available users
                    print(f"\n--- {category.replace('_', ' ').title()} ---")
                    for name, template in category_users:
                        desc = template.get('description', 'No description')
                        print(f"{counter}) {name} - {desc}")
                        choice_map[str(counter)] = f"ADD:{name}"
                        counter += 1
            
            print(f"\nb) Back to Manage Users Menu")
            
            # Build valid choices
            valid_choices = list(choice_map.keys()) + ['b']
            
            choice = self._get_choice("Select option", valid_choices, 'b')
            
            if choice == 'b':
                break
            elif choice == '0':
                # Add all users from this environment
                print(f"\n=== Adding All {environment.title()} Users ===")
                self._process_user_templates(templates, accept_defaults=False, allow_edit=True)
                break
            else:
                # Handle choice based on prefix
                action_value = choice_map[choice]
                
                if action_value.startswith('REMOVE:'):
                    # Remove user from instructions
                    user_name = action_value[7:]  # Remove "REMOVE:" prefix
                    self._remove_user_from_instructions(user_name)
                    print(f"✅ Removed {user_name} from instructions")
                    
                elif action_value.startswith('ADD:'):
                    # Add individual user
                    user_name = action_value[4:]  # Remove "ADD:" prefix
                    if user_name in templates:
                        selected_template = {user_name: templates[user_name]}
                        print(f"\n=== Adding {user_name} ===")
                        added_count = self._process_user_templates(selected_template, accept_defaults=False, allow_edit=True)
                        
                        if added_count > 0:
                            print(f"✅ Added {user_name} to instructions")
                
                # Continue the loop to reshow the menu
    
    def _remove_user_from_instructions(self, user_name: str):
        """Remove a user from the instructions"""
        # Remove from users list
        self.users = [u for u in self.users if u.get('name') != user_name]
        
        # Update the instructions document
        self.instructions['users'] = self.users
    
    def _apply_path_templates_to_all_paths(self):
        """Apply permission templates to all shuttle paths using template selection"""
        print(f"\n{self._wrap_title('APPLY TEMPLATES TO ALL PATHS')}")
        print("Select permission template to apply to all shuttle paths:")
        
        # Get base templates
        base_templates = get_path_permission_base_templates()
        
        # Build template choices (only standard templates for bulk application)
        template_choices = []
        for template_key, template_data in base_templates.items():
            if template_data['category'] == 'standard':
                recommended = "✓ Recommended" if template_data['recommended'] else ""
                label = f"{template_data['name']}\n   {template_data['description']}"
                if recommended:
                    label += f"\n   {recommended}"
                
                template_choices.append({
                    'key': str(len(template_choices) + 1),
                    'label': label,
                    'value': template_key
                })
        
        template_choices.append({'key': 'b', 'label': 'Back to Path Management', 'value': 'back'})
        
        # Get template choice
        choice_key = self._get_menu_choice("Select template for all paths", template_choices, '1')
        choice_value = self._get_choice_value(choice_key, template_choices, 'back')
        
        if choice_value == 'back':
            return
        
        template_data = base_templates[choice_value]
        
        # Show what will be applied
        print(f"\n{self._wrap_title('Template Application Preview')}")
        print(f"Template: {template_data['name']}")
        print(f"Description: {template_data['description']}")
        print(f"\nThis will configure {len(self.shuttle_paths)} shuttle paths:")
        
        paths_to_configure = []
        for path_name, actual_path in self.shuttle_paths.items():
            # Find the specific path template or use wildcard
            if path_name in template_data['templates']:
                path_template = template_data['templates'][path_name]
                paths_to_configure.append((path_name, actual_path, path_template))
                print(f"  • {path_name} → {actual_path}")
                print(f"    {path_template.get('description', 'No description')}")
            elif '*' in template_data['templates']:
                path_template = template_data['templates']['*'].copy()
                path_template['description'] = f"{path_name}: {path_template['description']}"
                paths_to_configure.append((path_name, actual_path, path_template))
                print(f"  • {path_name} → {actual_path}")
                print(f"    {path_template['description']}")
        
        if not paths_to_configure:
            print("❌ No matching path templates found")
            return
        
        # Confirm application
        if self._confirm(f"Apply {template_data['name']} template to all {len(paths_to_configure)} paths?", True):
            applied_count = 0
            for path_name, actual_path, path_template in paths_to_configure:
                self.paths[actual_path] = path_template.copy()
                applied_count += 1
            
            print(f"✅ Applied {template_data['name']} template to {applied_count} paths")
        else:
            print("← Cancelled template application")
    
    def _custom_configure_path_permissions(self):
        """Configure permissions, ownership, and ACLs for shuttle paths"""
        # Ensure paths section exists
        if 'paths' not in self.instructions:
            self.paths = {}
        
        while True:
            print(f"\n{self._wrap_title('PATH PERMISSION CONFIGURATION')}")
            print("Configure ownership, permissions, and ACLs for shuttle paths")
            print(f"\nConfigured path permissions: {len(self.paths)}")
            if self.paths:
                print("\nCurrent permission configurations:")
                for path, config in sorted(self.paths.items()):
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
                configured = " ✓" if actual_path in self.paths else ""
                print(f"  • {path_name} → {actual_path}{configured}")
            print("")
            
            choices = [
                {'key': '0', 'label': 'Apply Standard Path Permissions to All Paths'},
                {'key': '1', 'label': 'Configure Permissions for Shuttle Path'},
                {'key': '2', 'label': 'Configure Permissions for Custom Path'},
                {'key': '3', 'label': 'Edit Path Permission Configuration'},
                {'key': '4', 'label': 'Remove Path Permission Configuration'}
            ]
            
            choice = self._get_menu_choice(
                "Select action",
                choices,
                default_key='b',
                include_back=True,
                back_label="Main Custom Configuration Menu"
            )
            print()  # Add spacing between response and next section
            
            if choice == "0":
                self._apply_path_templates_to_all_paths()
            elif choice == "1":
                self._custom_configure_shuttle_path_permissions()
            elif choice == "2":
                self._custom_configure_custom_path_permissions()
            elif choice == "3":
                self._custom_edit_path_permissions()
            elif choice == "4":
                self._custom_remove_path_permissions()
            elif choice == "b":
                break
    
    def _custom_configure_shuttle_path_permissions(self):
        """Configure permissions for a shuttle path"""
        print(f"\n{self._wrap_title('CONFIGURE SHUTTLE PATH PERMISSIONS')}")
        print("Set ownership, permissions, and ACLs for shuttle paths")
        
        if not self.shuttle_paths:
            print("No shuttle paths available")
            return
        
        print("Select shuttle path to configure permissions for:")
        print("  0) Apply Standard Permissions to All Paths")
        print("")
        
        paths = list(self.shuttle_paths.items())
        for i, (path_name, actual_path) in enumerate(paths, 1):
            configured = " (permissions configured)" if actual_path in self.paths else " (not configured)"
            print(f"  {i}) {path_name} → {actual_path}{configured}")
        
        try:
            valid_choices = ["0"] + [str(i) for i in range(1, len(paths) + 1)]
            choice_str = self._get_choice("Select option", valid_choices, "0")
            
            if choice_str == "0":
                self._apply_path_templates_to_all_paths()
                return
            
            idx = int(choice_str)
            if 1 <= idx <= len(paths):
                path_name, actual_path = paths[idx - 1]
                self._configure_path_permission_with_templates(actual_path, path_name)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_configure_custom_path_permissions(self):
        """Configure permissions for a custom (non-shuttle) path"""
        print(f"\n{self._wrap_title('CONFIGURE CUSTOM PATH PERMISSIONS')}")
        print("Set permissions for paths outside the standard shuttle paths")
        
        path = input("\nFull path to configure permissions for: ").strip()
        if not path:
            print("❌ Path cannot be empty")
            return
        
        if path in self.paths:
            print(f"❌ Path '{path}' already has permission configuration")
            return
        
        description = input("Description: ").strip()
        self._configure_path_permission_details(path, f"Custom: {description or 'No description'}")
    
    def _configure_path_permission_with_templates(self, path, path_name):
        """Configure path permissions using template-based approach"""
        print(f"\n=== CONFIGURING PERMISSIONS: {path_name} ===")
        print(f"Path: {path}")
        print("Select permission template to apply:")
        
        # Get base templates
        base_templates = get_path_permission_base_templates()
        
        # Build menu choices for template selection
        template_choices = []
        
        for template_key, template_data in base_templates.items():
            if template_data['category'] == 'standard':
                recommended = "✓ Recommended" if template_data['recommended'] else ""
                label = f"{template_data['name']}\n   {template_data['description']}"
                if recommended:
                    label += f"\n   {recommended}"
                
                template_choices.append({
                    'key': str(len(template_choices) + 1),
                    'label': label,
                    'value': template_key
                })
        
        # Add custom template options
        for template_key, template_data in base_templates.items():
            if template_data['category'] == 'custom':
                label = f"{template_data['name']}\n   {template_data['description']}"
                
                template_choices.append({
                    'key': str(len(template_choices) + 1),
                    'label': label,
                    'value': template_key
                })
        
        template_choices.append({'key': 'c', 'label': 'Custom Configuration (Manual Entry)', 'value': 'custom'})
        template_choices.append({'key': 'b', 'label': 'Back to Path Selection', 'value': 'back'})
        
        # Get template choice
        choice_key = self._get_menu_choice("Select permission template", template_choices, '1')
        choice_value = self._get_choice_value(choice_key, template_choices, 'back')
        
        if choice_value == 'back':
            return
        elif choice_value == 'custom':
            # Fall back to manual configuration
            self._configure_path_permission_details(path, path_name)
            return
        
        # Apply template and allow editing
        template_data = base_templates[choice_value]
        
        # Find the specific path template or use wildcard
        if path_name in template_data['templates']:
            path_template = template_data['templates'][path_name].copy()
        elif '*' in template_data['templates']:
            path_template = template_data['templates']['*'].copy()
            path_template['description'] = f"{path_name}: {path_template['description']}"
        else:
            print(f"❌ No template found for {path_name} in {template_data['name']}")
            return
        
        # Show template preview and ask for confirmation
        print(f"\n{self._wrap_title('Template Preview')}")
        self._display_path_template(path_template, path_name)
        
        # Ask if user wants to accept defaults or edit
        if self._confirm(f"Accept these defaults for {path_name}?", True):
            # Apply template directly
            self.paths[path] = path_template
            print(f"✅ Applied {template_data['name']} template to {path_name}")
        else:
            # Edit template interactively
            edited_template = self._edit_path_template_interactively(path_name, path_template)
            if edited_template is not None:
                self.paths[path] = edited_template
                print(f"✅ Applied customized template to {path_name}")
            else:
                print("← Cancelled path configuration")

    def _configure_path_permission_details(self, path, description):
        """Configure ownership, permissions, and ACLs for a specific path"""
        print(f"\n=== CONFIGURING PERMISSIONS: {description} ===")
        print(f"Path: {path}")
        print("Configure ownership, file permissions, and access control lists")
        
        # Get basic ownership and permissions
        owner = input("Owner [root]: ").strip() or "root"
        
        # Show available groups
        if self.groups:
            selected_group = self._select_group_from_list(
                "Select group:",
                include_none=True,
                none_label="Enter custom group name",
                include_back=True
            )
            
            if selected_group is None and self.groups:
                # User selected back, return without configuring
                print("← Returning to previous menu")
                return
            elif selected_group:
                group = selected_group
            else:
                group = input("Group name: ").strip() or "root"
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
                    if self.groups:
                        selected_group = self._select_group_from_list(
                            "Select group for ACL:",
                            include_none=True,
                            none_label="Enter custom group"
                        )
                        
                        if selected_group:
                            groupname = selected_group
                        else:
                            groupname = input("Group name: ").strip()
                            
                        if not groupname:
                            continue
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
        self.paths[path] = path_config
        print(f"✅ Configured permissions for path: {path}")
    
    def _custom_edit_path_permissions(self):
        """Edit existing path permission configuration"""
        if not self.paths:
            print("No path permissions configured to edit")
            return
        
        print(f"\n{self._wrap_title('EDIT PATH PERMISSION CONFIGURATION')}")
        print("Select path to modify permissions for:")
        paths = list(self.paths.keys())
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
                config = self.paths[path]
                
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
        if not self.paths:
            print("No path permission configurations to remove")
            return
        
        print(f"\n{self._wrap_title('REMOVE PATH PERMISSION CONFIGURATION')}")
        print("Select path to remove permission configuration for:")
        paths = list(self.paths.keys())
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
                    del self.paths[path]
                    print(f"✅ Removed permission configuration for path: {path}")
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_manage_components(self):
        """Manage component configuration"""
        print("\n--- Component Configuration ---")
        
        print("\nCurrent settings:")
        print(f"  Install Samba: {self.instructions['components']['install_samba']}")
        print(f"  Install ACL tools: {self.instructions['components']['install_acl']}")
        print(f"  Configure firewall: {self.instructions['components']['configure_firewall']}")
        print(f"  Configure Samba: {self.instructions['components']['configure_samba']}")
        print(f"  Configure users/groups: {self.instructions['components']['configure_users_groups']}")
        print("")
        
        # Use unified method with custom mode behavior
        self._configure_components_interactive(firewall_default=False)
    
    def _custom_show_configuration(self):
        """Show current configuration summary"""
        print(f"\n{self._wrap_title('Current Configuration')}")
        print(f"\nEnvironment: {self.instructions['metadata'].get('environment', 'custom')}")
        print(f"Mode: {self.instructions['metadata'].get('mode', 'custom')}")
        
        print(f"\nGroups ({len(self.groups)}):")
        for name, details in sorted(self.groups.items()):
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
        
        print(f"\nPaths ({len(self.instructions.get('paths', {}))}):")
        if self.instructions.get('paths'):
            for path, config in sorted(self.paths.items()):
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
        for comp, enabled in self.instructions['components'].items():
            status = "Yes" if enabled else "No"
            print(f"  • {comp}: {status}")
    
    def _custom_validate_configuration(self):
        """Validate the current configuration"""
        print(f"\n{self._wrap_title('Configuration Validation')}")
        
        errors = []
        warnings = []
        
        # Check for groups
        if not self.groups:
            errors.append("No groups defined")
        
        # Check for users
        if not self.users:
            errors.append("No users defined")
        
        # Check each user
        for user in self.users:
            # Check primary group exists
            if user['groups']['primary'] and user['groups']['primary'] not in self.groups:
                errors.append(f"User '{user['name']}': primary group '{user['groups']['primary']}' does not exist")
            
            # Check secondary groups exist
            for group in user['groups']['secondary']:
                if group not in self.groups:
                    errors.append(f"User '{user['name']}': secondary group '{group}' does not exist")
            
            # Check for service accounts with shell access
            if user['account_type'] == 'service' and user.get('shell') == '/bin/bash':
                warnings.append(f"User '{user['name']}': service account has shell access")
            
            # Check for Samba users without Samba component
            if user.get('samba', {}).get('enabled') and not self.instructions['components']['install_samba']:
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
    
    def _custom_manage_domain_users(self):
        """Manage domain user configuration in custom mode"""
        if not self.domain_integration:
            print(f"\n{self._wrap_title('Domain User Configuration')}")
            print("❌ Domain user integration is not available")
            print("   This feature requires domain integration components")
            input("\nPress Enter to continue...")
            return
        
        while True:
            print(f"\n{self._wrap_title('Domain User Configuration')}")
            
            # Show current domain user status
            print("Current domain user status:")
            try:
                has_domain_users, domain_users = self.domain_integration.validator._detect_domain_users()
                if has_domain_users:
                    print(f"✅ Found {len(domain_users)} domain users:")
                    for user in domain_users:
                        print(f"   • {user}")
                    
                    config_exists, config_path = self.domain_integration.validator._check_domain_config()
                    if config_exists:
                        print(f"✅ Domain configuration: {config_path}")
                        if self.domain_integration.validator._validate_domain_config_file(config_path):
                            print("✅ Configuration is valid")
                        else:
                            print("⚠️  Configuration needs setup (contains placeholder)")
                    else:
                        print("❌ No domain configuration found")
                else:
                    print("ℹ️  No domain users detected")
            except Exception as e:
                print(f"❌ Error checking domain users: {e}")
            
            print("\nDomain User Actions:")
            print("1) Detect domain users in configuration")
            print("2) Create domain configuration template")
            print("3) Test domain configuration")
            print("4) Import specific domain user")
            print("5) Validate domain setup")
            print("6) Generate domain config interactively")
            print("b) Back to main menu")
            
            choice = self._get_choice("Select action", ["1", "2", "3", "4", "5", "6", "b"], "1")
            print()
            
            try:
                if choice == "1":
                    self.domain_integration._detect_and_report_domain_users()
                elif choice == "2":
                    self.domain_integration._create_domain_template_interactive()
                elif choice == "3":
                    self.domain_integration._test_domain_configuration_interactive()
                elif choice == "4":
                    self.domain_integration._import_domain_user_interactive()
                elif choice == "5":
                    self.domain_integration._validate_domain_setup_interactive()
                elif choice == "6":
                    self.domain_integration._configure_domain_import_interactive()
                elif choice == "b":
                    break
                
                if choice != "b":
                    input("\nPress Enter to continue...")
                    
            except Exception as e:
                print(f"❌ Domain operation failed: {e}")
                input("\nPress Enter to continue...")
    
    # =============================================
    # UNIFIED CONFIGURATION METHODS
    # =============================================
    
    def _configure_paths_for_environment(self, environment='production', accept_defaults=True):
        """Unified path configuration for any environment with interactive options
        
        Args:
            environment: 'production' or 'development'
            accept_defaults: If True, apply standard templates; if False, offer choices
        """
        print(f"\n=== {environment.title()} Path Configuration ===")
        
        if accept_defaults:
            # Auto-apply standard configurations
            if environment == 'development':
                print("Setting up development-friendly permissions for all shuttle paths...")
            else:
                print("Setting up standard permissions for all shuttle paths...")
            
            # Get environment-specific path permissions
            base_templates = get_path_permission_base_templates()
            standard_configs = base_templates[environment]['templates']
            paths_to_add = {}
        else:
            # Interactive path configuration - offer same choices as custom mode
            print("Choose how to configure path permissions:")
            print("")
            
            choices = [
                {'key': '1', 'label': 'Apply standard template to all paths'},
                {'key': '2', 'label': 'Configure each path individually'}
            ]
            
            choice = self._get_menu_choice(
                "Select path configuration approach:",
                choices,
                default_key='1',
                include_back=False
            )
            
            if choice == '1':
                # Use template selector like custom mode
                self._apply_path_templates_to_all_paths_linear(environment)
                return
            else:
                # Individual path configuration
                self._configure_paths_individually_linear(environment)
                return
        
        # Iterate through discovered paths (inverted loop)
        for path_name, actual_path in self.shuttle_paths.items():
            if path_name in standard_configs:
                # Use specific configuration if available
                config = standard_configs[path_name].copy()
            elif '*' in standard_configs:
                # Use catch-all configuration
                config = standard_configs['*'].copy()
                # Customize description for development catch-all
                if environment == 'development':
                    config['description'] = f'Development access for {path_name}'
            else:
                # Skip if no matching config
                continue
                
            paths_to_add[actual_path] = config
        
        # Add all paths using unified method
        added_count = self._add_paths_to_instructions(paths_to_add)
        
        if environment == 'development':
            print(f"✅ Configured development permissions for {added_count} paths")
            print("   All paths accessible to shuttle_admins group with full permissions")
        else:
            print(f"✅ Configured {added_count} standard paths")
    
    def _apply_path_templates_to_all_paths_linear(self, environment: str):
        """Apply permission templates to all paths in linear mode"""
        print(f"\n{self._wrap_title('PATH TEMPLATE SELECTION')}")
        print("Select permission template to apply to all shuttle paths:")
        
        # Get base templates
        base_templates = get_path_permission_base_templates()
        
        # Build template choices, prioritizing environment-appropriate defaults
        template_choices = []
        for template_key, template_data in base_templates.items():
            if template_data['category'] == 'standard':
                # Mark production template as recommended for production environment
                is_recommended = (
                    (environment == 'production' and template_key == 'production') or
                    (environment == 'development' and template_key == 'development')
                )
                
                recommended = "✓ Recommended" if is_recommended else ""
                label = f"{template_data['name']}\n   {template_data['description']}"
                if recommended:
                    label += f"\n   {recommended}"
                
                template_choices.append({
                    'key': str(len(template_choices) + 1),
                    'label': label,
                    'value': template_key
                })
        
        # Get template choice
        default_key = '1' if environment == 'production' else '2' if environment == 'development' else '1'
        choice_key = self._get_menu_choice("Select template for all paths", template_choices, default_key, include_back=False)
        choice_value = self._get_choice_value(choice_key, template_choices, 'production')
        
        # Apply selected template to all paths
        selected_template = base_templates[choice_value]
        
        paths_to_configure = []
        for path_name, actual_path in self.shuttle_paths.items():
            # Find the specific path template or use wildcard
            if path_name in selected_template['templates']:
                path_template = selected_template['templates'][path_name]
                paths_to_configure.append((path_name, actual_path, path_template))
            elif '*' in selected_template['templates']:
                path_template = selected_template['templates']['*'].copy()
                path_template['description'] = f"{path_name}: {path_template['description']}"
                paths_to_configure.append((path_name, actual_path, path_template))
        
        print(f"\n✅ Applying {selected_template['name']} template to {len(paths_to_configure)} paths...")
        
        applied_count = 0
        for path_name, actual_path, path_template in paths_to_configure:
            self.paths[actual_path] = path_template.copy()
            applied_count += 1
        
        print(f"✅ Applied {selected_template['name']} template to {applied_count} paths")
    
    def _configure_paths_individually_linear(self, environment: str):
        """Configure each path individually in linear mode"""
        print(f"\n{self._wrap_title('INDIVIDUAL PATH CONFIGURATION')}")
        print("Configure permissions for each shuttle path:")
        print("")
        
        configured_count = 0
        for path_name, actual_path in self.shuttle_paths.items():
            print(f"\n--- Configuring {path_name} ---")
            print(f"Path: {actual_path}")
            
            if self._confirm(f"Configure permissions for {path_name}?", True):
                # Use the same path template configuration as custom mode
                self._configure_path_permission_with_templates(actual_path, path_name)
                configured_count += 1
            else:
                print(f"   Skipped {path_name}")
        
        if configured_count == 0:
            print("\n⚠️  WARNING: No paths configured. Default system permissions will be used.")
        else:
            print(f"\n✅ Configured {configured_count} of {len(self.shuttle_paths)} paths")
    
    def _configure_components_interactive(self, firewall_default=True):
        """Unified component configuration for all modes"""
        print(f"\n{self._wrap_title('Component Configuration')}")
        print("Configure system components:")
        print("")
        
        # Samba (network file sharing)
        print("🌐 Network File Sharing:")
        samba_install = self._confirm("  Install Samba for network file access?", True)
        self._add_component_to_instructions('install_samba', samba_install)
        
        if samba_install:
            samba_configure = self._confirm("  Configure Samba users and shares?", True)
            self._add_component_to_instructions('configure_samba', samba_configure)
            
            if samba_configure:
                # Configure detailed Samba settings
                if self._confirm("  Configure detailed Samba settings?", False):
                    self._configure_samba_details_interactive()
        else:
            self._add_component_to_instructions('configure_samba', False)
        print("")
        
        # ACL tools (advanced permissions)
        print("🔒 Advanced Permissions:")
        acl_install = self._confirm("  Install ACL tools for fine-grained permissions?", True)
        self._add_component_to_instructions('install_acl', acl_install)
        print("")
        
        # Firewall
        print("🛡️ Security:")
        firewall_config = self._confirm("  Configure firewall settings?", firewall_default)
        self._add_component_to_instructions('configure_firewall', firewall_config)
        
        if firewall_config:
            # Configure detailed firewall settings
            if self._confirm("  Configure detailed firewall rules?", False):
                self._configure_firewall_details_interactive()
        print("")
        
        # Always configure users/groups in all modes
        self._add_component_to_instructions('configure_users_groups', True)
        
        # Summary
        enabled_components = [k for k, v in self.instructions['components'].items() if v]
        if enabled_components:
            print(f"✅ {len(enabled_components)} components will be configured")
        else:
            print("⚠️  No additional components selected")
    
    def _configure_samba_details_interactive(self):
        """Configure detailed Samba settings interactively"""
        print(f"\n{self._wrap_title('Samba Configuration Details')}")
        
        # Import the configuration template
        from post_install_standard_configuration_reader import get_standard_samba_config
        samba_config = get_standard_samba_config()
        
        # Configure workgroup
        workgroup = input(f"  Workgroup [{samba_config['global_settings']['workgroup']}]: ").strip()
        if workgroup:
            samba_config['global_settings']['workgroup'] = workgroup
        
        # Configure server description
        server_string = input(f"  Server description [{samba_config['global_settings']['server_string']}]: ").strip()
        if server_string:
            samba_config['global_settings']['server_string'] = server_string
        
        # Configure shares
        print("\n📁 Samba Shares:")
        configure_shares = self._confirm("  Configure default shuttle shares?", True)
        
        if configure_shares:
            # Configure inbound share
            print("\n  Inbound Share (file submission):")
            inbound_path = input(f"    Path [{samba_config['shares']['shuttle_inbound']['path']}]: ").strip()
            if inbound_path:
                samba_config['shares']['shuttle_inbound']['path'] = inbound_path
            
            # Configure outbound share
            print("\n  Outbound Share (file retrieval):")
            outbound_path = input(f"    Path [{samba_config['shares']['shuttle_outbound']['path']}]: ").strip()
            if outbound_path:
                samba_config['shares']['shuttle_outbound']['path'] = outbound_path
        
        # Save configuration to instructions
        self.instructions['samba'] = samba_config
        print("\n✅ Samba configuration saved")
    
    def _configure_firewall_details_interactive(self):
        """Configure detailed firewall settings interactively"""
        print(f"\n{self._wrap_title('Firewall Configuration Details')}")
        
        # Import the configuration template
        from post_install_standard_configuration_reader import get_standard_firewall_config
        firewall_config = get_standard_firewall_config()
        
        # Configure default policies
        print("\n🛡️ Default Policies:")
        default_incoming = self._get_choice(
            "  Default incoming policy",
            ['deny', 'allow', 'reject'],
            firewall_config['default_policy']['incoming']
        )
        firewall_config['default_policy']['incoming'] = default_incoming
        
        # Configure logging
        logging_level = self._get_choice(
            "  Firewall logging level",
            ['off', 'low', 'medium', 'high', 'full'],
            firewall_config['logging']
        )
        firewall_config['logging'] = logging_level
        
        # Configure network topology
        print("\n🌐 Network Topology:")
        if self._confirm("  Configure management networks?", True):
            self._configure_network_list(
                firewall_config['network_topology'],
                'management_networks',
                'Management networks (SSH, admin access)'
            )
        
        if self._confirm("  Configure client networks?", True):
            self._configure_network_list(
                firewall_config['network_topology'],
                'client_networks', 
                'Client networks (Samba access)'
            )
        
        # Configure specific firewall rules
        print("\n🔧 Firewall Rules:")
        if self._confirm("  Restrict SSH to management networks?", True):
            if firewall_config['network_topology']['management_networks']:
                firewall_config['rules']['ssh_access']['sources'] = firewall_config['network_topology']['management_networks']
            else:
                print("    ⚠️  No management networks configured - SSH will remain open")
        
        if self._confirm("  Configure Samba access rules?", True):
            if firewall_config['network_topology']['client_networks']:
                firewall_config['rules']['samba_access']['sources'] = firewall_config['network_topology']['client_networks']
            else:
                print("    ⚠️  No client networks configured - Samba will be blocked")
        
        # Save configuration to instructions
        self.instructions['firewall'] = firewall_config
        print("\n✅ Firewall configuration saved")
    
    def _configure_network_list(self, config_dict, key, description):
        """Configure a list of networks interactively"""
        print(f"\n  {description}:")
        networks = []
        
        while True:
            network = input("    Enter network (CIDR format, e.g., 192.168.1.0/24): ").strip()
            if not network:
                break
            
            # Basic validation
            if '/' in network or network == 'any':
                networks.append(network)
                print(f"    Added: {network}")
            else:
                print("    ⚠️  Use CIDR format (e.g., 192.168.1.0/24) or 'any'")
                continue
            
            if not self._confirm("    Add another network?", False):
                break
        
        config_dict[key] = networks
        if networks:
            print(f"    ✅ Configured {len(networks)} networks")
        else:
            print("    ℹ️  No networks configured")
    
    # =============================================
    # UNIFIED INSTRUCTION BUILDERS
    # =============================================
    
    def _add_group_to_instructions(self, group_name: str, group_data: dict) -> bool:
        """Universal method to add any group to the instruction set"""
        if group_name in self.groups:
            print(f"⚠️  Group '{group_name}' already exists in instructions")
            return False
        
        # Validate group data structure
        if not isinstance(group_data, dict):
            print(f"❌ Invalid group data for '{group_name}': must be dictionary")
            return False
        
        if 'description' not in group_data:
            print(f"❌ Invalid group data for '{group_name}': missing description")
            return False
        
        # Add to instructions
        self.groups[group_name] = group_data.copy()
        print(f"✅ Added group '{group_name}' to instructions")
        return True
    
    def _add_groups_to_instructions(self, groups_dict: dict) -> int:
        """Add multiple groups to instructions"""
        added_count = 0
        for group_name, group_data in groups_dict.items():
            if self._add_group_to_instructions(group_name, group_data):
                added_count += 1
        return added_count
    
    def _select_standard_groups_interactive(self, groups_dict: dict, environment: str):
        """Interactively select which standard groups to add"""
        print(f"\n{self._wrap_title('Group Configuration')}")
        print(f"Select which {environment} groups to configure:")
        print("")
        
        # Offer to add all groups at once
        if self._confirm("Add all recommended standard groups?", True):
            count = self._add_groups_to_instructions(groups_dict)
            print(f"✅ Added all {count} standard {environment} groups")
        else:
            # Let user approve each group
            added_count = 0
            for group_name, group_data in groups_dict.items():
                description = group_data.get('description', 'No description available')
                
                print(f"\n{group_name}:")
                print(f"   {description}")
                
                if self._confirm(f"Add group '{group_name}'?", True):
                    if self._add_group_to_instructions(group_name, group_data):
                        added_count += 1
                else:
                    print(f"   Skipped group '{group_name}'")
            
            if added_count == 0:
                print("\n⚠️  WARNING: No groups added. Users may not function correctly without groups.")
            else:
                print(f"\n✅ Added {added_count} of {len(groups_dict)} available groups")
    
    def _add_user_to_instructions(self, user_data: dict) -> bool:
        """Universal method to add any user to the instruction set"""
        if not isinstance(user_data, dict) or 'name' not in user_data:
            print(f"❌ Invalid user data: must be dictionary with 'name' field")
            return False
        
        username = user_data['name']
        
        # Check for duplicates
        for existing_user in self.users:
            if existing_user['name'] == username:
                print(f"⚠️  User '{username}' already exists in instructions")
                return False
        
        # Validate required fields
        required_fields = ['name', 'source', 'account_type', 'groups']
        for field in required_fields:
            if field not in user_data:
                print(f"❌ Invalid user data for '{username}': missing '{field}'")
                return False
        
        # Add to instructions
        self.users.append(user_data.copy())
        print(f"✅ Added user '{username}' to instructions")
        return True
    
    def _add_users_to_instructions(self, users_list: list) -> int:
        """Add multiple users to instructions"""
        added_count = 0
        for user_data in users_list:
            if self._add_user_to_instructions(user_data):
                added_count += 1
        return added_count
    
    def _add_component_to_instructions(self, component_name: str, component_value: bool) -> bool:
        """Universal method to add any component to the instruction set"""
        if component_name not in self.instructions['components']:
            print(f"❌ Unknown component: '{component_name}'")
            return False
        
        self.instructions['components'][component_name] = component_value
        status = "enabled" if component_value else "disabled"
        print(f"✅ Component '{component_name}' {status}")
        return True
    
    def _add_components_to_instructions(self, components_dict: dict) -> int:
        """Add multiple components to instructions"""
        added_count = 0
        for component_name, component_value in components_dict.items():
            if self._add_component_to_instructions(component_name, component_value):
                added_count += 1
        return added_count
    
    def _add_path_to_instructions(self, actual_path: str, path_config: dict) -> bool:
        """Universal method to add any path to the instruction set"""
        if not isinstance(path_config, dict):
            print(f"❌ Invalid path config for '{actual_path}': must be dictionary")
            return False
        
        # Ensure paths section exists
        if 'paths' not in self.instructions:
            self.paths = {}
        
        # Add to instructions
        self.paths[actual_path] = path_config.copy()
        
        # Get readable path name for output
        path_name = next((name for name, p in self.shuttle_paths.items() if p == actual_path), "custom")
        print(f"✅ Added path '{path_name}' to instructions")
        return True
    
    def _add_paths_to_instructions(self, paths_dict: dict) -> int:
        """Add multiple paths to instructions"""
        added_count = 0
        for actual_path, path_config in paths_dict.items():
            if self._add_path_to_instructions(actual_path, path_config):
                added_count += 1
        return added_count
    
    def _build_complete_config(self) -> List[Dict[str, Any]]:
        """Build complete configuration documents"""
        print("\n🔍 Finalizing configuration...")
        
        documents = []
        
        # First document: metadata, settings, and components only
        documents.append(self.instructions)
        
        # Group documents
        for group_name, group_details in self.groups.items():
            documents.append({
                'type': 'group',
                'group': {
                    'name': group_name,
                    **group_details
                }
            })
        
        # User documents
        for user in self.users:
            documents.append({
                'type': 'user',
                'user': user
            })
        
        # Path documents
        for path, path_config in self.paths.items():
            documents.append({
                'type': 'path',
                'path': {
                    'location': path,
                    **path_config
                }
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
            
            # Check required sections in base config
            required_sections = ['metadata', 'settings', 'components']
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
        
        # Count and validate different document types
        group_docs = []
        user_docs = []
        path_docs = []
        
        for i, doc in enumerate(docs[1:], 1):
            doc_type = doc.get('type')
            if doc_type == 'group':
                group_docs.append((i, doc))
            elif doc_type == 'user':
                user_docs.append((i, doc))
            elif doc_type == 'path':
                path_docs.append((i, doc))
            else:
                validation_errors.append(f"Document {i+1}: Invalid or missing type '{doc_type}'")
        
        # Validate groups
        if not group_docs:
            validation_errors.append("No groups defined")
        else:
            for i, doc in group_docs:
                if 'group' not in doc:
                    validation_errors.append(f"Document {i+1}: Missing 'group' section")
                else:
                    group = doc['group']
                    if 'name' not in group:
                        validation_errors.append(f"Document {i+1}: Group missing 'name' field")
                    if 'gid' not in group:
                        validation_errors.append(f"Document {i+1}: Group missing 'gid' field")
        
        # Validate users
        if not user_docs:
            validation_errors.append("No users defined")
        else:
            for i, doc in user_docs:
                if 'user' not in doc:
                    validation_errors.append(f"Document {i+1}: Missing 'user' section")
                else:
                    user = doc['user']
                    required_user_fields = ['name', 'source', 'account_type', 'groups']
                    for field in required_user_fields:
                        if field not in user:
                            validation_errors.append(f"User {user.get('name', 'unnamed')}: Missing required field '{field}'")
        
        # Validate paths
        if path_docs:
            for i, doc in path_docs:
                if 'path' not in doc:
                    validation_errors.append(f"Document {i+1}: Missing 'path' section")
                else:
                    path = doc['path']
                    if 'location' not in path:
                        validation_errors.append(f"Document {i+1}: Path missing 'location' field")
                    required_path_fields = ['owner', 'group', 'mode']
                    for field in required_path_fields:
                        if field not in path:
                            validation_errors.append(f"Path {path.get('location', 'unknown')}: Missing required field '{field}'")
        
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
    
    # Create wizard instance first to access _wrap_title method
    wizard = ConfigWizard(
        shuttle_config_path=args.shuttle_config_path,
        test_work_dir=args.test_work_dir,
        test_config_path=args.test_config_path
    )
    
    config = wizard.run()
    
    # Configuration Summary with standardized formatting
    print(wizard._wrap_title("Configuration Summary"))
    print(f"Environment: {config[0]['metadata']['environment']}")
    
    # Count different document types using reusable function
    print(wizard._get_config_counts(config, format_output=True))
    
    # Password setup guidance for users
    has_interactive_users = any(
        user.get('account_type') in ['interactive', 'admin'] 
        for doc in config for user in doc.get('users', [])
    )
    if has_interactive_users:
        print("\n⚠️  IMPORTANT: Interactive users require manual password setup after installation")
        print("   Use: sudo passwd <username>")
        print("   For Samba users: sudo smbpasswd -a <username>")
    
    # Save options using standard menu
    choices = [
        {'key': '1', 'label': 'Save configuration only (exit without applying)'},
        {'key': '2', 'label': 'Save configuration and continue'},
        {'key': 'x', 'label': 'Exit without saving'}
    ]
    
    choice = wizard._get_menu_choice(
        "What would you like to do?",
        choices,
        default_key='1',
        include_back=False
    )
    
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