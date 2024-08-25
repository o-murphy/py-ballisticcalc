# pylint: disable=wildcard-import
"""Check for available backends"""
import warnings

from .logger import logger

# try to use cython based backend
try:
    from py_ballisticcalc_exts import (TrajectoryCalc,  # type: ignore
                                       Vector,
                                       get_global_max_calc_step_size,
                                       get_global_use_powder_sensitivity,
                                       set_global_max_calc_step_size,
                                       set_global_use_powder_sensitivity,
                                       reset_globals)

    logger.debug("Binary modules found, running in binary mode")
except ImportError as error:
    from .trajectory_calc import (TrajectoryCalc,  # type: ignore
                                  Vector,
                                  get_global_max_calc_step_size,
                                  get_global_use_powder_sensitivity,
                                  set_global_max_calc_step_size,
                                  set_global_use_powder_sensitivity,
                                  reset_globals)

    warnings.warn("Library running in pure python mode. "
                  "For better performance install 'py_ballisticcalc.exts' package")

__all__ = (
    'TrajectoryCalc',
    'Vector',
    'get_global_max_calc_step_size',
    'get_global_use_powder_sensitivity',
    'set_global_max_calc_step_size',
    'set_global_use_powder_sensitivity',
    'reset_globals',
)
