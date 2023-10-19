"""Implements basic interface for the ballistics calculator"""
from dataclasses import dataclass, field

from .conditions import Atmo, Shot
from .munition import Weapon, Ammo
# pylint: disable=import-error,no-name-in-module
from .backend import *
from .trajectory_data import HitResult
from .unit import Angular, Distance
from .settings import Settings

__all__ = ('Calculator',)


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    weapon: Weapon
    ammo: Ammo
    zero_atmo: Atmo = field(default_factory=Atmo.icao)
    _elevation: Angular = field(init=False, repr=True, compare=False,
                                default_factory=lambda: Angular.Degree(0))
    _calc: TrajectoryCalc = field(init=False, repr=True, compare=False, default=None)

    def __post_init__(self):
        self.calculate_elevation()

    @property
    def elevation(self):
        """get current barrel elevation"""
        return self._elevation

    @property
    def cdm(self):
        """returns custom drag function based on input data"""
        return self._calc.cdm

    def calculate_elevation(self):
        """Recalculates barrel elevation for weapon and zero atmo"""
        self._calc = TrajectoryCalc(self.ammo)
        self._elevation = self._calc.zero_angle(self.weapon, self.zero_atmo)

    def fire(self, shot: Shot, trajectory_step: [float, Distance],
             extra_data: bool = False) -> HitResult:
        """Calculates trajectory
        :param shot: shot parameters
        :param trajectory_step: step between trajectory points
        :param extra_data: True => store TrajectoryData for every step;
            False => store TrajectoryData only for each trajectory_step
        """
        step = Settings.Units.distance(trajectory_step)
        self._calc = TrajectoryCalc(self.ammo)
        if not shot.zero_angle:
            shot.zero_angle = self._elevation
        data = self._calc.trajectory(self.weapon, shot, step, extra_data)
        return HitResult(self.weapon, shot, data, extra_data)
