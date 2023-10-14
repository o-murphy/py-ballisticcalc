"""Global settings of the py_ballisticcalc library"""
import logging

from .unit import Unit, Distance

__all__ = ('Settings',)


class Settings:  # pylint: disable=too-few-public-methods
    """Global settings class of the py_ballisticcalc library"""

    class Units:  # pylint: disable=too-few-public-methods
        """Default units for specified measures"""

        sight_height: Unit = Unit.INCH
        twist: Unit = Unit.INCH
        velocity: Unit = Unit.FPS
        distance: Unit = Unit.YARD
        temperature: Unit = Unit.CELSIUS
        weight: Unit = Unit.GRAIN
        length: Unit = Unit.INCH
        diameter: Unit = Unit.INCH
        pressure: Unit = Unit.HP
        drop: Unit = Unit.CENTIMETER
        angular: Unit = Unit.DEGREE
        adjustment: Unit = Unit.MIL
        energy: Unit = Unit.JOULE
        ogw: Unit = Unit.POUND
        target_height: Unit = Unit.INCH

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
