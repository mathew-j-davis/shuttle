#!/usr/bin/env python3
"""
Test script that redirects mdatp calls to the actual mdatp-simulator executable.

This test patches the DEFAULT_DEFENDER_COMMAND to point to the simulator
and then calls the real get_mdatp_version function to get a response from
the actual simulator, not a mock.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Add the Shuttle source directory to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

# Add the simulator directory to the path
sys.path.insert(0, os.path.join(project_root, 'tests', 'mdatp_simulator_app'))

# Import the simulator module to get its path
import mdatp_simulator

# Import the function we want to test
from shuttle_common.scan_utils import get_mdatp_version, scan_for_malware_using_defender, scan_result_types

class TestMDATPSimulatorRedirection(unittest.TestCase):
    """Test that redirects mdatp to the actual simulator executable"""
    
    def setUp(self):
        """Set up test paths"""
        self.test_dir = os.path.join(os.path.dirname(__file__), 'mdatp_simulator_test_files')
        self.clean_file = os.path.join(self.test_dir, 'clear.txt')
        self.malware_file = os.path.join(self.test_dir, 'flag_as_malware.txt')
        self.nonexistent_file = os.path.join(self.test_dir, 'file-does-not-exist.txt')
        
        # Get the path to the simulator script
        simulator_module = os.path.dirname(mdatp_simulator.__file__)
        self.simulator_script = os.path.join(simulator_module, 'simulator.py')
        
        # Make sure the simulator script is executable
        os.chmod(self.simulator_script, 0o755)
        
        # Create test files if needed
        os.makedirs(self.test_dir, exist_ok=True)
        if not os.path.exists(self.clean_file):
            with open(self.clean_file, 'w') as f:
                f.write('This is a clean file')
        if not os.path.exists(self.malware_file):
            with open(self.malware_file, 'w') as f:
                f.write('This file should be flagged as malware')
    
    def test_version_redirect(self):
        """Test redirecting get_mdatp_version to use the simulator"""
        
        # Patch the DEFAULT_DEFENDER_COMMAND to use our simulator script
        with patch('shuttle_common.scan_utils.DEFAULT_DEFENDER_COMMAND', self.simulator_script):
            # Call get_mdatp_version (without simulator flag)
            version = get_mdatp_version()
            
            # Check that we got the version from the simulator
            self.assertEqual(version, "0.0.0.0")
            
    def test_scan_redirect(self):
        """Test redirecting scan_for_malware_using_defender to use the simulator"""
        
        # Skip scan tests if there are problems with the test environment
        if not os.path.exists(self.simulator_script):
            self.skipTest("Simulator script not found")
            
        # Patch the DEFAULT_DEFENDER_COMMAND to use our simulator script  
        with patch('shuttle_common.scan_utils.DEFAULT_DEFENDER_COMMAND', self.simulator_script):
            # Test scanning a clean file
            result = scan_for_malware_using_defender(self.clean_file)
            self.assertEqual(result, scan_result_types.FILE_IS_CLEAN)
            
            # Test scanning a malware file
            result = scan_for_malware_using_defender(self.malware_file)
            self.assertEqual(result, scan_result_types.FILE_IS_SUSPECT)
            
            # Test scanning a non-existent file
            result = scan_for_malware_using_defender(self.nonexistent_file)
            self.assertEqual(result, scan_result_types.FILE_NOT_FOUND)

if __name__ == '__main__':
    unittest.main()
