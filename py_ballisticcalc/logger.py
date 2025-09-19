"""Logging configuration and utilities for py_ballisticcalc library.

This module provides a centralized logging system for the py_ballisticcalc library,
including both console and optional file logging capabilities. The logger is configured
with appropriate formatters and can be dynamically adjusted for different logging needs.

The module exposes a pre-configured logger instance and utility functions for managing
file-based logging. By default, only console logging is enabled with INFO level,
but file logging can be enabled as needed for debugging or detailed analysis.

Global Variables:
    - logger: Pre-configured logger instance for the library.
    - file_handler: Global file handler reference (None when file logging disabled).

Functions:
    enable_file_logging: Enable logging to a file with DEBUG level.
    disable_file_logging: Disable file logging and clean up resources.

Examples:
    Basic logging usage:
    ```python
    from py_ballisticcalc.logger import logger
    
    logger.info("Ballistic calculation started")
    logger.warning("Trajectory calculation ended before requested distance")
    logger.error("Unable to find angle to hit target")
    ```
    
    Enable file logging for debugging:
    ```python
    from py_ballisticcalc.logger import enable_file_logging, disable_file_logging
    
    # Enable detailed logging to file
    enable_file_logging("ballistics_debug.log")
    
    # Perform calculations with detailed logging
    # ... ballistic calculations ...
    
    # Clean up file logging
    disable_file_logging()
    ```

Note:
    The logger name 'py_balcalc' is used for historical compatibility.
    All log messages from the library components will be routed through this logger.
"""
import logging
from typing import Optional

__all__ = ('logger',
           'enable_file_logging',
           'disable_file_logging',
)

formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)  # Lowest level for console

logger: logging.Logger = logging.getLogger('py_balcalc')
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# File handler (optional, added dynamically)
file_handler: Optional[logging.FileHandler] = None


def enable_file_logging(filename: str = "debug.log") -> None:
    """Enable logging to a file with DEBUG level output.

    This function configures file-based logging, replacing any existing file handler.
    File logging captures all DEBUG level messages and above with timestamp information,
    providing detailed logging for debugging and analysis purposes.

    Args:
        filename: Name of the log file to create. Defaults to "debug.log".
                 The file will be created in the current working directory
                 unless an absolute path is provided.

    Note:
        If file logging is already enabled, the existing file handler will be
        removed and replaced with a new one using the specified filename.
        The file will be opened in append mode, so existing content is preserved.

    Examples:
        ```python
        from py_ballisticcalc.logger import enable_file_logging, logger
        
        # Enable detailed file logging
        enable_file_logging("trajectory_analysis.log")
        
        # All subsequent log messages will be written to file
        logger.debug("Detailed calculation step information")
        logger.info("Calculation completed successfully")
        ```
    """
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
    """Disable file logging and clean up resources.

    This function removes the file handler from the logger and properly closes the file handle,
    ensuring no resource leaks. After calling this function, only console logging will remain active.

    Note:
        If no file logging is currently enabled, this function has no effect.
        It's safe to call this function multiple times or when file logging is already disabled.

    Examples:
        ```python
        from py_ballisticcalc.logger import disable_file_logging
        
        # Clean up file logging when done with detailed analysis
        disable_file_logging()
        
        # Only console logging remains active
        ```
    """
    global file_handler
    if file_handler is not None:
        logger.removeHandler(file_handler)
        file_handler.close()
        file_handler = None
