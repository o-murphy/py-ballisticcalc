from py_ballisticcalc.extended.drag_extended import BallisticCoefficientExtended
from py_ballisticcalc.profile import *
from py_ballisticcalc.extended.trajectory_extended import TrajectoryCalculatorWithMBC


class ProfileExtended(Profile):

    _calculated_drag_function = None

    def calculate_trajectory(self):
        """
        :return: list[TrajectoryData]
        """
        bc = BallisticCoefficientExtended(self._bc_value, self._drag_table, self._bullet_diameter, self._bullet_weight)
        projectile = ProjectileWithDimensions(bc, self._bullet_diameter, self._bullet_length, self._bullet_weight)
        ammunition = Ammunition(projectile, self._muzzle_velocity)
        atmosphere = Atmosphere(self._altitude, self._pressure, self._temperature, self._humidity)
        zero = ZeroInfo(self._zero_distance, True, True, ammunition, atmosphere)
        twist = TwistInfo(self._twist_direction, self._twist)
        weapon = Weapon.create_with_twist(self._sight_height, zero, twist)
        wind = WindInfo.create_only_wind_info(self._wind_velocity, self._wind_direction)

        calc = TrajectoryCalculator()

        if not self._sight_angle.v:
            self._sight_angle = calc.sight_angle(ammunition, weapon, atmosphere)
        shot_info = ShotParameters(self._sight_angle, self._maximum_distance, self._distance_step)
        data = calc.trajectory(ammunition, weapon, atmosphere, shot_info, wind)
        self._trajectory_data = data
        # df = bc.calculated_drag_function()

        df = bc.calculated_drag_function()

        # print(1200, bc._bc_factory(1200))
        # print(800, bc._bc_factory(800))
        # print(700, bc._bc_factory(700))
        # print(500, bc._bc_factory(500))
        # print(200, bc._bc_factory(200))



        # print(df)
        self._calculated_drag_function = df


if __name__ == '__main__':
    profile = ProfileExtended()

    lines = [f'{point["B"]}\n'.replace('.', ',') for point in profile._calculated_drag_function]
    with open('calculated_df.txt', 'w') as fp:
        fp.writelines(lines)
