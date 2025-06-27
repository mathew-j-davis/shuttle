#!/usr/bin/env python3
"""
Configuration Format Converters
Helper functions to convert between different configuration formats
"""

def convert_standard_to_old_format(standard_configs):
    """
    Convert centralized standard configurations to the old path_configs format
    used in _configure_standard_paths
    """
    path_configs = []
    
    for path_name, config in standard_configs.items():
        path_config = {
            'path': path_name,
            'description': config.get('description', f'Standard {path_name}'),
            'owner': config['owner'],
            'group': config['group'],
            'mode': config['mode'],
            'acls': []
        }
        
        # Convert ACLs from string format to old dict format
        if 'acls' in config:
            for acl_string in config['acls']:
                # Parse "g:group_name:rwX" format
                parts = acl_string.split(':')
                if len(parts) == 3:
                    acl_type, name, perms = parts
                    if acl_type == 'g':
                        path_config['acls'].append({
                            'type': 'group',
                            'name': name,
                            'perms': perms
                        })
        
        path_configs.append(path_config)
    
    return path_configs

def convert_old_to_standard_format(path_configs):
    """
    Convert old path_configs format to centralized standard format
    """
    standard_configs = {}
    
    for path_config in path_configs:
        path_name = path_config['path']
        config = {
            'owner': path_config['owner'],
            'group': path_config['group'],
            'mode': path_config['mode'],
            'description': path_config.get('description', f'Standard {path_name}')
        }
        
        # Convert ACLs from old dict format to string format
        if path_config.get('acls'):
            config['acls'] = []
            for acl in path_config['acls']:
                if acl['type'] == 'group':
                    acl_string = f"g:{acl['name']}:{acl['perms']}"
                    config['acls'].append(acl_string)
        
        standard_configs[path_name] = config
    
    return standard_configs