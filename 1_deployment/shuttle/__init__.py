# Import all configuration types and functions
from .config import (
    ShuttleConfig, 
    parse_config
)

# Import all scanning related functions
from .scanning import (
    scan_result_types,
    process_files,
    scan_and_process_directory,
    scan_and_process_file,
    run_malware_scan,
)

# Import all post scan processing  related functions

from .post_scan_processing import (
    handle_clean_file,
    handle_suspect_file,
    handle_suspect_scan_result,
    handle_suspect_quarantine_file_and_delete_source,
    handle_suspect_source_file
)

# Import file handling functions
from .files import (
    is_filename_safe,
    is_pathname_safe,
    get_file_hash,
    compare_file_hashes,
    copy_temp_then_rename,
    normalize_path,
    is_file_open,
    is_file_stable,
    remove_directory_contents,
    remove_directory,
    remove_empty_directories,
    verify_file_integrity,
    encrypt_file,
    remove_file_with_logging
)

# Import logging setup
from .logging_setup import setup_logging

# Import notification system
from .notifier import Notifier

# Define what gets imported with "from shuttle import *"
__all__ = [
    # Config
    'ShuttleConfig',
    'parse_config'

    # Notification
    'Notifier',
    
    # Main scanning functions
    'scan_result_types',
    'process_files',
    'scan_and_process_directory',
    'scan_and_process_file',
    'handle_suspect_scan_result',
    'run_malware_scan',
    'handle_suspect_quarantine_file_and_delete_source',
    'handle_suspect_source_file',
    
    # post_scan_processing
    'handle_clean_file',
    'handle_suspect_file',
    'handle_suspect_scan_result',
    'handle_suspect_quarantine_file_and_delete_source',
    'handle_suspect_source_file',
    
    # File operations
    'is_filename_safe',
    'is_pathname_safe',
    'get_file_hash',
    'compare_file_hashes',
    'copy_temp_then_rename',
    'normalize_path',
    'is_file_open',
    'is_file_stable',
    'remove_directory_contents',
    'remove_directory',
    'remove_empty_directories',
    'verify_file_integrity',
    'handle_suspect_file',
    'encrypt_file',
    'remove_file_with_logging',
    
    # Logging
    'setup_logging'
]