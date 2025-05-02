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
    # Throttle settings
    throttle: bool = False
    throttle_max_file_volume_per_day: int = 1000000
    throttle_max_file_count_per_day: int = 1000
    throttle_free_space: int = 10000
    # Notification settings
    notify: bool = False
    notify_recipient_email: Optional[str] = None
    notify_sender_email: Optional[str] = None
    notify_smtp_server: Optional[str] = None
    notify_smtp_port: Optional[int] = None
    notify_username: Optional[str] = None
    notify_password: Optional[str] = None
    notify_use_tls: bool = True


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
    
    # Add throttle arguments
    parser.add_argument('-Throttle',
                       help='Enable throttling of file processing',
                       type=bool,
                       default=None)
    parser.add_argument('-ThrottleMaxFileVolumePerDay',
                       help='Maximum volume of files (in bytes) to process per day',
                       type=int,
                       default=None)
    parser.add_argument('-ThrottleMaxFileCountPerDay',
                       help='Maximum number of files to process per day',
                       type=int,
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

    # Get throttle settings
    throttle = args.Throttle
    if throttle is None and settings_file_config.has_option('settings', 'throttle'):
        throttle = settings_file_config.getboolean('settings', 'throttle')
    else:
        throttle = False
    
    throttle_max_file_volume_per_day = args.ThrottleMaxFileVolumePerDay
    if throttle_max_file_volume_per_day is None and settings_file_config.has_option('settings', 'throttle_max_file_volume_per_day'):
        throttle_max_file_volume_per_day = settings_file_config.getint('settings', 'throttle_max_file_volume_per_day')
    else:
        throttle_max_file_volume_per_day = 1000000
    
    throttle_max_file_count_per_day = args.ThrottleMaxFileCountPerDay
    if throttle_max_file_count_per_day is None and settings_file_config.has_option('settings', 'throttle_max_file_count_per_day'):
        throttle_max_file_count_per_day = settings_file_config.getint('settings', 'throttle_max_file_count_per_day')
    else:
        throttle_max_file_count_per_day = 1000
    
    throttle_free_space = args.ThrottleFreeSpace
    if throttle_free_space is None and settings_file_config.has_option('settings', 'throttle_free_space'):
        throttle_free_space = settings_file_config.getint('settings', 'throttle_free_space')
    else:
        throttle_free_space = 10000

    # Get notification settings
    notify = args.Notify
    if notify is None and settings_file_config.has_option('notification', 'notify'):
        notify = settings_file_config.getboolean('notification', 'notify')
    else:
        notify = False
    
    notify_recipient_email = get_setting(args.NotifyRecipientEmail, 'notification', 'recipient_email')
    notify_sender_email = get_setting(args.NotifySenderEmail, 'notification', 'sender_email')
    notify_smtp_server = get_setting(args.NotifySmtpServer, 'notification', 'smtp_server')
    
    # Get SMTP port with conversion to int
    notify_smtp_port = None
    if args.NotifySmtpPort is not None:
        notify_smtp_port = args.NotifySmtpPort
    elif settings_file_config.has_option('notification', 'smtp_port'):
        notify_smtp_port = settings_file_config.getint('notification', 'smtp_port')
    
    notify_username = get_setting(args.NotifyUsername, 'notification', 'username')
    notify_password = get_setting(args.NotifyPassword, 'notification', 'password')
    
    notify_use_tls = args.NotifyUseTLS
    if notify_use_tls is None and settings_file_config.has_option('notification', 'use_tls'):
        notify_use_tls = settings_file_config.getboolean('notification', 'use_tls')
    else:
        notify_use_tls = True  # Default to True

    # Create config object with all settings
    config_obj = ShuttleConfig(
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
        defender_handles_suspect_files=defender_handles_suspect_files,
        on_demand_defender=on_demand_defender,
        on_demand_clam_av=on_demand_clam_av,
        throttle=throttle,
        throttle_max_file_volume_per_day=throttle_max_file_volume_per_day,
        throttle_max_file_count_per_day=throttle_max_file_count_per_day,
        throttle_free_space=throttle_free_space,
        notify=notify,
        notify_recipient_email=notify_recipient_email,
        notify_sender_email=notify_sender_email,
        notify_smtp_server=notify_smtp_server,
        notify_smtp_port=notify_smtp_port,
        notify_username=notify_username,
        notify_password=notify_password,
        notify_use_tls=notify_use_tls
    )

    return config_obj
