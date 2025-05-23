#!/usr/bin/env python3
"""Integration test for Shuttle using the MDATP simulator

This test:
1. Sets up a temporary directory structure (source, destination, quarantine)
2. Places test files in the source directory (including one that will be detected as malware)
3. Runs shuttle with the simulator via the run_shuttle_with_simulator.py script
4. Verifies the files are correctly processed based on scan results
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess
import datetime
import random
import string
from unittest.mock import patch

# Add the required directories to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

class TestShuttleWithSimulator(unittest.TestCase):
    """Test the Shuttle application with MDATP simulator"""
    
    def setUp(self):
        """Set up temporary directories and files for testing"""
        # Create temporary directories in SHUTTLE_WORK_DIR/tmp
        work_dir = os.environ.get('SHUTTLE_WORK_DIR', os.path.expanduser('~/shuttle/work'))
        tmp_base = os.path.join(work_dir, 'tmp')
        os.makedirs(tmp_base, exist_ok=True)
        
        # Create a unique test directory with timestamp and random suffix
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        self.temp_dir = os.path.join(tmp_base, f'test_{timestamp}_{random_suffix}')        
        os.makedirs(self.temp_dir, exist_ok=True)
        self.source_dir = os.path.join(self.temp_dir, 'source')
        self.destination_dir = os.path.join(self.temp_dir, 'destination')
        self.quarantine_dir = os.path.join(self.temp_dir, 'quarantine')
        self.hazard_dir = os.path.join(self.temp_dir, 'hazard')
        
        os.makedirs(self.source_dir)
        os.makedirs(self.destination_dir)
        os.makedirs(self.quarantine_dir)
        os.makedirs(self.hazard_dir)
        
        # Create test files
        self.clean_file = os.path.join(self.source_dir, 'clean_file.txt')
        self.malware_file = os.path.join(self.source_dir, 'malware_file.txt')
        
        with open(self.clean_file, 'w') as f:
            f.write('This is a clean file')
        
        with open(self.malware_file, 'w') as f:
            f.write('This file should be detected as malware')
        
        # Path to the run_shuttle_with_simulator.py script
        self.simulator_runner = os.path.join(os.path.dirname(__file__), 'run_shuttle_with_simulator.py')
        
        # Path to a lock file in the temp directory
        self.lock_file = os.path.join(self.temp_dir, 'shuttle.lock')
    
    def tearDown(self):
        """Clean up temporary directories after the test"""
        # Remove lock file if it exists
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
        
        # Remove temp directory
        shutil.rmtree(self.temp_dir)
    
    def test_shuttle_with_simulator(self):
        """Test the full Shuttle workflow with the simulator"""
        # Build command to run shuttle with the simulator
        cmd = [
            sys.executable,  # Use the current Python interpreter
            self.simulator_runner,
            '-SourcePath', self.source_dir,
            '-DestinationPath', self.destination_dir,
            '-QuarantinePath', self.quarantine_dir,
            '-HazardArchivePath', self.hazard_dir,
            '-OnDemandDefender',  # Boolean flag, presence means True
            # Note: Omitting -OnDemandClamAV flag to keep it False
            '-LogPath', self.temp_dir,
            '-LockFile', self.lock_file
        ]
        
        # Run the command and stream output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Collect output while streaming it to console
        output_lines = []
        print("\n--- Shuttle Output Begin ---")
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            print(line, end='')  # Display in real-time
            output_lines.append(line)
        print("--- Shuttle Output End ---\n")
        
        # Close stdout and get return code
        process.stdout.close()
        return_code = process.wait()
        
        # Join all output for error reporting if needed
        output = ''.join(output_lines)
        
        # Check that the process ran successfully
        self.assertEqual(return_code, 0, 
                        f"Process failed with code {return_code}\nOutput: {output}")
            
        # Verify the clean file was moved to destination
        dest_clean_file = os.path.join(self.destination_dir, 'clean_file.txt')
        self.assertTrue(os.path.exists(dest_clean_file), 
                        f"Clean file was not moved to destination: {dest_clean_file}")
        
        # Verify the malware file was NOT moved to destination
        dest_malware_file = os.path.join(self.destination_dir, 'malware_file.txt')
        self.assertFalse(os.path.exists(dest_malware_file), 
                        f"Malware file was incorrectly moved to destination: {dest_malware_file}")
        
        # Verify the malware file was properly handled and not mishandled
        # Check that malware is not present in its original form in either quarantine or hazard
        quarantine_malware = os.path.join(self.quarantine_dir, 'malware_file.txt')
        hazard_malware = os.path.join(self.hazard_dir, 'malware_file.txt')
        
        malware_mishandled = os.path.exists(quarantine_malware) or os.path.exists(hazard_malware)
        self.assertFalse(malware_mishandled,
                         f"Malware file was mishandled - found in original form in quarantine or hazard")
        
        # Note: In a complete test, we would also verify that:
        # 1. The malware was properly archived in encrypted form in the hazard directory
        # 2. Appropriate logs were generated
        # 3. Notifications were sent if configured

if __name__ == '__main__':
    unittest.main()
