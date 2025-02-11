import os
import sys
import logging
import argparse
import configparser
from dataclasses import dataclass
from typing import Optional
import types



@dataclass
class ShuttleConfig:
    source_path: str
    destination_path: str
    quarantine_path: str
    log_path: Optional[str]
    hazard_archive_path: Optional[str]
    hazard_encryption_key_file_path: Optional[str]
    delete_source_files: bool
    max_scan_threads: int
    log_level: int
    lock_file: str
    defender_handles_suspect_files: bool
    on_demand_defender: bool
    on_demand_clam_av: bool


def parse_config() -> ShuttleConfig:

    # Set up argument parser
    parser = argparse.ArgumentParser(description='File Transfer Script')
    parser.add_argument('-SourcePath', help='Path to the source directory')
    parser.add_argument('-DestinationPath', help='Path to the destination directory')
    parser.add_argument('-QuarantinePath', help='Path to the quarantine directory')
    parser.add_argument('-LogPath', help='Path to the log directory')
    parser.add_argument('-SettingsPath', default=os.path.join(os.getenv('HOME'), '.shuttle', 'settings.ini'),
                        help='Path to the settings file')
    parser.add_argument('-TestSourceWriteAccess', action='store_true', help='Test write access to the source directory')
    parser.add_argument('-DeleteSourceFilesAfterCopying', action='store_true',
                        help='Delete the source files after copying them to the destination')
    parser.add_argument('-MaxScanThreads', type=int, help='Maximum number of parallel scans')
    parser.add_argument('-LockFile', help='Optional : Path to lock file to prevent multiple instances')
    parser.add_argument('-HazardArchivePath', help='Path to the hazard archive directory')
    parser.add_argument('-HazardEncryptionKeyPath', help='Path to the GPG public key file for encrypting hazard files')
    parser.add_argument('-LogLevel', default=None, help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')

    parser.add_argument('-DefenderHandlesSuspectFiles', 
                        action='store_true',
                        default=True,
                        help='Let Microsoft Defender handle suspect files (default: True)')
    parser.add_argument('-OnDemandDefender',
                       help='Use on-demand scanning for Microsoft Defender',
                       type=bool,
                       default=None)
    parser.add_argument('-OnDemandClamAV',
                       help='Use on-demand scanning for ClamAV',
                       type=bool,
                       default=None)
    
    args = parser.parse_args()

    # Load settings from the settings file using configparser
    settings_file_config = configparser.ConfigParser()
    settings_file_config.read(args.SettingsPath)

    # Helper function to get settings with priority: CLI args > settings file > default
    def get_setting(arg_value, section, option, default=None):
        if arg_value is not None:
            return arg_value
        elif settings_file_config.has_option(section, option):
            return settings_file_config.get(section, option)
        else:
            return default

    # Get paths and parameters from arguments or settings file
    source_path = get_setting(args.SourcePath, 'paths', 'source_path')
    destination_path = get_setting(args.DestinationPath, 'paths', 'destination_path')
    quarantine_path = get_setting(args.QuarantinePath, 'paths', 'quarantine_path')


    lock_file = get_setting(args.LockFile, 'paths', 'lock_path', '/tmp/shuttle.lock')
    log_path = get_setting(args.LogPath, 'paths', 'log_path')
    log_level_str = get_setting(args.LogLevel, 'logging', 'log_level', 'INFO').upper()

    # Map the log level string to a logging level
    numeric_level = getattr(logging, log_level_str, None)

    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level_str}")
        sys.exit(1)

    hazard_archive_path = get_setting(args.HazardArchivePath, 'paths', 'hazard_archive_path')
    hazard_encryption_key_file_path = args.HazardEncryptionKeyPath or settings_file_config.get('paths', 'hazard_encryption_key_path', fallback=None)

    delete_source_files = args.DeleteSourceFilesAfterCopying or settings_file_config.getboolean('settings', 'delete_source_files_after_copying', fallback=False)

    max_scan_threads = args.MaxScanThreads or settings_file_config.getint('settings', 'max_scan_threads', fallback=1)

    # Get defender handling setting
    defender_handles_suspect_files = args.DefenderHandlesSuspectFiles or settings_file_config.getboolean(
        'settings', 
        'defender_handles_suspect_files', 
        fallback=True
    )

    # Get on-demand scanning settings
    on_demand_defender = args.OnDemandDefender or settings_file_config.getboolean(
        'settings', 
        'on_demand_defender', 
        fallback=False
    )
    
    on_demand_clam_av = args.OnDemandClamAV or settings_file_config.getboolean(
        'settings', 
        'on_demand_clam_av', 
        fallback=True
    )

    # Create config object with all settings
    settings_file_config = ShuttleConfig(
        source_path=source_path,
        destination_path=destination_path,
        quarantine_path=quarantine_path,
        log_path=log_path,
        hazard_archive_path=hazard_archive_path,
        hazard_encryption_key_file_path=hazard_encryption_key_file_path,
        delete_source_files=delete_source_files,
        max_scan_threads=max_scan_threads,
        log_level=numeric_level,
        lock_file=lock_file,
        defender_handles_suspect_files= defender_handles_suspect_files,
        on_demand_defender=on_demand_defender,
        on_demand_clam_av=on_demand_clam_av
    )

    return settings_file_config
