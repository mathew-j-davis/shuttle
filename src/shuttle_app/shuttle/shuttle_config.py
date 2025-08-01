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
from shuttle_common.config import CommonConfig, add_common_arguments, parse_common_config, get_setting_from_arg_or_file, find_config_file
from shuttle_common.logger_injection import get_logger


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
    delete_source_files: bool = None
    max_scan_threads: int = 1
    
    # Scanning settings
    on_demand_defender: bool = None
    on_demand_clam_av: bool = None
    
    # Throttle settings
    throttle: bool = None
    throttle_free_space_mb: int = None  # Minimum MB of free space required
    daily_processing_tracker_logs_path: Optional[str] = None  # Path to store throttle logs
    throttle_max_file_volume_per_day_mb: int = None  # Maximum MB to process per day
    throttle_max_file_count_per_day: int = None  # Maximum files to process per day
    
    # Per-run/Per-batch limits (applied per execution of shuttle)
    throttle_max_file_count_per_run: int = 1000  # Maximum files to process per run (default: 1000)
    throttle_max_file_volume_per_run_mb: int = 1024  # Maximum MB to process per run (default: 1GB)
    
    # Testing settings
    skip_stability_check: bool = False  # Skip file stability check (for testing)
    
    # Mock settings for testing
    mock_free_space_mb: Optional[int] = None  # Mock free space in MB for all directories
    mock_free_space_quarantine_mb: Optional[int] = None  # Mock free space for quarantine
    mock_free_space_destination_mb: Optional[int] = None  # Mock free space for destination
    mock_free_space_hazard_mb: Optional[int] = None  # Mock free space for hazard


def parse_shuttle_config() -> ShuttleConfig:
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
    parser.add_argument('--source-path', help='Path to the source directory')
    parser.add_argument('--destination-path', help='Path to the destination directory')
    parser.add_argument('--quarantine-path', help='Path to the quarantine directory')

    parser.add_argument('--test-source-write-access', action='store_true', help='Test write access to the source directory',default=None)
    
    # Mock space settings for testing
    parser.add_argument('--mock-free-space-mb', type=int, help='Mock free space in MB for all directories')
    parser.add_argument('--mock-free-space-quarantine-mb', type=int, help='Mock free space in MB for quarantine directory')
    parser.add_argument('--mock-free-space-destination-mb', type=int, help='Mock free space in MB for destination directory')
    parser.add_argument('--mock-free-space-hazard-mb', type=int, help='Mock free space in MB for hazard directory')
    parser.add_argument('--delete-source-files-after-copying', 
                        action='store_true',
                        help='Delete the source files after copying them to the destination',
                        default=None)
    parser.add_argument('--max-scan-threads', type=int, help='Maximum number of parallel scans')
    parser.add_argument('--lock-file', help='Optional: Path to lock file to prevent multiple instances')
    parser.add_argument('--hazard-archive-path', help='Path to the hazard archive directory')
    parser.add_argument('--hazard-encryption-key-path', help='Path to the GPG public key file for encrypting hazard files')
    parser.add_argument('--on-demand-defender',
                        action='store_true',
                        help='Use on-demand scanning for Microsoft Defender',
                        default=None)

    parser.add_argument('--on-demand-clam-av', 
                        action='store_true',
                        help='Use on-demand scanning for ClamAV',
                        default=None)
    
    # Shuttle-specific throttle arguments
    parser.add_argument('--throttle',
                        action='store_true',
                        help='Enable throttling of file processing',
                        default=None)
    parser.add_argument('--throttle-free-space-mb',
                        help='Minimum free space (in MB) required on destination drive',
                        type=int,
                        default=None)
    parser.add_argument('--daily-processing-tracker-logs-path',
                        help='Path to store daily processing tracker logs (defaults to log_path if not specified)',
                        default=None)
                        
    # Testing parameters
    parser.add_argument('--skip-stability-check',
                        action='store_true',
                        help='Skip file stability check (only for testing)',
                        default=False)
    
    # Commented out for now
    parser.add_argument('--throttle-max-file-volume-per-day-mb',
                       help='Maximum volume of files (in MB) to process per day',
                       type=int,
                       default=None)
    parser.add_argument('--throttle-max-file-count-per-day',
                       help='Maximum number of files to process per day',
                       type=int,
                       default=None)
    parser.add_argument('--throttle-max-file-count-per-run',
                       help='Maximum number of files to process per execution/run (default: 1000)',
                       type=int,
                       default=None)
    parser.add_argument('--throttle-max-file-volume-per-run-mb',
                       help='Maximum volume of files (in MB) to process per execution/run (default: 1024)',
                       type=int,
                       default=None)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Parse common configuration - this will find and read the config file
    # Now returns (config_obj, config_parser_obj)
    common_config, settings_file_config = parse_common_config(args)
    
    # Create ShuttleConfig by inheriting from the common configuration
    config = ShuttleConfig(**vars(common_config))
    
    # We now reuse the ConfigParser from common_config
    # No need to reopen the file
    
    # Get path settings
    config.source_path = get_setting_from_arg_or_file(args, 'source_path', 'paths', 'source_path', None, None, settings_file_config)
    config.destination_path = get_setting_from_arg_or_file(args, 'destination_path', 'paths', 'destination_path', None, None, settings_file_config)
    config.quarantine_path = get_setting_from_arg_or_file(args, 'quarantine_path', 'paths', 'quarantine_path', None, None, settings_file_config)
    config.lock_file = get_setting_from_arg_or_file(args, 'lock_file', 'paths', 'lock_path', '/tmp/shuttle.lock', None, settings_file_config)
    config.hazard_archive_path = get_setting_from_arg_or_file(args, 'hazard_archive_path', 'paths', 'hazard_archive_path', None, None, settings_file_config)
    config.hazard_encryption_key_file_path = get_setting_from_arg_or_file(args, 'hazard_encryption_key_path', 'paths', 'hazard_encryption_key_path', None, None, settings_file_config)

    # Get processing settings
    config.delete_source_files = get_setting_from_arg_or_file(args, 'delete_source_files_after_copying', 'settings', 'delete_source_files_after_copying', False, bool, settings_file_config)
    config.max_scan_threads = get_setting_from_arg_or_file(args, 'max_scan_threads', 'settings', 'max_scan_threads', 1, int, settings_file_config)
    
    # Get scanning settings
    config.on_demand_defender = get_setting_from_arg_or_file(args, 'on_demand_defender', 'settings', 'on_demand_defender', False, bool, settings_file_config)
    config.on_demand_clam_av = get_setting_from_arg_or_file(args, 'on_demand_clam_av', 'settings', 'on_demand_clam_av', False, bool, settings_file_config)
        
    # Parse throttle settings
    config.throttle = get_setting_from_arg_or_file(args, 'throttle', 'settings', 'throttle', False, bool, settings_file_config)
    config.throttle_free_space_mb = get_setting_from_arg_or_file(args, 'throttle_free_space_mb', 'settings', 'throttle_free_space_mb', 10000, int, settings_file_config)
    config.daily_processing_tracker_logs_path = get_setting_from_arg_or_file(args, 'daily_processing_tracker_logs_path', 'paths', 'daily_processing_tracker_logs_path', None, None, settings_file_config)
    
    # Throttle settings specific to Shuttle
    config.throttle_max_file_volume_per_day_mb = get_setting_from_arg_or_file(args, 'throttle_max_file_volume_per_day_mb', 'settings', 'throttle_max_file_volume_per_day_mb', 0, int, settings_file_config)
    config.throttle_max_file_count_per_day = get_setting_from_arg_or_file(args, 'throttle_max_file_count_per_day', 'settings', 'throttle_max_file_count_per_day', 0, int, settings_file_config)
    config.throttle_max_file_count_per_run = get_setting_from_arg_or_file(args, 'throttle_max_file_count_per_run', 'settings', 'throttle_max_file_count_per_run', 1000, int, settings_file_config)
    config.throttle_max_file_volume_per_run_mb = get_setting_from_arg_or_file(args, 'throttle_max_file_volume_per_run_mb', 'settings', 'throttle_max_file_volume_per_run_mb', 1024, int, settings_file_config)
    
    # Parse testing settings
    config.skip_stability_check = get_setting_from_arg_or_file(args, 'skip_stability_check', 'settings', 'skip_stability_check', False, bool, settings_file_config)
    
    # Parse mock space settings
    config.mock_free_space_mb = get_setting_from_arg_or_file(args, 'mock_free_space_mb', 'testing', 'mock_free_space_mb', None, int, settings_file_config)
    config.mock_free_space_quarantine_mb = get_setting_from_arg_or_file(args, 'mock_free_space_quarantine_mb', 'testing', 'mock_free_space_quarantine_mb', None, int, settings_file_config)
    config.mock_free_space_destination_mb = get_setting_from_arg_or_file(args, 'mock_free_space_destination_mb', 'testing', 'mock_free_space_destination_mb', None, int, settings_file_config)
    config.mock_free_space_hazard_mb = get_setting_from_arg_or_file(args, 'mock_free_space_hazard_mb', 'testing', 'mock_free_space_hazard_mb', None, int, settings_file_config)
    
    # Set the full daily_processing_tracker_logs_path with fallback logic
    # If daily_processing_tracker_logs_path is not explicitly set, use log_path from common config
    # or fall back to default
    if not config.daily_processing_tracker_logs_path:
        config.daily_processing_tracker_logs_path = config.log_path
    
    # Validate required settings
    if not config.source_path:
        raise ValueError("Source path is required")
    if not config.destination_path:
        raise ValueError("Destination path is required")
    if not config.quarantine_path:
        raise ValueError("Quarantine path is required")
    if not config.daily_processing_tracker_logs_path:
        raise ValueError("Output path for daily processing tracker is required")
    return config
