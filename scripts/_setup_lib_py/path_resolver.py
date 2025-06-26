# #!/usr/bin/env python3
# """
# Path Resolver
# Resolves symbolic path names to actual file system paths
# """

# import os
# import configparser
# from pathlib import Path
# from typing import Optional, Dict


# class PathResolver:
#     """Resolves symbolic path names to actual file system paths"""
    
#     # Path mapping configuration (only config file paths)
#     PATH_MAP = {
#         'source_path': ('paths', 'source_path'),
#         'destination_path': ('paths', 'destination_path'),
#         'quarantine_path': ('paths', 'quarantine_path'),
#         'hazard_archive_path': ('paths', 'hazard_archive_path'),
#         'tracking_data_path': ('paths', 'tracking_data_path'),
#         'log_path': ('logging', 'log_path'),
#         'ledger_file_path': ('paths', 'ledger_file_path'),
#         'hazard_encryption_key_path': ('paths', 'hazard_encryption_key_path'),
#         # shuttle_config_path, shuttle_test_config_path, shuttle_test_work_dir 
#         # are handled as special cases in resolve_path()
#     }
    
#     def __init__(self, shuttle_config_path: Optional[str] = None,
#                  shuttle_test_config_path: Optional[str] = None,
#                  shuttle_test_work_dir: Optional[str] = None):
#         """
#         Initialize path resolver with explicit parameters
        
#         Args:
#             shuttle_config_path: Path to shuttle config (or env var SHUTTLE_CONFIG_PATH)
#             shuttle_test_config_path: Path to test config (or env var SHUTTLE_TEST_CONFIG_PATH) 
#             shuttle_test_work_dir: Test work directory (or env var SHUTTLE_TEST_WORK_DIR)
#         """
#         # Use parameters first, then environment variables as fallback
#         self.shuttle_config_path = (shuttle_config_path or 
#                                    os.environ.get('SHUTTLE_CONFIG_PATH'))
#         self.shuttle_test_config_path = (shuttle_test_config_path or 
#                                         os.environ.get('SHUTTLE_TEST_CONFIG_PATH'))
#         self.shuttle_test_work_dir = (shuttle_test_work_dir or 
#                                      os.environ.get('SHUTTLE_TEST_WORK_DIR'))
        
#         self.config = None
#         self._load_shuttle_config()
    
#     def _load_shuttle_config(self) -> None:
#         """Load shuttle configuration file if available"""
#         if self.shuttle_config_path and Path(self.shuttle_config_path).exists():
#             try:
#                 self.config = configparser.ConfigParser()
#                 self.config.read(self.shuttle_config_path)
#             except Exception:
#                 pass  # Ignore config read errors
    
#     def resolve_path(self, symbolic_name: str) -> str:
#         """
#         Resolve symbolic path name to actual path
        
#         Args:
#             symbolic_name: Symbolic path name to resolve
            
#         Returns:
#             Resolved file system path
            
#         Raises:
#             ValueError: If path cannot be resolved
#         """
#         # Handle special cases first (the 3 real env var paths)
#         if symbolic_name == 'shuttle_config_path':
#             if not self.shuttle_config_path:
#                 raise ValueError("shuttle_config_path not available - no config path provided")
#             return self.shuttle_config_path
        
#         if symbolic_name == 'shuttle_test_config_path':
#             if not self.shuttle_test_config_path:
#                 raise ValueError("shuttle_test_config_path not available - no test config path provided")
#             return self.shuttle_test_config_path
            
#         if symbolic_name == 'shuttle_test_work_dir':
#             if not self.shuttle_test_work_dir:
#                 raise ValueError("shuttle_test_work_dir not available - no test work dir provided")
#             return self.shuttle_test_work_dir
        
#         # Handle config file paths (read from shuttle config file)
#         if symbolic_name not in self.PATH_MAP:
#             raise ValueError(f"Unknown symbolic path: {symbolic_name}")
        
#         section, key = self.PATH_MAP[symbolic_name]
        
#         if not self.config:
#             raise ValueError(f"Cannot resolve {symbolic_name} - no config file loaded")
        
#         if not self.config.has_section(section):
#             raise ValueError(f"Config file missing [{section}] section for {symbolic_name}")
            
#         if not self.config.has_option(section, key):
#             raise ValueError(f"Config file missing {key} in [{section}] section")
        
#         return self.config.get(section, key)
    
#     def resolve_all_paths(self, path_list: list) -> Dict[str, str]:
#         """
#         Resolve a list of symbolic paths
        
#         Args:
#             path_list: List of symbolic path names
            
#         Returns:
#             Dictionary mapping symbolic names to resolved paths
#         """
#         return {path: self.resolve_path(path) for path in path_list}