import os
import shutil
import hashlib
import time
import subprocess
from pathlib import Path
import gnupg
from .logging_setup import setup_logging, LoggingOptions

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
        filename (str): Filename to check
        
    Returns:
        bool: True if filename is safe, False otherwise
    """
    # Block control characters (0x00-0x1F, 0x7F)
    if any(ord(char) < 32 or ord(char) == 0x7F for char in name):
        return False
        
    # Block specific dangerous characters
    dangerous_chars_file = ['/', '\\', '..', '>', '<', '|', '*', '$', '&', ';', '`']
    dangerous_chars_path = ['\\', '..', '>', '<', '|', '*', '$', '&', ';', '`']

    dangerous_chars = []
    if is_path:
        dangerous_chars = dangerous_chars_path
    else:
        dangerous_chars = dangerous_chars_file


    if any(char in name for char in dangerous_chars):
        return False
        
    # Block filenames starting with dash or period
    if name.startswith('-') or name.startswith('.'):
        return False
        
    # Ensure filename is valid UTF-8
    try:
        name.encode('utf-8').decode('utf-8')
    except UnicodeError:
        return False
        
    return True

def get_file_hash(file_path, logging_options=None):
    """
    Compute the SHA-256 hash of a file.

    Args:
        file_path (str): Path to the file.
        logging_options (LoggingOptions, optional): Logging configuration options.

    Returns:
        str: The computed hash or None if an error occurred.
    """
    hash_sha256 = hashlib.sha256()
    logger = setup_logging('shuttle.common.files.get_file_hash', logging_options)
        
    try:
        with open(file_path, 'rb') as f:
            # Read the file in chunks to avoid memory issues with large files
            for chunk in iter(lambda: f.read(4096), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except PermissionError:
        logger.error(f"Permission denied when accessing file: {file_path}")
        return None
    except Exception as e:
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

def remove_file_with_logging(file_path, logging_options=None):
    """
    Remove a file and log the result.
    
    Args:
        file_path (str): Path to the file to remove.
        logging_options (LoggingOptions, optional): Logging configuration options.
    
    Returns:
        bool: True if file was successfully deleted, False otherwise.
    """
    logger = setup_logging('shuttle.common.files.remove_file_with_logging', logging_options)
        
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

def test_write_access(path, logging_options=None):
    """
    Test if the script has write access to a given directory.
    
    Args:
        path (str): Path to the directory to test.
        logging_options (LoggingOptions, optional): Logging configuration options.
    
    Returns:
        bool: True if write access is confirmed, False otherwise.
    """
    logger = setup_logging('shuttle.common.files.test_write_access', logging_options)
        
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



def verify_file_integrity(source_file_path, comparison_file_path, logging_options=None):
    """
    Verify file integrity between source and destination.
    
    Args:
        source_file_path (str): Path to source file
        comparison_file_path (str): Path to comparison file
        logging_options (LoggingOptions, optional): Logging configuration options.
        
    Returns:
        dict: Result dictionary with success status and hash values
    """
    logger = setup_logging('shuttle.common.files.verify_file_integrity', logging_options)

    result = dict(); 
    result['success'] = False
    result['a'] = None
    result['b'] = None
 
    if os.path.getsize(source_file_path) == 0 or os.path.getsize(comparison_file_path) == 0:
        logger.error("One of the files is empty")
        return result

    source_hash = get_file_hash(source_file_path, logging_options)
    comparison_hash = get_file_hash(comparison_file_path, logging_options)

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


def copy_temp_then_rename(from_path, to_path, logging_options=None):
    """
    Copy a file to a temporary location then rename it to the final destination.
    
    Args:
        from_path (str): Source file path
        to_path (str): Destination file path
        logging_options (LoggingOptions, optional): Logger properties to use for logging.
    """
    logger = setup_logging('shuttle.common.files.copy_temp_then_rename', logging_options)
        
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


def remove_empty_directories(root, keep_root=False, logging_options=None):
    """
    Remove empty directories recursively.
    
    Args:
        root (str): Root directory to start from
        keep_root (bool): Whether to keep the root directory
        logging_options (LoggingOptions, optional): Logger properties to use for logging.
    """
    logger = setup_logging('shuttle.common.files.remove_empty_directories', logging_options)
        
    for path, _, _ in os.walk(root, topdown=False):  # Listing the files
        if keep_root and path == root:
            break
        try:
            os.rmdir(path)
            logger.debug(f"Removed empty directory: {path}")
        except OSError as ex:
            logger.debug(f"Could not remove directory: {path}, {ex}")

def remove_directory(path, logging_options=None):
    """
    Remove a directory.
    
    Args:
        path (str): Directory to remove
        logging_options (LoggingOptions, optional): Logging configuration options.
        
    Returns:
        bool: True if directory was removed, False otherwise
    """
    logger = setup_logging('shuttle.common.files.remove_directory', logging_options)
        
    try:
        os.rmdir(path)
        logger.debug(f"Removed directory: {path}")
        return True
    except OSError as ex:
        logger.debug(f"Could not remove directory: {path}, {ex}")
        return False

def remove_directory_contents(root, logging_options=None):
    """
    Remove all contents of a directory.
    
    Args:
        root (str): Directory to empty
        logging_options (LoggingOptions, optional): Logger properties to use for logging.
    """
    logger = setup_logging('shuttle.common.files.remove_directory_contents', logging_options)
        
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



def is_file_open(file_path, logging_options=None):
    """
    Check if a file is currently open by any process.
    
    Args:
        file_path (str): Path to the file to check.
        logging_options (LoggingOptions, optional): Logger properties to use for logging.
    
    Returns:
        bool: True if the file is open, False otherwise.
    """
    logger = setup_logging('shuttle.common.files.is_file_open', logging_options)
        
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
                logger.error(f"Error checking if file is open: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        logger.error(f"'lsof' command not found. Please ensure it is installed.")
        return False
    except PermissionError:
        logger.error(f"Permission denied when accessing 'lsof' or file: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Exception occurred while checking if file is open: {e}")
        return False
    
def is_file_stable(file_path, stability_time=5, logging_options=None):
    """
    Check if a file has not been modified in the last 'stability_time' seconds.
    
    Args:
        file_path (str): Path to the file to check.
        stability_time (int): Time in seconds to consider the file stable (default is 5).
        logging_options (LoggingOptions, optional): Logger properties to use for logging.
    
    Returns:
        bool: True if the file is stable, False otherwise.
    """
    logger = setup_logging('shuttle.common.files.is_file_stable', logging_options)
        
    try:
        last_modified_time = os.path.getmtime(file_path)
        current_time = time.time()
        is_stable = (current_time - last_modified_time) > stability_time
        if not is_stable:
            logger.debug(f"File is not yet stable: {file_path}")
        return is_stable
    except FileNotFoundError:
        logger.error(f"File not found when checking if file is stable: {file_path}")
        return False
    except PermissionError:
        logger.error(f"Permission denied when accessing file size: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Error checking if file is stable {file_path}: {e}")
        return False
    

def encrypt_file(file_path, output_path, key_file_path, logging_options=None):
    """
    Encrypt a file using GPG with a specified public key file.
    
    Args:
        file_path (str): Path to file to encrypt
        output_path (str): Path for encrypted output
        key_file_path (str): Full path to the public key file (.gpg)
        logging_options (LoggingOptions, optional): Logger properties to use for logging.
    
    Returns:
        bool: True if encryption successful, False otherwise
    """
    logger = setup_logging('shuttle.common.files.encrypt_file', logging_options)
        
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
