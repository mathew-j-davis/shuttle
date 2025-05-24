"""
Test Shuttle throttling with simulator by creating a test with minimal free space
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

class TestShuttleThrottling(unittest.TestCase):
    """Test case for Shuttle throttling with simulator"""
    
    # Default values for parameters that can be overridden via command line
    thread_count = 1
    clean_file_count = 5
    malware_file_count = 2
    file_size_mb = 10  # Default file size in MB
    throttle_free_space = 100  # Default minimum free space in MB
    
    def setUp(self):
        """Set up the test environment"""
        # Create temporary directories in SHUTTLE_WORK_DIR/tmp
        work_dir = os.environ.get('SHUTTLE_WORK_DIR', os.path.expanduser('~/shuttle/work'))
        tmp_base = os.path.join(work_dir, 'tmp')
        os.makedirs(tmp_base, exist_ok=True)
        
        # Create a unique test directory with timestamp and random suffix
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        self.temp_dir = os.path.join(tmp_base, f'throttle_test_{timestamp}_{random_suffix}')        
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
    
    def create_test_files(self, clean_count=5, malware_count=2, file_size_mb=10):
        """
        Create specified number of clean and malware test files
        
        Args:
            clean_count: Number of clean files to create
            malware_count: Number of malware files to create
            file_size_mb: Approximate size of each file in MB
        
        Returns:
            tuple: (list of clean files, list of malware files)
        """
        clean_files = []
        malware_files = []
        
        # Calculate size in bytes
        file_size_bytes = file_size_mb * 1024 * 1024
        
        # Generate random data once and reuse
        # This approach uses less memory than generating all the data at once
        chunk_size = min(file_size_bytes, 1024 * 1024)  # Use 1MB chunks
        random_chunk = ''.join(random.choices(string.ascii_letters + string.digits, k=chunk_size))
        
        # Create clean files
        for i in range(clean_count):
            filename = f'clean_file_{i:03d}.dat'
            filepath = os.path.join(self.source_dir, filename)
            with open(filepath, 'w') as f:
                remaining_size = file_size_bytes
                while remaining_size > 0:
                    write_size = min(remaining_size, chunk_size)
                    f.write(random_chunk[:write_size])
                    remaining_size -= write_size
            clean_files.append(filepath)
            print(f"Created clean file {filepath} ({file_size_mb} MB)")
        
        # Create malware files (containing the word "malware" to trigger detection)
        for i in range(malware_count):
            filename = f'malware_file_{i:03d}.dat'
            filepath = os.path.join(self.source_dir, filename)
            with open(filepath, 'w') as f:
                remaining_size = file_size_bytes
                # First write half the file
                half_size = remaining_size // 2
                while half_size > 0:
                    write_size = min(half_size, chunk_size)
                    f.write(random_chunk[:write_size])
                    half_size -= write_size
                
                # Write the malware signature
                f.write("malware")
                remaining_size -= (remaining_size // 2 + len("malware"))
                
                # Write the rest of the file
                while remaining_size > 0:
                    write_size = min(remaining_size, chunk_size)
                    f.write(random_chunk[:write_size])
                    remaining_size -= write_size
            
            malware_files.append(filepath)
            print(f"Created malware file {filepath} ({file_size_mb} MB)")
        
        return clean_files, malware_files
    
    def get_disk_space_info(self, directory):
        """Get disk space information for a directory"""
        stats = shutil.disk_usage(directory)
        total_mb = stats.total / (1024 * 1024)
        used_mb = stats.used / (1024 * 1024)
        free_mb = stats.free / (1024 * 1024)
        return {
            'total_mb': total_mb,
            'used_mb': used_mb,
            'free_mb': free_mb
        }
    
    def test_shuttle_throttling(self):
        """Test Shuttle throttling with a low free space setting"""
        # Create files based on command line args or defaults
        clean_files, malware_files = self.create_test_files(
            self.clean_file_count, 
            self.malware_file_count, 
            file_size_mb=self.file_size_mb
        )
        
        print(f"Created {len(clean_files)} clean files ({self.file_size_mb} MB each) "
              f"and {len(malware_files)} malware files ({self.file_size_mb} MB each)")
        
        # Get free space information before the test
        source_space = self.get_disk_space_info(self.source_dir)
        dest_space = self.get_disk_space_info(self.destination_dir)
        
        print(f"Source directory free space: {source_space['free_mb']:.2f} MB")
        print(f"Destination directory free space: {dest_space['free_mb']:.2f} MB")
        print(f"Setting throttle free space to: {self.throttle_free_space} MB")
        
        # Build command to run shuttle with the simulator and throttling
        cmd = [
            sys.executable,  # Use the current Python interpreter
            self.simulator_runner,
            '--source-path', self.source_dir,
            '--destination-path', self.destination_dir,
            '--quarantine-path', self.quarantine_dir,
            '--hazard-archive-path', self.hazard_dir,
            '--on-demand-defender',  # Boolean flag, presence means True
            '--skip-stability-check',  # Boolean flag, presence means True
            '--throttle',  # Enable throttling
            '--throttle-free-space', str(self.throttle_free_space),  # Set minimum free space
            '--max-scan-threads', str(self.thread_count),
            '--log-path', self.temp_dir,
            '--lock-file', self.lock_file
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
            output_lines.append(line.strip())
            print(line.strip())  # Print the line in real-time
        print("--- Shuttle Output End ---\n")
        
        # Wait for process to complete
        process.wait()
        
        # Record end time and calculate duration
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Execution time: {duration:.2f} seconds")
        
        # Get free space information after the test
        source_space_after = self.get_disk_space_info(self.source_dir)
        dest_space_after = self.get_disk_space_info(self.destination_dir)
        
        print(f"Source directory free space after: {source_space_after['free_mb']:.2f} MB")
        print(f"Destination directory free space after: {dest_space_after['free_mb']:.2f} MB")
        
        # Count files in destination and hazard directories
        dest_files = os.listdir(self.destination_dir)
        hazard_files = os.listdir(self.hazard_dir)
        
        print(f"Files in destination directory: {len(dest_files)}")
        print(f"Files in hazard directory: {len(hazard_files)}")
        
        # Check if throttling message appeared in the output
        throttle_messages = [line for line in output_lines if "throttling" in line.lower()]
        if throttle_messages:
            print("Throttling messages found in output:")
            for msg in throttle_messages:
                print(f"  {msg}")
        else:
            print("No throttling messages found in output")
        
        # Analyze if throttling worked as expected
        if self.throttle_free_space > dest_space['free_mb']:
            # We should expect throttling to have occurred
            self.assertTrue(any("throttling" in line.lower() for line in output_lines),
                           "Throttling should have occurred but no throttling messages found")
            self.assertEqual(0, len(dest_files),
                           "No files should have been moved to destination due to throttling")
        else:
            # We should expect all clean files to be processed
            self.assertEqual(len(clean_files), len(dest_files),
                           "All clean files should have been moved to destination")
            self.assertEqual(len(malware_files), len(hazard_files),
                           "All malware files should have been moved to hazard directory")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Shuttle throttling with varying parameters')
    parser.add_argument('--threads', type=int, default=1,
                        help='Number of threads to use (default: 1)')
    parser.add_argument('--clean-files', type=int, default=5,
                        help='Number of clean files to create (default: 5)')
    parser.add_argument('--malware-files', type=int, default=2,
                        help='Number of malware files to create (default: 2)')
    parser.add_argument('--file-size', type=int, default=10,
                        help='Size of each file in MB (default: 10)')
    parser.add_argument('--throttle-space', type=int, default=100,
                        help='Minimum free space in MB for throttling (default: 100)')
    
    args = parser.parse_args()
    
    # Set class variables from command line arguments
    TestShuttleThrottling.thread_count = args.threads
    TestShuttleThrottling.clean_file_count = args.clean_files
    TestShuttleThrottling.malware_file_count = args.malware_files
    TestShuttleThrottling.file_size_mb = args.file_size
    TestShuttleThrottling.throttle_free_space = args.throttle_space
    
    unittest.main(argv=['first-arg-is-ignored'])
