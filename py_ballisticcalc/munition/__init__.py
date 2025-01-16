"""Bootstrap to load binary Weapon extensions"""

from py_ballisticcalc.munition._munition import (Sight, SightFocalPlane,
                                                 SightReticleStep, SightClicks)
from py_ballisticcalc.logger import logger

try:
    # replace with cython based implementation
    from py_ballisticcalc_exts.munition import Weapon, Ammo  # type: ignore
except ImportError as err:
    """Fallback to pure python"""
    from py_ballisticcalc.munition._munition import Weapon, Ammo
    logger.debug(err)

__all__ = ('Weapon', 'Ammo', 'Sight', 'SightFocalPlane', 'SightClicks', 'SightReticleStep')
