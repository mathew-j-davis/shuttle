"""
Microsoft Defender Utilities

This module provides utility functions for working with Microsoft Defender
that can be shared between the main application and test scripts.
"""

import subprocess
import logging
import re
import types
import time
from typing import Optional

# Define scan output patterns
defender_scan_patterns = types.SimpleNamespace()
defender_scan_patterns.THREAT_FOUND = "Threat(s) found"
defender_scan_patterns.NO_THREATS = "0 threat(s) detected"

# Define scan result types - these should match the values in shuttle.scanning
scan_result_types = types.SimpleNamespace()
scan_result_types.FILE_IS_SUSPECT = 3
scan_result_types.FILE_IS_CLEAN = 0
scan_result_types.FILE_SCAN_FAILED = 100


def get_mdatp_version(logger=None) -> Optional[str]:
    """
    Get the current Microsoft Defender for Endpoint (mdatp) version.
    
    Args:
        logger: Optional logger instance. If not provided, a new logger will be created.
        
    Returns:
        str: Version number in format XXX.XXXX.XXXX, or None if version cannot be determined
    """
    if logger is None:
        logger = logging.getLogger('shuttle')
    
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


def run_malware_scan(cmd, path, result_handler):
    """
    Run a malware scan using the specified command and process the results.
    
    Args:
        cmd (list): Command to run
        path (str): Path to file being scanned
        result_handler (callable): Function to process scan results
        
    Returns:
        int: scan_result_types value
    """
    logger = logging.getLogger('shuttle')
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
        
        return result_handler(result.returncode, result.stdout)
        
    except Exception as e:
        logger.error(f"Exception during malware scan: {e}")
        return scan_result_types.FILE_SCAN_FAILED


def handle_defender_scan_result(returncode, output):
    """
    Process Microsoft Defender scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        
    Returns:
        int: scan_result_types value
    """
    logger = logging.getLogger('shuttle')
    
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


def scan_for_malware_using_defender(path, custom_handler=handle_defender_scan_result):
    """Scan a file using Microsoft Defender.
    
    Args:
        path (str): Path to the file to scan
        custom_handler (callable, optional): Custom result handler function.
                                           Default is handle_defender_scan_result.
    
    Returns:
        The result from the handler function
    """
    cmd = [
        "mdatp",
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path",
        path
    ]
    return run_malware_scan(cmd, path, custom_handler)


# if __name__ == "__main__":
#     # Simple test if run directly
#     version = get_mdatp_version()
#     if version:
#         print(f"Microsoft Defender version: {version}")
#     else:
#         print("Could not determine Microsoft Defender version")
