"""Bootstrap to load binary TrajectoryCalc, Vector extensions"""
from typing_extensions import Union, Final

from py_ballisticcalc.unit import Distance, PreferredUnits

from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_calc._trajectory_calc import (
    Config,
    get_correction,
    calculate_energy,
    calculate_ogw,
    create_trajectory_row,
    _TrajectoryDataFilter,
    _WindSock
)

cZeroFindingAccuracy: Final[float] = 0.000005
cMinimumVelocity: Final[float] = 50.0
cMaximumDrop: Final[float] = -15000
cMaxIterations: Final[int] = 20
cGravityConstant: Final[float] = -32.17405
cMinimumAltitude: Final[float] = -1410.748  # ft

_globalChartResolution: float = 0.2  # ft
_globalUsePowderSensitivity = False
_globalMaxCalcStepSizeFeet: float = 0.5


def get_global_max_calc_step_size() -> Distance:
    return PreferredUnits.distance(Distance.Foot(_globalMaxCalcStepSizeFeet))


def reset_globals() -> None:
    # pylint: disable=global-statement
    global _globalUsePowderSensitivity, _globalMaxCalcStepSizeFeet
    _globalUsePowderSensitivity = False
    _globalMaxCalcStepSizeFeet = 0.5


def set_global_max_calc_step_size(value: Union[float, Distance]) -> None:
    # pylint: disable=global-statement
    global _globalMaxCalcStepSizeFeet
    if (_value := PreferredUnits.distance(value)).raw_value <= 0:
        raise ValueError("_globalMaxCalcStepSize have to be > 0")
    _globalMaxCalcStepSizeFeet = _value >> Distance.Foot


try:
    # replace with cython based implementation
    from py_ballisticcalc_exts.trajectory_calc import TrajectoryCalc  # type: ignore
except ImportError as err:
    """Fallback to pure python"""
    from py_ballisticcalc.trajectory_calc._trajectory_calc import TrajectoryCalc

    logger.debug(err)

__all__ = (
    'TrajectoryCalc',
    'get_global_max_calc_step_size',
    'set_global_max_calc_step_size',
    'reset_globals',
    'cZeroFindingAccuracy',
    'cMinimumVelocity',
    'cMaximumDrop',
    'cMaxIterations',
    'cGravityConstant',
    'cMinimumAltitude',
    'Config',
    'calculate_energy',
    'calculate_ogw',
    'get_correction',
    'create_trajectory_row',
    '_TrajectoryDataFilter',
    '_WindSock'
)
