"""
Common Module Package

This package contains shared code used by both the shuttle and defender_test modules.
By centralizing these shared components, we maintain consistency and reduce duplication.
"""

# Import all shared components to make them easily accessible
from .defender_utils import get_mdatp_version
from .scan_utils import run_malware_scan, scan_result_types
from .ledger import Ledger
from .notifier import Notifier
from .logging_setup import setup_logging

# Define what's publicly available when using "from common import *"
__all__ = [
    # Defender utilities
    'get_mdatp_version',
    
    # Scan utilities
    'run_malware_scan',
    'scan_result_types',
    
    # Ledger system
    'Ledger',
    
    # Notification system
    'Notifier',
    
    # Logging
    'setup_logging'
]
