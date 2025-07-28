"""
Installation Defaults Reader

Reads user-configurable default values from installation_defaults.conf
located in the same directory as this module (_setup_lib_py).
This separates configurable defaults from code-defined enums and constants.
"""

import configparser
import os
import sys
from typing import Optional


class InstallationDefaults:
    """Reader for installation default values from config file"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize with config file path
        
        Args:
            config_path: Path to installation_defaults.conf (auto-detected if None)
        """
        if config_path is None:
            # Auto-detect config path in the same directory as this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "installation_defaults.conf")
        
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        
        # Disable built-in interpolation since we'll handle variables manually
        # This prevents errors with ${PROJECT_ROOT} which is not a config option
        self.config = configparser.ConfigParser(
            interpolation=None
        )
        
        # Read the config file if it exists, otherwise use built-in defaults
        self.config_file_exists = os.path.exists(config_path)
        if self.config_file_exists:
            self.config.read(config_path)
        # If config file doesn't exist, we'll use built-in fallback defaults
    
    def get_default_install_mode(self) -> str:
        """Get default installation mode"""
        return self.config.get('install_mode', 'default', fallback='dev')
    
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
        key = f"{install_mode}_{path_type}"
        path = self.config.get('paths', key, fallback='')
        
        # If no path found in config file (or no config file), use built-in defaults
        if not path:
            path = self._get_builtin_default_path(install_mode, path_type, project_root)
        
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
    
    def _get_builtin_default_path(self, install_mode: str, path_type: str, project_root: str = None) -> str:
        """
        Get built-in default paths when config file doesn't exist
        
        Args:
            install_mode: Installation mode (dev, user, service)
            path_type: Path type (config, source, destination, etc.)
            project_root: Project root directory for dev mode (optional)
            
        Returns:
            Built-in default path
        """
        # Auto-detect project root if not provided
        if not project_root:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
        
        # Built-in default paths
        defaults = {
            # Development mode paths
            'dev_config': f'{project_root}/config/config.conf',
            'dev_source': f'{project_root}/work/incoming',
            'dev_destination': f'{project_root}/work/processed',
            'dev_quarantine': f'{project_root}/work/quarantine',
            'dev_logs': f'{project_root}/work/logs',
            'dev_hazard': f'{project_root}/work/hazard',
            'dev_venv': f'{project_root}/.venv',
            'dev_test_config': f'{project_root}/config/test_config.yaml',
            'dev_test_work': f'{project_root}/test_area',
            
            # User mode paths
            'user_config': '${HOME}/.config/shuttle/config.conf',
            'user_source': '${HOME}/shuttle/incoming',
            'user_destination': '${HOME}/shuttle/processed',
            'user_quarantine': '/tmp/shuttle/quarantine',
            'user_logs': '${HOME}/shuttle/logs',
            'user_hazard': '${HOME}/shuttle/hazard',
            'user_venv': '${HOME}/.local/share/shuttle/venv',
            'user_test_config': '${HOME}/.config/shuttle/test_config.yaml',
            'user_test_work': '/tmp/shuttle/test_area',
            
            # Service mode paths
            'service_config': '/etc/shuttle/config.conf',
            'service_source': '/mnt/in',
            'service_destination': '/mnt/out',
            'service_quarantine': '/mnt/quarantine',
            'service_logs': '/var/log/shuttle',
            'service_hazard': '/mnt/hazard',
            'service_venv': '/opt/shuttle/venv',
            'service_test_config': '/etc/shuttle/test_config.yaml',
            'service_test_work': '/var/tmp/shuttle/test_area',
        }
        
        key = f"{install_mode}_{path_type}"
        return defaults.get(key, '')
    
    def get_default_log_level(self, install_mode: str) -> str:
        """Get default log level for installation mode"""
        key = f"{install_mode}_log_level"
        return self.config.get('logging', key, fallback='INFO')
    
    def get_default_threads(self) -> int:
        """Get default number of scan threads"""
        return self.config.getint('processing', 'default_threads', fallback=1)
    
    def get_default_min_free_space(self) -> int:
        """Get default minimum free space in MB"""
        return self.config.getint('processing', 'default_min_free_space_mb', fallback=100)
    
    def get_default_use_clamav(self) -> bool:
        """Get default ClamAV usage setting"""
        return self.config.getboolean('scanning', 'default_use_clamav', fallback=False)
    
    def get_default_use_defender(self) -> bool:
        """Get default Defender usage setting"""
        return self.config.getboolean('scanning', 'default_use_defender', fallback=True)
    
    def get_default_smtp_port(self) -> int:
        """Get default SMTP port"""
        return self.config.getint('email', 'default_smtp_port', fallback=587)
    
    def get_default_use_tls(self) -> bool:
        """Get default TLS usage setting"""
        return self.config.getboolean('email', 'default_use_tls', fallback=True)
    
    def get_default_delete_source(self) -> bool:
        """Get default delete source files setting"""
        return self.config.getboolean('file_processing', 'default_delete_source', fallback=True)
    
    def get_default_install_basic_deps(self) -> bool:
        """Get default install basic dependencies setting"""
        return self.config.getboolean('system_deps', 'default_install_basic_deps', fallback=True)
    
    def get_default_install_python(self) -> bool:
        """Get default install Python setting"""
        return self.config.getboolean('system_deps', 'default_install_python', fallback=True)
    
    def get_default_install_clamav(self) -> bool:
        """Get default install ClamAV setting"""
        return self.config.getboolean('system_deps', 'default_install_clamav', fallback=False)
    
    def get_default_check_defender(self) -> bool:
        """Get default check Defender setting"""
        return self.config.getboolean('system_deps', 'default_check_defender', fallback=True)
    
    def get_default_create_directory(self, dir_type: str) -> bool:
        """Get default directory creation setting"""
        key = f"default_create_{dir_type}_dir"
        return self.config.getboolean('directories', key, fallback=True)
    
    def get_default_venv_choice_no_venv(self) -> str:
        """Get default venv choice when no venv is active"""
        return self.config.get('venv', 'default_choice_no_venv', fallback='script_creates')
    
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
        defaults = {}
        
        # Path defaults
        path_types = ['config', 'source', 'destination', 'quarantine', 'logs', 'hazard', 'venv', 'test_config', 'test_work']
        for path_type in path_types:
            path = self.get_default_path(install_mode, path_type, project_root)
            defaults[f'{path_type}_path'] = path
        
        # Other defaults
        defaults['log_level'] = self.get_default_log_level(install_mode)
        defaults['threads'] = self.get_default_threads()
        defaults['min_free_space'] = self.get_default_min_free_space()
        defaults['use_clamav'] = self.get_default_use_clamav()
        defaults['use_defender'] = self.get_default_use_defender()
        defaults['smtp_port'] = self.get_default_smtp_port()
        defaults['use_tls'] = self.get_default_use_tls()
        defaults['delete_source'] = self.get_default_delete_source()
        
        return defaults


def get_installation_defaults(config_path: Optional[str] = None) -> InstallationDefaults:
    """
    Get InstallationDefaults instance
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        InstallationDefaults instance
    """
    return InstallationDefaults(config_path)


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
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)