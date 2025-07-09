"""Default logger for py_ballisticcalc library"""
import logging

__all__ = ('logger',
           'enable_file_logging',
           'disable_file_logging',
           )

formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)  # Lowest level for console

logger = logging.getLogger('py_balcalc')
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# File handler (optional, added dynamically)
file_handler = None


def enable_file_logging(filename: str = "debug.log") -> None:
    """Enable logging to a file, replacing any existing file handler."""
    global file_handler
    # Remove the existing file handler if it exists
    if file_handler is not None:
        disable_file_logging()

    # Add a new file handler
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)  # Log everything to the file
    file_formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)


def disable_file_logging() -> None:
    """Disable logging to a file if it is currently enabled."""
    global file_handler
    if file_handler is not None:
        logger.removeHandler(file_handler)
        file_handler.close()
        file_handler = None
