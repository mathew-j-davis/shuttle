#!/usr/bin/env python3
"""
Read specific settings from YAML configuration file.
Used to extract interactive mode and dry-run settings.
"""

import yaml
import sys
from typing import Optional, List, Dict, Any


def read_setting(config_file: str, setting_type: str) -> Optional[str]:
    """
    Read a specific setting from the configuration file.
    
    Args:
        config_file: Path to YAML configuration file
        setting_type: Type of setting to read ('interactive_mode' or 'dry_run_default')
        
    Returns:
        Setting value as string, or None if not found
    """
    try:
        with open(config_file, 'r') as f:
            docs = list(yaml.safe_load_all(f))
        
        for doc in docs:
            if doc and 'settings' in doc:
                if setting_type == 'interactive_mode':
                    mode = doc['settings'].get('interactive_mode', '')
                    if mode:
                        return mode
                elif setting_type == 'dry_run_default':
                    if doc['settings'].get('dry_run_default', False):
                        return 'true'
                    else:
                        return 'false'
        
        return None
    except Exception:
        return None


def main():
    """Main entry point for reading configuration settings."""
    if len(sys.argv) < 3:
        print("Usage: read_config_settings.py <config_file> <setting_type>", file=sys.stderr)
        sys.exit(1)
    
    config_file = sys.argv[1]
    setting_type = sys.argv[2]
    
    result = read_setting(config_file, setting_type)
    if result:
        print(result)
    
    sys.exit(0)


if __name__ == "__main__":
    main()