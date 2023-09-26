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

    MIN_CALC_STEP_SIZE: Distance = Distance.Foot(1)
    USE_POWDER_SENSITIVITY: bool = False
