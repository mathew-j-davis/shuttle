"""
Test Shuttle with simulator using multiple files to test multithreading
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
import time
import argparse
from unittest.mock import patch

# Add the required directories to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'mdatp_simulator_app')))

class TestShuttleMultithreading(unittest.TestCase):
    """Test case for Shuttle multithreading with simulator"""
    
    # Default values for parameters that can be overridden via command line
    thread_count = 1
    clean_file_count = 20
    malware_file_count = 10
    file_size_kb = 100
    
    def setUp(self):
        """Set up the test environment"""
        # Create temporary directories in SHUTTLE_WORK_DIR/tmp
        work_dir = os.environ.get('SHUTTLE_WORK_DIR', os.path.expanduser('~/shuttle/work'))
        tmp_base = os.path.join(work_dir, 'tmp')
        os.makedirs(tmp_base, exist_ok=True)
        
        # Create a unique test directory with timestamp and random suffix
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        self.temp_dir = os.path.join(tmp_base, f'multithread_test_{timestamp}_{random_suffix}')        
        os.makedirs(self.temp_dir, exist_ok=True)
        self.source_dir = os.path.join(self.temp_dir, 'source')
        self.destination_dir = os.path.join(self.temp_dir, 'destination')
        self.quarantine_dir = os.path.join(self.temp_dir, 'quarantine')
        self.hazard_dir = os.path.join(self.temp_dir, 'hazard')
        
        os.makedirs(self.source_dir)
        os.makedirs(self.destination_dir)
        os.makedirs(self.quarantine_dir)
        os.makedirs(self.hazard_dir)
        
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
    
    def create_test_files(self, clean_count=5, malware_count=5, file_size_kb=10):
        """
        Create specified number of clean and malware test files
        
        Args:
            clean_count: Number of clean files to create
            malware_count: Number of malware files to create
            file_size_kb: Approximate size of each file in KB
        
        Returns:
            tuple: (list of clean files, list of malware files)
        """
        clean_files = []
        malware_files = []
        
        # Generate random data once and reuse
        random_data = ''.join(random.choices(string.ascii_letters + string.digits, 
                                           k=file_size_kb * 1024))
        
        # Create clean files
        for i in range(clean_count):
            filename = f'clean_file_{i:03d}.txt'
            filepath = os.path.join(self.source_dir, filename)
            with open(filepath, 'w') as f:
                f.write(random_data)
            clean_files.append(filepath)
        
        # Create malware files (containing the word "malware" to trigger detection)
        for i in range(malware_count):
            filename = f'malware_file_{i:03d}.txt'
            filepath = os.path.join(self.source_dir, filename)
            with open(filepath, 'w') as f:
                # Insert "malware" string in the middle of the data to trigger detection
                midpoint = len(random_data) // 2
                malware_data = random_data[:midpoint] + "malware" + random_data[midpoint:]
                f.write(malware_data)
            malware_files.append(filepath)
        
        return clean_files, malware_files

    def test_shuttle_multithreading(self):
        """Test Shuttle with multiple files to check multithreading"""
        # Create files based on command line args or defaults
        clean_files, malware_files = self.create_test_files(
            self.clean_file_count, 
            self.malware_file_count, 
            file_size_kb=self.file_size_kb
        )
        
        print(f"Created {len(clean_files)} clean files and {len(malware_files)} malware files")
        
        # Build command to run shuttle with the simulator
        cmd = [
            sys.executable,  # Use the current Python interpreter
            self.simulator_runner,
            '-SourcePath', self.source_dir,
            '-DestinationPath', self.destination_dir,
            '-QuarantinePath', self.quarantine_dir,
            '-HazardArchivePath', self.hazard_dir,
            '-OnDemandDefender',  # Boolean flag, presence means True
            '-MaxScanThreads', str(self.thread_count),  # Thread count from command line
            '-LogPath', self.temp_dir,
            '-LockFile', self.lock_file
        ]
        
        # Record start time
        start_time = time.time()
        
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
        
        # Record end time
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Join all output for error reporting if needed
        output = ''.join(output_lines)
        
        # Check that the process ran successfully
        self.assertEqual(return_code, 0, 
                        f"Process failed with code {return_code}\nOutput: {output}")
        
        print(f"Processing completed in {elapsed_time:.2f} seconds")
        
        # Verify clean files were moved to destination
        clean_file_count = 0
        for filename in os.listdir(self.destination_dir):
            if filename.startswith('clean_file_'):
                clean_file_count += 1
        
        # Verify malware files are not in destination
        malware_file_count = 0
        for filename in os.listdir(self.destination_dir):
            if filename.startswith('malware_file_'):
                malware_file_count += 1
        
        # Verify counts match expectations
        self.assertEqual(clean_file_count, len(clean_files), 
                         f"Expected {len(clean_files)} clean files in destination, found {clean_file_count}")
        self.assertEqual(malware_file_count, 0, 
                         f"Expected 0 malware files in destination, found {malware_file_count}")
        
        # Check hazard directory if configured
        hazard_file_count = len(os.listdir(self.hazard_dir))
        print(f"Files in hazard directory: {hazard_file_count}")
        
        # Additional detailed verification could be added here
        # ...

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test Shuttle multithreading with configurable parameters')
    parser.add_argument('--threads', type=int, default=1, help='Number of threads to use for scanning')
    parser.add_argument('--clean-files', type=int, default=20, help='Number of clean files to create')
    parser.add_argument('--malware-files', type=int, default=10, help='Number of malware files to create')
    parser.add_argument('--file-size', type=int, default=100, help='Size of test files in KB')
    return parser.parse_args()

if __name__ == '__main__':
    # Parse command line args before unittest runs
    args = parse_args()
    
    # Store args in global variables that test can access
    # This is a bit of a hack, but it works for a test script
    TestShuttleMultithreading.thread_count = args.threads
    TestShuttleMultithreading.clean_file_count = args.clean_files
    TestShuttleMultithreading.malware_file_count = args.malware_files
    TestShuttleMultithreading.file_size_kb = args.file_size
    
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'])
