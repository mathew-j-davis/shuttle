#!/usr/bin/env python3
"""
Check if a specific component is enabled in the configuration file.
Used to determine which installation/configuration phases to run.
"""

import yaml
import sys
from typing import List, Dict, Any


def is_component_enabled(config_file: str, component_name: str) -> bool:
    """
    Check if a component is enabled in the configuration.
    
    Args:
        config_file: Path to YAML configuration file
        component_name: Name of component to check
        
    Returns:
        True if component is enabled (or not specified - default to enabled)
    """
    try:
        with open(config_file, 'r') as f:
            docs = list(yaml.safe_load_all(f))
        
        for doc in docs:
            if doc and 'components' in doc:
                # Default to True if not specified
                return doc['components'].get(component_name, True)
        
        # Default to enabled if not specified
        return True
    except Exception:
        # Default to enabled if error
        return True


def main():
    """Main entry point for checking component status."""
    if len(sys.argv) < 3:
        print("Usage: check_component_enabled.py <config_file> <component_name>", file=sys.stderr)
        sys.exit(1)
    
    config_file = sys.argv[1]
    component_name = sys.argv[2]
    
    enabled = is_component_enabled(config_file, component_name)
    sys.exit(0 if enabled else 1)


if __name__ == "__main__":
    main()