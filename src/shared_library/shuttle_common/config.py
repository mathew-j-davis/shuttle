"""
Common Configuration Module

This module provides configuration classes and parsing functions
for settings that are shared between multiple applications.
"""

import os
import argparse
import configparser
import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommonConfig:
    """
    Configuration settings shared across applications.
    Includes logging, notifications, throttling, and ledger settings.
    """
    # Logging settings
    log_path: Optional[str] = None
    log_level: int = logging.INFO
    
    # Notification settings
    notify: bool = False
    notify_summary: bool = False
    notify_recipient_email: Optional[str] = None
    notify_sender_email: Optional[str] = None
    notify_smtp_server: Optional[str] = None
    notify_smtp_port: Optional[int] = None
    notify_username: Optional[str] = None
    notify_password: Optional[str] = None
    notify_use_tls: bool = True
    
    # Ledger settings
    ledger_path: Optional[str] = None  # Path to track tested defender versions


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add common command-line arguments to an argument parser.
    
    Args:
        parser: ArgumentParser instance to add arguments to
    """
    # Add logging arguments
    parser.add_argument('-LogPath', help='Path to the log directory')
    parser.add_argument('-LogLevel', default=None, 
                        help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    

    parser.add_argument('-SettingsPath', default=os.path.join(os.getenv('HOME') or os.path.expanduser('~'), '.shuttle', 'settings.ini'),
                        help='Path to the settings file')
    # Add notification arguments
    parser.add_argument('-Notify', 
                      help='Enable email notifications for important events',
                      type=bool,
                      default=None)
    parser.add_argument('-NotifySummary', 
                      help='Enable email notifications on completion of all transfers',
                      type=bool,
                      default=None)
    parser.add_argument('-NotifyRecipientEmail', 
                      help='Email address of the recipient for notifications',
                      default=None)
    parser.add_argument('-NotifySenderEmail', 
                      help='Email address of the sender for notifications',
                      default=None)
    parser.add_argument('-NotifySmtpServer', 
                      help='SMTP server address for sending notifications',
                      default=None)
    parser.add_argument('-NotifySmtpPort', 
                      help='SMTP server port for sending notifications',
                      type=int,
                      default=None)
    parser.add_argument('-NotifyUsername', 
                      help='SMTP username for authentication',
                      default=None)
    parser.add_argument('-NotifyPassword', 
                      help='SMTP password for authentication',
                      default=None)
    parser.add_argument('-NotifyUseTLS', 
                      help='Use TLS encryption for SMTP',
                      type=bool,
                      default=None)
    
    # Add ledger arguments
    parser.add_argument('-LedgerPath',
                      help='Path to the ledger file for tracking tested versions',
                      default=None)


def parse_common_config(args=None, settings_file_path=None) -> CommonConfig:
    """
    Parse common configuration settings from command line arguments and settings file.
    
    Args:
        args: Parsed argument namespace (optional)
        settings_file_path: Path to settings file (optional)
    
    Returns:
        CommonConfig object with parsed settings
    """
    config = CommonConfig()
    
    # If no args provided, return default config
    if args is None and settings_file_path is None:
        return config
    
    # Load settings from file if path provided
    settings_file_config = configparser.ConfigParser()
    if settings_file_path and os.path.exists(settings_file_path):
        settings_file_config.read(settings_file_path)
    
    # Helper function to convert a value to boolean
    def convert_to_bool(value):
        """
        Convert a value to boolean using string matching for string values.
        Strings like 'true', 'yes', and '1' are converted to True.
        Other strings and falsy values are converted to False.
        
        Args:
            value: The value to convert to boolean
            
        Returns:
            bool: The converted boolean value
        """
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1')
        return bool(value)
        
    # Helper function to safely convert a value to a specified type
    def convert_to_type(value, type_func):
        """
        Safely convert a value to the specified type.
        Special handling for boolean conversion using string matching.
        
        Args:
            value: The value to convert
            type_func: The type function to use for conversion (int, str, bool, etc.)
            
        Returns:
            The converted value, or None if conversion fails
        """
        if type_func is None:
            return value
            
        # Special handling for boolean conversion
        if type_func == bool:
            return convert_to_bool(value)
            
        try:
            return type_func(value)
        except (ValueError, TypeError):
            # Return None to signal conversion failure
            return None
    
    # Helper function to get settings with priority: CLI args > settings file > default
    def get_setting(arg_value, section, option, default=None, type=None):
        # Try argument value first (highest priority)
        if arg_value is not None:
            converted_value = convert_to_type(arg_value, type)
            if converted_value is not None:
                return converted_value
            # If conversion fails, try settings file instead
            
        # Next try settings file (medium priority)
        if settings_file_config.has_section(section) and settings_file_config.has_option(section, option):
            setting_value = settings_file_config.get(section, option)
            converted_value = convert_to_type(setting_value, type)
            if converted_value is not None:
                return converted_value
            # If conversion fails, fall back to default
            
        # Fall back to default
        return default
    
    # Helper function to get settings from args or config file
    def get_setting_from_arg_or_file(args_obj, arg_name, section, option, default=None, type=None):
        """
        Get setting with priority: CLI args > settings file > default
        Extracts the arg_name from args_obj automatically
        
        Args:
            args_obj: The args object containing command line arguments
            arg_name: Name of the argument to extract from args_obj
            section: Section in config file
            option: Option name in config file
            default: Default value if not found in args or config file
            type: Optional type conversion function (int, str, bool, etc.)
            
        Returns:
            The setting value based on priority with type conversion applied
        """
        arg_value = getattr(args_obj, arg_name, None) if args_obj else None
        return get_setting(arg_value, section, option, default, type)
    
    # Parse logging settings
    config.log_path = get_setting_from_arg_or_file(args, 'LogPath', 'logging', 'log_path', None)
    
    # Get log level as a string and convert to logging constant
    log_level_str = get_setting_from_arg_or_file(args, 'LogLevel', 'logging', 'log_level', 'INFO')
    if log_level_str:
        log_level_str = log_level_str.upper()
        config.log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Parse notification settings
    config.notify = get_setting_from_arg_or_file(args, 'Notify', 'notifications', 'notify', False, bool)
    config.notify_summary = get_setting_from_arg_or_file(args, 'NotifySummary', 'notifications', 'notify_summary', False, bool)
    
    config.notify_recipient_email = get_setting_from_arg_or_file(args, 'NotifyRecipientEmail', 'notifications', 'recipient_email', None)
    config.notify_sender_email = get_setting_from_arg_or_file(args, 'NotifySenderEmail', 'notifications', 'sender_email', None)
    config.notify_smtp_server = get_setting_from_arg_or_file(args, 'NotifySmtpServer', 'notifications', 'smtp_server', None)
    config.notify_smtp_port = get_setting_from_arg_or_file(args, 'NotifySmtpPort', 'notifications', 'smtp_port', None, int)
    
    config.notify_username = get_setting_from_arg_or_file(args, 'NotifyUsername', 'notifications', 'username', None)
    config.notify_password = get_setting_from_arg_or_file(args, 'NotifyPassword', 'notifications', 'password', None)
    config.notify_use_tls = get_setting_from_arg_or_file(args, 'NotifyUseTLS', 'notifications', 'use_tls', True, bool)
    
    # Parse ledger settings
    config.ledger_path = get_setting_from_arg_or_file(args, 'LedgerPath', 'paths', 'ledger_path', None)
    
    return config
