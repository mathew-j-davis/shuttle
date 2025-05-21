"""
Scan Utilities

This module provides utility functions for working with Microsoft Defender and ClamAV
that can be shared between the main application and test scripts.
"""

import subprocess
import re
import types
import time
from typing import List, Callable, Any, Optional
from . import files
from .logging_setup import setup_logging, LoggingOptions

# Define scan output patterns
defender_scan_patterns = types.SimpleNamespace()
defender_scan_patterns.THREAT_FOUND = "Threat(s) found"
defender_scan_patterns.NO_THREATS = "0 threat(s) detected"

# Define scan result types - these should match the values in shuttle.scanning
scan_result_types = types.SimpleNamespace()
scan_result_types.FILE_IS_SUSPECT = 3
scan_result_types.FILE_IS_CLEAN = 0
scan_result_types.FILE_SCAN_FAILED = 100

def get_mdatp_version(logging_options=None) -> Optional[str]:
    """
    Get the current Microsoft Defender for Endpoint (mdatp) version.
    
    Args:
        logging_options (LoggingOptions, optional): Logging configuration options
         
    Returns:
        str: Version number in format XXX.XXXX.XXXX, or None if version cannot be determined
    """

    logger = setup_logging('shuttle.common.scan_utils.get_mdatp_version', logging_options)
    
    try:
        # Run mdatp version command
        result = subprocess.run(
            ["mdatp", "version"],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Check if command succeeded
        if result.returncode != 0:
            logger.error(f"mdatp version command failed with code {result.returncode}: {result.stderr}")
            return None
            
        # Parse output for version number
        output = result.stdout
        match = re.search(r'Product version: ([\d\.]+)', output)
        
        if match:
            version = match.group(1)
            logger.debug(f"Detected mdatp version: {version}")
            return version
        else:
            logger.error(f"Failed to parse mdatp version from output: {output}")
            return None
            
    except FileNotFoundError:
        logger.error("mdatp command not found. Microsoft Defender for Endpoint may not be installed.")
        return None
    except Exception as e:
        logger.error(f"Error getting mdatp version: {e}")
        return None


def run_malware_scan(cmd, path, result_handler, logging_options=None):
    """
    Run a malware scan using the specified command and process the results.
    SECURITY NOTE: This function executes external commands. Only use with trusted,
    hardcoded command lists. Never pass user-controlled input to the cmd parameter.
        
    Args:
        cmd (list): Command to run as a list of strings (not shell string)
        path (str): Path to file being scanned
        result_handler (callable): Function to process scan results
        logging_options (LoggingOptions, optional): Logging configuration options
        
    Returns:
        int: scan_result_types value
    """
    logger = setup_logging('shuttle.common.scan_utils.run_malware_scan', logging_options)
    
    # Security validation
    if not isinstance(cmd, list):
        logger.error("Security error: cmd must be a list, not a string")
        return scan_result_types.FILE_SCAN_FAILED
    
    # Add validation for the path
    if not files.is_pathname_safe(path):
        logger.error(f"Security error: Unsafe filename detected: {path}")
        return scan_result_types.FILE_SCAN_FAILED
    
    # Append the path to the command
    cmd.append(path)
    
    try:
        logger.info(f"Scanning file {path} for malware...")
        
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        scan_time = time.time() - start_time
        
        logger.debug(f"Scan completed in {scan_time:.2f} seconds")
        logger.debug(f"Return code: {result.returncode}")
        logger.debug(f"Output: {result.stdout}")
        
        return result_handler(result.returncode, result.stdout, logging_options)
        
    except Exception as e:
        logger.error(f"Exception during malware scan: {e}")
        return scan_result_types.FILE_SCAN_FAILED


def handle_defender_scan_result(returncode, output, logging_options=None):
    """
    Process Microsoft Defender scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        logging_options (LoggingOptions, optional): Logging configuration options
        
    Returns:
        int: scan_result_types value
    """
    logger = setup_logging('shuttle.common.scan_utils.handle_defender_scan_result', logging_options)
    
    if returncode == 0:
        # Always check for threat pattern first, otherwise a malicious filename could be used to add clean response text to output
        if defender_scan_patterns.THREAT_FOUND in output:
            logger.warning("Threats found")
            return scan_result_types.FILE_IS_SUSPECT
        
        elif output.rstrip().endswith(defender_scan_patterns.NO_THREATS):
            logger.info("No threat found")
            return scan_result_types.FILE_IS_CLEAN
        
        else:
            logger.warning(f"Unexpected scan output: {output}")
            
    else:
        logger.warning(f"Scan failed with return code {returncode}")
    
    return scan_result_types.FILE_SCAN_FAILED


def scan_for_malware_using_defender(path, custom_handler=handle_defender_scan_result, logging_options=None):
    """Scan a file using Microsoft Defender.
    
    Args:
        path (str): Path to the file to scan
        custom_handler (callable, optional): Custom result handler function.
                                           Default is handle_defender_scan_result.
        logging_options: Optional logging configuration options
    
    Returns:
        The result from the handler function
    """

    # path appended to cmd after safety check in run_malware_scan

    cmd = [
        "mdatp",
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path"
    ]
    return run_malware_scan(cmd, path, custom_handler, logging_options)

def handle_clamav_scan_result(returncode, output, logging_options=None):
    """
    Process ClamAV scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        logging_options (LoggingOptions, optional): Logging configuration options
        
    Returns:
        int: scan_result_types value
    """
    logger = setup_logging('shuttle.common.scan_utils.handle_clamav_scan_result', logging_options)
    
    # RETURN CODES
    #        0 : No virus found.
    #        1 : Virus(es) found.
    #        2 : An error occurred.
    
    if returncode == 1:
        logger.warning("Threats found")
        return scan_result_types.FILE_IS_SUSPECT
        
    if returncode == 2:
        logger.warning("Error while scanning")
        return scan_result_types.FILE_SCAN_FAILED
        
    if returncode == 0:
        logger.info("No threat found")
        return scan_result_types.FILE_IS_CLEAN
        
    logger.warning(f"Unexpected return code: {returncode}")
    return scan_result_types.FILE_SCAN_FAILED


def scan_for_malware_using_clam_av(path, logging_options=None):
    """Scan a file using ClamAV.
    
    Args:
        path (str): Path to the file to scan
        logging_options: Optional logging configuration options
        
    Returns:
        The result from the handler function
    """
    # path appended to cmd after safety check in run_malware_scan
    cmd = [
        "clamdscan",
        "--fdpass"  # temp until permissions issues resolved
    ]
    return run_malware_scan(cmd, path, handle_clamav_scan_result, logging_options)
