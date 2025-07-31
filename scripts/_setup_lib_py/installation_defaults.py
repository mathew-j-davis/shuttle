"""
Installation Defaults Reader

Reads user-configurable default values from YAML files
located in the standard_configs subdirectory.
This separates configurable defaults from code-defined enums and constants.
"""

import os
import sys
import yaml
from typing import Optional, Dict, Any


class InstallationDefaults:
    """Reader for installation default values from YAML files"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize with config directory path
        
        Args:
            config_dir: Path to directory containing YAML defaults (auto-detected if None)
        """
        if config_dir is None:
            # Auto-detect config directory in standard_configs subdirectory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(script_dir, "standard_configs")
        
        self.config_dir = config_dir
        self.config_cache = {}  # Cache loaded YAML files
        
        # Check if config directory exists
        self.config_dir_exists = os.path.exists(config_dir) and os.path.isdir(config_dir)
    
    def _load_general_config(self) -> Dict[str, Any]:
        """
        Load general configuration (cross-mode defaults needed before mode selection)
        
        Returns:
            Dictionary with general configuration data
        """
        # Check cache first
        if "general" in self.config_cache:
            return self.config_cache["general"]
        
        filename = "installation_defaults_general.yaml"
        config_path = os.path.join(self.config_dir, filename)
        
        if not os.path.exists(config_path):
            # Return empty dict - let callers handle fallbacks
            config_data = {}
        else:
            try:
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load {config_path}: {e}", file=sys.stderr)
                config_data = {}
        
        # Cache the loaded config
        self.config_cache["general"] = config_data
        return config_data
    
    def _load_yaml_config(self, install_mode: str) -> Dict[str, Any]:
        """
        Load YAML configuration for a specific installation mode
        
        Args:
            install_mode: Installation mode (dev, user, service)
            
        Returns:
            Dictionary with configuration data
        """
        # Map install modes to file names
        mode_to_file = {
            "dev": "development",
            "user": "user", 
            "service": "production"
        }
        file_mode = mode_to_file.get(install_mode, install_mode)
        
        # Check cache first
        if file_mode in self.config_cache:
            return self.config_cache[file_mode]
        
        filename = f"installation_defaults_{file_mode}.yaml"
        config_path = os.path.join(self.config_dir, filename)
        
        if not os.path.exists(config_path):
            # Return empty dict - let callers handle fallbacks
            config_data = {}
        else:
            try:
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load {config_path}: {e}", file=sys.stderr)
                config_data = {}
        
        # Cache the loaded config
        self.config_cache[file_mode] = config_data
        return config_data
    
    def get_default_install_mode(self) -> str:
        """Get default installation mode (from general config)"""
        config = self._load_general_config()
        return config.get("install_mode", {}).get("default", "dev")
    
    def get_default_path(self, install_mode: str, path_type: str, project_root: str = None) -> str:
        """
        Get default path for installation mode and type
        
        Args:
            install_mode: Installation mode (dev, user, service)
            path_type: Path type (config, source, destination, etc.)
            project_root: Project root directory for dev mode (optional)
            
        Returns:
            Default path with variables expanded
        """
        config = self._load_yaml_config(install_mode)
        path = config.get("paths", {}).get(path_type, "")
        
        if path:
            # Handle COMPUTED_PROJECT_ROOT placeholder for dev mode
            if 'COMPUTED_PROJECT_ROOT' in path:
                if project_root:
                    path = path.replace('COMPUTED_PROJECT_ROOT', project_root)
                else:
                    # Auto-detect project root relative to this script
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    computed_project_root = os.path.dirname(os.path.dirname(script_dir))
                    path = path.replace('COMPUTED_PROJECT_ROOT', computed_project_root)
            
            # Expand environment variables like ${HOME}
            path = os.path.expandvars(path)
        
        return path
    
    def get_default_log_level(self, install_mode: str) -> str:
        """Get default log level for installation mode"""
        config = self._load_yaml_config(install_mode)
        return config.get("logging", {}).get("log_level", "INFO")
    
    def get_default_threads(self) -> int:
        """Get default number of scan threads (uses service mode defaults)"""
        config = self._load_yaml_config("service")
        return config.get("settings", {}).get("max_scan_threads", 1)
    
    def get_default_min_free_space(self) -> int:
        """Get default minimum free space in MB (uses service mode defaults)"""
        config = self._load_yaml_config("service")
        return config.get("settings", {}).get("throttle_free_space_mb", 100)
    
    def get_default_max_file_count_per_run(self, install_mode: str = "service") -> int:
        """Get default max file count per run"""
        config = self._load_yaml_config(install_mode)
        return config.get("settings", {}).get("throttle_max_file_count_per_run", 1000)
    
    def get_default_max_file_volume_per_run_mb(self, install_mode: str = "service") -> int:
        """Get default max file volume per run in MB"""
        config = self._load_yaml_config(install_mode)
        return config.get("settings", {}).get("throttle_max_file_volume_per_run_mb", 1024)
    
    def get_default_max_file_volume_per_day_mb(self, install_mode: str = "service") -> int:
        """Get default max file volume per day in MB"""
        config = self._load_yaml_config(install_mode)
        return config.get("settings", {}).get("throttle_max_file_volume_per_day_mb", 0)
    
    def get_default_max_file_count_per_day(self, install_mode: str = "service") -> int:
        """Get default max file count per day"""
        config = self._load_yaml_config(install_mode)
        return config.get("settings", {}).get("throttle_max_file_count_per_day", 0)
    
    def get_default_use_clamav(self) -> bool:
        """Get default ClamAV usage setting (from general config)"""
        config = self._load_general_config()
        return config.get("scanning", {}).get("use_clamav", False)
    
    def get_default_use_defender(self) -> bool:
        """Get default Defender usage setting (from general config)"""
        config = self._load_general_config()
        return config.get("scanning", {}).get("use_defender", True)
    
    def get_default_malware_scan_timeout_seconds(self, install_mode: str = "service") -> int:
        """Get default malware scan timeout in seconds"""
        config = self._load_yaml_config(install_mode)
        return config.get("scanning", {}).get("malware_scan_timeout_seconds", 60)
    
    def get_default_malware_scan_timeout_ms_per_byte(self, install_mode: str = "service") -> float:
        """Get default malware scan timeout per byte in milliseconds"""
        config = self._load_yaml_config(install_mode)
        return config.get("scanning", {}).get("malware_scan_timeout_ms_per_byte", 0.01)
    
    def get_default_malware_scan_retry_wait_seconds(self, install_mode: str = "service") -> int:
        """Get default malware scan retry wait in seconds"""
        config = self._load_yaml_config(install_mode)
        return config.get("scanning", {}).get("malware_scan_retry_wait_seconds", 30)
    
    def get_default_malware_scan_retry_count(self, install_mode: str = "service") -> int:
        """Get default malware scan retry count"""
        config = self._load_yaml_config(install_mode)
        return config.get("scanning", {}).get("malware_scan_retry_count", 5)
    
    def get_default_smtp_port(self) -> int:
        """Get default SMTP port"""
        config = self._load_yaml_config("service")
        return config.get("notifications", {}).get("smtp_port", 587)
    
    def get_default_use_tls(self) -> bool:
        """Get default TLS usage setting"""
        config = self._load_yaml_config("service")
        return config.get("notifications", {}).get("use_tls", True)
    
    def get_default_delete_source(self) -> bool:
        """Get default delete source files setting"""
        config = self._load_yaml_config("service")
        return config.get("settings", {}).get("delete_source_files_after_copying", True)
    
    def get_default_install_basic_deps(self) -> bool:
        """Get default install basic dependencies setting (from general config)"""
        config = self._load_general_config()
        return config.get("system_deps", {}).get("install_basic_deps", True)
    
    def get_default_install_python(self) -> bool:
        """Get default install Python setting (from general config)"""
        config = self._load_general_config()
        return config.get("system_deps", {}).get("install_python", True)
    
    def get_default_install_clamav(self) -> bool:
        """Get default install ClamAV setting (from general config)"""
        config = self._load_general_config()
        return config.get("system_deps", {}).get("install_clamav", False)
    
    def get_default_check_defender(self) -> bool:
        """Get default check Defender setting (from general config)"""
        config = self._load_general_config()
        return config.get("system_deps", {}).get("check_defender", True)
    
    def get_default_create_directory(self, dir_type: str) -> bool:
        """Get default directory creation setting (from general config)"""
        config = self._load_general_config()
        key = f"create_{dir_type}_dir"
        return config.get("directories", {}).get(key, True)
    
    def get_default_venv_choice_no_venv(self) -> str:
        """Get default venv choice when no venv is active (from general config)"""
        config = self._load_general_config()
        return config.get("venv", {}).get("choice_no_venv", "script_creates")
    
    def expand_project_root(self, path: str, project_root: str) -> str:
        """
        Expand ${PROJECT_ROOT} variable in path
        
        Args:
            path: Path that may contain ${PROJECT_ROOT}
            project_root: Actual project root directory
            
        Returns:
            Path with ${PROJECT_ROOT} expanded
        """
        return path.replace('${PROJECT_ROOT}', project_root)
    
    def get_all_defaults_for_mode(self, install_mode: str, project_root: str = None) -> dict:
        """
        Get all default values for a specific installation mode
        
        Args:
            install_mode: Installation mode (dev, user, service)
            project_root: Project root directory for variable expansion
            
        Returns:
            Dictionary of all defaults for the mode
        """
        config = self._load_yaml_config(install_mode)
        defaults = {}
        
        # Path defaults
        path_types = ['config', 'source', 'destination', 'quarantine', 'logs', 'hazard', 'venv', 'test_config', 'test_work',
                     'hazard_encryption_key', 'ledger_file', 'daily_processing_tracker_logs']
        for path_type in path_types:
            path = self.get_default_path(install_mode, path_type, project_root)
            defaults[f'{path_type}_path'] = path
        
        # Settings defaults
        settings = config.get("settings", {})
        for key, value in settings.items():
            defaults[key] = value
        
        # Other defaults
        defaults['log_level'] = self.get_default_log_level(install_mode)
        
        # Scanning defaults
        scanning = config.get("scanning", {})
        for key, value in scanning.items():
            defaults[key] = value
        
        # Notification defaults
        notifications = config.get("notifications", {})
        for key, value in notifications.items():
            defaults[key] = value
        
        return defaults


def get_installation_defaults(config_dir: Optional[str] = None) -> InstallationDefaults:
    """
    Get InstallationDefaults instance
    
    Args:
        config_dir: Optional path to config directory
        
    Returns:
        InstallationDefaults instance
    """
    return InstallationDefaults(config_dir)


if __name__ == "__main__":
    """Test the defaults reader"""
    try:
        defaults = get_installation_defaults()
        
        print("Installation Defaults Configuration")
        print("=" * 40)
        
        print(f"Default install mode: {defaults.get_default_install_mode()}")
        print()
        
        # Test all installation modes
        for mode in ['dev', 'user', 'service']:
            print(f"{mode.upper()} mode defaults:")
            mode_defaults = defaults.get_all_defaults_for_mode(mode, '/path/to/project')
            for key, value in sorted(mode_defaults.items()):
                print(f"  {key}: {value}")
            print()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)