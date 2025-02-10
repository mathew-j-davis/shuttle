import logging
import subprocess
from .config import scan_result_types, defender_scan_patterns
from .scanning import run_malware_scan

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

def scan_for_malware_using_defender(path):
    """Scan a file using Microsoft Defender."""
    cmd = [
        "mdatp",
        "scan",
        "custom",
        "--ignore-exclusions",
        "--path",
        path
    ]
    return run_malware_scan(cmd, path, handle_defender_scan_result)

