#!/usr/bin/env python3
"""
MDATP Simulator

This module simulates the Microsoft Defender for Endpoint (MDATP) command-line interface
for testing purposes. It responds to the same commands as the real mdatp tool but with
simulated behavior.

IMPORTANT: This is for development and testing only.
           DO NOT use in production environments.
"""

import sys
import os
import re
import argparse
import time
import random
from datetime import datetime
# Import the config module (use absolute import for command-line execution)
from mdatp_simulator.config import read_delay_config, apply_simulated_delay

VERSION = "0.0.0.0"

# Read delay configuration
MIN_DELAY_MS, MAX_DELAY_MS = read_delay_config()

# Flag to indicate if we've already logged delay info
DELAY_INFO_LOGGED = False

def log_delay_info():
    """
    Log information about the configured delay
    """
    global DELAY_INFO_LOGGED
    
    if not DELAY_INFO_LOGGED:
        if MIN_DELAY_MS > 0 or MAX_DELAY_MS > 0:
            print(f"SIMULATOR: Using random delay between {MIN_DELAY_MS}-{MAX_DELAY_MS} ms", file=sys.stderr)
        DELAY_INFO_LOGGED = True

def version_command():
    """
    Simulate the 'mdatp version' command
    """
    # Apply configured delay
    apply_simulated_delay(MIN_DELAY_MS, MAX_DELAY_MS)
    log_delay_info()
    
    print(f"Product version: {VERSION}")
    print("Engine version: SIMULATOR.ONLY.DO.NOT.USE")
    print("Anti-virus definition version: SIMULATOR.ONLY.DO.NOT.USE")
    print("Anti-virus engine type: SIMULATOR.ONLY.DO.NOT.USE")
    return 0

def scan_command(args):
    """
    Simulate the 'mdatp scan' command
    Flags any file matching EICAR*.TXT pattern as malware
    """
    # Apply configured delay
    apply_simulated_delay(MIN_DELAY_MS, MAX_DELAY_MS)
    log_delay_info()
    parser = argparse.ArgumentParser(description='Scan files for threats')
    parser.add_argument('scan_type', help='Scan type (custom, quick, full)')
    parser.add_argument('--ignore-exclusions', action='store_true', help='Ignore exclusions')
    parser.add_argument('--path', help='Path to scan')
    
    try:
        scan_args = parser.parse_args(args)
    except:
        print("Invalid arguments for scan command")
        return 1
    
    if not scan_args.path:
        print("Error: No path specified")
        return 1
    
    path = scan_args.path
    
    # Check if path exists
    if not os.path.exists(path):
        # For non-existent files, still return success (0) but with specific output pattern
        # that parse_defender_scan_result will recognize as FILE_NOT_FOUND
        print(f"Error: Path does not exist: {path}")
        # Match the FILE_NOT_FOUND pattern exactly as in scan_utils.py
        print("\n\t0 file(s) scanned\n\t0 threat(s) detected")
        return 0
    
    print(f"Starting {scan_args.scan_type} scan of {path}")
    
    # Simulate scanning time based on file size
    if os.path.isfile(path):
        size = os.path.getsize(path)
        # Simulate longer scan time for larger files (but keep it reasonable)
        sleep_time = min(0.5, size / 1000000)
        time.sleep(sleep_time)
        
        # Check for any file with eicar or malware in the name
        filename = os.path.basename(path)
        if 'eicar' in filename.lower() or 'malware' in filename.lower():
            # Must exactly match the pattern in defender_scan_patterns.THREAT_FOUND
            print("Scanning file: " + path)
            print("Threat detected!")
            print(f"Threat found: Test-Malware in {path}")
            print("Threat category: Test")
            print("Threat severity: High")
            print("Threat(s) found")
            
            # parse_defender_scan_result expects a zero return code even for malware detection (it uses the output text to determine result)
            return 0  # Return code for successful scan, even though threat was found
        else:
            print(f"Scanning file: {path}")
            print("No threats found.")
            # Must exactly end with pattern in defender_scan_patterns.NO_THREATS
            print("\n\t0 threat(s) detected")
            return 0
    else:
        # For directories, just pretend to scan and return success
        print(f"Scanning directory {path}...")
        time.sleep(1)
        print(f"No threats found in {path}")
        # Match the NO_THREATS pattern from scan_utils.py
        print("\n\t0 threat(s) detected")
        return 0

def status_command(args):
    """
    Simulate the 'mdatp status' command
    """
    # Apply configured delay
    apply_simulated_delay(MIN_DELAY_MS, MAX_DELAY_MS)
    log_delay_info()
    
    print("Microsoft Defender for Endpoint Simulator")
    print(f"Product version: {VERSION}")
    print("Real-time protection: SIMULATED")
    print("Cloud-delivered protection: SIMULATED")
    print("Automatic sample submission: SIMULATED")
    print("Tamper protection: SIMULATED")
    print("Antivirus passive mode: DISABLED")
    return 0

def main():
    """
    Main entry point - parse arguments and route to appropriate handler
    """
    if len(sys.argv) < 2:
        print("Error: No command specified")
        print("Usage: mdatp-simulator <command> [options]")
        print("Commands: version, scan, status")
        return 1
    
    command = sys.argv[1].lower()
    args = sys.argv[2:]
    
    if command == "version":
        return version_command()
    elif command == "scan":
        return scan_command(args)
    elif command == "status":
        return status_command(args)
    else:
        print(f"Error: Unknown command '{command}'")
        return 1

if __name__ == "__main__":
    sys.exit(main())
