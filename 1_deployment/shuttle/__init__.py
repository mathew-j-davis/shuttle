# Import all configuration types and functions
from .config import (
    ShuttleConfig, 
    parse_config
)

# Import all scanning related functions
from .scanning import (
    process_files,
    scan_and_process_directory,
    scan_and_process_file,
)

# Import all post scan processing related functions
from .post_scan_processing import (
    handle_clean_file,
    handle_suspect_file,
    handle_suspect_scan_result,
    handle_suspect_quarantine_file_and_delete_source,
    handle_suspect_source_file
)
# Import file handling functions from common module
from ..common.files import (
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

# Import throttler for disk space management
from .throttler import Throttler

# Import main Shuttle application
from .shuttle import main as shuttle_main

# Define what gets imported with "from shuttle import *"
__all__ = [
    # Config
    'ShuttleConfig',
    'parse_config',
    
    # Main scanning functions
    'process_files',
    'scan_and_process_directory',
    'scan_and_process_file',
    
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
    'encrypt_file',
    'remove_file_with_logging',
    
    # Throttling functionality
    'Throttler',
    
    # Main application
    'shuttle_main'
]