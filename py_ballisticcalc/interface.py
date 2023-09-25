
import pyximport

from py_ballisticcalc.conditions import *
from py_ballisticcalc.projectile import Ammo
from py_ballisticcalc.weapon import Weapon

pyximport.install(language_level=3)

from py_ballisticcalc.trajectory_calc import TrajectoryCalc
from py_ballisticcalc.unit import *








class BalCalc:
    def __init__(self):
        self.sight_angle = None
        self._calc = TrajectoryCalc()

    def set_zero(self, ammo: Ammo, weapon: Weapon, atmo: Atmo):
        self.sight_angle = self._calc.sight_angle(ammo, weapon, atmo)

    def calculate(self, ammo: Ammo, weapon: Weapon, atmo: Atmo, shot: Shot, winds: list[Wind]):
        if not self.sight_angle:
            self.set_zero(ammo, weapon, atmo)
        return self._calc.trajectory(ammo, weapon, atmo, shot, winds)
