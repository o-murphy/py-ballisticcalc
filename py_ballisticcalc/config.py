from typing import NamedTuple

from py_ballisticcalc.unit import Unit

__all__ = ('MakeConfig', 'basic_config', 'get_config')


class MakeConfig(NamedTuple):
    sight_height_unit: Unit = Unit.Centimeter
    twist_unit: Unit = Unit.Inch
    velocity_unit: Unit = Unit.MPS
    distance_unit: Unit = Unit.Meter
    temperature_unit: Unit = Unit.Celsius
    weight_unit: Unit = Unit.Grain
    length_unit: Unit = Unit.Inch
    diameter_unit: Unit = Unit.Inch
    pressure_unit: Unit = Unit.HP
    drop_unit: Unit = Unit.Centimeter
    angular_unit: Unit = Unit.Degree
    adjustment_unit: Unit = Unit.Mil
    energy_unit: Unit = Unit.Joule
    max_calc_step: float = 1


_PYBC_CONFIG = MakeConfig()


def basic_config(config: MakeConfig):
    global _PYBC_CONFIG
    _PYBC_CONFIG = config


def get_config():
    return _PYBC_CONFIG
