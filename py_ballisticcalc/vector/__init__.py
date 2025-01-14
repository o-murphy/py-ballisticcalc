"""Bootstrap to load binary Vector extension"""

from py_ballisticcalc.logger import logger

try:
    # replace with cython based implementation
    from py_ballisticcalc_exts.vector import Vector  # type: ignore
except ImportError as err:
    """Fallback to pure python"""
    from py_ballisticcalc.vector.vector import Vector
    logger.debug(err)