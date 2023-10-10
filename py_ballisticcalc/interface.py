"""Implements basic interface for the ballistics calculator"""
import math
from dataclasses import dataclass, field

from .conditions import Atmo, Wind, Shot
from .munition import Weapon, Ammo
from .settings import Settings as Set
# pylint: disable=import-error,no-name-in-module
from .trajectory_calc import TrajectoryCalc
from .trajectory_data import TrajectoryData, TrajFlag
from .unit import Angular, Distance, is_unit

__all__ = ('Calculator',)


@dataclass
class Calculator:
    """Basic interface for the ballistics calculator"""

    weapon: Weapon
    ammo: Ammo
    zero_atmo: Atmo

    _elevation: Angular = field(init=False, repr=True, compare=False,
                                default_factory=lambda: Angular.Degree(0))
    _calc: TrajectoryCalc = field(init=False, repr=True, compare=False, default=None)

    @property
    def elevation(self):
        """get current barrel elevation"""
        return self._elevation

    @property
    def cdm(self):
        """returns custom drag function based on input data"""
        return self._calc.cdm

    def update_elevation(self):
        """Recalculates barrel elevation for weapon and zero atmo"""
        self._calc = TrajectoryCalc(self.ammo)
        self._elevation = self._calc.sight_angle(self.weapon, self.zero_atmo)

    def trajectory(self, shot: Shot, current_atmo: Atmo, winds: list[Wind]) -> list:
        """Calculates trajectory with current conditions
        :param shot: shot parameters
        :param current_atmo: current atmosphere conditions
        :param winds: current winds list
        :return: trajectory table
        """
        self._calc = TrajectoryCalc(self.ammo)
        if not self._elevation and not shot.sight_angle:
            self.update_elevation()
            shot.sight_angle = self._elevation
        data = self._calc.trajectory(self.weapon, current_atmo, shot, winds)
        return data

    def zero_given_elevation(self, shot: Shot,
                             winds: list[Wind] = None) -> TrajectoryData:
        """Find the zero distance for a given barrel elevation"""
        self._calc = TrajectoryCalc(self.ammo)
        if not winds:
            winds = [Wind()]

        data = self._calc.trajectory(
            self.weapon, self.zero_atmo, shot, winds,
            filter_flags=(TrajFlag.ZERO_UP | TrajFlag.ZERO_DOWN).value)
        if len(data) < 1:
            raise ArithmeticError("Can't found zero crossing points")
        return data

    @staticmethod
    def danger_space(trajectory: TrajectoryData, target_height: [float, Distance]) -> Distance:
        """Given a TrajectoryData row, we have the angle of travel
        of bullet at that point in its trajectory, which is at distance *d*.
        "Danger Space" is defined for *d* and for a target of height
        `targetHeight` as the error range for the target, meaning
        if the trajectory hits the center of the target when
        the target is exactly at *d*, then "Danger Space" is the distance
        before or after *d* across which the bullet would still hit somewhere on the target.
        (This ignores windage; vertical only.)

        :param trajectory: single point from trajectory table
        :param target_height: error range for the target
        :return: danger space for target_height specified
        """

        target_height = (target_height if is_unit(target_height)
                         else Set.Units.target_height(target_height)) >> Distance.Yard
        traj_angle_tan = math.tan(trajectory.angle >> Angular.Radian)
        return Distance.Yard(-(target_height / traj_angle_tan))

    @staticmethod
    def to_dataframe(trajectory: list[TrajectoryData]):
        import pandas as pd
        col_names = TrajectoryData._fields
        trajectory = [p.in_def_units() for p in trajectory]
        return pd.DataFrame(trajectory, columns=col_names)

    def show_plot(self, shot, winds):
        import matplotlib
        import matplotlib.pyplot as plt
        matplotlib.use('TkAgg')
        self._calc = TrajectoryCalc(self.ammo)
        # self.update_elevation()
        data = self._calc.trajectory(self.weapon, self.zero_atmo, shot, winds,
                                     TrajFlag.ALL.value)  # Step in 10-yard increments to produce smoother curves
        df = self.to_dataframe(data)
        ax = df.plot(x='distance', y=['drop'], ylabel=Set.Units.drop.symbol)

        # zero_d = self.weapon.zero_distance >> Set.Units.distance
        # zero = ax.plot([zero_d, zero_d], [df['drop'].min(), df['drop'].max()], linestyle='--')

        for p in data:

            if TrajFlag(p.flag) & TrajFlag.ZERO:
                ax.plot([p.distance >> Set.Units.distance, p.distance >> Set.Units.distance],
                        [df['drop'].min(), p.drop >> Set.Units.drop], linestyle=':')
            if TrajFlag(p.flag) & TrajFlag.MACH:
                ax.plot([p.distance >> Set.Units.distance, p.distance >> Set.Units.distance],
                        [df['drop'].min(), p.drop >> Set.Units.drop], linestyle='--', label='mach')
                ax.text(p.distance >> Set.Units.distance, df['drop'].min(), " Mach")

        sh = self.weapon.sight_height >> Set.Units.drop

        # # scope line
        x_values = [0, df.distance.max()]  # Adjust these as needed
        # y_values = [sh, sh - df.distance.max() * math.tan(self.elevation >> Angular.Degree)]  # Adjust these as needed
        y_values = [0, 0]  # Adjust these as needed
        ax.plot(x_values, y_values, linestyle='--', label='scope line')
        ax.text(df.distance.max() - 100, -100, "Scope")

        # # # barrel line
        # elevation = self.elevation >> Angular.Degree
        #
        # y = sh / math.cos(elevation)
        # x0 = sh / math.sin(elevation)
        # x1 = sh * math.sin(elevation)
        # x_values = [0, x0]
        # y_values = [-sh, 0]
        # ax.plot(x_values, y_values, linestyle='-.', label='barrel line')

        df.plot(x='distance', xlabel=Set.Units.distance.symbol,
                y=['velocity'], ylabel=Set.Units.velocity.symbol,
                secondary_y=True,
                ylim=[0, df['velocity'].max()], ax=ax)
        plt.title = f"{self.weapon.sight_height} {self.weapon.zero_distance}"

        plt.show()
        # ax = df.plot(y=[c.tableCols['Drop'][0]], ylabel=UNIT_DISPLAY[c.heightUnits].units)
        # df.plot(y=[c.tableCols['Velocity'][0]], ylabel=UNIT_DISPLAY[c.bullet.velocityUnits].units, secondary_y=True,
        #         ylim=[0, df[c.tableCols['Velocity'][0]].max()], ax=ax)
        # plt.show()
