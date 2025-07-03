#!/usr/bin/env python3
"""
Configuration Wizard UI Module
Universal menu system and user interface utilities

This module contains UI/UX functionality:
- Menu display and navigation
- Input validation and confirmation dialogs
- Title formatting and display utilities
- User interaction patterns
"""

import sys
from typing import Dict, List, Any, Optional

class ConfigWizardUI:
    """User interface utilities for the configuration wizard"""
    
    def _wrap_title(self, title: str) -> str:
        """Wrap a title with decorative borders for consistent formatting"""
        return f"\n=== {title} ===\n"
    
    def _get_menu_choice(self, title: str, choices: List[Dict[str, Any]], 
                        default_key: str, include_back: bool = True, 
                        back_label: str = "parent menu") -> str:
        """
        Universal menu choice function - works for any menu pattern
        
        This is the core reusable function that replaces all hardcoded menu patterns.
        Any menu in the application can use this by defining a data structure.
        
        Args:
            title: Menu title/header text
            choices: List of choice dictionaries with 'key', 'label', and 'value' fields
            default_key: The key that should be used as default (shown in brackets)
            include_back: Whether to include a back option
            back_label: Label for the back option (e.g., "parent menu", "main menu")
        
        Returns:
            The selected choice key (not the value)
        
        Example usage:
            choices = [
                {'key': '1', 'label': 'Add Group', 'value': 'add'},
                {'key': '2', 'label': 'Edit Group', 'value': 'edit'},
                {'key': 'x', 'label': 'Exit', 'value': 'exit'}
            ]
            choice = self._get_menu_choice("Group Management", choices, '1')
        """
        while True:
            # Print title if provided
            if title:
                print(title)
            
            # Print all choices
            for choice in choices:
                key = choice['key']
                label = choice['label']
                # Show default marker
                if key == default_key:
                    print(f"  {key}) {label} [default]")
                else:
                    print(f"  {key}) {label}")
            
            # Add back option if requested
            if include_back:
                print(f"  b) Back to {back_label}")
            
            # Get user input
            prompt = f"\nChoice [{default_key}]: " if default_key else "\nChoice: "
            user_input = input(prompt).strip().lower()
            
            # Handle empty input (use default)
            if not user_input and default_key:
                return default_key
            
            # Check if input matches any choice key
            for choice in choices:
                if user_input == choice['key'].lower():
                    return choice['key']
            
            # Check for back option
            if include_back and user_input == 'b':
                return 'b'
            
            # Invalid input
            print(f"❌ Invalid choice '{user_input}'. Please try again.")
    
    def _confirm(self, prompt: str, default: bool = True) -> bool:
        """
        Ask user for yes/no confirmation with validation loop
        
        Args:
            prompt: The question to ask
            default: Default value if user just presses enter
            
        Returns:
            True for yes, False for no
        """
        default_str = "Y/n" if default else "y/N"
        
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            
            if not response:
                return default
            elif response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            elif response in ['x', 'exit']:
                print("Exiting configuration wizard...")
                sys.exit(3)
            else:
                print(f"❌ Invalid input '{response}'. Please enter 'y' for yes, 'n' for no, or 'x' to exit.")
    
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
            # Count from wizard state (must be provided by calling class)
            group_count = len(getattr(self, 'groups', {}))
            user_count = len(getattr(self, 'users', []))
            path_count = len(getattr(self, 'paths', {}))
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
    
    def _display_missing_references(self, context: str = ""):
        """Display missing group/user references with helpful context"""
        missing_groups = getattr(self, '_last_missing_groups', set())
        missing_users = getattr(self, '_last_missing_users', set())
        
        if missing_groups or missing_users:
            print(f"\n⚠️  Missing References in {context}:")
            if missing_groups:
                print(f"   Groups: {', '.join(sorted(missing_groups))}")
            if missing_users:
                print(f"   Users: {', '.join(sorted(missing_users))}")
            print()
    
    def _get_choice_value(self, choice_key: str, choices: List[Dict[str, Any]]) -> Any:
        """Get the value associated with a choice key"""
        for choice in choices:
            if choice['key'] == choice_key:
                return choice['value']
        return None
    
    def _find_default_key(self, choices: List[Dict[str, Any]]) -> Optional[str]:
        """Find the first choice key to use as default"""
        return choices[0]['key'] if choices else None
    
    def _display_configuration_summary(self):
        """Display current configuration summary"""
        counts = self._get_config_counts()
        
        print(f"\n📊 Current Configuration:")
        print(f"   Groups: {counts['groups']}")
        print(f"   Users: {counts['users']}")
        print(f"   Paths: {counts['paths']}")
        
        # Count user types if users exist
        if hasattr(self, 'users') and self.users:
            service_users = sum(1 for user in self.users if user.get('account_type') == 'service')
            interactive_users = sum(1 for user in self.users if user.get('account_type') == 'interactive')
            if service_users > 0 or interactive_users > 0:
                print(f"   └─ Service accounts: {service_users}")
                print(f"   └─ Interactive accounts: {interactive_users}")
        
        print()
    
    def _display_warning(self, message: str):
        """Display a warning message with consistent formatting"""
        print(f"\n⚠️  WARNING: {message}\n")
    
    def _display_error(self, message: str):
        """Display an error message with consistent formatting"""
        print(f"\n❌ ERROR: {message}\n")
    
    def _display_success(self, message: str):
        """Display a success message with consistent formatting"""
        print(f"\n✅ {message}\n")
    
    def _display_info(self, message: str):
        """Display an info message with consistent formatting"""
        print(f"\nℹ️  {message}\n")
    
    def _get_text_input(self, prompt: str, default: str = None, validator=None) -> Optional[str]:
        """
        Get text input from user with optional validation
        
        Args:
            prompt: Input prompt
            default: Default value if user enters nothing
            validator: Optional function to validate input (returns bool, error_msg)
            
        Returns:
            User input or None if cancelled
        """
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if not user_input:
                return None
            
            if user_input.lower() in ['x', 'exit', 'cancel']:
                return None
            
            # Apply validator if provided
            if validator:
                is_valid, error_msg = validator(user_input)
                if not is_valid:
                    print(f"❌ {error_msg}")
                    continue
            
            return user_input
    
    def _get_numeric_input(self, prompt: str, default: int = None, 
                          min_value: int = None, max_value: int = None) -> Optional[int]:
        """
        Get numeric input from user with validation
        
        Args:
            prompt: Input prompt
            default: Default value if user enters nothing
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            User input as integer or None if cancelled
        """
        while True:
            if default is not None:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if not user_input:
                return None
            
            if user_input.lower() in ['x', 'exit', 'cancel']:
                return None
            
            try:
                value = int(user_input)
                
                if min_value is not None and value < min_value:
                    print(f"❌ Value must be at least {min_value}")
                    continue
                
                if max_value is not None and value > max_value:
                    print(f"❌ Value must be at most {max_value}")
                    continue
                
                return value
                
            except ValueError:
                print(f"❌ '{user_input}' is not a valid number")
    
    def _pause_for_user(self, message: str = "Press Enter to continue..."):
        """Pause execution and wait for user input"""
        input(f"\n{message}")
    
    def _display_list_with_numbers(self, items: List[str], title: str = None, 
                                  start_number: int = 1) -> None:
        """Display a numbered list of items"""
        if title:
            print(f"\n{title}:")
        
        for i, item in enumerate(items, start_number):
            print(f"  {i}) {item}")
        print()
    
    def _display_key_value_pairs(self, data: Dict[str, Any], title: str = None, 
                                indent: str = "  ") -> None:
        """Display key-value pairs in a formatted way"""
        if title:
            print(f"\n{title}:")
        
        for key, value in data.items():
            print(f"{indent}{key}: {value}")
        print()