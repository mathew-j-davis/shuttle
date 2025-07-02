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
    get_standard_user_templates, get_standard_instruction_template,
    get_custom_user_base_templates,
    STANDARD_MODE_CONFIGS, STANDARD_SAMBA_CONFIG
)

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





def get_development_admin_group():
    """Factory function for development admin group configuration"""
    return {
        'shuttle_admins': {
            'description': 'Administrative users with full shuttle access',
            'gid': 5000
        }
    }


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
    
    def _get_all_available_groups(self) -> Dict[str, Dict[str, Any]]:
        """Get all available groups (standard + instruction groups) with status"""
        from standard_configs import get_standard_groups
        
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
                               exclude_groups: List[str] = None) -> Optional[str]:
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
                'key': '0',
                'label': none_label,
                'value': None
            })
        
        # Sort groups: standard first, then custom
        standard_groups = [(k, v) for k, v in available_groups.items() if v['source'] == 'standard']
        custom_groups = [(k, v) for k, v in available_groups.items() if v['source'] == 'custom']
        
        all_sorted = sorted(standard_groups) + sorted(custom_groups)
        
        for i, (group_name, group_data) in enumerate(all_sorted, 1):
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
            include_back=False
        )
        
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
                'key': '0',
                'label': "Done selecting groups",
                'value': 'DONE'
            })
            
            # Second section: Available groups to add (excluding selected and excluded)
            available_groups = {k: v for k, v in all_groups.items() 
                              if k not in selected and k not in excluded_set}
            
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
            default_key = '0'  # Default to "Done"
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
    
    def _add_templated_user(self, template_name: str, name: str = None, source: str = None, 
                           account_type: str = None, primary_group: str = None, 
                           secondary_groups: List[str] = None, shell: str = None, 
                           home_directory: str = None, create_home: bool = None,
                           auth_method: str = None) -> None:
        """Add a user from standard templates with optional overrides
        
        Args:
            template_name: Name of template from standard_configs.py
            name: Override user name (defaults to template name)
            source: Override source type
            account_type: Override account type
            primary_group: Override primary group
            secondary_groups: Override secondary groups (replaces entire list)
            shell: Override shell
            home_directory: Override home directory
            create_home: Override create_home flag
            auth_method: Samba auth method if applicable
        """
        # Get the template
        user_template = get_standard_user_templates()[template_name].copy()
        
        # Apply overrides for simple properties
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
            
        # Handle nested groups structure
        if primary_group is not None:
            if 'groups' not in user_template:
                user_template['groups'] = {}
            user_template['groups']['primary'] = primary_group
        if secondary_groups is not None:
            if 'groups' not in user_template:
                user_template['groups'] = {}
            user_template['groups']['secondary'] = secondary_groups
            
        # Handle Samba auth method if specified
        if auth_method is not None and 'samba' in user_template and user_template['samba'].get('enabled'):
            user_template['samba']['auth_method'] = auth_method
            
        # Add to instructions
        self._add_user_to_instructions(user_template)
    
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
        
        for template_name, template_data in templates.items():
            should_add = False
            user_data = None
            
            if accept_defaults:
                # Auto-add if recommended
                should_add = template_data.get('recommended', True)
                user_data = template_data.copy()
            else:
                # Display full template details
                self._display_full_template(template_name, template_data)
                
                # Three-way choice: yes, no, or edit
                if allow_edit:
                    choice = self._get_template_action(template_data.get('recommended', True))
                    
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
            current_primary = current_user_info['primary_group']
            current_secondary = current_user_info['secondary_groups']
            
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

    def _get_template_action(self, recommended: bool = True) -> str:
        """Get user's choice for template action (yes/no/edit)"""
        default_choice = 'y' if recommended else 'n'
        prompt = "Add this user? [Y/n/e]" if recommended else "Add this user? [y/N/e]"
        print("   y = Yes, add with defaults")
        print("   n = No, skip this user")
        print("   e = Edit template values")
        print("   x = Exit wizard")
        
        while True:
            choice = input(f"{prompt}: ").strip().lower()
            
            if choice == 'x':
                print("\nExiting wizard...")
                sys.exit(3)
            
            if not choice:
                return default_choice
                
            if choice in ['y', 'n', 'e']:
                return choice
                
            print("Invalid choice. Please enter y, n, e, or x.")
    
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
                print("1) Service - No shell, application access only")
                print("2) Interactive - Shell access for human users")
                type_choice = self._get_choice("Select account type", ["1", "2"], "1")
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
        print("\n=== Final Configuration ===")
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
        print("\n=== Shuttle Configuration Wizard ===")
        print("This wizard will help you create a user setup configuration.")
        print("")
        
        # Select deployment mode first
        mode = self._select_deployment_mode()
        
        if mode in ['development', 'production']:
            config = self._run_standard_mode(mode)
            # Option to customize standard configuration
            if mode == 'production' and self._offer_customization():
                return self._run_custom_mode(base_config=config)
            return config
        else:  # custom
            return self._run_custom_mode()
    
    def _select_deployment_mode(self) -> str:
        """Select the deployment mode using generic menu system"""
        description = """
=== Deployment Mode Selection ===
        """
        print(description)
        
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
        
        description = f"""
=== {config['title']} ===

{config['description']}
        """
        print(description)


        
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
            
            # Add groups based on mode
            if standard == 'development':
                admin_group_data = {
                    'description': 'Administrative users with full shuttle access',
                    'gid': 5000
                }
                self._add_group_to_instructions('shuttle_admins', admin_group_data)
            else:  # production
                self._add_groups_to_instructions(get_standard_groups())

        # Create users with unified approach - works for both accept_defaults and interactive modes
        self._create_standard_users(standard, accept_defaults=accept_defaults, allow_edit=(not accept_defaults))

        # Configure path permissions
        self._configure_paths_for_environment(standard)
        
        print(f"\n✅ {config['completion_message']}")
        
        if standard == 'development':
            print(f"   {config['completion_details'].format(user_count=len(self.users))}")
        else:
            print(f"   {config['completion_details'].format(user_count=len(self.users), path_count=len(self.shuttle_paths))}")
        
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
            self.instructions = base_config[0]  # Load the main config
            self.users = [doc['user'] for doc in base_config[1:] if doc.get('type') == 'user']
            self.instructions['metadata']['mode'] = 'standard_customized'
        else:
            print("\n=== CUSTOM MODE ===")
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
                    self.groups = {}
                    self.paths = {}
                    self.users = []
                    print("✅ Configuration reset")
            elif choice == "s":
                # Save configuration and exit
                break
        
        # Return complete configuration
        return self._build_complete_config()
    
    
    # def _select_user_approach(self):
    #     """Select user configuration approach"""
    #     print("\n4. User Configuration Approach")
    #     print("-----------------------------")
    #     print("1) Single user for all functions (simplest)")
    #     print("2) Separate users by function (most secure)")
    #     print("3) Custom configuration (advanced)")
        
    #     choice = self._get_choice("Select approach", ["1", "2", "3"], "1")
        
    #     if choice == "1":
    #         self._configure_single_user()
    #     elif choice == "2":
    #         self._configure_separate_users()
    #     else:
    #         self._configure_custom_users()
    
    # def _configure_single_user(self):
    #     """Configure single user for all functions"""
    #     print("\n5. Single User Configuration")
    #     print("---------------------------")
        
    #     # User source
    #     user_source = self._select_user_source()
        
    #     # Username
    #     if user_source == "domain":
    #         username = input("Enter domain username (without domain prefix) [shuttle_service]: ").strip() or "shuttle_service"
    #         if self._confirm_domain_format():
    #             username = f"DOMAIN\\{username}"
    #     else:
    #         username = input("Enter username [shuttle_all]: ").strip() or "shuttle_all"
        
    #     # Account type (only relevant for new users)
    #     account_type = "service"
    #     if self.instructions['metadata']['environment'] == 'development':
    #         if user_source != "existing":
    #             # Only ask for new users where it actually matters
    #             print("\nAccount Type Selection")
    #             print("======================")
    #             print("Service accounts (recommended for Samba):")
    #             print("  - No shell access (/usr/sbin/nologin)")
    #             print("  - Can only connect via Samba from other machines")
    #             print("  - More secure for file sharing only")
    #             print("")
    #             print("Interactive accounts:")
    #             print("  - Full shell access (/bin/bash)")
    #             print("  - Can log in directly to this server")
    #             print("  - Needed only if user requires local login")
    #             print("")
    #             if self._confirm("Create interactive account with shell access?", False):
    #                 account_type = "interactive"
    #             else:
    #                 print("→ Creating service account (Samba access only)")
        
    #     # Create groups
    #     self.groups = {
    #         'shuttle_all_users': {
    #             'description': 'All shuttle functionality'
    #         },
    #         'shuttle_config_readers': {
    #             'description': 'Configuration file readers'
    #         }
    #     }
        
    #     # Create user
    #     user = {
    #         'name': username,
    #         'source': user_source,
    #         'account_type': account_type,
    #     }
        
    #     # Only set shell and home for non-existing users
    #     if user_source != "existing":
    #         user['shell'] = '/bin/bash' if account_type == 'interactive' else '/usr/sbin/nologin'
    #         user['home_directory'] = self._get_home_directory(username, account_type, user_source)
    #         user['create_home'] = True
        
    #     # Continue with groups and permissions
    #     user.update({
    #         'groups': {
    #             'primary': 'shuttle_all_users',
    #             'secondary': ['shuttle_config_readers']
    #         },
    #         'permissions': self._configure_path_permissions("Single User")
    #     })
        
    #     # Samba configuration
    #     print("\nEnable Samba Access for User")
    #     print("============================")
    #     if self.instructions['components']['configure_samba'] and self._confirm("Enable Samba access for this user?", True):
    #         self._enable_samba_access(user)
            
    #         # Samba authentication method
    #         print("\nSamba authentication method:")
    #         print("1) Samba user database (smbpasswd) - separate Samba password")
    #         print("2) Domain security - use AD/domain authentication")
    #         print("3) Configure later (enable user, set password manually)")
    #         print("4) Show other options (PAM sync, Kerberos) - manual setup required")
            
    #         auth_choice = self._get_choice("Select authentication method", ["1", "2", "3", "4"], "1")
            
    #         if auth_choice == "1":
    #             # Traditional smbpasswd approach
    #             user['samba']['auth_method'] = 'smbpasswd'
    #             password = self._get_password("Enter Samba password")
    #             if password:
    #                 user['samba']['password'] = password
                    
    #         elif auth_choice == "2":
    #             # Domain security
    #             user['samba']['auth_method'] = 'domain'
    #             print("\nDomain security selected:")
    #             print("- Requires machine to be joined to domain")
    #             print("- Users authenticate against domain controller")
    #             print("- No separate Samba passwords needed")
                
    #         elif auth_choice == "3":
    #             # Configure later
    #             user['samba']['auth_method'] = 'manual'
    #             print("\nUser will be enabled for Samba but password must be set manually:")
    #             print("sudo smbpasswd -a {username}")
                
    #         elif auth_choice == "4":
    #             # Show other options but don't implement
    #             self._show_advanced_samba_options()
    #             # Default to manual configuration
    #             user['samba']['auth_method'] = 'manual'
        
    #     self._add_user_to_instructions(user)
    
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
    
    # def _configure_separate_users(self):
    #     """Configure separate users for each function"""
    #     print("\n5. Separate Users Configuration")
    #     print("-------------------------------")
        
    #     # Create groups
    #     self.groups = {
    #         'shuttle_app_users': {'description': 'Users who run shuttle application'},
    #         'shuttle_test_users': {'description': 'Users who run defender tests'},
    #         'shuttle_samba_users': {'description': 'Users who access via Samba'},
    #         'shuttle_config_readers': {'description': 'Users who can read config files'},
    #         'shuttle_ledger_writers': {'description': 'Users who can write to ledger'}
    #     }
        
    #     # Configure each user type
    #     if self._confirm("Configure Samba user?", True):
    #         self._add_samba_user()
        
    #     if self._confirm("Add shuttle_runner (main application user)?", True):
    #         user_template = get_standard_user_templates()['shuttle_runner'].copy()
    #         user_template['name'] = 'shuttle_runner'
    #         self._add_user_to_instructions(user_template)
        
    #     # Test Users - clarify the different purposes
    #     print("\n--- Test User Configuration ---")
    #     print("There are two types of test users:")
    #     print("1. shuttle_tester: For running automated test suites (development/pre-production)")
    #     print("2. shuttle_defender_test_runner: For validating Defender config (production requirement)")
    #     print("")
        
    #     if self._confirm("Add shuttle_tester (automated test runner)?", False):
    #         user_template = get_standard_user_templates()['shuttle_tester'].copy()
    #         user_template['name'] = 'shuttle_tester'
    #         self._add_user_to_instructions(user_template)
            
    #     if self._confirm("Add shuttle_defender_test_runner (production Defender validation)?", True):
    #         user_template = get_standard_user_templates()['shuttle_defender_test_runner'].copy()
    #         user_template['name'] = 'shuttle_defender_test_runner'
    #         self._add_user_to_instructions(user_template)
    
    # def _add_samba_user(self):
    #     """Add Samba user configuration"""
    #     print("\nSamba User Configuration")
        
    #     user_source = self._select_user_source()
    #     username = self._get_username("Samba username", "samba_service", user_source)
        
    #     user = self._new_user(
    #         name=username,
    #         source=user_source,
    #         account_type='service',
    #         primary_group='shuttle_samba_users',
    #         secondary_groups=['shuttle_config_readers'],
    #         home_directory='/var/lib/shuttle/samba' if user_source != "existing" else None
    #     )
        
    #     user = self._add_permissions_to_user(user,
    #         read_write=[{'path': 'source_path', 'mode': '755'}],
    #         read_only=[{'path': 'shuttle_config_path', 'mode': '644'}]
    #     )
        
    #     user = self._add_samba_to_user(user, enabled=True)
        
    #     if self._confirm("Set Samba password now?", False):
    #         password = self._get_password("Enter Samba password")
    #         if password:
    #             user['samba']['password'] = password
        
    #     self._add_user_to_instructions(user)
    
    
    
    # def _configure_custom_users(self):
    #     """Configure custom users"""
    #     print("\n5. Custom User Configuration")
    #     print("---------------------------")
        
    #     # Create default groups
    #     self.groups = {
    #         'shuttle_users': {'description': 'General shuttle users'},
    #         'shuttle_config_readers': {'description': 'Configuration file readers'}
    #     }
        
    #     while True:
    #         if not self._confirm("\nAdd a user?", True):
    #             break
            
    #         self._add_custom_user()
    
    # def _add_custom_user(self):
    #     """Add a custom user interactively"""
    #     print("\nCustom User Configuration")
        
    #     # Basic info
    #     user_source = self._select_user_source()
    #     username = self._get_username("Username", "user", user_source)
        
    #     # Account type
    #     print("\nAccount type:")
    #     print("1) Service account (no shell)")
    #     print("2) Interactive account (shell access)")
    #     account_type_choice = self._get_choice("Select account type", ["1", "2"], "1")
    #     account_type = "service" if account_type_choice == "1" else "interactive"
        
    #     # Build user config
    #     user = {
    #         'name': username,
    #         'source': user_source,
    #         'account_type': account_type,
    #         'groups': {
    #             'primary': 'shuttle_users',
    #             'secondary': []
    #         },
    #     }
        
    #     # Only set shell and home for non-existing users
    #     if user_source != "existing":
    #         user['shell'] = '/bin/bash' if account_type == 'interactive' else '/usr/sbin/nologin'
    #         user['home_directory'] = self._get_home_directory(username, account_type, user_source)
    #         user['create_home'] = True
        
    #     # Groups
    #     if self._confirm("Add to config readers group?", True):
    #         user['groups']['secondary'].append('shuttle_config_readers')
        
        
    #     # Permissions (simplified)
    #     if self._confirm("Read/write access to source directory?", False):
    #         user['permissions']['read_write'].append({'path': 'source_path', 'mode': '755'})
    #     if self._confirm("Read/write access to test directory?", False):
    #         user['permissions']['read_write'].append({'path': 'test_work_dir', 'mode': '755', 'recursive': True})
        
    #     # Always add config read access
    #     user['permissions']['read_only'].append({'path': 'shuttle_config_path', 'mode': '644'})
        
    #     # Samba
    #     if self._confirm("Enable Samba access?", False):
    #         self._enable_samba_access(user)
        
    #     self._add_user_to_instructions(user)
    
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
    

    def _select_and_create_standard_service_roles(self):
        description = """
        - Service accounts (shuttle_runner, defender_test_runner)
        
        """
        print(description)

        if self._confirm("Create service accounts?", True):
            self._create_service_accounts()

    # Standard Mode Helper Methods
    def _select_and_create_standard_roles(self):

        description = """
        --- Select and add standard user roles ---

        The standard production pattern has standard user roles:
        
        - Network users (samba_in_user, out_user)
        - Test users (shuttle_tester)
        - Admin users (interactive administrators)
        """
        print(description)
     
        # Service Accounts
        self._select_and_create_standard_service_roles()
        
        # Network Users
        if self._confirm("Create network users?", True):
            self._choose_create_network_users()
        
        # Test User
        if self._confirm("Create test user?", False):
            self._create_test_user()
        
        # Admin User
        if self._confirm("Create admin user?", True):
            self._create_admin_user()
    
    def _create_service_accounts(self):
        """Create standard service accounts - actual creation logic"""
        self._add_templated_user('shuttle_runner')
        print("✅ Added shuttle_runner to instructions")
        self._add_templated_user('shuttle_defender_test_runner')
        print("✅ Added shuttle_defender_test_runner to instructions")
        
    def _choose_create_service_accounts(self):
        """Create standard service accounts - UX/choice handling"""
        print("\n--- Add Service Accounts ---")
        
        # Individual service account choices
        if self._confirm("Add shuttle_runner service account?", True):
            self._add_templated_user('shuttle_runner')
            print("✅ Added shuttle_runner to instructions")
        
        if self._confirm("Add shuttle_defender_test_runner?", True):
            self._add_templated_user('shuttle_defender_test_runner')
            print("✅ Added shuttle_defender_test_runner to instructions")
    def _create_network_users(self):
        """Create standard network users - actual creation logic"""
        # Samba In User
        self._add_templated_user('shuttle_in_user', source='existing', auth_method='smbpasswd')
        print("✅ Added shuttle_in_user to instructions")
        
        # Out User  
        self._add_templated_user('shuttle_out_user', auth_method='smbpasswd')
        print("✅ Added shuttle_out_user to instructions")
        
    def _choose_create_network_users(self):
        """Create standard network users - UX/choice handling"""
        print("\n--- Network Users ---")
        
        # Ask for both network users
        create_in = self._confirm("Add shuttle_in_user (inbound)?", True)
        create_out = self._confirm("Add shuttle_out_user (outbound)?", True)
        
        # Create based on choices
        if create_in or create_out:
            if create_in:
                self._add_templated_user('shuttle_in_user', source='existing', auth_method='smbpasswd')
                print("✅ Added shuttle_in_user to instructions")
            if create_out:
                self._add_templated_user('shuttle_out_user', auth_method='smbpasswd')
                print("✅ Added shuttle_out_user to instructions")
    
    def _create_test_user(self):
        """Create standard test user - actual creation logic"""
        self._add_templated_user('shuttle_tester')
        print("✅ Added shuttle_tester to instructions")
        
    def _choose_create_test_user(self):
        """Create standard test user - UX/choice handling"""
        print("\n--- Test User ---")
        
        if self._confirm("Add shuttle_tester?", True):
            self._create_test_user()
    
    def _create_admin_user(self):
        """Create admin user - actual creation logic with custom username"""
        username = input("Enter admin username [shuttle_admin]: ").strip() or "shuttle_admin"
        user_type = self._get_user_type()
        
        # Use template but override name and source
        self._add_templated_user('shuttle_admin', name=username, source=user_type)
        print(f"✅ Added {username} to instructions")
        
    def _choose_create_admin_user(self):
        """Create admin user - UX/choice handling"""
        print("\n--- Admin User ---")
        
        if self._confirm("Create admin user?", True):
            self._create_admin_user()
    
    # Component Selection Methods
    def _development_mode_components(self):
        """Component selection for development mode with recommended defaults"""
        print("\n=== Component Selection ===")
        print("Select which components to install and configure:")
        print("")
        
        install_recommended = self._confirm("Install recommended components (Samba + ACL tools + Firewall)?", True)
        
        if install_recommended:
            print("✅ Using recommended component configuration")
            # Keep existing defaults (all True)
        else:
            print("\nCustom component selection:")
            self.instructions['components']['install_samba'] = self._confirm("  Install Samba (network file sharing)?", False)
            self.instructions['components']['install_acl'] = self._confirm("  Install ACL tools (advanced permissions)?", True)
            self.instructions['components']['configure_firewall'] = self._confirm("  Configure firewall settings?", False)
            
            if self.instructions['components']['install_samba']:
                self.instructions['components']['configure_samba'] = self._confirm("  Configure Samba settings?", True)
            else:
                self.instructions['components']['configure_samba'] = False
        
        print("")
    
    # def _create_default_admin_user(self):
    #     """Create default admin user with standard settings"""
    #     admin_user = self._new_user(
    #         name='shuttle_admin',
    #         source='local',
    #         account_type='admin',
    #         primary_group='shuttle_admins'
    #     )
        
    #     # Include Samba access by default in development
    #     if self.instructions['components']['install_samba']:
    #         admin_user = self._add_samba_to_user(admin_user, enabled=True, auth_method='smbpasswd')
        
    #     self._add_user_to_instructions(admin_user)
        
    #     # Configure development-specific path permissions using the shared method
    #     self._configure_paths_for_environment('development')
    
    def _create_all_standard_roles_with_defaults(self):
        """Create all standard roles using default values"""
        print("✅ Creating all standard user roles with default names...")
        
        # Get all standard user templates and add them with default names
        user_templates = get_standard_user_templates()
        
        for template_name, template_data in user_templates.items():
            user_data = template_data.copy()
            # Ensure the name field is set to the template name
            user_data['name'] = template_name
            
            # Add to instructions using unified method
            self._add_user_to_instructions(user_data)
    
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
        return self._process_user_templates(templates, accept_defaults, allow_edit)
    
    def _create_path_config(self, actual_path, path_name, owner='root', group='shuttle_data_owners', 
                           mode='2770', acls=None, description=None):
        """
        Shared utility method to create a standard path configuration entry.
        Used by all modes to ensure consistent path configuration format.
        """
        config = {
            'owner': owner,
            'group': group,
            'mode': mode,
            'description': description or f'Shuttle {path_name}',
            'default_acls': {
                'file': ['u::rw-', 'g::rw-', 'o::---'],
                'directory': ['u::rwx', 'g::rwx', 'o::---']
            }
        }
        
        if acls:
            config['acls'] = acls if isinstance(acls, list) else [acls]
        
        return config
    
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
        description = f"""
=== CUSTOM MODE MENU ===

Current configuration:
  Groups: {len(self.groups)}
  Users: {len(self.users)}
  Paths: {len(self.instructions.get('paths', {}))}

1) Manage Groups
2) Manage Users
3) Configure Path Permissions
4) Configure Components
5) Import from Templates
6) Show Current Configuration
7) Validate Configuration

d) Delete Custom Configuration and return to main menu
r) Reset Custom Configuration
s) Use this configuration and continue.
        """
        print(description)
    
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
=== GROUP MANAGEMENT ===

Current groups in instructions: {len(self.groups)}
{groups_list}
0) Add Standard Groups to Instructions
1) Add Custom Group to Instructions
2) Remove Group from Instructions
3) Edit Group in Instructions

b) Back to Main Custom Configuration Menu
            """
            print(description)
            
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
        
        # Use new validation helper
        is_valid, error_msg = self._validate_group_name(group_name)
        if not is_valid:
            print(f"❌ {error_msg}")
            return
        
        description = input("Description: ").strip()
        gid_str = input("GID (leave blank for auto): ").strip()
        
        group_data = {
            'description': description or f"Custom group {group_name}"
        }
        
        if gid_str:
            try:
                gid = int(gid_str)
                # Use new GID validation helper
                is_valid, msg = self._validate_gid(gid, group_name)
                if not is_valid:
                    print(f"❌ {msg}")
                    return
                elif msg.startswith("WARNING"):
                    if not self._confirm(f"{msg} Continue?", False):
                        return
                group_data['gid'] = gid
            except ValueError:
                print("❌ Invalid GID - must be a number")
                return
        else:
            # Auto-assign GID
            group_data['gid'] = self._get_next_available_gid()
            print(f"Auto-assigned GID: {group_data['gid']}")
        
        self._add_group_to_instructions(group_name, group_data)
    
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
        
        # Show "Add All" option first at position 0
        print(f"  0) Add All Available Groups")
        
        # Show individual groups starting at position 1
        for i, (name, details) in enumerate(available_groups, 1):
            print(f"  {i}) {name} - {details['description']}")
        
        # Show already added groups with checkmarks
        for name, details in standard_groups.items():
            if name in self.groups:
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
                groups_to_add = {name: details for name, details in available_groups}
                added_count = self._add_groups_to_instructions(groups_to_add)
                print(f"✅ Added {added_count} standard groups to instructions")
        else:
            # Add single group
            choice = int(choice_str)
            if 1 <= choice <= len(available_groups):
                name, details = available_groups[choice - 1]
                self._add_group_to_instructions(name, details)
    
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
        """Edit a group"""
        if not self.groups:
            print("No groups in instructions to edit")
            return
        
        print("\n--- Edit Group in Instructions ---")
        
        # Use the new group selection helper
        group_name = self._select_group_from_list("Select group to edit")
        
        if not group_name:  # User cancelled
            return
        
        group_data = self.groups[group_name]
        
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
                # Use validation helper
                is_valid, msg = self._validate_gid(gid, group_name)
                if not is_valid:
                    print(f"❌ {msg}")
                    return
                elif msg.startswith("WARNING"):
                    if not self._confirm(f"{msg} Continue?", False):
                        return
                group_data['gid'] = gid
            except ValueError:
                print("❌ Invalid GID - must be a number")
                return
        
        print(f"✅ Updated group '{group_name}' in instructions")
    
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
=== USER MANAGEMENT ===

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
            print(f"Samba: {'Enabled' if self._is_samba_enabled(user) else 'Disabled'}")
            print("")
            print("1) Edit Groups")
            print("2) Edit Shell/Home Directory")
            print("3) Toggle Samba Access")
            print("4) Back to User Menu")
            
            choice = self._get_choice("Select action", ["1", "2", "3", "4"], "4")
            print()  # Add spacing between response and next section
            
            if choice == "1":
                self._custom_edit_user_groups(user)
            elif choice == "2":
                self._custom_edit_user_shell_home(user)
            elif choice == "3":
                self._toggle_samba_for_user(user)
            elif choice == "4":
                break
    
    def _toggle_samba_for_user(self, user: Dict[str, Any]) -> None:
        """Toggle Samba access for user - UI handling"""
        is_enabled = self._toggle_samba_access(user)
        if is_enabled:
            print("✅ Samba access enabled")
        else:
            print("✅ Samba access disabled")
    
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
        if self.groups:
            current_primary = user['groups']['primary']
            selected_group = self._select_group_from_list(
                "Select new primary group:",
                include_none=True,
                none_label="No primary group",
                current_group=current_primary
            )
            
            # Only update if user made a selection (not cancelled with empty default)
            if selected_group != current_primary:
                user['groups']['primary'] = selected_group
                if selected_group:
                    print(f"✅ Updated primary group to '{selected_group}'")
                else:
                    print("✅ Removed primary group")
        
        # Secondary groups
        if self.groups and self._confirm("\nEdit secondary groups?", False):
            exclude_primary = [user['groups']['primary']] if user['groups']['primary'] else []
            user['groups']['secondary'] = self._select_multiple_groups(
                "Select secondary groups:",
                already_selected=user['groups']['secondary'],
                exclude_groups=exclude_primary,
                primary_group=user['groups']['primary']
            )
            print("✅ Updated secondary groups")
    
    
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
            
            print(f"\nb) Back to Import Menu")
            
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
    
    def _custom_configure_path_permissions(self):
        """Configure permissions, ownership, and ACLs for shuttle paths"""
        # Ensure paths section exists
        if 'paths' not in self.instructions:
            self.paths = {}
        
        while True:
            print("\n=== PATH PERMISSION CONFIGURATION ===")
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
                self._configure_paths_for_environment('production')
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
            configured = " (permissions configured)" if actual_path in self.paths else " (not configured)"
            print(f"  {i}) {path_name} → {actual_path}{configured}")
        
        try:
            valid_choices = ["0"] + [str(i) for i in range(1, len(paths) + 1)]
            choice_str = self._get_choice("Select option", valid_choices, "0")
            
            if choice_str == "0":
                self._configure_paths_for_environment('production')
                return
            
            idx = int(choice_str)
            if 1 <= idx <= len(paths):
                path_name, actual_path = paths[idx - 1]
                self._configure_path_permission_details(actual_path, path_name)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _custom_configure_custom_path_permissions(self):
        """Configure permissions for a custom (non-shuttle) path"""
        print("\n=== CONFIGURE CUSTOM PATH PERMISSIONS ===")
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
                none_label="Enter custom group name"
            )
            
            if selected_group:
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
        
        print("\n=== EDIT PATH PERMISSION CONFIGURATION ===")
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
        
        print("\n=== REMOVE PATH PERMISSION CONFIGURATION ===")
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
    
    def _custom_import_standard_path_permissions(self):
        """Import standard path permission configurations"""
        if self._confirm("Import standard path permission configurations?", True):
            # Use unified method
            self._configure_paths_for_environment('production')

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
    
    def _custom_import_template(self):
        """Import from predefined templates"""
        description = """
--- Import Templates ---

1) Import Production Mode Template
2) Import Development Mode Template (single admin)  
3) Import Minimal Template (basic groups only)
4) Cancel
        """
        print(description)
        
        choice = self._get_choice("Select template", ["1", "2", "3", "4"], "1")
        
        if choice == "1":
            self._import_production_template()
        elif choice == "2":
            self._import_development_template()
        elif choice == "3":
            self._import_minimal_template()
    
    def _import_development_template(self):
        """Import development mode template"""
        print("\nImporting Development Mode template...")
        
        # Add admin group if not exists
        if 'shuttle_admins' not in self.groups:
            self.groups['shuttle_admins'] = {
                'description': 'Administrative users with full shuttle access',
                'gid': 5000
            }
        
        # Set components
        self.instructions['components']['install_samba'] = True
        self.instructions['components']['install_acl'] = True
        self.instructions['components']['configure_firewall'] = True
        self.instructions['components']['configure_samba'] = True
        
        print("✅ Imported Development Mode template")
        print("   - Added shuttle_admins group")
        print("   - Enabled all components")
        print("\nUse 'Import Standard Users' > 'Admin User' to add an admin user")
    
    def _import_production_template(self):
        """Import production template"""
        print("\nImporting Production template...")
        
        # Import all standard groups from centralized definitions
        standard_groups = get_standard_groups()
        
        imported = 0
        for name, details in standard_groups.items():
            if name not in self.groups:
                self.groups[name] = details.copy()
                imported += 1
        
        # Set production components from centralized definitions
        self.instructions['components'].update({
            'install_samba': True,
            'install_acl': True,
            'configure_users_groups': True,
            'configure_samba': True,
            'configure_firewall': True
        })
        
        # Set production environment
        self.instructions['metadata']['environment'] = 'production'
        self.instructions['settings']['interactive_mode'] = 'non-interactive'
        
        print("\n✅ Imported Production template")
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
            if name not in self.groups:
                self.groups[name] = details.copy()
                imported += 1
        
        # Minimal components
        self.instructions['components']['install_samba'] = False
        self.instructions['components']['install_acl'] = False
        self.instructions['components']['configure_firewall'] = False
        self.instructions['components']['configure_samba'] = False
        
        print(f"✅ Imported Minimal template")
        print(f"   - Added {imported} essential groups")
        print("   - Disabled optional components")
    
    def _custom_show_configuration(self):
        """Show current configuration summary"""
        print("\n=== Current Configuration ===")
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
        print("\n=== Configuration Validation ===")
        
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
    
    # =============================================
    # UNIFIED CONFIGURATION METHODS
    # =============================================
    
    def _configure_paths_for_environment(self, environment='production'):
        """Unified path configuration for any environment with catch-all support
        
        Args:
            environment: 'production' or 'development'
        """
        print(f"\n=== {environment.title()} Path Configuration ===")
        if environment == 'development':
            print("Setting up development-friendly permissions for all shuttle paths...")
        else:
            print("Setting up standard permissions for all shuttle paths...")
        
        # Get environment-specific path permissions
        standard_configs = get_standard_path_permissions(environment)
        paths_to_add = {}
        
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
    
    
    def _configure_components_interactive(self, firewall_default=True):
        """Unified component configuration for all modes"""
        print("\n=== Component Configuration ===")
        print("Configure system components:")
        print("")
        
        # Samba (network file sharing)
        print("🌐 Network File Sharing:")
        samba_install = self._confirm("  Install Samba for network file access?", True)
        self._add_component_to_instructions('install_samba', samba_install)
        
        if samba_install:
            samba_configure = self._confirm("  Configure Samba users and shares?", True)
            self._add_component_to_instructions('configure_samba', samba_configure)
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
        print("")
        
        # Always configure users/groups in all modes
        self._add_component_to_instructions('configure_users_groups', True)
        
        # Summary
        enabled_components = [k for k, v in self.instructions['components'].items() if v]
        if enabled_components:
            print(f"✅ {len(enabled_components)} components will be configured")
        else:
            print("⚠️  No additional components selected")
    
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
        # Validate all paths for safety before building config
        print("\n🔍 Validating path safety...")
        if not self._validate_all_paths(self.users):
            print("❌ Configuration cancelled due to path safety concerns.")
            sys.exit(1)
        
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
    
    # Count different document types
    group_count = sum(1 for doc in config if doc.get('type') == 'group')
    user_count = sum(1 for doc in config if doc.get('type') == 'user')
    path_count = sum(1 for doc in config if doc.get('type') == 'path')
    
    print(f"Groups: {group_count}")
    print(f"Users: {user_count}")
    print(f"Paths: {path_count}")
    
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