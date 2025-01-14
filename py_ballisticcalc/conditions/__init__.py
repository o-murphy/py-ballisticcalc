"""Bootstrap to load binary Wind, Shot extensions"""

from py_ballisticcalc.conditions._conditions import Atmo
from py_ballisticcalc.logger import logger

try:
    # replace with cython based implementation
    from py_ballisticcalc_exts import Wind, Shot  # type: ignore
except ImportError as err:
    """Fallback to pure python"""
    from py_ballisticcalc.conditions._conditions import Wind, Shot

    logger.debug(err)

__all__ = (
    'Wind',
    'Shot',
    'Atmo'
)
