from shuttle import (
    setup_logging,
    get_file_hash,
    compare_file_hashes,
    remove_file_with_logging,
    test_write_access,
    verify_file_integrity,
    copy_temp_then_rename,
    normalize_path,
    remove_empty_directories,
    remove_directory,
    remove_directory_contents,
    is_file_open,
    is_file_stable
)

import os
import shutil
import hashlib
import argparse
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import configparser  # Added import for configparser
import gnupg
import types

from dataclasses import dataclass
from typing import Optional


process_modes= types.SimpleNamespace()

process_modes.PASSIVE = 0
process_modes.ACTIVE = 1

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
    process_mode: int
    lock_file: str
    defender_handles_suspect_files: bool

class ShuttleBase:

    @staticmethod
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
        parser.add_argument('-ProcessMode', 
                          choices=['active', 'passive'],
                          default='active',
                          help='Processing mode (active or passive)')
        parser.add_argument('-DefenderHandlesSuspectFiles', 
                           action='store_true',
                           default=True,
                           help='Let Microsoft Defender handle suspect files (default: True)')
        
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

        # Map the log level string to a logging level
        numeric_level = getattr(logging, log_level_str, None)

        if not isinstance(numeric_level, int):
            print(f"Invalid log level: {log_level_str}")
            sys.exit(1)

        lock_file = get_setting(args.LockFile, 'paths', 'destination_path', fallback='/tmp/shuttle.lock')
        log_path = get_setting(args.LogPath, 'paths', 'log_path')
        log_level_str = get_setting(args.LogLevel, 'logging', 'log_level', 'INFO').upper()

        hazard_archive_path = get_setting(args.HazardArchivePath, 'paths', 'hazard_archive_path')
        hazard_encryption_key_file_path = args.HazardEncryptionKeyPath or settings_file_config.get('paths', 'hazard_encryption_key_path', fallback=None)

        delete_source_files = args.DeleteSourceFilesAfterCopying or settings_file_config.getboolean('settings', 'delete_source_files_after_copying', fallback=False)

        max_scan_threads = args.MaxScanThreads or settings_file_config.getint('settings', 'max_scan_threads', fallback=2)

        # Convert process mode string to int
        process_mode = process_modes.PASSIVE if args.ProcessMode == 'passive' else process_modes.ACTIVE

        # Get defender handling setting
        defender_handles_suspect = args.DefenderHandlesSuspectFiles or settings_file_config.getboolean(
            'settings', 
            'defender_handles_suspect_files', 
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
            process_mode=process_mode,
            lock_file=lock_file,
            defender_handles_suspect=defender_handles_suspect
        )

        return settings_file_config

    def __init__(self, config: ShuttleConfig):
        self.config = config
        self.logger = None
        
     
    def initialize(self):
        """Common initialization code"""
        # Lock file handling
        if os.path.exists(self.config.lock_file):
            print(f"Another instance is running. Lock file {self.config.lock_file} exists.")
            sys.exit(1)
            
        with open(self.config.lock_file, 'w') as lock_file:
            lock_file.write(str(os.getpid()))
            
        # Load config, set up logging, etc.
        # ... (move common initialization code here)

        # Create log file name with timestamp and unique ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = os.getpid()  # Using process ID as unique identifier
        log_filename = f"shuttle_{timestamp}_{unique_id}.log"

        # Construct full log path if log directory is specified
        log_file = None

        if self.config.log_path:
            os.makedirs(self.config.log_path, exist_ok=True)
            log_file = os.path.join(self.config.log_path, log_filename)

        # Set up logging with the configured log level
        self.logger = setup_logging(log_file=log_file, log_level=self.config.log_level)

        self.logger.info(f"Starting Shuttle Linux file transfer and scanning process (PID: {unique_id})")


        # Check for required external commands
        import shutil

        required_commands = ['lsof', 'mdatp', 'gpg']
        missing_commands = []

        for cmd in required_commands:
            if shutil.which(cmd) is None:
                missing_commands.append(cmd)

        if missing_commands:
            for cmd in missing_commands:
                self.logger.error(f"Required command '{cmd}' not found. Please ensure it is installed and accessible in your PATH.")
            sys.exit(1)

        # Get encryption key file path
        if self.config.hazard_archive_path:
            
            if not self.config.hazard_encryption_key_file_path:
                self.logger.error("Hazard archive path specified but no encryption key file provided")
                sys.exit(1)
            if not os.path.isfile(self.config.hazard_encryption_key_file_path):
                self.logger.error(f"Encryption key file not found: {self.config.hazard_encryption_key_file_path}")
                sys.exit(1)

        else:
            self.config.hazard_encryption_key_file_path = None

        # Retrieve other settings

        # Validate required paths
        if not (self.config.source_path and self.config.destination_path and self.config.quarantine_path):
            self.logger.error("SourcePath, DestinationPath, and QuarantinePath must all be provided either as parameters or in the settings file.")
            sys.exit(1)

        self.logger.info(f"SourcePath: {self.config.source_path}")
        self.logger.info(f"DestinationPath: {self.config.destination_path}")
        self.logger.info(f"QuarantinePath: {self.config.quarantine_path}")

    

    def cleanup(self):
        """Common cleanup code"""
        if os.path.exists(self.args.lock_file):
            os.remove(self.args.lock_file)
            
    def main(self):
        """Template method pattern"""
        try:
            config = self.initialize()
            self.process_files(config)   # This will be implemented by subclasses
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        finally:
            self.cleanup()
