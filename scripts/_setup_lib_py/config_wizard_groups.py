#!/usr/bin/env python3
"""
Configuration Wizard Groups Module
Group management and configuration

This module contains group-specific functionality:
- Group template handling and editing
- Group validation and GID management
- Multiple group selection
- Group configuration workflows
"""

import sys
from typing import Dict, List, Any, Optional, Set
from post_install_standard_configuration_reader import get_standard_groups, get_custom_group_base_templates

class ConfigWizardGroups:
    """Group management functionality for the configuration wizard"""
    
    def _get_sorted_groups(self) -> List[str]:
        """Get sorted list of group names"""
        return sorted(self.groups.keys())
    
    def _find_users_using_group(self, group_name: str) -> List[str]:
        """Find all users that reference a group
        
        Returns:
            List of usernames using the group
        """
        users_using_group = []
        
        for user in self.users:
            # Check primary group
            if user.get('groups', {}).get('primary') == group_name:
                users_using_group.append(user['name'])
            # Check secondary groups
            elif group_name in user.get('groups', {}).get('secondary', []):
                users_using_group.append(user['name'])
        
        return users_using_group
    
    def _get_next_available_gid(self, start_gid: int = 5000) -> int:
        """Find the next available GID starting from start_gid"""
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
        experience across the wizard.
        
        Args:
            group_name: Name of the group being configured
            template_data: Group configuration template
            
        Returns:
            Modified template or None if cancelled
        """
        edited_template = template_data.copy()
        
        while True:
            print(f"\n{self._wrap_title('Edit Group Template')}")
            print(f"Group: {group_name}")
            self._display_group_template(group_name, edited_template)
            
            edit_choices = [
                {'key': '1', 'label': 'Edit Description', 'value': 'description'},
                {'key': '2', 'label': 'Edit GID', 'value': 'gid'},
                {'key': 's', 'label': 'Save Changes', 'value': 'save'},
                {'key': 'x', 'label': 'Cancel (Discard Changes)', 'value': 'cancel'}
            ]
            
            choice = self._get_menu_choice(
                "Edit Options:",
                edit_choices,
                's',  # Default to save
                include_back=False
            )
            
            if choice == 's':
                return edited_template
            elif choice == 'x':
                return None
            elif choice == '1':  # Edit description
                new_desc = self._get_text_input(
                    "Enter group description",
                    edited_template.get('description', '')
                )
                if new_desc is not None:
                    edited_template['description'] = new_desc
            elif choice == '2':  # Edit GID
                current_gid = edited_template.get('gid')
                if current_gid:
                    default_gid = current_gid
                else:
                    default_gid = self._get_next_available_gid()
                
                new_gid = self._get_numeric_input(
                    "Enter GID (Group ID)",
                    default_gid,
                    min_value=0
                )
                
                if new_gid is not None:
                    is_valid, error_msg = self._validate_gid(new_gid, group_name)
                    if is_valid:
                        edited_template['gid'] = new_gid
                        if "WARNING" in error_msg:
                            self._display_warning(error_msg)
                    else:
                        self._display_error(error_msg)
    
    def _display_group_template(self, group_name: str, template_data: Dict[str, Any]):
        """Display group template information in a consistent format"""
        print(f"\nGroup Configuration:")
        print(f"  Name: {group_name}")
        print(f"  Description: {template_data.get('description', 'No description')}")
        
        gid = template_data.get('gid')
        if gid:
            print(f"  GID: {gid}")
        else:
            print(f"  GID: (automatic)")
    
    def _get_all_available_groups(self) -> Dict[str, Dict[str, Any]]:
        """Get all available groups from standard configs and custom templates"""
        available_groups = {}
        
        # Add standard groups for all environments
        standard_groups = get_standard_groups()
        for group_name, group_data in standard_groups.items():
            available_groups[group_name] = {
                **group_data,
                'source': 'standard',
                'recommended': group_data.get('recommended', False)
            }
        
        # Add custom group base templates
        custom_templates = get_custom_group_base_templates()
        for template_name, template_data in custom_templates.items():
            available_groups[template_name] = {
                **template_data,
                'source': 'custom_template',
                'recommended': False
            }
        
        return available_groups
    
    def _select_group_from_list(self, prompt: str, include_none: bool = False, 
                               none_label: str = "None", current_group: str = None,
                               exclude_groups: List[str] = None, include_back: bool = True) -> Optional[str]:
        """
        Select a group from available groups with consistent interface
        
        Args:
            prompt: User prompt text
            include_none: Include a "None" option
            none_label: Label for the "None" option
            current_group: Currently selected group (for editing)
            exclude_groups: Groups to exclude from the list
            include_back: Include back navigation option
            
        Returns:
            Selected group name, None for none option, or None for back/cancel
        """
        available_groups = self._get_all_available_groups()
        
        # Remove excluded groups
        if exclude_groups:
            for group_name in exclude_groups:
                available_groups.pop(group_name, None)
        
        # Build menu items
        menu_items = []
        
        # Add special "Add All" option as menu item 0
        if not current_group:  # Only show in selection mode, not edit mode
            menu_items.append({
                'key': '0',
                'label': 'Add All Available Groups',
                'value': '__add_all__'
            })
        
        # Regular group selections start at 1
        item_number = 1
        for group_name, group_data in sorted(available_groups.items()):
            in_instructions = group_name in self.groups
            source_label = ""
            
            if group_data.get('recommended'):
                source_label += " [RECOMMENDED]"
            
            if in_instructions:
                label = f"{group_name} ✓{source_label}"
            else:
                label = f"{group_name} ○{source_label}"
                
            menu_items.append({
                'key': str(item_number),
                'label': label,
                'value': group_name
            })
            item_number += 1
        
        # Add None option if requested
        if include_none:
            menu_items.append({
                'key': str(item_number),
                'label': none_label,
                'value': None
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
        
        return choice_value
    
    def _select_multiple_groups(self, prompt: str, already_selected: List[str] = None,
                               max_selections: int = None, include_back: bool = True) -> Optional[List[str]]:
        """
        Select multiple groups with a checkbox-style interface
        
        Args:
            prompt: User prompt text
            already_selected: Previously selected groups
            max_selections: Maximum number of groups that can be selected
            include_back: Include back navigation option
            
        Returns:
            List of selected group names, or None if cancelled
        """
        if already_selected is None:
            already_selected = []
        
        selected_groups = already_selected.copy()
        available_groups = self._get_all_available_groups()
        
        while True:
            print(f"\n{prompt}")
            
            if max_selections:
                remaining = max_selections - len(selected_groups)
                print(f"Selected: {len(selected_groups)}/{max_selections} (can select {remaining} more)")
            else:
                print(f"Selected: {len(selected_groups)} groups")
            
            # Show currently selected
            if selected_groups:
                print("Currently selected:", ", ".join(selected_groups))
            
            # Build menu
            menu_items = []
            
            # Special actions
            if not selected_groups:
                menu_items.append({
                    'key': '0',
                    'label': 'Select All Available Groups',
                    'value': '__select_all__'
                })
            
            menu_items.append({
                'key': 'd',
                'label': 'Done - Save Selections',
                'value': '__done__'
            })
            
            # Group selection options
            item_number = 1
            for group_name, group_data in sorted(available_groups.items()):
                is_selected = group_name in selected_groups
                can_select = (not max_selections or 
                            len(selected_groups) < max_selections or 
                            is_selected)
                
                if is_selected:
                    label = f"[✓] {group_name} - SELECTED"
                    action = "remove"
                elif can_select:
                    label = f"[ ] {group_name}"
                    action = "add"
                else:
                    label = f"[×] {group_name} - (limit reached)"
                    action = "disabled"
                
                if group_data.get('recommended'):
                    label += " [RECOMMENDED]"
                
                if action != "disabled":
                    menu_items.append({
                        'key': str(item_number),
                        'label': label,
                        'value': (group_name, action)
                    })
                    item_number += 1
            
            choice = self._get_menu_choice(
                "Select groups (choose number to toggle):",
                menu_items,
                'd',  # Default to done
                include_back=include_back
            )
            
            if choice == 'b':
                return None
            elif choice == 'd' or choice == '__done__':
                return selected_groups
            
            choice_value = self._get_choice_value(choice, menu_items)
            
            if choice_value == '__select_all__':
                # Add all groups up to limit
                for group_name in sorted(available_groups.keys()):
                    if group_name not in selected_groups:
                        if not max_selections or len(selected_groups) < max_selections:
                            selected_groups.append(group_name)
                        else:
                            break
            elif isinstance(choice_value, tuple):
                group_name, action = choice_value
                if action == "add" and group_name not in selected_groups:
                    selected_groups.append(group_name)
                elif action == "remove" and group_name in selected_groups:
                    selected_groups.remove(group_name)
    
    def _configure_groups(self):
        """Main group configuration interface"""
        while True:
            print(f"\n{self._wrap_title('GROUP MANAGEMENT')}")
            print(f"Current groups: {len(self.groups)}")
            
            if self.groups:
                print("Configured groups:")
                for i, (group_name, group_data) in enumerate(sorted(self.groups.items()), 1):
                    gid = group_data.get('gid', 'auto')
                    description = group_data.get('description', 'No description')
                    print(f"  {i}. {group_name} (GID: {gid}) - {description}")
            
            # Display validation warnings if needed
            self._display_missing_references("current configuration")
            
            menu_choices = [
                {'key': '0', 'label': 'Add All Standard Groups', 'value': 'add_all'},
                {'key': '1', 'label': 'Add Group from Template', 'value': 'add_template'},
                {'key': '2', 'label': 'Add Custom Group', 'value': 'add_custom'},
                {'key': '3', 'label': 'Edit Group', 'value': 'edit'},
                {'key': '4', 'label': 'Remove Group', 'value': 'remove'},
            ]
            
            choice = self._get_menu_choice(
                "Group Management Options:",
                menu_choices,
                '1',  # Default to add from template
                include_back=True,
                back_label="main menu"
            )
            
            if choice == 'b':
                break
            elif choice == '0':  # Add all standard groups
                self._add_all_standard_groups()
            elif choice == '1':  # Add from template
                self._add_group_from_template()
            elif choice == '2':  # Add custom group
                self._add_custom_group()
            elif choice == '3':  # Edit group
                self._edit_existing_group()
            elif choice == '4':  # Remove group
                self._remove_group()
    
    def _add_all_standard_groups(self):
        """Add all standard groups for the current environment"""
        standard_groups = get_standard_groups()
        added_count = 0
        
        for group_name, group_data in standard_groups.items():
            if group_name not in self.groups:
                self.groups[group_name] = group_data.copy()
                added_count += 1
        
        if added_count > 0:
            self._display_success(f"Added {added_count} standard groups to configuration")
        else:
            self._display_info("All standard groups are already configured")
    
    def _add_group_from_template(self):
        """Add a group using available templates"""
        group_name = self._select_group_from_list(
            "Select a group template to add:",
            include_back=True
        )
        
        if group_name is None:
            return
        
        if group_name == '__add_all__':
            self._add_all_standard_groups()
            return
        
        if group_name in self.groups:
            self._display_error(f"Group '{group_name}' is already configured")
            return
        
        # Get template data
        available_groups = self._get_all_available_groups()
        template_data = available_groups.get(group_name, {})
        
        # Ask user what to do with the template
        template_choice = self._get_template_action()
        
        if template_choice == 'use':
            # Use template as-is
            self.groups[group_name] = template_data.copy()
            self._display_success(f"Added group '{group_name}' using template")
        elif template_choice == 'edit':
            # Edit template interactively
            edited_template = self._edit_group_template_interactively(group_name, template_data)
            if edited_template:
                self.groups[group_name] = edited_template
                self._display_success(f"Added group '{group_name}' with custom settings")
        # 'skip' case - do nothing
    
    def _add_custom_group(self):
        """Add a completely custom group"""
        group_name = self._get_text_input(
            "Enter group name",
            validator=lambda name: self._validate_group_name(name)
        )
        
        if not group_name:
            return
        
        # Create basic template
        template_data = {
            'description': f'Custom group: {group_name}',
            'gid': self._get_next_available_gid()
        }
        
        # Edit the template
        edited_template = self._edit_group_template_interactively(group_name, template_data)
        if edited_template:
            self.groups[group_name] = edited_template
            self._display_success(f"Added custom group '{group_name}'")
    
    def _edit_existing_group(self):
        """Edit an existing group configuration"""
        if not self.groups:
            self._display_error("No groups configured to edit")
            return
        
        # Select group to edit
        group_names = sorted(self.groups.keys())
        
        menu_items = []
        for i, group_name in enumerate(group_names, 1):
            group_data = self.groups[group_name]
            gid = group_data.get('gid', 'auto')
            description = group_data.get('description', 'No description')
            menu_items.append({
                'key': str(i),
                'label': f"{group_name} (GID: {gid}) - {description}",
                'value': group_name
            })
        
        choice = self._get_menu_choice(
            "Select group to edit:",
            menu_items,
            '1',
            include_back=True
        )
        
        if choice == 'b':
            return
        
        group_name = self._get_choice_value(choice, menu_items)
        if group_name:
            template_data = self.groups[group_name].copy()
            edited_template = self._edit_group_template_interactively(group_name, template_data)
            if edited_template:
                self.groups[group_name] = edited_template
                self._display_success(f"Updated group '{group_name}'")
    
    def _remove_group(self):
        """Remove a group from configuration"""
        if not self.groups:
            self._display_error("No groups configured to remove")
            return
        
        # Select group to remove
        group_names = sorted(self.groups.keys())
        
        menu_items = []
        for i, group_name in enumerate(group_names, 1):
            # Check if any users reference this group
            users_using = self._find_users_using_group(group_name)
            if users_using:
                label = f"{group_name} (⚠️  Used by: {', '.join(users_using)})"
            else:
                label = group_name
            
            menu_items.append({
                'key': str(i),
                'label': label,
                'value': group_name
            })
        
        choice = self._get_menu_choice(
            "Select group to remove:",
            menu_items,
            '1',
            include_back=True
        )
        
        if choice == 'b':
            return
        
        group_name = self._get_choice_value(choice, menu_items)
        if group_name:
            # Check for user references
            users_using = self._find_users_using_group(group_name)
            if users_using:
                self._display_warning(f"Group '{group_name}' is used by users: {', '.join(users_using)}")
                if not self._confirm(f"Remove group '{group_name}' anyway? This will leave users with invalid group references."):
                    return
            
            del self.groups[group_name]
            self._display_success(f"Removed group '{group_name}'")
    
    def _get_template_action(self) -> str:
        """Ask user what to do with a template"""
        action_choices = [
            {'key': '1', 'label': 'Use template as-is', 'value': 'use'},
            {'key': '2', 'label': 'Edit template before adding', 'value': 'edit'},
            {'key': '3', 'label': 'Skip this template', 'value': 'skip'}
        ]
        
        choice = self._get_menu_choice(
            "What would you like to do with this template?",
            action_choices,
            '1',
            include_back=False
        )
        
        return self._get_choice_value(choice, action_choices)