#!/usr/bin/env python3

import sys
from test_shuttle_multithreaded import TestShuttleMultithreaded, TestParameters

def main():
    """Run the configurable throttling test using TestShuttleMultithreaded's functionality"""
    # Create test instance
    test = TestShuttleMultithreaded("__init__")  # Need to provide a method name for initialization
    
    # Run the configurable test with parameters from command line
    return test.run_configurable()

if __name__ == '__main__':
    # When run directly, execute the configurable test
    sys.exit(main())
