
import pyximport

from py_ballisticcalc.environment import *
from py_ballisticcalc.projectile import Ammo
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.weapon import Weapon

pyximport.install(language_level=3)

from py_ballisticcalc.trajectory_calc import TrajectoryCalc
from py_ballisticcalc.unit import *








class BalCalc:
    def __init__(self, config: Config):
        self.sight_angle = None
        self._config = config
        self._calc = TrajectoryCalc(Distance(config.max_calc_step, config.distance_unit))

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config: Config):
        self._config = config
        self._calc.set_max_calc_step_size(Distance(config.max_calc_step, config.distance_unit))

    def set_zero(self, ammo: Ammo, weapon: Weapon, atmo: Atmosphere):
        self.sight_angle = self._calc.sight_angle(ammo, weapon, atmo)

    def calculate(self, ammo: Ammo, weapon: Weapon, atmo: Atmosphere, shot: Shot, winds: list[Wind]):
        if not self.sight_angle:
            self.set_zero(ammo, weapon, atmo)
        return self._calc.trajectory(ammo, weapon, atmo, shot, winds)
