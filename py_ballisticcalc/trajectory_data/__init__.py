from py_ballisticcalc.trajectory_data._trajectory_data import HitResult, TrajFlag, DangerSpace
from py_ballisticcalc.logger import logger
import platform


try:
    if platform.python_implementation() == "PyPy":
        from py_ballisticcalc.trajectory_data._trajectory_data import TrajectoryData
    else:
        # replace with cython based implementation
        from py_ballisticcalc_exts import TrajectoryData  # type: ignore
except ImportError as err:
    from py_ballisticcalc.trajectory_data._trajectory_data import TrajectoryData
    logger.debug(err)


__all__ = ('TrajectoryData', 'HitResult', 'TrajFlag', 'DangerSpace')
