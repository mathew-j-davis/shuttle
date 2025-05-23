"""
Configuration module for MDATP simulator

Handles reading config values for simulator behavior
"""
import os
import random
import logging

# Default delay range if no config is present (0-0 ms means no delay)
DEFAULT_MIN_DELAY_MS = 0
DEFAULT_MAX_DELAY_MS = 0

def read_delay_config(config_path=None):
    """
    Read delay configuration from a file
    
    Args:
        config_path: Path to config file. If None, looks for config.txt in the same directory
                     as this script.
    
    Returns:
        tuple: (min_delay_ms, max_delay_ms)
    """
    if config_path is None:
        # Default to config.txt in the same directory as this script
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'delay_config.txt')
    
    min_delay_ms = DEFAULT_MIN_DELAY_MS
    max_delay_ms = DEFAULT_MAX_DELAY_MS
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                lines = f.readlines()
                
                if len(lines) >= 2:
                    try:
                        min_delay_ms = int(lines[0].strip())
                        max_delay_ms = int(lines[1].strip())
                        
                        # Ensure min <= max
                        if min_delay_ms > max_delay_ms:
                            min_delay_ms, max_delay_ms = max_delay_ms, min_delay_ms
                            
                    except ValueError:
                        logging.warning(f"Invalid delay values in {config_path}, using defaults")
                else:
                    logging.warning(f"Config file {config_path} does not contain two lines, using defaults")
    except Exception as e:
        logging.warning(f"Error reading config file {config_path}: {e}, using defaults")
    
    return min_delay_ms, max_delay_ms

def get_random_delay_ms(min_ms, max_ms):
    """
    Get a random delay between min_ms and max_ms
    
    Args:
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds
        
    Returns:
        int: Random delay in milliseconds
    """
    if min_ms == max_ms:
        return min_ms
    return random.randint(min_ms, max_ms)

def apply_simulated_delay(min_ms, max_ms):
    """
    Sleep for a random duration between min_ms and max_ms
    
    Args:
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds
    """
    import time
    
    delay_ms = get_random_delay_ms(min_ms, max_ms)
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)  # Convert ms to seconds
