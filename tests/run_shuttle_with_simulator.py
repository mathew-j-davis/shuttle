#!/usr/bin/env python3
"""
Simple script to run Shuttle with MDATP simulator

This script:
1. Patches the DEFAULT_DEFENDER_COMMAND to use the simulator
2. Passes any arguments to shuttle.main()

Usage:
  python run_shuttle_with_simulator.py [shuttle arguments]
  
Examples:
  python run_shuttle_with_simulator.py --source-path /path/to/source --destination-path /path/to/destination
"""

import os
import sys
from unittest.mock import patch

# Add the required directories to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'tests', 'mdatp_simulator_app'))

# Import the simulator module to get its path
import mdatp_simulator

# Import shuttle main function
from shuttle_app.shuttle.shuttle import main

def run_shuttle_with_simulator():
    """Run shuttle.main() with the MDATP simulator"""
    # Get the path to the simulator script
    simulator_module = os.path.dirname(mdatp_simulator.__file__)
    simulator_script = os.path.join(simulator_module, 'simulator.py')
    
    # Make sure the simulator script is executable
    os.chmod(simulator_script, 0o755)
    
    # Path to the simulator ledger file that approves version 0.0.0.0
    simulator_ledger = os.path.join(os.path.dirname(__file__), 'simulator_ledger.yaml')
    
    # Add ledger path to arguments if not already specified
    if '--ledger-path' not in sys.argv and '--ledger-path' not in sys.argv:
        sys.argv.extend(['--ledger-path', simulator_ledger])
        
    # Add skip-stability-check flag for tests
    sys.argv.append('--skip-stability-check')
    
    # Patch the DEFAULT_DEFENDER_COMMAND to use the simulator script
    with patch('shuttle_common.scan_utils.DEFENDER_COMMAND', simulator_script):
        try:
            # Run the main function, passing any command line args
            main()
        except SystemExit as e:
            # main() calls sys.exit(), which we catch to get the exit code
            sys.exit(e.code)

if __name__ == '__main__':
    run_shuttle_with_simulator()
