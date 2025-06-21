#!/usr/bin/env python3
"""
Post Install Configuration Constants
Shared constants for configuration file naming and paths
"""

# Configuration file naming
INSTRUCTIONS_FILE_PREFIX = "post_install_config_steps"
INSTRUCTIONS_FILE_EXTENSION = "yaml"
INSTRUCTIONS_DEFAULT_FILENAME = "post_install_config_steps.yaml"

# Command history file naming
COMMAND_HISTORY_PREFIX = "shuttle_post_install_config_command_history"


def get_config_filename(environment=None):
    """Generate a configuration filename based on environment"""
    if environment:
        return f"{INSTRUCTIONS_FILE_PREFIX}_{environment}.{INSTRUCTIONS_FILE_EXTENSION}"
    return INSTRUCTIONS_DEFAULT_FILENAME


def get_config_glob_pattern():
    """Get glob pattern for finding config files"""
    return f"{INSTRUCTIONS_FILE_PREFIX}_*.{INSTRUCTIONS_FILE_EXTENSION}"


def get_command_history_filename(timestamp):
    """Generate command history filename with timestamp"""
    return f"{COMMAND_HISTORY_PREFIX}_{timestamp}.log"