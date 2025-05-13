"""
Shuttle Configuration Module

This module provides configuration classes and parsing functions
for Shuttle-specific settings, extending the common configuration.
"""

import os
import sys
import logging
import argparse
import configparser
from dataclasses import dataclass
from typing import Optional

# Import common configuration using relative imports
from ..common.config import CommonConfig, add_common_arguments, parse_common_config


@dataclass
class ShuttleConfig(CommonConfig):
    """
    Configuration settings specific to the Shuttle application.
    Extends CommonConfig with Shuttle-specific settings.
    """
    # Path settings
    source_path: Optional[str] = None
    destination_path: Optional[str] = None
    quarantine_path: Optional[str] = None
    hazard_archive_path: Optional[str] = None
    hazard_encryption_key_file_path: Optional[str] = None
    lock_file: str = '/tmp/shuttle.lock'
    
    # Processing settings
    delete_source_files: bool = False
    max_scan_threads: int = 1
    
    # Scanning settings
    defender_handles_suspect_files: bool = True
    on_demand_defender: bool = False
    on_demand_clam_av: bool = True
    
    # Shuttle-specific throttle settings
    throttle_max_file_volume_per_day: int = 1000000
    throttle_max_file_count_per_day: int = 1000


def parse_config() -> ShuttleConfig:
    """
    Parse Shuttle configuration from command line arguments and settings file.
    
    Returns:
        ShuttleConfig object with all parsed settings
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Shuttle File Transfer Script')
    
    # Add common arguments
    add_common_arguments(parser)
    
    # Add Shuttle-specific arguments
    parser.add_argument('-SourcePath', help='Path to the source directory')
    parser.add_argument('-DestinationPath', help='Path to the destination directory')
    parser.add_argument('-QuarantinePath', help='Path to the quarantine directory')
    parser.add_argument('-SettingsPath', default=os.path.join(os.getenv('HOME') or os.path.expanduser('~'), '.shuttle', 'settings.ini'),
                        help='Path to the settings file')
    parser.add_argument('-TestSourceWriteAccess', action='store_true', help='Test write access to the source directory')
    parser.add_argument('-DeleteSourceFilesAfterCopying', action='store_true',
                        help='Delete the source files after copying them to the destination')
    parser.add_argument('-MaxScanThreads', type=int, help='Maximum number of parallel scans')
    parser.add_argument('-LockFile', help='Optional: Path to lock file to prevent multiple instances')
    parser.add_argument('-HazardArchivePath', help='Path to the hazard archive directory')
    parser.add_argument('-HazardEncryptionKeyPath', help='Path to the GPG public key file for encrypting hazard files')

    parser.add_argument('-DefenderHandlesSuspectFiles', 
                        action='store_true',
                        default=None,
                        help='Let Microsoft Defender handle suspect files (default: True)')
    parser.add_argument('-OnDemandDefender',
                       help='Use on-demand scanning for Microsoft Defender',
                       type=bool,
                       default=None)
    parser.add_argument('-OnDemandClamAV',
                       help='Use on-demand scanning for ClamAV',
                       type=bool,
                       default=None)
    
    # Shuttle-specific throttle arguments
    parser.add_argument('-ThrottleMaxFileVolumePerDay',
                       help='Maximum volume of files (in bytes) to process per day',
                       type=int,
                       default=None)
    parser.add_argument('-ThrottleMaxFileCountPerDay',
                       help='Maximum number of files to process per day',
                       type=int,
                       default=None)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Parse common configuration
    common_config = parse_common_config(args, args.SettingsPath)
    
    # Create ShuttleConfig from common configuration
    config = ShuttleConfig(
        # Copy common configuration
        log_path=common_config.log_path,
        log_level=common_config.log_level,
        throttle=common_config.throttle,
        throttle_free_space=common_config.throttle_free_space,
        notify=common_config.notify,
        notify_summary=common_config.notify_summary,
        notify_recipient_email=common_config.notify_recipient_email,
        notify_sender_email=common_config.notify_sender_email,
        notify_smtp_server=common_config.notify_smtp_server,
        notify_smtp_port=common_config.notify_smtp_port,
        notify_username=common_config.notify_username,
        notify_password=common_config.notify_password,
        notify_use_tls=common_config.notify_use_tls,
        ledger_file=common_config.ledger_file
    )
    
    # Load settings from the settings file using configparser
    settings_file_config = configparser.ConfigParser()
    settings_file_config.read(args.SettingsPath)

    # Helper function to get settings with priority: CLI args > settings file > default
    def get_setting(arg_value, section, option, default=None):
        if arg_value is not None:
            return arg_value
        elif settings_file_config.has_section(section) and settings_file_config.has_option(section, option):
            return settings_file_config.get(section, option)
        else:
            return default

    # Get path settings
    config.source_path = get_setting(args.SourcePath, 'paths', 'source_path')
    config.destination_path = get_setting(args.DestinationPath, 'paths', 'destination_path')
    config.quarantine_path = get_setting(args.QuarantinePath, 'paths', 'quarantine_path')
    config.lock_file = get_setting(args.LockFile, 'paths', 'lock_path', '/tmp/shuttle.lock')
    config.hazard_archive_path = get_setting(args.HazardArchivePath, 'paths', 'hazard_archive_path')
    config.hazard_encryption_key_file_path = get_setting(args.HazardEncryptionKeyPath, 'paths', 'hazard_encryption_key_path')

    # Get processing settings
    delete_source_files = get_setting(args.DeleteSourceFilesAfterCopying, 'settings', 'delete_source_files_after_copying', False)
    if isinstance(delete_source_files, str):
        config.delete_source_files = delete_source_files.lower() in ('true', 'yes', '1')
    else:
        config.delete_source_files = bool(delete_source_files)
    
    max_scan_threads = get_setting(args.MaxScanThreads, 'settings', 'max_scan_threads', 1)
    if isinstance(max_scan_threads, str):
        config.max_scan_threads = int(max_scan_threads)
    else:
        config.max_scan_threads = max_scan_threads

    # Get scanning settings
    defender_handles_suspect_files = get_setting(args.DefenderHandlesSuspectFiles, 'settings', 'defender_handles_suspect_files', True)
    if isinstance(defender_handles_suspect_files, str):
        config.defender_handles_suspect_files = defender_handles_suspect_files.lower() in ('true', 'yes', '1')
    else:
        config.defender_handles_suspect_files = bool(defender_handles_suspect_files)
    
    on_demand_defender = get_setting(args.OnDemandDefender, 'settings', 'on_demand_defender', False)
    if isinstance(on_demand_defender, str):
        config.on_demand_defender = on_demand_defender.lower() in ('true', 'yes', '1')
    else:
        config.on_demand_defender = bool(on_demand_defender)
    
    on_demand_clam_av = get_setting(args.OnDemandClamAV, 'settings', 'on_demand_clam_av', True)
    if isinstance(on_demand_clam_av, str):
        config.on_demand_clam_av = on_demand_clam_av.lower() in ('true', 'yes', '1')
    else:
        config.on_demand_clam_av = bool(on_demand_clam_av)
    
    # Throttle settings specific to Shuttle
    throttle_max_file_volume_per_day = get_setting(args.ThrottleMaxFileVolumePerDay, 'settings', 'throttle_max_file_volume_per_day', 1000000)
    if isinstance(throttle_max_file_volume_per_day, str):
        config.throttle_max_file_volume_per_day = int(throttle_max_file_volume_per_day)
    else:
        config.throttle_max_file_volume_per_day = throttle_max_file_volume_per_day
    
    throttle_max_file_count_per_day = get_setting(args.ThrottleMaxFileCountPerDay, 'settings', 'throttle_max_file_count_per_day', 1000)
    if isinstance(throttle_max_file_count_per_day, str):
        config.throttle_max_file_count_per_day = int(throttle_max_file_count_per_day)
    else:
        config.throttle_max_file_count_per_day = throttle_max_file_count_per_day
    
    # Validate required settings
    if not config.source_path:
        raise ValueError("Source path is required")
    if not config.destination_path:
        raise ValueError("Destination path is required")
    if not config.quarantine_path:
        raise ValueError("Quarantine path is required")
    
    return config
