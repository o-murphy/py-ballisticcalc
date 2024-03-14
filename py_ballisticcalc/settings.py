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
        angular: Unit = Unit.Degree
        distance: Unit = Unit.Yard
        velocity: Unit = Unit.FPS
        pressure: Unit = Unit.InHg
        temperature: Unit = Unit.Fahrenheit
        diameter: Unit = Unit.Inch
        length: Unit = Unit.Inch
        weight: Unit = Unit.Grain
        adjustment: Unit = Unit.Mil
        drop: Unit = Unit.Inch
        energy: Unit = Unit.FootPound
        ogw: Unit = Unit.Pound
        sight_height: Unit = Unit.Inch
        target_height: Unit = Unit.Inch
        twist: Unit = Unit.Inch

    _MAX_CALC_STEP_SIZE: float = 0.5
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

    @classmethod
    def get_max_calc_step_size(cls) -> [float, Distance]:
        return cls._MAX_CALC_STEP_SIZE
