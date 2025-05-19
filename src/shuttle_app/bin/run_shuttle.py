#!/usr/bin/env python3
"""
Shuttle Runner

This script provides a simple entry point to run the Shuttle file transfer and scanning utility.
It handles secure file transfers with malware scanning and ensures sufficient disk space.
"""

from shuttle.shuttle import main

if __name__ == '__main__':
    import sys
    sys.exit(main())
