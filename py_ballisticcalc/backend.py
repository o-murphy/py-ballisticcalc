"""Searching for an available backends"""

from .logger import logger

# trying to use cython based backend
try:
    from py_ballisticcalc_exts import *  # pylint: disable=wildcard-import

    logger.info("Binary modules found, running in binary mode")
except ImportError as error:
    from .drag_model import *
    from .trajectory_calc import *

    logger.warning("Library running in pure python mode. "
                   "For better performance install 'py_ballisticcalc.exts' package")
