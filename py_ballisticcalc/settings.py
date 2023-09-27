from py_ballisticcalc.unit import *


__all__ = ('Settings',)


class Settings:

    class Units:
        sight_height: Unit = Unit.Inch
        twist: Unit = Unit.Inch
        velocity: Unit = Unit.FPS
        distance: Unit = Unit.Yard
        temperature: Unit = Unit.Celsius
        weight: Unit = Unit.Grain
        length: Unit = Unit.Inch
        diameter: Unit = Unit.Inch
        pressure: Unit = Unit.HP
        drop: Unit = Unit.Centimeter
        angular: Unit = Unit.Degree
        adjustment: Unit = Unit.Mil
        energy: Unit = Unit.Joule

    _MIN_CALC_STEP_SIZE: float
    USE_POWDER_SENSITIVITY: bool = False

    @classmethod
    def set_calc_step_size(cls, value: [float, Distance]):
        if not isinstance(value, (Distance, float, int)):
            raise ValueError("MIN_CALC_STEP_SIZE have to be a type of 'Distance'")
        cls._MIN_CALC_STEP_SIZE = (value if is_unit(value) else cls.Units.distance(value)).raw_value >> Distance.Foot
