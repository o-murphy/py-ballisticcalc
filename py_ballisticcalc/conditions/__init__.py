"""Bootstrap to load binary Wind, Shot extensions"""

from py_ballisticcalc.conditions.conditions import Atmo
from py_ballisticcalc.logger import logger

try:
    # replace with cython based implementation
    from py_ballisticcalc_exts import Wind, Shot  # type: ignore
except ImportError as err:
    """Fallback to pure python"""
    from py_ballisticcalc.conditions.conditions import Wind, Shot
    logger.debug(err)
