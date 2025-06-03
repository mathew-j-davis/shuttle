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
from typing import Optional, Any, Callable, TypeVar, Union
from .logger_injection import with_logger

T = TypeVar('T')


# Convert a value to boolean using string matching for string values
@with_logger
def convert_to_bool(value, logger=None) -> bool:
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
    

# Safely convert a value to a specified type
@with_logger
def convert_to_type(value, type_func, logger=None) -> Any:
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
@with_logger
def get_setting(arg_value, section, option, default: T = None, type: Optional[Callable[[Any], T]] = None, config=None, logger=None) -> T:
    """
    Get setting with priority: CLI args > settings file > default
    
    Args:
        arg_value: Value from command line argument
        section: Section in config file
        option: Option name in config file
        default: Default value if not found in args or config file
        type: Optional type conversion function (int, str, bool, etc.)
        config: ConfigParser object (if None, setting from file will be None)
        
    Returns:
        The setting value based on priority with type conversion applied
    """
    # Try argument value first (highest priority)
    if arg_value is not None:
        converted_value = convert_to_type(arg_value, type)
        if converted_value is not None:
            return converted_value
        # If conversion fails, try settings file instead
        
    # Next try settings file (medium priority)
    if config and config.has_section(section) and config.has_option(section, option):
        setting_value = config.get(section, option)
        converted_value = convert_to_type(setting_value, type)
        if converted_value is not None:
            return converted_value
        # If conversion fails, fall back to default
        
    # Fall back to default
    return default


# Helper function to get settings from args or config file
@with_logger
def get_setting_from_arg_or_file(args_obj, arg_name: str, section: str, option: str, default: T = None, type: Optional[Callable[[Any], T]] = None, config=None, logger=None) -> T:
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
        config: ConfigParser object (if None, setting from file will be None)
        
    Returns:
        The setting value based on priority with type conversion applied
    """
    arg_value = getattr(args_obj, arg_name, None) if args_obj else None
    return get_setting(arg_value, section, option, default, type, config)


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
    notify_recipient_email_error: Optional[str] = None
    notify_recipient_email_summary: Optional[str] = None
    notify_recipient_email_hazard: Optional[str] = None
    notify_sender_email: Optional[str] = None
    notify_smtp_server: Optional[str] = None
    notify_smtp_port: Optional[int] = None
    notify_username: Optional[str] = None
    notify_password: Optional[str] = None
    notify_use_tls: bool = True
    
    # Scanning settings
    defender_handles_suspect_files: bool = True
    
    # Ledger settings
    ledger_path: Optional[str] = None  # Path to track tested defender versions
    
 


@with_logger
def add_common_arguments(parser: argparse.ArgumentParser, logger=None) -> None:
    """
    Add common command-line arguments to an argument parser.
    
    Args:
        parser: ArgumentParser instance to add arguments to
    """
    # Add logging arguments
    parser.add_argument('--log-path', help='Path to the log directory')
    parser.add_argument('--log-level', default=None, 
                        help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    

    parser.add_argument('--settings-path', 
                        help='Path to the settings file (if not specified, standard locations will be searched)')
    
    # Add notification arguments
    parser.add_argument('--notify', 
                      help='Enable email notifications for important events',
                      type=bool,
                      default=None)
    parser.add_argument('--notify-summary', 
                      help='Enable email notifications on completion of all transfers',
                      type=bool,
                      default=None)
    parser.add_argument('--notify-recipient-email', 
                      help='Email address of the recipient for notifications',
                      default=None)
    parser.add_argument('--notify-recipient-email-error', 
                      help='Email address for error notifications (defaults to notify-recipient-email)',
                      default=None)
    parser.add_argument('--notify-recipient-email-summary', 
                      help='Email address for summary notifications (defaults to notify-recipient-email)',
                      default=None)
    parser.add_argument('--notify-recipient-email-hazard', 
                      help='Email address for hazard/malware notifications (defaults to notify-recipient-email)',
                      default=None)
    parser.add_argument('--notify-sender-email', 
                      help='Email address of the sender for notifications',
                      default=None)
    parser.add_argument('--notify-smtp-server', 
                      help='SMTP server address for sending notifications',
                      default=None)
    parser.add_argument('--notify-smtp-port', 
                      help='SMTP server port for sending notifications',
                      type=int,
                      default=None)
    parser.add_argument('--notify-username', 
                      help='SMTP username for authentication',
                      default=None)
    parser.add_argument('--notify-password', 
                      help='SMTP password for authentication',
                      default=None)
    parser.add_argument('--notify-use-tls', 
                      help='Use TLS encryption for SMTP',
                      type=bool,
                      default=None)
    
    # Add scanning arguments
    parser.add_argument('--defender-handles-suspect-files', 
                      action='store_true',
                      default=None,
                      help='Let Microsoft Defender handle suspect files (default: True)')
    
    # Add ledger arguments
    parser.add_argument('--ledger-path',
                      help='Path to the ledger file for tracking tested versions',
                      default=None)


@with_logger
def find_config_file(logger=None):
    """
    Search for a config file in standard locations.
    
    Returns:
        Path to the first config file found, or None if no config file is found
    """
    # Check environment variable first
    env_path = os.getenv('SHUTTLE_CONFIG_PATH')
    if env_path and os.path.isfile(env_path):
        return env_path
        
    # Define potential config file locations
    home_dir = os.getenv('HOME') or os.path.expanduser('~')

    # Unix/Linux/MacOS
    potential_locations = [
        os.path.join(home_dir, '.config', 'shuttle', 'config.conf'),
        os.path.join(home_dir, '.shuttle', 'config.conf'),
        os.path.join(home_dir, '.shuttle', 'settings.ini'),
        '/etc/shuttle/config.conf',
        '/usr/local/etc/shuttle/config.conf'
    ]
    
    # Filter out None values and check each location
    for location in filter(None, potential_locations):
        if os.path.isfile(location):
            return location
            
    return None


@with_logger
def parse_common_config(args=None, logger=None):
    """
    Parse common configuration settings from command line arguments and settings file.
    
    Args:
        args: Parsed argument namespace (optional)
        settings_file_path: Path to settings file (optional)
    
    Returns:
        tuple: (CommonConfig object with parsed settings, ConfigParser object)
    """
    config = CommonConfig()
    
    # Initialize settings file config parser
    settings_file_config = configparser.ConfigParser()
    
    # Determine config file path with priority:
    # 1. Command line argument (if provided)
    # 2. Search in standard locations
    config_file_path = None
    if args and hasattr(args, 'settings_path') and args.settings_path:
        config_file_path = args.settings_path
    else:
        config_file_path = find_config_file()
    
    # Try to load settings from file if found
    if config_file_path:
        settings_file_config.read(config_file_path)
    
    # We'll use our module-level helpers for getting settings from the config file
    
    # Use the module-level get_setting_from_arg_or_file function
    # to get settings based on priority
    
    # Parse logging settings
    config.log_path = get_setting_from_arg_or_file(args, 'log_path', 'logging', 'log_path', None, None, settings_file_config)
    
    # Get log level as a string and convert to logging constant
    log_level_str = get_setting_from_arg_or_file(args, 'log_level', 'logging', 'log_level', 'INFO', None, settings_file_config)
    if log_level_str:
        log_level_str = log_level_str.upper()
        config.log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Parse notification settings
    config.notify = get_setting_from_arg_or_file(args, 'notify', 'notifications', 'notify', False, bool, settings_file_config)
    config.notify_summary = get_setting_from_arg_or_file(args, 'notify_summary', 'notifications', 'notify_summary', False, bool, settings_file_config)
    
    config.notify_recipient_email = get_setting_from_arg_or_file(args, 'notify_recipient_email', 'notifications', 'recipient_email', None, None, settings_file_config)
    config.notify_recipient_email_error = get_setting_from_arg_or_file(args, 'notify_recipient_email_error', 'notifications', 'recipient_email_error', None, None, settings_file_config)
    config.notify_recipient_email_summary = get_setting_from_arg_or_file(args, 'notify_recipient_email_summary', 'notifications', 'recipient_email_summary', None, None, settings_file_config)
    config.notify_recipient_email_hazard = get_setting_from_arg_or_file(args, 'notify_recipient_email_hazard', 'notifications', 'recipient_email_hazard', None, None, settings_file_config)
    config.notify_sender_email = get_setting_from_arg_or_file(args, 'notify_sender_email', 'notifications', 'sender_email', None, None, settings_file_config)
    config.notify_smtp_server = get_setting_from_arg_or_file(args, 'notify_smtp_server', 'notifications', 'smtp_server', None, None, settings_file_config)
    config.notify_smtp_port = get_setting_from_arg_or_file(args, 'notify_smtp_port', 'notifications', 'smtp_port', None, int, settings_file_config)
    
    config.notify_username = get_setting_from_arg_or_file(args, 'notify_username', 'notifications', 'username', None, None, settings_file_config)
    config.notify_password = get_setting_from_arg_or_file(args, 'notify_password', 'notifications', 'password', None, None, settings_file_config)
    config.notify_use_tls = get_setting_from_arg_or_file(args, 'notify_use_tls', 'notifications', 'use_tls', True, bool, settings_file_config)
    
    # Parse ledger settings
    config.ledger_path = get_setting_from_arg_or_file(args, 'ledger_path', 'paths', 'ledger_path', None, None, settings_file_config)
    
    # Parse scanning settings
    config.defender_handles_suspect_files = get_setting_from_arg_or_file(args, 'defender_handles_suspect_files', 'scanning', 'defender_handles_suspect_files', True, bool, settings_file_config)
    
    # Return both the config object and the ConfigParser to avoid reopening the file
    return config, settings_file_config
