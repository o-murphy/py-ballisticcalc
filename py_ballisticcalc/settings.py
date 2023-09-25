from dataclasses import dataclass

from py_ballisticcalc.unit import *


__all__ = (
    'MIN_CALC_STEP_SIZE',
    'USE_POWDER_SENSITIVITY',
    'DefaultUnits'
)


@dataclass
class DefaultUnits:
    sight_height: Unit = Unit.Centimeter
    twist: Unit = Unit.Inch
    velocity: Unit = Unit.MPS
    distance: Unit = Unit.Meter
    temperature: Unit = Unit.Celsius
    weight: Unit = Unit.Grain
    length: Unit = Unit.Inch
    diameter: Unit = Unit.Inch
    pressure: Unit = Unit.HP
    drop: Unit = Unit.Centimeter
    angular: Unit = Unit.Degree
    adjustment: Unit = Unit.Mil
    energy: Unit = Unit.Joule


MIN_CALC_STEP_SIZE: Distance = Distance(1, Distance.Foot)
USE_POWDER_SENSITIVITY: bool = False
