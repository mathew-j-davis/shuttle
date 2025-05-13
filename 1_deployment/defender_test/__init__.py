"""
Defender Testing Module

This module provides tools for testing Microsoft Defender's output format and
tracking compatible versions. It ensures that the pattern matching logic used in
shuttle's scanning module remains compatible with the current Defender version.

Main components:
- defender_test.py: Core testing functionality for Microsoft Defender output patterns
- read_write_ledger.py: Handles recording and retrieving tested Defender versions
"""

# Import main functionality for easy access
from .defender_test import main, run_defender_scan, verify_output_patterns
from .read_write_ledger import ReadWriteLedger
