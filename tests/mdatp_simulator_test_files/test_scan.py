#!/usr/bin/env python3
import os
import sys
import subprocess
from shared_library.shuttle_common.scan_utils import scan_for_malware_using_defender, DEFENDER_COMMAND

# Override the DEFAULT_DEFENDER_COMMAND with path to simulator
simulator_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mdatp_simulator_app', 'mdatp_simulator', 'simulator.py'))
os.environ['DEFENDER_COMMAND'] = simulator_path

# Patch the scan function to use our environment variable
def patched_scan(*args, **kwargs):
    cmd = [os.environ.get('DEFENDER_COMMAND', DEFENDER_COMMAND)]
    cmd.extend(args[0][1:])  # Skip the first element (normally mdatp) and add the rest
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result

# Apply the patch and run the scan
with patch('subprocess.run', side_effect=patched_scan):
    # Get arguments from command line
    if len(sys.argv) < 2:
        print("Usage: test_scan.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    result = scan_for_malware_using_defender(file_path)
    print(f"Scan result: {result}")
    sys.exit(0)
