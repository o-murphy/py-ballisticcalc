from py_ballisticcalc.atmosphere import *
from py_ballisticcalc.weapon import Weapon, ZeroInfo, TwistInfo
from py_ballisticcalc.wind import WindInfo
from py_ballisticcalc.shot_parameters import ShotParameters

from py_ballisticcalc.profile import Profile

from py_ballisticcalc.extended.trajectory_calculator_extended import TrajectoryCalculatorExtended
from py_ballisticcalc.extended.drag_extended import BallisticCoefficientExtended
from py_ballisticcalc.extended.ammunition_extended import AmmunitionExtended
from py_ballisticcalc.extended.projectile_extended import ProjectileExtended, ProjectileWithDimensionsExtended


class ProfileExtended(Profile):

    _calculated_drag_function = None

    def calculate_trajectory(self):
        """
        :return: list[TrajectoryData]
        """
        bc = BallisticCoefficientExtended(self._bc_value, self._drag_table, self._bullet_diameter, self._bullet_weight)
        projectile = ProjectileWithDimensionsExtended(bc, self._bullet_diameter, self._bullet_length, self._bullet_weight)
        ammunition = AmmunitionExtended(projectile, self._muzzle_velocity)
        atmosphere = Atmosphere(self._altitude, self._pressure, self._temperature, self._humidity)
        zero = ZeroInfo(self._zero_distance, True, True, ammunition, atmosphere)
        twist = TwistInfo(self._twist_direction, self._twist)
        weapon = Weapon.create_with_twist(self._sight_height, zero, twist)
        wind = WindInfo.create_only_wind_info(self._wind_velocity, self._wind_direction)
        calc = TrajectoryCalculatorExtended()
        if not self._sight_angle.v:
            self._sight_angle = calc.sight_angle(ammunition, weapon, atmosphere)
        shot_info = ShotParameters(self._sight_angle, self._maximum_distance, self._distance_step)
        data = calc.trajectory(ammunition, weapon, atmosphere, shot_info, wind)
        self._trajectory_data = data

        df = bc.calculated_drag_function()
        print(df)
        self._calculated_drag_function = df


if __name__ == '__main__':
    profile = ProfileExtended(maximum_distance=(3000, unit.DistanceMeter), distance_step=(500, unit.DistanceMeter))
