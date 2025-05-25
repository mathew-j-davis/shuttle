#!/usr/bin/env python3
"""
Simple script to run Shuttle with MDATP simulator and optional throttling

This script:
1. Patches the DEFAULT_DEFENDER_COMMAND to use the simulator
2. Optionally patches Throttler methods for disk space simulation
3. Passes any arguments to shuttle.main()

Usage:
  python run_shuttle_with_simulator.py [shuttle arguments] [throttling arguments]
  
Throttling arguments:
  --mock-free-space <MB>: Simulated free disk space in MB (default: 0, no mocking)

Examples:
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination --mock-free-space 100
"""

import os
import sys
import argparse
from unittest.mock import patch
from contextlib import ExitStack

# Add the required directories to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'tests', 'mdatp_simulator_app'))

# Import the simulator module to get its path
import mdatp_simulator

# Import shuttle main function and Throttler
from shuttle_app.shuttle.shuttle import main
from shuttle_app.shuttle.throttler import Throttler

def parse_throttling_args():
    """Extract throttling arguments from command line"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mock-free-space', type=float, default=0)
    
    # Parse known args and remove them from sys.argv
    args, remaining = parser.parse_known_args()
    
    # Remove the throttling args from sys.argv
    sys.argv = [sys.argv[0]] + remaining
    
    return args

def run_shuttle_with_simulator():
    """Run shuttle.main() with the MDATP simulator and optional throttling"""
    # Parse throttling arguments
    throttling_args = parse_throttling_args()
    mock_free_space = throttling_args.mock_free_space
    
    # Get the path to the simulator script
    simulator_module = os.path.dirname(mdatp_simulator.__file__)
    simulator_script = os.path.join(simulator_module, 'simulator.py')
    
    # Make sure the simulator script is executable
    os.chmod(simulator_script, 0o755)
    
    # Path to the simulator ledger file that approves version 0.0.0.0
    simulator_ledger = os.path.join(os.path.dirname(__file__), 'simulator_ledger.yaml')
    
    # Add ledger path to arguments if not already specified
    if '--ledger-path' not in sys.argv:
        sys.argv.extend(['--ledger-path', simulator_ledger])
        
    # Add skip-stability-check flag for tests
    if '--skip-stability-check' not in sys.argv:
        sys.argv.append('--skip-stability-check')
    
    # Patchers to use
    patchers = [patch('shuttle_common.scan_utils.DEFENDER_COMMAND', simulator_script)]
    
    # Only set up throttling if mock_free_space is specified
    if mock_free_space > 0:
        print(f"\n>>> THROTTLING: Simulating {mock_free_space} MB free disk space <<<\n")
        
        # Create a dynamic function for mocking disk space
        def mock_get_free_space_mb(directory_path):
            """Mock implementation that returns simulated free space minus files already processed"""
            # Calculate total size of files in the directory
            total_size_mb = 0
            if os.path.exists(directory_path):
                for filename in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, filename)
                    if os.path.isfile(file_path):
                        # Get file size in MB
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        total_size_mb += file_size_mb
            
            # Calculate remaining space by subtracting processed files from initial mock space
            remaining_space = max(0, mock_free_space - total_size_mb)
            print(f"\n>>> MOCK DISK SPACE CHECK FOR: {directory_path} <<<")
            print(f">>> Initial free space: {mock_free_space} MB, Used: {total_size_mb:.2f} MB, Remaining: {remaining_space:.2f} MB <<<")
            return remaining_space
        
        # Don't patch check_directory_space since it calls get_free_space_mb
        # which we've already patched with our dynamic implementation
        
        # Add throttling patcher for get_free_space_mb only
        patchers.append(patch.object(Throttler, 'get_free_space_mb', mock_get_free_space_mb))
    
    # Apply all patchers using a context manager stack
    with ExitStack() as stack:
        for patcher in patchers:
            stack.enter_context(patcher)
        
        try:
            # Run the main function, passing any command line args
            main()
        except SystemExit as e:
            # main() calls sys.exit(), which we catch to get the exit code
            sys.exit(e.code)

if __name__ == '__main__':
    run_shuttle_with_simulator()
