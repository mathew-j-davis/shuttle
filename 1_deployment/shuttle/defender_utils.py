"""
Microsoft Defender Utilities

This module provides utility functions for working with Microsoft Defender
that can be shared between the main application and test scripts.
"""

import subprocess
import logging
import re
from typing import Optional


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




if __name__ == "__main__":
    # Simple test if run directly
    version = get_mdatp_version()
    if version:
        print(f"Microsoft Defender version: {version}")
    else:
        print("Failed to get Microsoft Defender version")
