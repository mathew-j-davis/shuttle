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
  --mock-free-space-mb <MB>: Simulated free disk space in MB (default: 0, no mocking)
  --no-defender-simulator: Use real Microsoft Defender instead of the simulator

Examples:
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination --mock-free-space-mb 100
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

# Import shuttle classes
from shuttle_app.shuttle.shuttle import main, Shuttle
from shuttle_app.shuttle.throttler import Throttler
from shuttle_app.shuttle.daily_processing_tracker import DailyProcessingTracker

def parse_args():
    """Extract simulator and throttling arguments from command line"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mock-free-space-mb', type=float, default=None,
                        help='Simulated free disk space in MB (default: None, no mocking)')
    parser.add_argument('--no-defender-simulator', action='store_true',
                        help='Use real Microsoft Defender instead of the simulator')
    
    # Path-specific mock space parameters
    parser.add_argument('--mock-free-space-quarantine-mb', type=float, default=None,
                        help='Simulated free disk space for quarantine path in MB')
    parser.add_argument('--mock-free-space-destination-mb', type=float, default=None,
                        help='Simulated free disk space for destination path in MB')
    parser.add_argument('--mock-free-space-hazard-mb', type=float, default=None,
                        help='Simulated free disk space for hazard archive path in MB')
    
    # Parse known args and remove them from sys.argv
    args, remaining = parser.parse_known_args()
    
    # Remove our custom args from sys.argv so they don't interfere with shuttle args
    sys.argv = [sys.argv[0]] + remaining
    
    return args

def run_shuttle_with_simulator():
    """Run shuttle.main() with optional MDATP simulator and throttling"""
    # Parse arguments once at the top level
    args = parse_args()
    use_real_defender = args.no_defender_simulator
    
    # We'll access paths at runtime from Shuttle's configuration
    # instead of parsing them from command line arguments
    
    # Set up mock space values
    mock_free_space_mb = 0
    has_mock_default = False
    
    if args.mock_free_space_mb is not None and args.mock_free_space_mb > 0:
        has_mock_default = True
        mock_free_space_mb = args.mock_free_space_mb
    
    # Initialize path-specific mock values with defaults or specific values
    mock_free_space_quarantine_mb = 0
    mock_free_space_destination_mb = 0
    mock_free_space_hazard_mb = 0
    
    has_mock_quarantine = False
    has_mock_destination = False
    has_mock_hazard = False
    
    # If specific values are provided, use them; otherwise use default if available
    if args.mock_free_space_quarantine_mb is not None and args.mock_free_space_quarantine_mb > 0:
        mock_free_space_quarantine_mb = args.mock_free_space_quarantine_mb
        has_mock_quarantine = True
    elif has_mock_default:
        mock_free_space_quarantine_mb = mock_free_space_mb
        has_mock_quarantine = True
    
    if args.mock_free_space_destination_mb is not None and args.mock_free_space_destination_mb > 0:
        mock_free_space_destination_mb = args.mock_free_space_destination_mb
        has_mock_destination = True
    elif has_mock_default:
        mock_free_space_destination_mb = mock_free_space_mb
        has_mock_destination = True
    
    if args.mock_free_space_hazard_mb is not None and args.mock_free_space_hazard_mb > 0:
        mock_free_space_hazard_mb = args.mock_free_space_hazard_mb
        has_mock_hazard = True
    elif has_mock_default:
        mock_free_space_hazard_mb = mock_free_space_mb
        has_mock_hazard = True
    
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
    
    # Apply mocking if any mock space parameter is set
    if has_mock_quarantine or has_mock_destination or has_mock_hazard:
        print("\n>>> DISK SPACE MOCKING ENABLED <<<\n")
        if has_mock_default:
            print(f">>> Default mock space: {mock_free_space_mb} MB <<<")
        if has_mock_quarantine:
            print(f">>> Quarantine-specific mock space: {mock_free_space_quarantine_mb} MB <<<")
        if has_mock_destination:
            print(f">>> Destination-specific mock space: {mock_free_space_destination_mb} MB <<<")
        if has_mock_hazard:
            print(f">>> Hazard-specific mock space: {mock_free_space_hazard_mb} MB <<<")
        
        # Store original method for use in the mock
        Throttler._original_get_free_space_mb = Throttler.get_free_space_mb
        
        # Create a dynamic function for mocking disk space
        def mock_get_free_space_mb(directory_path):
            """Mock implementation that uses path-specific mock space values where specified,
            otherwise calls the original method"""
            # Access variables from outer scope
            nonlocal mock_free_space_quarantine_mb, mock_free_space_destination_mb, mock_free_space_hazard_mb
            nonlocal has_mock_quarantine, has_mock_destination, has_mock_hazard
            
            # Get the original method
            original_get_free_space = Throttler._original_get_free_space_mb
            
            # Normalize path for comparison
            norm_path = os.path.normpath(directory_path)
            
            # Create a Shuttle instance to access the configuration
            # We don't need to run the full application, just get the config
            shuttle_instance = Shuttle()
            
            # Get paths from Shuttle's configuration
            quarantine_path = shuttle_instance.get_quarantine_path()
            destination_path = shuttle_instance.get_destination_path()
            hazard_path = shuttle_instance.get_hazard_archive_path()
            
            # Log found paths for debugging
            print(f"\n>>> PATHS FROM SHUTTLE INSTANCE: Q:{quarantine_path}, D:{destination_path}, H:{hazard_path} <<<\n")
            
            # Normalize paths for comparison
            if quarantine_path:
                quarantine_path = os.path.normpath(quarantine_path)
            if destination_path:
                destination_path = os.path.normpath(destination_path)
            if hazard_path:
                hazard_path = os.path.normpath(hazard_path)
            
            # Check if there's a specific mock for this path
            if quarantine_path and norm_path == quarantine_path and has_mock_quarantine:
                # For quarantine path, subtract pending volume from the mock value
                # This simulates the real-world scenario where files are already copied to quarantine
                pending_volume = shuttle_instance.get_pending_volume()
                remaining_space = max(0, mock_free_space_quarantine_mb - pending_volume)

                print(f"\n>>> MOCK DISK SPACE CHECK FOR QUARANTINE: {directory_path} <<<")
                print(f">>> Mock free space: {mock_free_space_quarantine_mb} MB, Pending volume: {pending_volume:.2f} MB, Remaining: {remaining_space:.2f} MB <<<")
                return remaining_space
            
            elif destination_path and norm_path == destination_path and has_mock_destination:
                # For destination path, return raw mock value
                # Shuttle/Throttler will handle subtracting pending volume itself
                print(f"\n>>> MOCK DISK SPACE CHECK FOR DESTINATION: {directory_path} <<<")
                print(f">>> Mock free space: {mock_free_space_destination_mb} MB <<<")
                return mock_free_space_destination_mb
            
            elif hazard_path and norm_path == hazard_path and has_mock_hazard:
                # For hazard path, return raw mock value
                # Shuttle/Throttler will handle subtracting pending volume itself
                print(f"\n>>> MOCK DISK SPACE CHECK FOR HAZARD: {directory_path} <<<")
                print(f">>> Mock free space: {mock_free_space_hazard_mb} MB <<<")
                return mock_free_space_hazard_mb
            
            # For any other case, use the original method
            print(f"\n>>> NO MOCK SPECIFIED FOR PATH: {directory_path}, USING REAL DISK SPACE <<<")
            return original_get_free_space(directory_path)
        
        # Add mocking patcher for get_free_space_mb only
        patchers.append(patch.object(Throttler, 'get_free_space_mb', mock_get_free_space_mb))
    
    # Apply all patchers using a context manager stack
    with ExitStack() as stack:
        for patcher in patchers:
            stack.enter_context(patcher)
        
        try:
            # Create a Shuttle instance and run it
            shuttle = Shuttle()
            exit_code = shuttle.run()
            
            # Exit with the returned code
            sys.exit(exit_code)
        except SystemExit as e:
            # run() may call sys.exit(), which we catch to get the exit code
            sys.exit(e.code)

if __name__ == '__main__':
    run_shuttle_with_simulator()
