#!/usr/bin/env python3
"""
Configuration Analyzer
Analyzes YAML configuration and provides summary information
"""

import yaml
import sys
from typing import Dict, List, Any, Tuple


def analyze_config(config_file: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Analyze YAML configuration file and extract components
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        Tuple of (groups, users, settings)
    """
    try:
        with open(config_file, 'r') as f:
            docs = list(yaml.safe_load_all(f))
    except Exception as e:
        print(f"Error reading configuration: {e}")
        sys.exit(1)

    users = []
    groups = {}
    settings = {}

    for doc in docs:
        if doc is None:
            continue
        if doc.get('type') == 'user':
            users.append(doc['user'])
        elif 'groups' in doc:
            groups = doc.get('groups', {})
            settings = doc.get('settings', {})
            if 'metadata' in doc:
                settings['metadata'] = doc['metadata']

    return groups, users, settings


def print_config_summary(config_file: str) -> None:
    """
    Print a summary of the configuration
    
    Args:
        config_file: Path to YAML configuration file
    """
    groups, users, settings = analyze_config(config_file)
    
    print("Configuration Summary:")
    print(f"  Environment: {settings.get('metadata', {}).get('environment', 'Not specified')}")
    
    # Show interactive mode if configured
    interactive_mode = settings.get('interactive_mode', '')
    if interactive_mode:
        print(f"  Interactive Mode: {interactive_mode}")
    
    # Show dry-run default if configured
    if settings.get('dry_run_default', False):
        print(f"  Dry-run Default: Enabled")
    
    print(f"  Groups to create: {len(groups)}")
    
    for group_name, group_info in groups.items():
        if isinstance(group_info, dict):
            desc = group_info.get('description', 'No description')
        else:
            desc = str(group_info)
        print(f"    - {group_name}: {desc}")

    print(f"  Users to configure: {len(users)}")
    for user in users:
        caps = user.get('capabilities', {}).get('executables', [])
        caps_str = ', '.join(caps) if caps else 'None'
        samba_enabled = user.get('samba', {}).get('enabled', False)
        samba_str = ' (Samba enabled)' if samba_enabled else ''
        account_type = user.get('account_type', 'existing')
        print(f"    - {user['name']} ({user['source']}, {account_type}){samba_str}")
        print(f"      Capabilities: {caps_str}")
        
        # Show permission summary
        permissions = user.get('permissions', {})
        rw_count = len(permissions.get('read_write', []))
        ro_count = len(permissions.get('read_only', []))
        if rw_count > 0 or ro_count > 0:
            print(f"      Permissions: {rw_count} read-write, {ro_count} read-only")

    if len(users) == 0:
        print("⚠️  No users defined in configuration")


def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <config_file>")
        sys.exit(1)
    
    print_config_summary(sys.argv[1])


if __name__ == '__main__':
    main()