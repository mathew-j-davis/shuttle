# """
# Hierarchy-aware logging for Shuttle - shows call stack context
# """
# import inspect
# import functools
# import logging
# from typing import Dict, Any, Callable, Optional
# from .logging_setup import setup_logging, LoggingOptions

# # Global storage for logging options
# _global_logging_options: Dict[str, Any] = {}


# def configure_logging(logging_options: Dict[str, Any]) -> None:
#     """Configure global logging options. Call once at startup."""
#     global _global_logging_options
#     _global_logging_options = logging_options


# def with_logger(func: Callable) -> Callable:
#     """
#     Decorator that creates a logger with call hierarchy information.
#     Shows the call chain in debug logs for better traceability.
#     """
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         # Get call stack for context
#         frame = inspect.currentframe().f_back
#         call_chain = []
        
#         while frame and len(call_chain) < 5:  # Limit depth
#             func_name = frame.f_code.co_name
#             module_name = frame.f_globals.get('__name__', '')
            
#             # Only include shuttle modules
#             if module_name.startswith('shuttle') or module_name == '__main__':
#                 if 'self' in frame.f_locals:
#                     self_obj = frame.f_locals['self']
#                     class_name = self_obj.__class__.__name__
#                     call_chain.append(f"{class_name}.{func_name}")
#                 else:
#                     call_chain.append(func_name)
            
#             frame = frame.f_back
        
#         # Reverse to get root → current order
#         call_chain.reverse()
        
#         # Determine current function name
#         if args and hasattr(args[0], '__class__'):
#             self = args[0]
#             current = f"{self.__class__.__name__}.{func.__name__}"
#             logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}.{func.__name__}"
#         else:
#             current = func.__name__
#             logger_name = f"{func.__module__}.{func.__name__}"
        
#         # Get logging options with robust fallback
#         logging_options = None
        
#         # First check for instance-level logging options (legacy support)
#         if args and hasattr(args[0], 'logging_options'):
#             logging_options = args[0].logging_options
        
#         # If not found, check global configuration
#         if logging_options is None and _global_logging_options:
#             logging_options = LoggingOptions(
#                 filePath=_global_logging_options.get('log_file_path'),
#                 level=_global_logging_options.get('log_level', logging.INFO)
#             )
        
#         # Final fallback: create default console-only logger
#         if logging_options is None:
#             # Default to INFO level, console output only
#             logging_options = LoggingOptions(
#                 filePath=None,  # No file logging
#                 level=logging.INFO  # Default to INFO level
#             )
        
#         # Create logger
#         logger = setup_logging(logger_name, logging_options)
        
#         # Log call hierarchy in debug mode
#         if call_chain and logger.isEnabledFor(logging.DEBUG):
#             chain_str = " → ".join(call_chain[-3:] + [current])
#             logger.debug(f"[CALL STACK: {chain_str}]")
        
#         # Inject logger
#         if 'logger' in inspect.signature(func).parameters:
#             kwargs['logger'] = logger
        
#         return func(*args, **kwargs)
    
#     return wrapper