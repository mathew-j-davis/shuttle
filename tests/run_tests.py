#!/usr/bin/env python3
"""
Test runner script for Shuttle.
Discovers and runs all tests in the tests directory.
"""

import unittest
import sys
import os

if __name__ == '__main__':
    # Add parent directory to path to make imports work
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Discover all tests in the current directory
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(os.path.dirname(__file__))
    
    # Run tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())
