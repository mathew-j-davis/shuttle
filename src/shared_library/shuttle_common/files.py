import os
import shutil
import hashlib
import time
import subprocess
from pathlib import Path
import gnupg
from .logger_injection import get_logger

def is_filename_safe(filename):
    """
    Check if a filename contains potentially dangerous characters.
    Allows alphanumeric, spaces, and valid UTF-8 characters, but blocks
    control characters and specific dangerous symbols.
    
    Args:
        filename (str): Filename to check
        
    Returns:
        bool: True if filename is safe, False otherwise
    """
        
    return is_name_safe(filename)


def is_pathname_safe(pathname):
    """
    Check if a filename contains potentially dangerous characters.
    Allows alphanumeric, spaces, and valid UTF-8 characters, but blocks
    control characters and specific dangerous symbols.
    
    Args:
        filename (str): Filename to check
        
    Returns:
        bool: True if filename is safe, False otherwise
    """
        
    return is_name_safe(pathname, True)

def is_name_safe(name, is_path = False):
    """
    Check if a filename contains potentially dangerous characters.
    Allows alphanumeric, spaces, and valid UTF-8 characters, but blocks
    control characters and specific dangerous symbols.
    
    Args:
        name (str): Filename or path to check
        is_path (bool): Whether the name is a path (allows forward slashes)
        
    Returns:
        bool: True if filename is safe, False otherwise
    """
    # Block control characters (0x00-0x1F, 0x7F)
    if any(ord(char) < 32 or ord(char) == 0x7F for char in name):
        return False
        
    # Define dangerous characters based on whether this is a path or filename
    dangerous_chars = ['\\', '..', '>', '<', '|', '*', '$', '&', ';', '`']
    
    # For filenames (not paths), also block forward slashes
    if not is_path:
        dangerous_chars.append('/')
    
    # Check for dangerous character sequences
    for char in dangerous_chars:
        if char in name:
            return False
        
    # For paths, only check the filename part for starting with dash or period
    check_name = name
    if is_path and '/' in name:
        check_name = name.rstrip('/').split('/')[-1]  # Get the last component
    
    # Block filenames starting with dash or period (unless it's . or ..)
    if check_name not in ['.', '..'] and (check_name.startswith('-') or check_name.startswith('.')):
        return False
        
    # Ensure filename is valid UTF-8
    try:
        name.encode('utf-8').decode('utf-8')
    except UnicodeError:
        return False
        
    return True

def get_file_hash(file_path):
    """
    Compute the SHA-256 hash of a file.

    Args:
        file_path (str): Path to the file.


    Returns:
        str: The computed hash or None if an error occurred.
    """
    hash_sha256 = hashlib.sha256()
        
    try:
        with open(file_path, 'rb') as f:
            # Read the file in chunks to avoid memory issues with large files
            for chunk in iter(lambda: f.read(4096), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except FileNotFoundError:
        logger = get_logger()
        logger.error(f"File not found: {file_path}")
        return None
    except PermissionError:
        logger = get_logger()
        logger.error(f"Permission denied when accessing file: {file_path}")
        return None
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error computing hash for {file_path}: {e}")
        return None

def compare_file_hashes(hash1, hash2):
    """
    Compare two hash strings.
    
    Args:
        hash1 (str): First hash string.
        hash2 (str): Second hash string.
    
    Returns:
        bool: True if hashes match, False otherwise.
    """
    return hash1 == hash2

def remove_file_with_logging(file_path):
    """
    Remove a file and log the result.
    
    Args:
        file_path (str): Path to the file to remove.

    
    Returns:
        bool: True if file was successfully deleted, False otherwise.
    """
    logger = get_logger()
        
    try:
        os.remove(file_path)
        if not os.path.exists(file_path):
            logger.info(f"Successfully deleted file: {file_path}")
            return True
    except PermissionError:
        logger.error(f"Permission denied while deleting file: {file_path}")
    except FileNotFoundError:
        logger.warning(f"File not found while attempting deletion: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
    return False

def test_write_access(path):
    """
    Test if the script has write access to a given directory.
    
    Args:
        path (str): Path to the directory to test.

    
    Returns:
        bool: True if write access is confirmed, False otherwise.
    """
    logger = get_logger()
        
    try:
        test_file = os.path.join(path, 'write_test.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info(f"Write access confirmed for {path}")
        return True
    except Exception as e:
        logger.error(f"No write access to {path}. Error: {e}")
        return False



def verify_file_integrity(source_file_path, comparison_file_path):
    """
    Verify file integrity between source and destination.
    
    Args:
        source_file_path (str): Path to source file
        comparison_file_path (str): Path to comparison file

        
    Returns:
        dict: Result dictionary with success status and hash values
    """
    logger = get_logger()

    result = dict(); 
    result['success'] = False
    result['a'] = None
    result['b'] = None
 
    # Zero-length files are valid and can be verified by comparing hashes
    # Remove the check that rejected empty files

    source_hash = get_file_hash(source_file_path)
    comparison_hash = get_file_hash(comparison_file_path)

    result['a'] = source_hash
    result['b'] = comparison_hash 

    if source_hash is None:
        logger.error(f"Failed to compute hash for source file: {source_file_path}")
        return result
    
    if comparison_hash is None:
        logger.error(f"Failed to compute hash for comparison file: {comparison_file_path}")
        return result

    if compare_file_hashes(source_hash, comparison_hash):
        logger.info(f"File integrity verified between {source_file_path} and {comparison_file_path}")

        result['success'] = True
        return result
    
    else:
        logger.error(f"File integrity check failed between {source_file_path} and {comparison_file_path}")
        return result


def copy_temp_then_rename(from_path, to_path):
    """
    Copy a file to a temporary location then rename it to the final destination.
    
    Args:
        from_path (str): Source file path
        to_path (str): Destination file path
       
    """
    logger = get_logger()
        
    to_dir = os.path.dirname(to_path)
    to_path_temp = os.path.join(to_path + '.copying')
    
    try:        
        os.makedirs(to_dir, exist_ok=True)

        if os.path.exists(to_path_temp):
            os.remove(to_path_temp)

        shutil.copy2(from_path, to_path_temp)
        os.rename(to_path_temp, to_path)

        logger.info(f"Copied file {from_path} to : {to_path}")

    except FileNotFoundError as e:
        logger.error(f"File not found during copying: {from_path} to: {to_path}. Error: {e}")
        raise

    except PermissionError as e:
        logger.error(f"Permission denied when copying file: {from_path} to: {to_path}. Error: {e}")
        raise

    except Exception as e:
        logger.error(f"Failed to copy file: {from_path} to : {to_path}. Error: {e}")
        raise

    finally:
        if os.path.exists(to_path_temp):
            os.remove(to_path_temp)

def normalize_path(path):
    p = Path(path)
    return str(p.parent.resolve().joinpath(p.name))


def remove_empty_directories(root, keep_root=False):
    """
    Remove empty directories recursively.
    
    Args:
        root (str): Root directory to start from
        keep_root (bool): Whether to keep the root directory
       
    """
    logger = get_logger()
        
    for path, _, _ in os.walk(root, topdown=False):  # Listing the files
        if keep_root and path == root:
            break
        try:
            os.rmdir(path)
            logger.debug(f"Removed empty directory: {path}")
        except OSError as ex:
            logger.debug(f"Could not remove directory: {path}, {ex}")

def is_directory_empty(directory_path):
    """
    Check if a directory is empty.
    
    Args:
        directory_path (str): Path to the directory to check
        
    Returns:
        bool: True if directory exists and is empty, False otherwise
    """
    try:
        if not os.path.exists(directory_path):
            return False
        if not os.path.isdir(directory_path):
            return False
        return len(os.listdir(directory_path)) == 0
    except (OSError, PermissionError):
        return False

def is_safe_to_remove_directory(directory_path, root_paths, stability_seconds=300):
    """
    Check if it's safe to remove a directory with comprehensive safety checks.
    
    Args:
        directory_path (str): Path to directory to check
        root_paths (list): List of root paths we should never go above
        stability_seconds (int): Minimum seconds since last modification (0 = no check)
        
    Returns:
        bool: True if safe to remove, False otherwise
    """
    logger = get_logger()
    
    # Normalize path
    normalized_dir = normalize_path(directory_path)
    
    # Protected system paths - never remove these
    PROTECTED_PATHS = [
        "/", "/usr", "/bin", "/sbin", "/lib", "/lib64", "/var", "/etc", 
        "/home", "/root", "/tmp", "/dev", "/proc", "/sys", "/run"
    ]
    
    # Check against protected system paths
    for protected in PROTECTED_PATHS:
        if normalized_dir.startswith(protected + "/") or normalized_dir == protected:
            logger.debug(f"Directory {directory_path} is protected system path")
            return False
    
    # Check against root boundaries
    for root_path in root_paths:
        normalized_root = normalize_path(root_path)
        if normalized_dir == normalized_root:
            logger.debug(f"Directory {directory_path} is a root path")
            return False
        if not normalized_dir.startswith(normalized_root + "/"):
            logger.debug(f"Directory {directory_path} is outside root boundary {root_path}")
            return False
    
    # Check if directory exists and is actually a directory
    if not os.path.exists(directory_path):
        return False
    if not os.path.isdir(directory_path):
        return False
    
    # Check if directory is empty
    if not is_directory_empty(directory_path):
        return False
    
    # Check if directory is stable (not recently modified)
    if stability_seconds > 0 and not is_path_stable(directory_path, stability_seconds):
        return False
    
    # Check if directory is currently open/in use
    if is_path_open(directory_path):
        logger.debug(f"Directory {directory_path} is currently in use")
        return False
    
    # Check for mount points
    try:
        if os.path.ismount(directory_path):
            logger.debug(f"Directory {directory_path} is a mount point")
            return False
    except (OSError, PermissionError):
        return False
    
    return True

def would_directory_be_empty_after_removals(directory_path, planned_removals):
    """
    Check if a directory would be empty after planned removals are executed.
    
    Args:
        directory_path (str): Directory to check
        planned_removals (set): Set of directories planned for removal
        
    Returns:
        bool: True if directory would be empty after removals
    """
    logger = get_logger()
    try:
        contents = os.listdir(directory_path)
        logger.debug(f"Checking if {directory_path} would be empty. Contents: {contents}")
        
        # Check each item in the directory
        for item in contents:
            item_path = os.path.join(directory_path, item)
            
            # If this item is NOT planned for removal, directory won't be empty
            if item_path not in planned_removals:
                logger.debug(f"Item {item_path} not in planned removals")
                # Check if it's a directory that would become empty
                if os.path.isdir(item_path):
                    logger.debug(f"Item {item_path} is a directory, checking recursively")
                    if not would_directory_be_empty_after_removals(item_path, planned_removals):
                        logger.debug(f"Directory {item_path} would not be empty, so {directory_path} won't be empty")
                        return False
                    else:
                        logger.debug(f"Directory {item_path} would be empty")
                else:
                    # It's a file, so directory won't be empty
                    logger.debug(f"Item {item_path} is a file, so {directory_path} won't be empty")
                    return False
            else:
                logger.debug(f"Item {item_path} is planned for removal")
        
        # All contents are either planned for removal or would be empty
        logger.debug(f"Directory {directory_path} would be empty after removals")
        return True
        
    except (OSError, PermissionError) as e:
        logger.debug(f"Error checking directory {directory_path}: {e}")
        return False

def collect_all_removable_directories(empty_directories, root_paths, stability_seconds=300, max_depth=131):
    """
    Collect all directories that can be removed, including parents that would become empty.
    
    Args:
        empty_directories (set): Set of currently empty directories
        root_paths (list): List of root paths we should never go above
        stability_seconds (int): Minimum seconds since last modification
        max_depth (int): Maximum levels to traverse upward
        
    Returns:
        set: Set of all directories that can be removed
    """
    logger = get_logger()
    removable_dirs = set()
    
    # Start with all empty directories that pass safety checks
    for directory in empty_directories:
        if is_safe_to_remove_directory(directory, root_paths, stability_seconds):
            removable_dirs.add(directory)
    
    # Now check parent directories iteratively
    changed = True
    iteration = 0
    
    while changed and iteration < max_depth:
        changed = False
        iteration += 1
        
        # Check parents of all currently removable directories
        parents_to_check = set()
        for directory in removable_dirs:
            parent = os.path.dirname(directory)
            
            # Skip if parent is a root path
            should_skip = False
            for root_path in root_paths:
                if normalize_path(parent) == normalize_path(root_path):
                    should_skip = True
                    break
            
            if not should_skip and parent not in removable_dirs:
                parents_to_check.add(parent)
        
        # Check each parent
        for parent in parents_to_check:
            logger.debug(f"Iteration {iteration}: Checking parent {parent}")
            # Check if parent passes safety checks
            if is_safe_to_remove_directory(parent, root_paths, stability_seconds):
                logger.debug(f"Parent {parent} passes safety checks")
                # Check if parent would be empty after planned removals
                if would_directory_be_empty_after_removals(parent, removable_dirs):
                    removable_dirs.add(parent)
                    changed = True
                    logger.debug(f"Parent {parent} would be empty after removals, adding to cleanup")
                else:
                    logger.debug(f"Parent {parent} would NOT be empty after removals")
            else:
                logger.debug(f"Parent {parent} does not pass safety checks")
    
    logger.info(f"Collected {len(removable_dirs)} directories for removal after {iteration} iterations")
    return removable_dirs

def cleanup_empty_directories(root_paths, stability_seconds=300):
    """
    Enhanced directory cleanup with proper parent directory handling.
    Single-pass approach since mtime updates would block subsequent iterations.
    
    Args:
        root_paths (list): List of root directories to clean
        stability_seconds (int): Minimum seconds since last modification (default 300 = 5 minutes)
        
    Returns:
        dict: Summary of cleanup results
    """
    logger = get_logger()
    
    cleanup_results = {
        'directories_removed': 0,
        'directories_failed': 0,
        'root_paths_processed': 0
    }
    
    # Scan all empty directories in root paths
    directories_to_check = set()
    for root_path in root_paths:
        if os.path.exists(root_path):
            # Collect all empty directories
            for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
                if dirpath == root_path:
                    continue
                if len(dirnames) == 0 and len(filenames) == 0:
                    directories_to_check.add(dirpath)
    
    if not directories_to_check:
        logger.info("No empty directories found for cleanup")
    else:
        logger.info(f"Found {len(directories_to_check)} empty directories for cleanup")
    
    # Phase 1: Plan all removals (no mtime changes yet)
    # Use the new algorithm that properly handles multiple empty siblings
    all_removable_dirs = collect_all_removable_directories(
        directories_to_check, root_paths, stability_seconds, max_depth=131
    )
    
    # Phase 2: Execute removals (deepest first to avoid conflicts)
    sorted_removals = sorted(all_removable_dirs, key=lambda x: x.count('/'), reverse=True)
    
    for directory in sorted_removals:
        if not os.path.exists(directory):
            # Already removed as a subdirectory of another removal
            continue
        
        # Double-check that directory is still empty before removal
        # (someone might have written files while we were planning)
        try:
            if not is_directory_empty(directory):
                logger.warning(f"Directory {directory} is no longer empty - user activity detected, abandoning cleanup")
                cleanup_results['directories_failed'] += 1
                # Stop cleanup entirely to avoid interfering with user work
                break
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot verify directory {directory} is empty: {e} - abandoning cleanup")
            cleanup_results['directories_failed'] += 1
            break
            
        # Attempt removal
        try:
            if remove_directory(directory):
                cleanup_results['directories_removed'] += 1
                logger.info(f"Removed empty directory: {directory}")
            else:
                # Removal failed - likely due to concurrent file creation
                logger.warning(f"Failed to remove directory: {directory} - possible user activity, abandoning cleanup")
                cleanup_results['directories_failed'] += 1
                break
        except Exception as e:
            logger.warning(f"Error removing directory {directory}: {e} - abandoning cleanup")
            cleanup_results['directories_failed'] += 1
            break
    
    cleanup_results['root_paths_processed'] = len(root_paths)
    
    logger.info(f"Directory cleanup completed: "
                f"{cleanup_results['directories_removed']} removed, "
                f"{cleanup_results['directories_failed']} failed")
    
    return cleanup_results

def remove_directory(path):
    """
    Remove a directory.
    
    Args:
        path (str): Directory to remove

        
    Returns:
        bool: True if directory was removed, False otherwise
    """
    logger = get_logger()
        
    try:
        os.rmdir(path)
        logger.debug(f"Removed directory: {path}")
        return True
    except OSError as ex:
        logger.debug(f"Could not remove directory: {path}, {ex}")
        return False

def remove_directory_contents(root):
    """
    Remove all contents of a directory.
    
    Args:
        root (str): Directory to empty
       
    """
    logger = get_logger()
        
    for filename in os.listdir(root):
        file_path = os.path.join(root, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                logger.debug(f"Removed file: {file_path}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                logger.debug(f"Removed directory tree: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")



def is_path_open(file_path):
    """
    Check if a file is currently open by any process.
    
    Args:
        file_path (str): Path to the file to check.
       
    
    Returns:
        bool: True if the file is open, False otherwise.
    """
    try:
        result = subprocess.run(
            ['lsof', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
        elif result.returncode == 1:
            # lsof returns 1 if no processes are using the file
            return False
        else:
            if result.stderr:
                logger = get_logger()
                logger.error(f"Error checking if file is open: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        logger = get_logger()
        logger.error(f"'lsof' command not found. Please ensure it is installed.")
        return False
    except PermissionError:
        logger = get_logger()
        logger.error(f"Permission denied when accessing 'lsof' or file: {file_path}")
        return False
    except Exception as e:
        logger = get_logger()
        logger.error(f"Exception occurred while checking if file is open: {e}")
        return False
    
def is_path_stable(file_path, stability_time=5):
    """
    Check if a file has not been modified in the last 'stability_time' seconds.
    
    Args:
        file_path (str): Path to the file to check.
        stability_time (int): Time in seconds to consider the file stable (default is 5).
       
    
    Returns:
        bool: True if the file is stable, False otherwise.
    """
    try:
        last_modified_time = os.path.getmtime(file_path)
        current_time = time.time()
        is_stable = (current_time - last_modified_time) > stability_time
        if not is_stable:
            logger = get_logger()
            logger.debug(f"File is not yet stable: {file_path}")
        return is_stable
    except FileNotFoundError:
        logger = get_logger()
        logger.error(f"File not found when checking if file is stable: {file_path}")
        return False
    except PermissionError:
        logger = get_logger()
        logger.error(f"Permission denied when accessing file mtime: {file_path}")
        return False
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error checking if file is stable {file_path}: {e}")
        return False
    

def encrypt_file(file_path, output_path, key_file_path):
    """
    Encrypt a file using GPG with a specified public key file.
    
    Args:
        file_path (str): Path to file to encrypt
        output_path (str): Path for encrypted output
        key_file_path (str): Full path to the public key file (.gpg)
       
    
    Returns:
        bool: True if encryption successful, False otherwise
    """
    logger = get_logger()
        
    try:
        gpg = gnupg.GPG()
        
        # Import the key from file
        with open(key_file_path, 'rb') as key_file:
            import_result = gpg.import_keys(key_file.read())
            if not import_result.count:
                logger.error(f"Failed to import key from {key_file_path}")
                return False
            
            # Use the fingerprint from the imported key
            key_id = import_result.fingerprints[0]
        
        # Encrypt file
        with open(file_path, 'rb') as f:
            status = gpg.encrypt_file(
                f,
                recipients=[key_id],
                output=output_path,
                always_trust=True
            )
        
        if status.ok:
            logger.info(f"File encrypted successfully: {output_path}")
            return True
        else:
            logger.error(f"Encryption failed: {status.status}")
            return False
            
    except FileNotFoundError:
        logger.error(f"Key file not found: {key_file_path}")
        return False
    except Exception as e:
        logger.error(f"Error during encryption: {e}")
        return False

"""
File safety checking functionality for Shuttle.

This module contains functions to ensure files are safe to process.
"""

def are_file_and_path_names_safe(source_file, source_root):
    """
    Check if filenames and paths are safe for processing.
    
    Args:
        source_file: Filename only
        source_root: Directory containing the file
       
    Returns:
        bool: True if all names are safe, False otherwise
    """
    logger = get_logger()
    
    # Calculate the full path
    source_file_path = os.path.join(source_root, source_file)
    
    # Check filename safety
    if not is_filename_safe(source_file):
        logger.error(f"Skipping file {source_file} because it contains unsafe characters.")
        return False
    
    # Check pathname safety
    if not is_pathname_safe(source_root):
        logger.error(f"Skipping file in directory {source_root} because the path contains unsafe characters.")
        return False
    
    # Check full path safety
    if not is_pathname_safe(source_file_path):
        logger.error(f"Skipping path {source_file_path} because it contains unsafe characters.")
        return False
    
    return True

def is_file_ready(source_file_path, skip_stability_check=False):
    """
    Check if a file is ready for processing (stable and not open).
    
    Args:
        source_file_path: Full path to source file
        skip_stability_check: Whether to skip file stability check
       
        
    Returns:
        bool: True if file is ready for processing, False otherwise
    """
    logger = get_logger()
    
    # Check file stability
    if not skip_stability_check and not is_path_stable(source_file_path):
        logger.debug(f"Skipping file {source_file_path} because it may still be written to.")
        return False
    elif skip_stability_check:
        logger.debug(f"Stability check bypassed for {source_file_path} (test mode).")
    
    # Check if file is open
    if is_path_open(source_file_path):
        logger.debug(f"Skipping file {source_file_path} because it is currently open.")
        return False
    
    return True

def is_file_safe_for_processing(source_file, source_root, skip_stability_check=False):
    """
    Check if a file is safe to process (filename, path, stability, not open).
    
    Args:
        source_file: Filename only
        source_root: Directory containing the file
        skip_stability_check: Whether to skip file stability check
        
    Returns:
        bool: True if file is safe to process, False otherwise
    """

    # First check if names are safe
    if not are_file_and_path_names_safe(source_file, source_root):
        return False
    
    # Calculate the full path
    source_file_path = os.path.join(source_root, source_file)
    
    # Then check if the file is ready
    if not is_file_ready(source_file_path, skip_stability_check):
        return False
    
    return True
