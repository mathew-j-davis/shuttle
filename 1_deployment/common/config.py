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
    
    # Throttle settings
    throttle: bool = False
    throttle_free_space: int = 10000  # Minimum MB of free space required
    
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
    
    # Add throttle arguments
    parser.add_argument('-Throttle',
                      help='Enable throttling of file processing',
                      type=bool,
                      default=None)
    parser.add_argument('-ThrottleFreeSpace',
                      help='Minimum free space (in MB) required on destination drive',
                      type=int,
                      default=None)
    
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
    
    # Helper function to get settings with priority: CLI args > settings file > default
    def get_setting(arg_value, section, option, default=None):
        if arg_value is not None:
            return arg_value
        elif settings_file_config.has_section(section) and settings_file_config.has_option(section, option):
            return settings_file_config.get(section, option)
        else:
            return default
    
    # Parse logging settings
    if args:
        log_path = args.LogPath if hasattr(args, 'LogPath') else None
        log_level_str = args.LogLevel if hasattr(args, 'LogLevel') else None
    else:
        log_path = None
        log_level_str = None
    
    config.log_path = get_setting(log_path, 'logging', 'log_path')
    
    log_level_str = get_setting(log_level_str, 'logging', 'log_level', 'INFO').upper()
    config.log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Parse throttle settings
    if args:
        throttle = args.Throttle if hasattr(args, 'Throttle') else None
        throttle_free_space = args.ThrottleFreeSpace if hasattr(args, 'ThrottleFreeSpace') else None
    else:
        throttle = None
        throttle_free_space = None
    
    config.throttle = get_setting(throttle, 'settings', 'throttle', False)
    if isinstance(config.throttle, str):
        config.throttle = config.throttle.lower() in ('true', 'yes', '1')
    
    config.throttle_free_space = get_setting(throttle_free_space, 'settings', 'throttle_free_space', 10000)
    if isinstance(config.throttle_free_space, str):
        config.throttle_free_space = int(config.throttle_free_space)
    
    # Parse notification settings
    if args:
        notify = args.Notify if hasattr(args, 'Notify') else None
        notify_summary = args.NotifySummary if hasattr(args, 'NotifySummary') else None
        notify_recipient_email = args.NotifyRecipientEmail if hasattr(args, 'NotifyRecipientEmail') else None
        notify_sender_email = args.NotifySenderEmail if hasattr(args, 'NotifySenderEmail') else None
        notify_smtp_server = args.NotifySmtpServer if hasattr(args, 'NotifySmtpServer') else None
        notify_smtp_port = args.NotifySmtpPort if hasattr(args, 'NotifySmtpPort') else None
        notify_username = args.NotifyUsername if hasattr(args, 'NotifyUsername') else None
        notify_password = args.NotifyPassword if hasattr(args, 'NotifyPassword') else None
        notify_use_tls = args.NotifyUseTLS if hasattr(args, 'NotifyUseTLS') else None
    else:
        notify = notify_summary = notify_recipient_email = notify_sender_email = None
        notify_smtp_server = notify_smtp_port = notify_username = notify_password = notify_use_tls = None
    
    config.notify = get_setting(notify, 'notifications', 'notify', False)
    if isinstance(config.notify, str):
        config.notify = config.notify.lower() in ('true', 'yes', '1')
    
    config.notify_summary = get_setting(notify_summary, 'notifications', 'notify_summary', False)
    if isinstance(config.notify_summary, str):
        config.notify_summary = config.notify_summary.lower() in ('true', 'yes', '1')
    
    config.notify_recipient_email = get_setting(notify_recipient_email, 'notifications', 'recipient_email')
    config.notify_sender_email = get_setting(notify_sender_email, 'notifications', 'sender_email')
    config.notify_smtp_server = get_setting(notify_smtp_server, 'notifications', 'smtp_server')
    
    smtp_port = get_setting(notify_smtp_port, 'notifications', 'smtp_port')
    if smtp_port:
        config.notify_smtp_port = int(smtp_port)
    
    config.notify_username = get_setting(notify_username, 'notifications', 'username')
    config.notify_password = get_setting(notify_password, 'notifications', 'password')
    
    use_tls = get_setting(notify_use_tls, 'notifications', 'use_tls', True)
    if isinstance(use_tls, str):
        config.notify_use_tls = use_tls.lower() in ('true', 'yes', '1')
    else:
        config.notify_use_tls = bool(use_tls)
    
    # Parse ledger settings
    if args:
        ledger_path = args.LedgerPath if hasattr(args, 'LedgerPath') else None
    else:
        ledger_path = None
    
    config.ledger_path = get_setting(ledger_path, 'defender', 'ledger_path')
    
    return config
