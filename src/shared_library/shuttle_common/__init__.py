"""
ShuttleCommonModule Package

This package contains shared code used by both the shuttle and defender_test modules.
By centralizing these shared components, we maintain consistency and reduce duplication.
"""

__version__ = '0.1.0'
__author__ = 'Mat Davis'

# Import all shared components to make them easily accessible
from .scan_utils import run_malware_scan, scan_result_types, get_mdatp_version, DefenderScanResult, process_defender_result, is_using_simulator
from .ledger import Ledger
from .notifier import Notifier
from .logging_setup import setup_logging
from .config import CommonConfig, add_common_arguments, parse_common_config, get_setting_from_arg_or_file
from .files import is_file_safe_for_processing, are_file_and_path_names_safe, is_file_ready
from .logger_injection import (configure_logging, get_logger)

# Define what's publicly available when using "from shuttle_common import *"
__all__ = [

    # Scan utilities
    'get_mdatp_version',
    'run_malware_scan',
    'scan_result_types',
    'DefenderScanResult',
    'process_defender_result',
    'is_using_simulator',
    'parse_defender_scan_result',
    'handle_clamav_scan_result',
    
    # Ledger system
    'Ledger',
    
    # Notification system
    'Notifier',
    
    # Logging
    'LoggingOptions',
    'setup_logging',
    
    # Configuration
    'CommonConfig',
    'add_common_arguments',
    'parse_common_config',
    'get_setting_from_arg_or_file',
    
    # File safety
    'is_file_safe_for_processing',
    'are_file_and_path_names_safe',
    'is_file_ready',
    
    # Hierarchy logging
    'configure_logging',
    'with_logger',
    'get_logger'
]
