"""Global settings of the py_ballisticcalc library"""
import logging
from dataclasses import dataclass, fields

from .unit import Unit, Distance, AbstractUnit

__all__ = ('Settings',)


class Metadataclass(type):
    """Provide representation method for static dataclasses."""

    def __repr__(cls):
        return '\n'.join(f'{field.name} = {getattr(cls, field.name)!r}'
                         for field in fields(cls))


class Settings:  # pylint: disable=too-few-public-methods
    """Global settings class of the py_ballisticcalc library"""

    @dataclass
    class Units(metaclass=Metadataclass):  # pylint: disable=too-many-instance-attributes
        """Default units for specified measures"""

        # TODO: move it to Units, use instance instead of class
        # TODO: add default sets for imperial/metric

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


@dataclass
class PreferUnits:  # pylint: disable=too-few-public-methods
    """
    TODO: move it to Units, use it instead of TypedUnits
    Abstract class to apply auto-conversion values to
    specified units by type-hints in inherited dataclasses
    """

    def __setattr__(self, key, value):
        """
        converts value to specified units by type-hints in inherited dataclass
        """

        _fields = self.__getattribute__('__dataclass_fields__')

        if (_field := _fields.get(key)) and value is not None and not isinstance(value, AbstractUnit):
            # print(f"{key=} {value=} {type(value)}")

            if units := _field.metadata.get('units'):

                if isinstance(units, Unit):
                    value = units(value)
                elif isinstance(units, str):
                    value = Settings.Units.__dict__[units](value)
                else:
                    raise TypeError("Unsupported unit or dimension")

            # elif isinstance(default_factory := _field.default_factory, typing.Callable):
            #     warnings.warn(
            #         "Using 'default_factory' is deprecated, "
            #         "use 'metadata={'units': 'sight_height'} for preferred units"
            #         "or {'units': Unit.Meter}' instead. metadata['units'] has a priority",
            #         DeprecationWarning
            #     )
            #
            #     if isinstance(value, Unit):
            #         value = None
            #     else:
            #         value = default_factory()(value)

        super().__setattr__(key, value)
