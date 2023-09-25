from dataclasses import dataclass

from py_ballisticcalc.unit import *

__all__ = ('Weapon',)


@dataclass
class Weapon:
    sight_height: Distance
    zero_distance: Distance
    twist: Distance
    click_value: Angular

    def __init__(self,
                 sight_height: [float, Distance],
                 zero_distance: [float, Distance] = Distance(100, Distance.Yard),
                 twist: [float, Distance] = Distance(0, Distance.Inch),
                 click_value: [float, Angular] = Angular(0.25, Angular.Mil)):

        self.sight_height = sight_height if is_unit(sight_height) else Distance(sight_height, DefaultUnits.sight_height)
        self.zero_distance = zero_distance if is_unit(zero_distance) else Distance(zero_distance, DefaultUnits.distance)
        self.twist = twist if is_unit(twist) else Distance(twist, DefaultUnits.twist)
        self.click_value = click_value if is_unit(click_value) else Angular(click_value, DefaultUnits.adjustment)
