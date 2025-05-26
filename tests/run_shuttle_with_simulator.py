#!/usr/bin/env python3
"""
Simple script to run Shuttle with MDATP simulator and optional throttling

This script:
1. Optionally patches the DEFAULT_DEFENDER_COMMAND to use the simulator
2. Optionally patches Throttler methods for disk space simulation
3. Passes any arguments to shuttle.main()

Usage:
  python run_shuttle_with_simulator.py [shuttle arguments] [throttling arguments]
  
Optional arguments:
  --mock-free-space <MB>: Simulated free disk space in MB (default: 0, no mocking)
  --no-defender-simulator: Use real Microsoft Defender instead of the simulator

Examples:
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination --mock-free-space 100
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination --no-defender-simulator
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

def parse_args():
    """Extract simulator and throttling arguments from command line"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mock-free-space', type=float, default=0,
                        help='Simulated free disk space in MB (default: 0, no mocking)')
    parser.add_argument('--no-defender-simulator', action='store_true',
                        help='Use real Microsoft Defender instead of the simulator')
    
    # Parse known args and remove them from sys.argv
    args, remaining = parser.parse_known_args()
    
    # Remove our custom args from sys.argv so they don't interfere with shuttle args
    sys.argv = [sys.argv[0]] + remaining
    
    return args

def run_shuttle_with_simulator():
    """Run shuttle.main() with optional MDATP simulator and throttling"""
    # Parse arguments
    args = parse_args()
    mock_free_space = args.mock_free_space
    use_real_defender = args.no_defender_simulator
    
    # Initialize patchers list
    patchers = []
    
    # Set up simulator if not using real defender
    if not use_real_defender:
        print("\n>>> USING MDATP SIMULATOR <<<\n")
        
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
        
        # Add simulator patcher
        patchers.append(patch('shuttle_common.scan_utils.DEFENDER_COMMAND', simulator_script))
    else:
        print("\n>>> USING REAL MICROSOFT DEFENDER <<<\n")
        
        # Verify that real Defender is available
        try:
            import subprocess
            result = subprocess.run(['mdatp', '--version'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  text=True)
            if result.returncode != 0:
                print("WARNING: Microsoft Defender does not appear to be installed or functioning")
                print(f"Error: {result.stderr}")
                print("Proceeding anyway, but tests may fail")
            else:
                print(f"Detected Microsoft Defender version: {result.stdout.strip()}")
        except Exception as e:
            print(f"WARNING: Error checking Microsoft Defender: {e}")
            print("Proceeding anyway, but tests may fail")
    
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
