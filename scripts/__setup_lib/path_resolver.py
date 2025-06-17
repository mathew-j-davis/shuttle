#!/usr/bin/env python3
"""
Path Resolver
Resolves symbolic path names to actual file system paths
"""

import os
import configparser
from pathlib import Path
from typing import Optional, Dict, Tuple, Any


class PathResolver:
    """Resolves symbolic path names to actual file system paths"""
    
    # Path mapping configuration
    PATH_MAP = {
        'source_path': {
            'env': 'SHUTTLE_CONFIG_SOURCE_PATH',
            'config': ('paths', 'source_path'),
            'default': '/srv/shuttle/incoming'
        },
        'destination_path': {
            'env': 'SHUTTLE_CONFIG_DEST_PATH',
            'config': ('paths', 'destination_path'),
            'default': '/srv/shuttle/processed'
        },
        'quarantine_path': {
            'env': 'SHUTTLE_CONFIG_QUARANTINE_PATH',
            'config': ('paths', 'quarantine_path'),
            'default': '/tmp/shuttle/quarantine'
        },
        'log_path': {
            'env': 'SHUTTLE_CONFIG_LOG_PATH',
            'config': ('paths', 'log_path'),
            'default': '/var/log/shuttle'
        },
        'hazard_archive_path': {
            'env': 'SHUTTLE_CONFIG_HAZARD_PATH',
            'config': ('paths', 'hazard_archive_path'),
            'default': '/srv/shuttle/hazard'
        },
        'ledger_file_path': {
            'env': 'SHUTTLE_CONFIG_LEDGER_PATH',
            'config': ('paths', 'ledger_file_path'),
            'default': '/etc/shuttle/ledger.yaml'
        },
        'hazard_encryption_key_path': {
            'env': 'SHUTTLE_CONFIG_KEY_PATH',
            'config': ('paths', 'hazard_encryption_key_path'),
            'default': '/etc/shuttle/shuttle_public.gpg'
        },
        'shuttle_config_path': {
            'env': 'SHUTTLE_CONFIG_PATH',
            'config': None,
            'default': '/etc/shuttle/config.conf'
        },
        'test_work_dir': {
            'env': 'SHUTTLE_TEST_WORK_DIR',
            'config': None,
            'default': '/var/lib/shuttle/test'
        },
        'test_config_path': {
            'env': 'SHUTTLE_TEST_CONFIG_PATH',
            'config': None,
            'default': '/etc/shuttle/test_config.conf'
        }
    }
    
    def __init__(self, shuttle_config_path: Optional[str] = None):
        """
        Initialize path resolver
        
        Args:
            shuttle_config_path: Path to shuttle configuration file
        """
        self.shuttle_config_path = shuttle_config_path or os.environ.get('SHUTTLE_CONFIG_PATH')
        self.config = None
        self._load_shuttle_config()
    
    def _load_shuttle_config(self) -> None:
        """Load shuttle configuration file if available"""
        if self.shuttle_config_path and Path(self.shuttle_config_path).exists():
            try:
                self.config = configparser.ConfigParser()
                self.config.read(self.shuttle_config_path)
            except:
                pass  # Ignore config read errors
    
    def resolve_path(self, symbolic_name: str) -> str:
        """
        Resolve symbolic path name to actual path
        
        Args:
            symbolic_name: Symbolic path name to resolve
            
        Returns:
            Resolved file system path
        """
        # Return as-is if not a symbolic path
        if symbolic_name not in self.PATH_MAP:
            return symbolic_name
        
        path_info = self.PATH_MAP[symbolic_name]
        
        # 1. Check environment variable
        if path_info['env'] and os.environ.get(path_info['env']):
            return os.environ[path_info['env']]
        
        # 2. Check config file
        if (path_info['config'] and self.config and 
            self.config.has_section(path_info['config'][0]) and
            self.config.has_option(path_info['config'][0], path_info['config'][1])):
            return self.config.get(path_info['config'][0], path_info['config'][1])
        
        # 3. Use default
        return path_info['default']
    
    def resolve_all_paths(self, path_list: list) -> Dict[str, str]:
        """
        Resolve a list of symbolic paths
        
        Args:
            path_list: List of symbolic path names
            
        Returns:
            Dictionary mapping symbolic names to resolved paths
        """
        return {path: self.resolve_path(path) for path in path_list}


# Module-level convenience function
def resolve_path(symbolic_name: str) -> str:
    """
    Resolve symbolic path name to actual path (convenience function)
    
    Args:
        symbolic_name: Symbolic path name to resolve
        
    Returns:
        Resolved file system path
    """
    resolver = PathResolver()
    return resolver.resolve_path(symbolic_name)