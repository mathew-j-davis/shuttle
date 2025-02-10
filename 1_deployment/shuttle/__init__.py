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

    handle_suspect_scan_result,

    handle_suspect_quarantine_file_and_delete_source,
    handle_suspect_source_file
)

# Import defender specific functions
from .scanning_defender import (
    scan_for_malware_using_defender,
    handle_defender_scan_result,
    parse_defender_scan_result
)

# Import ClamAV specific functions
from .scanning_clamav import (
    scan_for_malware_using_clam_av,
    handle_clamav_scan_result,
    parse_clamav_scan_result
)

# Import file handling functions
from .files import (
    is_filename_safe,
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
    handle_suspect_file,
    encrypt_file,
    remove_file_with_logging
)

# Import logging setup
from .logging_setup import setup_logging

# Define what gets imported with "from shuttle import *"
__all__ = [
    # Config
    'ShuttleConfig',
    'parse_config',

    'defender_scan_patterns',
    'clamav_parse_response_patterns',
    
    # Main scanning functions
    'scan_result_types',
    'process_files',
    'scan_and_process_directory',
    'scan_and_process_file',
    'handle_suspect_scan_result',
    'run_malware_scan',
    'handle_suspect_quarantine_file_and_delete_source',
    'handle_suspect_source_file',
    
    # Defender specific
    'scan_for_malware_using_defender',
    'handle_defender_scan_result',
    'parse_defender_scan_result',
    
    # ClamAV specific
    'scan_for_malware_using_clam_av',
    'handle_clamav_scan_result',
    'parse_clamav_scan_result',
    
    # File operations
    'is_filename_safe',
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