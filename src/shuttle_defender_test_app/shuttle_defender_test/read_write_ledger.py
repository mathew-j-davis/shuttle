"""
ReadWriteLedger Module

# This file extends the Ledger class from the common module

This module extends the Ledger class to provide read-write functionality
for working with the defender version ledger file.
"""

import yaml
from typing import List, Dict, Any
from datetime import datetime

# Import Ledger from shuttle_common package using absolute imports
from shuttle_common.ledger import Ledger
from shuttle_common.logger_injection import get_logger


class ReadWriteLedger(Ledger):
    """
    Extended class for working with the Defender ledger file that adds write capabilities.
            
    This class inherits the read functionality from the Ledger class and adds
    methods to save changes and add new tested versions.
    """
    
    def __init__(self):
        """
        Initialize the ReadWriteLedger.
        
        """
        super().__init__()
    
    def save(self, ledger_file_path) -> bool:
        """
        Save the ledger data to the file.
        
        Args:
            ledger_file_path (str): Path to the ledger.yaml file
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        logger = get_logger()

        if not ledger_file_path:
            logger.error("No ledger file path provided")
            return False
        
        if self.data is None:
            logger.error("No ledger data to save")
            return False
            
        try:
            with open(ledger_file_path, 'w') as file:
                yaml.dump(self.data, file, default_flow_style=False, sort_keys=False)
                return True
        except Exception as e:
            logger.error(f"Error saving ledger file: {e}")
            return False
            
    def add_tested_version(self, ledger_file_path, version: str, test_result: str, test_details: str = "") -> bool:
        """
        Add a tested version to the ledger.
        
        Args:
            ledger_file_path (str): Path to the ledger.yaml file
            version (str): Version string to add
            test_result (str): Result of the test ('pass' or 'fail')
            test_details (str): Additional details about the test
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        
        if not self.data:
            self.data = {}
            
        if 'defender' not in self.data:
            self.data['defender'] = {}
            
        if 'tested_versions' not in self.data['defender']:
            self.data['defender']['tested_versions'] = []
            
        # Check if version already exists
        for tested_version in self.data['defender']['tested_versions']:
            if isinstance(tested_version, dict) and 'version' in tested_version and tested_version['version'] == version:
                # Update existing version
                tested_version.update({
                    'test_time': datetime.now().isoformat(),
                    'test_result': test_result,
                    'test_details': test_details
                })
                return self.save(ledger_file_path)
                
        # Add new version
        self.data['defender']['tested_versions'].append({
            'version': version,
            'test_time': datetime.now().isoformat(),
            'test_result': test_result,
            'test_details': test_details
        })
        
        return self.save(ledger_file_path)
        
    # def get_defender_tested_versions(self) -> List[Dict[str, Any]]:
    #     """
    #     Get all tested versions.
        
    #     Returns:
    #         list: List of tested version dictionaries
    #     """
    #     if not self.data or 'defender' not in self.data or 'tested_versions' not in self.data['defender']:
    #         return []
            
    #     return self.data['defender']['tested_versions']