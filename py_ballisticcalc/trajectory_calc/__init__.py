"""Bootstrap to load binary TrajectoryCalc, Vector extensions"""
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_calc.trajectory_calc import (Config,
                                                              get_global_max_calc_step_size,
                                                              set_global_max_calc_step_size,
                                                              reset_globals)

try:
    # replace with cython based implementation
    from py_ballisticcalc_exts.trajectory_calc import TrajectoryCalc  # type: ignore
    from py_ballisticcalc_exts.vector import Vector  # type: ignore
except ImportError as err:
    """Fallback to pure python"""
    from py_ballisticcalc.trajectory_calc.trajectory_calc import TrajectoryCalc
    from py_ballisticcalc.vector.vector import Vector
    logger.debug(err)
