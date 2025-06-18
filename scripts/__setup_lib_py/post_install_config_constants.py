#!/usr/bin/env python3
"""
Post Install Configuration Constants
Shared constants for configuration file naming and paths
"""

# Configuration file naming
CONFIG_FILE_PREFIX = "shuttle_post_install_config"
CONFIG_FILE_EXTENSION = "yaml"
CONFIG_DEFAULT_FILENAME = f"{CONFIG_FILE_PREFIX}uration.{CONFIG_FILE_EXTENSION}"  # shuttle_post_install_configuration.yaml

# Command history file naming
COMMAND_HISTORY_PREFIX = "shuttle_post_install_configuration_command_history"


def get_config_filename(environment=None):
    """Generate a configuration filename based on environment"""
    if environment:
        return f"{CONFIG_FILE_PREFIX}_{environment}.{CONFIG_FILE_EXTENSION}"
    return CONFIG_DEFAULT_FILENAME


def get_config_glob_pattern():
    """Get glob pattern for finding config files"""
    return f"{CONFIG_FILE_PREFIX}_*.{CONFIG_FILE_EXTENSION}"


def get_command_history_filename(timestamp):
    """Generate command history filename with timestamp"""
    return f"{COMMAND_HISTORY_PREFIX}_{timestamp}.log"