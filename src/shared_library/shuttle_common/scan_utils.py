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
from .logger_injection import with_logger

# Define commands for real defender and simulator
REAL_DEFENDER_COMMAND = "mdatp"
DEFENDER_COMMAND = "mdatp"

@with_logger
def is_using_simulator(logger=None):
    """
    Check if the DEFENDER_COMMAND has been patched to use the simulator.
    
    This can be used to detect if the application is running in simulator mode
    due to patching.
    
    Returns:
        bool: True if DEFAULT_DEFENDER_COMMAND has been patched, False otherwise
    """
    return DEFENDER_COMMAND != REAL_DEFENDER_COMMAND

# Define scan output patterns
defender_scan_patterns = types.SimpleNamespace()
defender_scan_patterns.THREAT_FOUND = "Threat(s) found"
defender_scan_patterns.FILE_NOT_FOUND = "\n\t0 file(s) scanned\n\t0 threat(s) detected"
defender_scan_patterns.NO_THREATS = "\n\t0 threat(s) detected"


# Define scan result types - these should match the values in shuttle.scanning
class scan_result_types:
    """Constants for scan results"""
    FILE_IS_CLEAN = 0
    FILE_IS_SUSPECT = 1
    FILE_NOT_FOUND = 2
    FILE_SCAN_FAILED = 100


class DefenderScanResult:
    """Container for Microsoft Defender scan result information"""
    def __init__(self, scan_completed=False, suspect_detected=False, scanner_handles_suspect=False):
        self.scan_completed = scan_completed  # Was the scan completed successfully
        self.suspect_detected = suspect_detected  # Was a threat found?
        self.scanner_handles_suspect = scanner_handles_suspect  # Is scanner handling it?


@with_logger
def process_defender_result(result_code, path, scanner_handles_suspect=False, logging_options=None, logger=None):
    """
    Process defender scan result and determine actions
    
    Args:
        result_code: The scan result type from parse_defender_scan_result
        path: Path to the scanned file
        scanner_handles_suspect: Whether defender is configured to handle suspicious files
        logging_options: Optional logging configuration
        
    Returns:
        DefenderScanResult: Information about the scan result and how to handle it
    """
    # Logger provided by decorator
    
    # Threat detection
    if result_code == scan_result_types.FILE_IS_SUSPECT:
        msg = "letting Defender handle it" if scanner_handles_suspect else "handling internally"
        logger.warning(f"Threats found in {path}, {msg}")
        return DefenderScanResult(
            scan_completed=True,
            suspect_detected=True,
            scanner_handles_suspect=scanner_handles_suspect
        )
        
    # File not found
    elif result_code == scan_result_types.FILE_NOT_FOUND:
        if scanner_handles_suspect:
            logger.warning(f"File not found at {path}, assuming Defender quarantined it")
            return DefenderScanResult(
                scan_completed=True,
                suspect_detected=True,
                scanner_handles_suspect=True
            )  # treat as suspect + handled
        else:
            logger.warning(f"File not found at {path}")
            return DefenderScanResult(
                scan_completed=False,
                suspect_detected=False,
                scanner_handles_suspect=False
            )  # error condition
            
    # Clean case
    elif result_code == scan_result_types.FILE_IS_CLEAN:
        logger.info(f"No threats found in {path}")
        return DefenderScanResult(
            scan_completed=True,
            suspect_detected=False,
            scanner_handles_suspect=False
        )
        
    # Other errors
    else:
        logger.warning(f"Scan failed for {path} with code {result_code}")
        return DefenderScanResult(
            scan_completed=False,
            suspect_detected=False,
            scanner_handles_suspect=False
        )


@with_logger
def get_mdatp_version(logging_options=None, logger=None) -> Optional[str]:
    """
    Get the current Microsoft Defender for Endpoint (mdatp) version.
    
    Args:
        logging_options (LoggingOptions, optional): Logging configuration options

         
    Returns:
        str: Version number in format XXX.XXXX.XXXX, or None if version cannot be determined
    """

    # Logger provided by decorator
    

    try:
        # Run mdatp version command
        result = subprocess.run(
            [DEFENDER_COMMAND, "version"],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Check if command succeeded
        if result.returncode != 0:
            logger.error(f"{DEFENDER_COMMAND} version command failed with code {result.returncode}: {result.stderr}")
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
        logger.error(f"{DEFENDER_COMMAND} command not found. Microsoft Defender for Endpoint may not be installed.")
        return None
    except Exception as e:
        logger.error(f"Error getting {DEFENDER_COMMAND} version: {e}")
        return None


@with_logger
def run_malware_scan(cmd, path, result_handler, logging_options=None, logger=None):
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
    # Logger provided by decorator
    
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


@with_logger
def parse_defender_scan_result(returncode, output, logging_options=None, logger=None):
    """
    Process Microsoft Defender scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        logging_options (LoggingOptions, optional): Logging configuration options
        
    Returns:
        int: scan_result_types value
    """
    # Logger provided by decorator
    
    if returncode == 0:
        # Always check for threat pattern first, otherwise a malicious filename could be used to add clean response text to output
        if defender_scan_patterns.THREAT_FOUND in output:
            logger.warning("Threats found")
            return scan_result_types.FILE_IS_SUSPECT

        elif output.rstrip().endswith(defender_scan_patterns.FILE_NOT_FOUND):
            logger.warning("File not found")
            return scan_result_types.FILE_NOT_FOUND
        
        elif output.rstrip().endswith(defender_scan_patterns.NO_THREATS):
            logger.info("No threat found")
            return scan_result_types.FILE_IS_CLEAN
        
        else:
            logger.warning(f"Unexpected scan output: {output}")
            
    else:
        logger.warning(f"Scan failed with return code {returncode}")
    
    return scan_result_types.FILE_SCAN_FAILED


@with_logger
def scan_for_malware_using_defender(path, logging_options=None, logger=None):
    """Scan a file using Microsoft Defender.
    
    Args:
        path (str): Path to the file to scan
        logging_options: Optional logging configuration options
            
    Returns:
        The result from the handler function
    """

    # path appended to cmd after safety check in run_malware_scan
    
    cmd = [
        DEFENDER_COMMAND,
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path"
    ]

    return run_malware_scan(cmd, path, parse_defender_scan_result, logging_options)

@with_logger
def handle_clamav_scan_result(returncode, output, logging_options=None, logger=None):
    """
    Process ClamAV scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        logging_options (LoggingOptions, optional): Logging configuration options
        
    Returns:
        int: scan_result_types value
    """
    # Logger provided by decorator
    
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


@with_logger
def scan_for_malware_using_clam_av(path, logging_options=None, logger=None):
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
