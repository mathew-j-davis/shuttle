"""
Ledger Module

This module provides the Ledger class for working with the defender version ledger file.
The ledger tracks which versions of Microsoft Defender have been tested and verified to work.
"""

import yaml
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime


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
    
    def __init__(self, logger=None):
        """
        Initialize the Ledger with a file path.
        
        Args:
            ledger_file_path (str): Path to the ledger.yaml file
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger('shuttle')
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
            
    # def save(self) -> bool:
    #     """
    #     Save the ledger data to the file.
        
    #     Returns:
    #         bool: True if saved successfully, False otherwise
    #     """
    #     if self.data is None:
    #         self.logger.error("No ledger data to save")
    #         return False
            
    #     try:
    #         with open(self.ledger_file_path, 'w') as file:
    #             yaml.dump(self.data, file, default_flow_style=False, sort_keys=False)
    #             return True
    #     except Exception as e:
    #         self.logger.error(f"Error saving ledger file: {e}")
    #         return False
            
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
            
    # def add_tested_version(self, version: str, test_result: str, test_details: str = "") -> bool:
    #     """
    #     Add a tested version to the ledger.
        
    #     Args:
    #         version (str): Version string to add
    #         test_result (str): Result of the test ('pass' or 'fail')
    #         test_details (str): Additional details about the test
            
    #     Returns:
    #         bool: True if added successfully, False otherwise
    #     """
    #     if not self.data:
    #         self.data = {}
            
    #     if 'defender' not in self.data:
    #         self.data['defender'] = {}
            
    #     if 'tested_versions' not in self.data['defender']:
    #         self.data['defender']['tested_versions'] = []
            
    #     # Check if version already exists
    #     for tested_version in self.data['defender']['tested_versions']:
    #         if isinstance(tested_version, dict) and 'version' in tested_version and tested_version['version'] == version:
    #             # Update existing version
    #             tested_version.update({
    #                 'test_time': datetime.now().isoformat(),
    #                 'test_result': test_result,
    #                 'test_details': test_details
    #             })
    #             return self.save()
                
    #     # Add new version
    #     self.data['defender']['tested_versions'].append({
    #         'version': version,
    #         'test_time': datetime.now().isoformat(),
    #         'test_result': test_result,
    #         'test_details': test_details
    #     })
        
    #     return self.save()
        
    # def get_defender_tested_versions(self) -> List[Dict[str, Any]]:
    #     """
    #     Get all tested versions.
        
    #     Returns:
    #         list: List of tested version dictionaries
    #     """
    #     if not self.data or 'defender' not in self.data or 'tested_versions' not in self.data['defender']:
    #         return []
            
    #     return self.data['defender']['tested_versions']


# if __name__ == "__main__":
#     # Simple test
#     logging.basicConfig(level=logging.DEBUG)
#     logger = logging.getLogger("ledger_test")
    
#     import os
#     test_file = os.path.expanduser("~/test_ledger.yaml")
    
#     # Create test ledger
#     ledger = Ledger(test_file, logger)
    
#     # Add test versions
#     ledger.data = {'defender': {'tested_versions': []}}
#     ledger.add_tested_version("101.1234.567", "pass", "Test version 1")
#     ledger.add_tested_version("102.2345.678", "fail", "Test version 2")
    
#     # Load and verify
#     ledger = Ledger(test_file, logger)
#     if ledger.load():
#         print("Loaded ledger data successfully")
#         print(f"Version 101.1234.567 tested: {ledger.is_version_tested('101.1234.567')}")
#         print(f"Version 102.2345.678 tested: {ledger.is_version_tested('102.2345.678')}")
#         print(f"Version 103.3456.789 tested: {ledger.is_version_tested('103.3456.789')}")
#     else:
#         print("Failed to load ledger data")
