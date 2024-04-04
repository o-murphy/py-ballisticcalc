# pylint: disable=wildcard-import
"""Check for available backends"""

from .logger import logger

# try to use cython based backend
try:
    from py_ballisticcalc_exts import TrajectoryCalc

    logger.info("Binary modules found, running in binary mode")
except ImportError as error:
    from .trajectory_calc import TrajectoryCalc

    logger.warning("Library running in pure python mode. "
                   "For better performance install 'py_ballisticcalc.exts' package")

__all__ = ('TrajectoryCalc', )
