"""
Logger injection system for Shuttle - eliminates need to pass logging_options everywhere
"""
from typing import Dict, Any, Callable, Optional
import functools
import logging
import inspect
from .logging_setup import setup_logging, LoggingOptions

# Global storage for logging options - set once at application startup
_global_logging_options: Dict[str, Any] = {}


def configure_logging(logging_options: Dict[str, Any]) -> None:
    """
    Configure global logging options. Call this once at application startup.
    
    Args:
        logging_options: Dictionary containing logging configuration (e.g., log_file_path)
    
    Example:
        configure_logging({'log_file_path': '/var/log/shuttle/app.log'})
    """
    global _global_logging_options
    _global_logging_options = logging_options


def _get_logger_name_from_context(func_name: str = None, func_module: str = None, instance=None) -> str:
    """Helper function to determine logger name from context."""

    if func_module and func_name:
        return f"{func_module}.{func_name}"
    else:
        return "shuttle.unknown"


def _resolve_logging_options():
    """Helper function to resolve logging options with fallback chain."""
    
    # Check global configuration
    if _global_logging_options:
        return LoggingOptions(
            filePath=_global_logging_options.get('log_file_path'),
            level=_global_logging_options.get('log_level', logging.INFO)
        )
    
    # fallback: create debug console-only logger for tests
    return LoggingOptions(
        filePath=None,  # No file logging
        level=logging.DEBUG  # Default to INFO level
    )


def _get_call_hierarchy():
    """Helper function to get call stack hierarchy for debug logging."""
    
    frame = inspect.currentframe().f_back.f_back  # Skip this function and get_logger
    call_chain = []
    target_function = None
    
    # Get the immediate caller of get_logger as our target function
    if frame:
        target_function = frame.f_code.co_name
        frame = frame.f_back  # Move to the caller of the target function
    
    # Now collect the call chain
    while frame and len(call_chain) < 5:  # Limit depth
        frame_func_name = frame.f_code.co_name
        module_name = frame.f_globals.get('__name__', '')
        
        # Skip wrapper functions
        if frame_func_name == 'wrapper':
            frame = frame.f_back
            continue
        
        # Only include shuttle modules
        if module_name.startswith('shuttle') or module_name == '__main__':
            if 'self' in frame.f_locals:
                self_obj = frame.f_locals['self']
                class_name = self_obj.__class__.__name__
                call_chain.append(f"{class_name}.{frame_func_name}")
            else:
                call_chain.append(frame_func_name)
        
        frame = frame.f_back
    
    # Reverse to get root → current order
    call_chain.reverse()
        
    return call_chain, target_function


def get_logger():
    """
    Get a logger with comprehensive fallback logic.

    Returns:
        Logger instance
    """
    
    # Auto-detect function info if not provided
    caller_frame = inspect.currentframe().f_back
    if caller_frame:
        func_name = caller_frame.f_code.co_name
        func_module = caller_frame.f_globals.get('__name__', 'unknown')
    
    # Determine logger name
    logger_name = _get_logger_name_from_context(func_name, func_module)
    
    # Resolve logging options
    resolved_logging_options = _resolve_logging_options()
    
    # Add call hierarchy to logger name if log level is DEBUG
    if resolved_logging_options.level == logging.DEBUG:
        try:
            call_chain, current = _get_call_hierarchy()
            if call_chain and current:
                chain_str = " → ".join(call_chain[-3:] + [current])
                logger_name = f"{logger_name}[CALL STACK: {chain_str}]"
        except Exception:
            # If hierarchy logging fails, don't break the main functionality
            pass
    
    # Create logger with hierarchy-enhanced name
    logger = setup_logging(logger_name, resolved_logging_options)
    
    return logger


def get_logging_options() -> Dict[str, Any]:
    """Get the current global logging options"""
    return _global_logging_options


def reset_logging_config() -> None:
    """Reset global logging configuration (mainly for testing)"""
    global _global_logging_options
    _global_logging_options = {}


# Example usage documentation
"""
Example Integration with Shuttle:

1. USAGE (for functions where debugging is important):
    
    from shuttle_common.logger_injection import get_logger
    
    def handle_throttle_check(source_file_path, quarantine_path):
        logger = get_logger()
        logger.info(f"Checking throttle for {source_file_path}")
        # Now you can debug this function normally!

2. METHOD USAGE:
    
    class Scanner:
        def scan_file(self, file_path):
            logger = get_logger()
            logger.debug(f"Scanning {file_path}")

3. GLOBAL CONFIGURATION (call once at startup):
    
    from shuttle_common.logger_injection import configure_logging
    
    def main():
        configure_logging({
            'log_file_path': '/var/log/shuttle/app.log',
            'log_level': logging.DEBUG
        })
"""