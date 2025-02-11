import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_file=None, log_level=logging.INFO):
    """
    Set up logging for the script.

    Args:
        log_file (str): Path to the log file.
        log_level (int): Logging level (e.g., logging.DEBUG, logging.INFO).
    """
    # Create logger
    logger = logging.getLogger('shuttle')
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler if log_file is specified
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
