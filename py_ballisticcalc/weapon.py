from dataclasses import dataclass
from py_ballisticcalc.unit import *
from py_ballisticcalc.config import get_config

__all__ = ('Weapon',)


@dataclass
class Weapon:
    sight_height: Distance
    zero_distance: Distance = Distance(100, Distance.Yard)
    twist: Distance = Distance(0, Distance.Inch)
    click_value: Angular = Angular(0.25, Angular.MOA)

    def __init__(self, sight_height=90, zero_distance=100, twist=0, click_value=0.25):
        cfg = get_config()
        self.sight_height = Distance(sight_height, cfg.sight_height_unit)
        self.zero_distance = Distance(sight_height, cfg.distance_unit)
        self.twist = Distance(sight_height, cfg.twist_unit)
        self.click_value = Distance(click_value, cfg.)
