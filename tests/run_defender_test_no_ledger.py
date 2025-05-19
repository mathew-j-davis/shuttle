#!/usr/bin/env python3
"""
Defender Test Runner (No Ledger)

This script provides a test-only entry point to run the defender_test module
without updating the ledger. It's useful for manual testing of Microsoft Defender's
output pattern detection without recording the results in the ledger file.

It tests Microsoft Defender's output format to ensure pattern matching
logic in the scanning module remains compatible.

# Basic usage - will run with no ledger updates
python tests/run_defender_test_no_ledger.py

# With additional parameters - ledger will still be disabled
python tests/run_defender_test_no_ledger.py -Notify true -LogPath "/path/to/logs"

# Even if you specify a ledger file, it will be ignored
python tests/run_defender_test_no_ledger.py -LedgerPath "/some/path" -Notify true

"""

import sys
import os
import logging

# Add parent directory to path to allow importing from defender_test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from defender_test.defender_test import main

if __name__ == '__main__':
    # Build arguments list with explicit empty ledger file
    # This will prevent any ledger updates during the test
    if len(sys.argv) == 1:
        # No arguments supplied, add just the empty ledger
        sys.argv.extend(['-LedgerPath', ''])
    else:
        # Check if ledger file is already specified
        if '-LedgerPath' not in sys.argv:
            # Add empty ledger file parameter
            sys.argv.extend(['-LedgerPath', ''])
        else:
            # Find the position of -LedgerPath and set its value to empty
            ledger_index = sys.argv.index('-LedgerPath')
            if ledger_index + 1 < len(sys.argv):
                sys.argv[ledger_index + 1] = ''
    
    # Optional: Add verbose output to show we're running without ledger
    print("Running Defender test without updating ledger...")
    
    # Run the test
    sys.exit(main())
