"""
Scan Utilities

This module provides utility functions for working with Microsoft Defender and ClamAV
that can be shared between the main application and test scripts.
"""

import os
import subprocess
import re
import types
import time
from typing import List, Callable, Any, Optional
from . import files
from .logger_injection import get_logger

# Custom exceptions
class ScanTimeoutError(Exception):
    """Raised when a malware scan times out"""
    pass

# Define commands for real defender and simulator
REAL_DEFENDER_COMMAND = "mdatp"
DEFENDER_COMMAND = "mdatp"

def is_using_simulator():
    """
    Check if the DEFENDER_COMMAND has been patched to use the simulator.
    
    This can be used to detect if the application is running in simulator mode
    due to patching.
    
    Returns:
        bool: True if DEFENDER_COMMAND has been patched, False otherwise
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


def process_defender_result(result_code, path, scanner_handles_suspect=False):
    """
    Process defender scan result and determine actions
    
    Args:
        result_code: The scan result type from parse_defender_scan_result
        path: Path to the scanned file
        scanner_handles_suspect: Whether defender is configured to handle suspicious files
        
    Returns:
        DefenderScanResult: Information about the scan result and how to handle it
    """
    logger = get_logger()
    
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


def calculate_dynamic_timeout(file_path: str, base_timeout_seconds: int, ms_per_byte: float) -> Optional[int]:
    """
    Calculate dynamic timeout based on file size and configuration.
    
    Formula: (base_timeout_seconds | 0 if none) + (file_bytes * (ms_per_byte | 0 if none))
    Zero result = no timeout
    
    Args:
        file_path: Path to the file to be scanned
        base_timeout_seconds: Fixed timeout component (0 = no base timeout)
        ms_per_byte: Milliseconds per byte for size-based timeout (0 = no per-byte timeout)
        
    Returns:
        int: Calculated timeout in seconds, or None if no timeout should be applied
    """
    logger = get_logger()
    
    try:
        # Get file size
        file_size_bytes = os.path.getsize(file_path)
        
        # Calculate components
        base_component = base_timeout_seconds if base_timeout_seconds > 0 else 0
        per_byte_component_ms = (file_size_bytes * ms_per_byte) if ms_per_byte > 0 else 0
        per_byte_component_seconds = per_byte_component_ms / 1000.0
        
        # Calculate total timeout
        total_timeout = base_component + per_byte_component_seconds
        
        # Round to nearest second
        total_timeout_int = int(round(total_timeout))
        
        # Log the calculation
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.debug(f"Dynamic timeout calculation for {os.path.basename(file_path)}:")
        logger.debug(f"  File size: {file_size_bytes:,} bytes ({file_size_mb:.2f} MB)")
        logger.debug(f"  Base timeout: {base_component} seconds")
        logger.debug(f"  Per-byte timeout: {per_byte_component_ms:.1f} ms ({per_byte_component_seconds:.1f} seconds)")
        logger.debug(f"  Total timeout: {total_timeout_int} seconds")
        
        # Return None if total is zero (no timeout)
        if total_timeout_int <= 0:
            logger.debug("  Result: No timeout (total = 0)")
            return None
        else:
            logger.debug(f"  Result: {total_timeout_int} seconds")
            return total_timeout_int
            
    except OSError as e:
        logger.error(f"Could not get file size for {file_path}: {e}")
        # Fall back to base timeout only
        if base_timeout_seconds > 0:
            logger.debug(f"Fallback to base timeout: {base_timeout_seconds} seconds")
            return base_timeout_seconds
        else:
            logger.debug("Fallback: No timeout")
            return None


def get_mdatp_version() -> Optional[str]:
    """
    Get the current Microsoft Defender for Endpoint (mdatp) version.
             
    Returns:
        str: Version number in format XXX.XXXX.XXXX, or None if version cannot be determined
    """
    logger = get_logger()
    

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


def run_malware_scan(cmd, path, result_handler, timeout_seconds=None):
    """
    Run a malware scan using the specified command and process the results.
    SECURITY NOTE: This function executes external commands. Only use with trusted,
    hardcoded command lists. Never pass user-controlled input to the cmd parameter.
        
    Args:
        cmd (list): Command to run as a list of strings (not shell string)
        path (str): Path to file being scanned
        result_handler (callable): Function to process scan results
        timeout_seconds (int, optional): Timeout in seconds (None for no timeout)
        
    Returns:
        int: scan_result_types value
        
    Raises:
        ScanTimeoutError: If scan times out
    """
    logger = get_logger()
    
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
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds
            )
        except subprocess.TimeoutExpired:
            scan_time = time.time() - start_time
            logger.error(f"Scan timed out after {timeout_seconds} seconds for {path} (actual time: {scan_time:.2f}s)")
            raise ScanTimeoutError(f"Scan timed out for {path}")
            
        scan_time = time.time() - start_time
        
        # Calculate and log scan metrics
        try:
            file_size_bytes = os.path.getsize(path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            ms_per_byte = (scan_time * 1000) / file_size_bytes if file_size_bytes > 0 else 0
            
            # Log detailed scan metrics
            logger.info(f"Scan metrics for {os.path.basename(path)}:")
            logger.info(f"  Scan time: {scan_time:.3f} seconds")
            logger.info(f"  File size: {file_size_bytes:,} bytes ({file_size_mb:.2f} MB)")
            logger.info(f"  Scan rate: {ms_per_byte:.6f} ms/byte")
            if timeout_seconds:
                logger.info(f"  Timeout used: {timeout_seconds} seconds")
            else:
                logger.info(f"  Timeout used: None (unlimited)")
        except OSError as e:
            logger.warning(f"Could not calculate scan metrics for {path}: {e}")
            logger.info(f"Scan completed in {scan_time:.3f} seconds")
        
        logger.debug(f"Return code: {result.returncode}")
        logger.debug(f"Output: {result.stdout}")
        
        return result_handler(result.returncode, result.stdout)
        
    except ScanTimeoutError:
        # Re-raise timeout errors so they can be handled by retry logic
        raise
    except Exception as e:
        logger.error(f"Exception during malware scan: {e}")
        return scan_result_types.FILE_SCAN_FAILED


def parse_defender_scan_result(returncode, output):
    """
    Process Microsoft Defender scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        
    Returns:
        int: scan_result_types value
    """
    logger = get_logger()
    
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


def scan_for_malware_using_defender(path, config=None):
    """
    Scan a file using Microsoft Defender with retry logic for timeouts.
    
    Args:
        path (str): Path to the file to scan
        config: CommonConfig object with timeout settings
        
    Returns:
        Scan result or raises ScanTimeoutError after all retries
    """
    cmd = [
        DEFENDER_COMMAND,
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path"
    ]
    
    # Get timeout settings from config (config defaults are already set in CommonConfig)
    base_timeout = config.malware_scan_timeout_seconds if config else 300
    ms_per_byte = config.malware_scan_timeout_ms_per_byte if config else 0.0
    retry_wait = config.malware_scan_retry_wait_seconds if config else 30
    retry_count = config.malware_scan_retry_count if config else 3
    
    logger = get_logger()
    
    # Calculate dynamic timeout based on file size
    timeout = calculate_dynamic_timeout(path, base_timeout, ms_per_byte)
        
    # If retry_count is 0, use unlimited retries
    attempt = 0
    while True:
        try:
            return run_malware_scan(cmd, path, parse_defender_scan_result, timeout)
        except ScanTimeoutError:
            attempt += 1
            
            # Check if we should retry
            if retry_count > 0 and attempt >= retry_count:
                logger.error(f"Defender scan timeout after {retry_count} attempts for {path}")
                raise
            
            # Log retry attempt
            if retry_count > 0:
                logger.warning(f"Defender scan timeout on attempt {attempt}/{retry_count} for {path}")
            else:
                logger.warning(f"Defender scan timeout on attempt {attempt} (unlimited retries) for {path}")
            
            # Wait before retry (unless wait time is 0)
            if retry_wait > 0:
                logger.debug(f"Waiting {retry_wait}s before retry")
                time.sleep(retry_wait)

def handle_clamav_scan_result(returncode, output):
    """
    Process ClamAV scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        
    Returns:
        int: scan_result_types value
    """
    logger = get_logger()
    
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


def scan_for_malware_using_clam_av(path, config=None):
    """
    Scan a file using ClamAV with retry logic for timeouts.
    
    Args:
        path (str): Path to the file to scan
        config: CommonConfig object with timeout settings
        
    Returns:
        Scan result or raises ScanTimeoutError after all retries
    """
    cmd = [
        "clamdscan",
        "--fdpass"  # temp until permissions issues resolved
    ]
    
    # Get timeout settings from config (config defaults are already set in CommonConfig)
    base_timeout = config.malware_scan_timeout_seconds if config else 300
    ms_per_byte = config.malware_scan_timeout_ms_per_byte if config else 0.0
    retry_wait = config.malware_scan_retry_wait_seconds if config else 30
    retry_count = config.malware_scan_retry_count if config else 3
    
    logger = get_logger()
    
    # Calculate dynamic timeout based on file size
    timeout = calculate_dynamic_timeout(path, base_timeout, ms_per_byte)
        
    # If retry_count is 0, use unlimited retries
    attempt = 0
    while True:
        try:
            return run_malware_scan(cmd, path, handle_clamav_scan_result, timeout)
        except ScanTimeoutError:
            attempt += 1
            
            # Check if we should retry
            if retry_count > 0 and attempt >= retry_count:
                logger.error(f"ClamAV scan timeout after {retry_count} attempts for {path}")
                raise
            
            # Log retry attempt
            if retry_count > 0:
                logger.warning(f"ClamAV scan timeout on attempt {attempt}/{retry_count} for {path}")
            else:
                logger.warning(f"ClamAV scan timeout on attempt {attempt} (unlimited retries) for {path}")
            
            # Wait before retry (unless wait time is 0)
            if retry_wait > 0:
                logger.debug(f"Waiting {retry_wait}s before retry")
                time.sleep(retry_wait)
