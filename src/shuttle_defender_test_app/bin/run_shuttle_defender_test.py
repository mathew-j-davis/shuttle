#!/usr/bin/env python3
"""
Shuttle Defender Test Runner

This script provides a simple entry point to run the defender_test module.
It tests Microsoft Defender's output format to ensure pattern matching
logic in the scanning module remains compatible.
"""

from shuttle_defender_test.shuttle_defender_test import main

if __name__ == '__main__':
    import sys
    sys.exit(main())
