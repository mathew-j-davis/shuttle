#!/usr/bin/env python3
"""
Validate YAML configuration file structure for post-install configuration.
Supports both complete configurations and minimal configurations with CLI overrides.
"""

import yaml
import sys
import os
from typing import List, Dict, Any, Tuple


def validate_yaml_syntax(config_file: str) -> bool:
    """
    Validate basic YAML syntax by attempting to load the file.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        True if YAML syntax is valid, False otherwise
    """
    try:
        with open(config_file, 'r') as f:
            list(yaml.safe_load_all(f))
        return True
    except yaml.YAMLError:
        return False
    except Exception:
        return False


def validate_config_structure(config_file: str) -> Tuple[bool, str]:
    """
    Validate the structure of the configuration file.
    Checks for required sections and validates document types.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        with open(config_file, 'r') as f:
            docs = list(yaml.safe_load_all(f))
        
        # Check if we have documents
        if not docs:
            return False, "❌ No configuration documents found"
        
        # Count document types
        base_docs = []
        group_docs = []
        user_docs = []
        path_docs = []
        
        for doc in docs:
            if not doc:
                continue
            doc_type = doc.get('type')
            if doc_type == 'group':
                group_docs.append(doc)
            elif doc_type == 'user':
                user_docs.append(doc)
            elif doc_type == 'path':
                path_docs.append(doc)
            else:
                # Assume base config document
                base_docs.append(doc)
        
        # Determine if CLI overrides are provided
        cli_has_components = any([
            os.getenv('CLI_OVERRIDE_INSTALL_ACL'),
            os.getenv('CLI_OVERRIDE_INSTALL_SAMBA'),
            os.getenv('CLI_OVERRIDE_CONFIGURE_USERS_GROUPS'),
            os.getenv('CLI_OVERRIDE_CONFIGURE_SAMBA'),
            os.getenv('CLI_OVERRIDE_CONFIGURE_FIREWALL')
        ])
        
        cli_has_settings = any([
            os.getenv('CLI_OVERRIDE_CREATE_HOME'),
            os.getenv('CLI_OVERRIDE_BACKUP_USERS'),
            os.getenv('CLI_OVERRIDE_VALIDATE')
        ])
        
        cli_has_metadata = any([
            os.getenv('CLI_OVERRIDE_ENVIRONMENT'),
            os.getenv('CLI_OVERRIDE_MODE')
        ])
        
        # Check that we have at least groups, users, or paths
        has_content = len(group_docs) > 0 or len(user_docs) > 0 or len(path_docs) > 0
        
        if not has_content:
            return False, "❌ Configuration must contain at least one group, user, or path definition"
        
        # Validate that if base config exists, it has valid structure
        if base_docs:
            for base_doc in base_docs:
                # Check for valid sections if they exist
                if 'components' in base_doc:
                    components = base_doc['components']
                    if not isinstance(components, dict):
                        return False, "❌ Components section must be a dictionary"
        
        # Success - either we have a complete config, or minimal config with CLI overrides
        if base_docs and not (cli_has_components or cli_has_settings or cli_has_metadata):
            return True, "✅ Complete configuration file validated"
        elif cli_has_components or cli_has_settings or cli_has_metadata:
            return True, "✅ Minimal configuration file validated (CLI overrides provided)"
        else:
            return True, "✅ Configuration file validated"
            
    except Exception as e:
        return False, f"❌ Configuration validation failed: {e}"


def main():
    """Main entry point for configuration validation."""
    if len(sys.argv) < 2:
        print("Usage: validate_config.py <config_file>", file=sys.stderr)
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    # First validate YAML syntax
    if not validate_yaml_syntax(config_file):
        sys.exit(1)
    
    # Then validate structure
    success, message = validate_config_structure(config_file)
    print(message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()