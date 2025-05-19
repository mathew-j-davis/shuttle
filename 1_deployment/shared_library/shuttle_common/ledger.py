"""
Ledger Module

This module provides the Ledger class for working with the defender version ledger file.
The ledger tracks which versions of Microsoft Defender have been tested and verified to work.
"""

import yaml
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from .logging_setup import setup_logging

class Ledger:
    """
    Class for working with the Defender ledger file that tracks tested versions.
    
    The ledger file is a YAML file with a structure like:
    
    defender:
      tested_versions:
        - version: "101.12345.123"
          test_time: "2025-05-09T10:30:00"
          test_result: "pass"
          test_details: "All detection tests passed"
    """
    
    def __init__(self, logging_options):
        """
        Initialize the Ledger
        
        Args:
            logging_options (LoggingOptions): Logger properties to use for logging
        """
        self.logger = setup_logging('shuttle.common.ledger', logging_options)
        self.data = None
        
    def load(self,ledger_file_path: str) -> bool:
        """
        Load the ledger data from the file.
        
        Args:
            ledger_file_path (str): Path to the ledger.yaml file
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            with open(ledger_file_path, 'r') as file:
                self.data = yaml.safe_load(file)
                return True
        except FileNotFoundError:
            self.logger.error(f"Ledger file not found at: {ledger_file_path}")
            return False
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing ledger file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error reading ledger file: {e}")
            return False
            
    def is_version_tested(self, version: str) -> bool:
        """
        Check if the specified version has been successfully tested.
        
        Args:
            version (str): Version string to check
            
        Returns:
            bool: True if version has been tested successfully, False otherwise
        """
        if not self.data:
            self.logger.error("Ledger data not loaded")
            return False
            
        try:
            if 'defender' not in self.data:
                self.logger.error("No 'defender' section in ledger")
                return False
                
            if 'tested_versions' not in self.data['defender']:
                self.logger.error("No 'tested_versions' list in ledger")
                return False
                
            tested_versions = self.data['defender']['tested_versions']
            
            # Check if version exists in the tested_versions list
            for tested_version in tested_versions:
                if (isinstance(tested_version, dict) and 
                    'version' in tested_version and 
                    tested_version['version'] == version and
                    'test_result' in tested_version and
                    tested_version['test_result'] == 'pass'):
                        
                    self.logger.info(f"Found matching tested version: {version}")
                    return True
                    
            self.logger.warning(f"Version {version} not found in tested versions or did not pass testing")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking tested versions: {e}")
            return False
