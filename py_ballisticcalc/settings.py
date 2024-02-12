"""Global settings of the py_ballisticcalc library"""
import logging
import dataclasses
from .unit import Unit, Distance

__all__ = ('Settings',)

class Metadataclass(type):
    """Provide representation method for static dataclasses."""
    def __repr__(cls):
        return '\n'.join(f'{field.name} = {getattr(cls, field.name)!r}'
                    for field in dataclasses.fields(cls))

class Settings:  # pylint: disable=too-few-public-methods
    """Global settings class of the py_ballisticcalc library"""

    @dataclasses.dataclass
    class Units(metaclass=Metadataclass):  # pylint: disable=too-many-instance-attributes
        """Default units for specified measures"""
        angular: Unit = Unit.DEGREE
        distance: Unit = Unit.YARD
        velocity: Unit = Unit.FPS
        pressure: Unit = Unit.IN_HG
        temperature: Unit = Unit.FAHRENHEIT
        diameter: Unit = Unit.INCH
        length: Unit = Unit.INCH
        weight: Unit = Unit.GRAIN
        adjustment: Unit = Unit.MIL
        drop: Unit = Unit.INCH
        energy: Unit = Unit.FOOT_POUND
        ogw: Unit = Unit.POUND
        sight_height: Unit = Unit.INCH
        target_height: Unit = Unit.INCH
        twist: Unit = Unit.INCH

    _MAX_CALC_STEP_SIZE: float = 1
    USE_POWDER_SENSITIVITY: bool = False

    @classmethod
    def set_max_calc_step_size(cls, value: [float, Distance]):
        """_MAX_CALC_STEP_SIZE setter
        :param value: [float, Distance] maximum calculation step (used internally)
        """
        logging.warning("Settings._MAX_CALC_STEP_SIZE: change this property "
                        "only if you know what you are doing; "
                        "too big step can corrupt calculation accuracy")
        if not isinstance(value, (Distance, float, int)):
            raise ValueError("MIN_CALC_STEP_SIZE have to be a type of 'Distance'")
        cls._MAX_CALC_STEP_SIZE = cls.Units.distance(value) >> Distance.Foot
