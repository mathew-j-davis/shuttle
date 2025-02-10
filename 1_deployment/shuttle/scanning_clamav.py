import logging
import subprocess
import types
from .scanning import run_malware_scan, scan_result_types

clamav_parse_response_patterns = types.SimpleNamespace()
clamav_parse_response_patterns.ERROR = "^ERROR"
clamav_parse_response_patterns.TOTAL_ERRORS = "Total errors: "
clamav_parse_response_patterns.THREAT_FOUND = "FOUND\n\n"
clamav_parse_response_patterns.OK = "^OK\n"
clamav_parse_response_patterns.NO_THREATS = "Infected files: 0"

def handle_clamav_scan_result(returncode, output):
    """
    Process ClamAV scan results.
    
    Args:
        returncode (int): Process return code
        output (str): Process output
        
    Returns:
        int: scan_result_types value
    """
    logger = logging.getLogger('shuttle')
    
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


def scan_for_malware_using_clam_av(path):
    """Scan a file using ClamAV."""
    cmd = [
        "clamdscan",
        "--fdpass",  # temp until permissions issues resolved
        path
    ]
    return run_malware_scan(cmd, path, handle_clamav_scan_result)
