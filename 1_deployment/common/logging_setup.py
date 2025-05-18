import logging
from logging.handlers import RotatingFileHandler
from collections import namedtuple

LoggingOptions = namedtuple('LoggingOptions', ['filePath', 'level'])

def setup_logging(logger_name, logging_options ):
    """
    Set up logging for the script.

    Args:
        logger_name (str): Name of the logger (defaults to 'shuttle').
        logging_options (LoggingOptions): An object containing logging options.
    """
    # Set default values 
    
    logger_name = logger_name or "logger"
    logging_options = logging_options or LoggingOptions(filePath=None, level=logging.INFO)
    log_file_path = logging_options.filePath or None
    log_level = logging_options.level or logging.INFO

    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers = []
    
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler if log_file is specified
    if log_file_path:
        fh = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
