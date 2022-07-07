from py_ballisticcalc.extended.multiple_ballistic_coefficient import BallisticCoefficientExtended
from py_ballisticcalc.profile import *
from tjcalc import TjCalc


class ProfileExtended(Profile):
    def __init__(self,
                 bc_value: float = 0.223,
                 drag_table: int = DragTableG7,
                 bullet_diameter: (float, int) = (0.308, unit.DistanceInch),
                 bullet_length: (float, int) = (1.2, unit.DistanceInch),
                 bullet_weight: (float, int) = (167, unit.WeightGrain),
                 muzzle_velocity: (float, int) = (800, unit.VelocityMPS),
                 altitude: (float, int) = (0, unit.DistanceMeter),
                 pressure: (float, int) = (760, unit.PressureMmHg),
                 temperature: (float, int) = (15, unit.TemperatureCelsius),
                 humidity: float = 0.5,
                 zero_distance: (float, int) = (100, unit.DistanceMeter),
                 twist: (float, int) = (11, unit.DistanceInch),
                 twist_direction: int = 1,
                 sight_height: (float, int) = (90, unit.DistanceMillimeter),
                 sight_angle: (float, int) = (0, unit.AngularMOA),
                 maximum_distance: (float, int) = (1000, unit.DistanceMeter),
                 distance_step: (float, int) = (100, unit.DistanceMeter),
                 wind_velocity: (float, int) = (0, unit.VelocityKMH),
                 wind_direction: (float, int) = (0, unit.AngularDegree),
                 custom_drag_function: list[dict[str, float]] = None,
                 maximum_step_size: (float, int) = (1, unit.DistanceFoot)
                 ):
        self._custom_drag_function = custom_drag_function
        self._calculated_drag_function = None
        self._maximum_step_size = unit.Distance(*maximum_step_size)
        super(ProfileExtended, self).__init__(bc_value, drag_table, bullet_diameter, bullet_length, bullet_weight,
                                              muzzle_velocity, altitude, pressure, temperature, humidity, zero_distance,
                                              twist, twist_direction, sight_height, sight_angle, maximum_distance,
                                              distance_step, wind_velocity, wind_direction)

    def calculate_trajectory(self):
        """
        :return: list[TrajectoryData]
        """

        bc = BallisticCoefficientExtended(self._bc_value, self._drag_table, self._bullet_diameter, self._bullet_weight,
                                          self._custom_drag_function)
        projectile = ProjectileWithDimensions(bc, self._bullet_diameter, self._bullet_length, self._bullet_weight)
        ammunition = Ammunition(projectile, self._muzzle_velocity)
        atmosphere = Atmosphere(self._altitude, self._pressure, self._temperature, self._humidity)
        zero = ZeroInfo(self._zero_distance, True, True, ammunition, atmosphere)
        twist = TwistInfo(self._twist_direction, self._twist)
        weapon = Weapon.create_with_twist(self._sight_height, zero, twist)
        wind = WindInfo.create_only_wind_info(self._wind_velocity, self._wind_direction)

        calc = TjCalc()
        calc.maximum_calculator_step_size = self._maximum_step_size

        if not self._sight_angle.v:
            self._sight_angle = calc.sight_angle(ammunition, weapon, atmosphere)
        shot_info = ShotParameters(self._sight_angle, self._maximum_distance, self._distance_step)
        data = calc.trajectory(ammunition, weapon, atmosphere, shot_info, wind)
        self._trajectory_data = data

        df = bc.calculated_drag_function()
        self._calculated_drag_function = df

#
# if __name__ == '__main__':
#
#     """
#     Example for Lapua .30 10,85 g / 167 gr Scenar OTM GB422 bullet
#     """
#
#     custom_drag_func = [
#         {'A': 0.0, 'B': 0.18}, {'A': 0.4, 'B': 0.178}, {'A': 0.5, 'B': 0.154},
#         {'A': 0.6, 'B': 0.129}, {'A': 0.7, 'B': 0.131}, {'A': 0.8, 'B': 0.136},
#         {'A': 0.825, 'B': 0.14}, {'A': 0.85, 'B': 0.144}, {'A': 0.875, 'B': 0.153},
#         {'A': 0.9, 'B': 0.177}, {'A': 0.925, 'B': 0.226}, {'A': 0.95, 'B': 0.26},
#         {'A': 0.975, 'B': 0.349}, {'A': 1.0, 'B': 0.427}, {'A': 1.025, 'B': 0.45},
#         {'A': 1.05, 'B': 0.452}, {'A': 1.075, 'B': 0.45}, {'A': 1.1, 'B': 0.447},
#         {'A': 1.15, 'B': 0.437}, {'A': 1.2, 'B': 0.429}, {'A': 1.3, 'B': 0.418},
#         {'A': 1.4, 'B': 0.406}, {'A': 1.5, 'B': 0.394}, {'A': 1.6, 'B': 0.382},
#         {'A': 1.8, 'B': 0.359}, {'A': 2.0, 'B': 0.339}, {'A': 2.2, 'B': 0.321},
#         {'A': 2.4, 'B': 0.301}, {'A': 2.6, 'B': 0.28}, {'A': 3.0, 'B': 0.25},
#         {'A': 4.0, 'B': 0.2}, {'A': 5.0, 'B': 0.18}
#     ]
#
#     profile = ProfileExtended(drag_table=0, custom_drag_function=custom_drag_func)
#     custom_drag_func_trajectory = profile.trajectory_data
#
#     profile1 = ProfileExtended()
#     g7_bc_trajectory = profile1.trajectory_data
#
#     for i, d in enumerate(g7_bc_trajectory):
#         distance = d.travelled_distance.convert(unit.DistanceMeter)
#         g7_path = d.drop.convert(unit.DistanceCentimeter)
#         custom_path = custom_drag_func_trajectory[i].drop.convert(unit.DistanceCentimeter)
#         print(f'Distance: {distance}, i7 * G7 BC: {g7_path}, Custom Drag Table: {custom_path}')
