from py_ballisticcalc.projectile import *
from py_ballisticcalc.drag import *
from py_ballisticcalc.weapon import *
from py_ballisticcalc.trajectory_calculator import *
from py_ballisticcalc.atmosphere import *
from py_ballisticcalc.shot_parameters import *
from py_ballisticcalc.bmath import unit


class Profile(object):
    def __init__(self,
                 bc_value: float = 0.275,
                 drag_table: int = DragTableG7,
                 bullet_diameter: (float, int) = (0.308, unit.DistanceInch),
                 bullet_length: (float, int) = (1.3, unit.DistanceInch),
                 bullet_weight: (float, int) = (178, unit.WeightGrain),
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
                 maximum_distance: (float, int) = (1001, unit.DistanceMeter),
                 distance_step: (float, int) = (100, unit.DistanceMeter),
                 wind_velocity: (float, int) = (0, unit.VelocityKMH),
                 wind_direction: (float, int) = (0, unit.AngularDegree)
                 ):
        self._trajectory_data = None

        self._bc_value: float = bc_value
        self._drag_table: int = drag_table
        self._bullet_diameter: unit.Distance = unit.Distance(*bullet_diameter).validate()
        self._bullet_length: unit.Distance = unit.Distance(*bullet_length).validate()
        self._bullet_weight: unit.Weight = unit.Weight(*bullet_weight).validate()
        self._muzzle_velocity: unit.Velocity = unit.Velocity(*muzzle_velocity).validate()
        self._altitude: unit.Distance = unit.Distance(*altitude).validate()
        self._pressure: unit.Pressure = unit.Pressure(*pressure).validate()
        self._temperature: (float, int) = unit.Temperature(*temperature).validate()
        self._humidity: float = humidity
        self._zero_distance: unit.Distance = unit.Distance(*zero_distance).validate()
        self._twist: unit.Distance = unit.Distance(*twist).validate()
        self._twist_direction: int = twist_direction
        self._sight_height: unit.Distance = unit.Distance(*sight_height).validate()
        self._sight_angle: unit.Angular = unit.Angular(*sight_angle).validate()
        self._maximum_distance: unit.Distance = unit.Distance(*maximum_distance).validate()
        self._distance_step: unit.Distance = unit.Distance(*distance_step).validate()
        self._wind_velocity: unit.Velocity = unit.Velocity(*wind_velocity).validate()
        self._wind_direction: unit.Angular = unit.Angular(*wind_direction).validate()

        self.calculate_trajectory()

    def update(self, **kwargs):
        if kwargs:
            for k, v in kwargs.items():
                if hasattr(self, f'_{k}'):
                    self.__setattr__(f'_{k}', v)
            self.calculate_trajectory()
        return self._trajectory_data

    # @property
    # def trajectory_data(self) -> list['TrajectoryData']:
    #     return self._trajectory_data

    def calculate_trajectory(self):
        """
        :return: list[TrajectoryData]
        """
        bc = BallisticCoefficient(self._bc_value, self._drag_table)
        projectile = ProjectileWithDimensions(bc,
                                              self._bullet_diameter,
                                              self._bullet_length,
                                              self._bullet_weight)
        ammo = Ammunition(projectile, self._muzzle_velocity)
        atmosphere = Atmosphere(self._altitude, self._pressure, self._temperature, self._humidity)
        zero = ZeroInfo(self._zero_distance, True, True, ammo, atmosphere)
        twist = TwistInfo(self._twist_direction, self._twist)
        weapon = Weapon.create_with_twist(self._sight_height, zero, twist)
        shot_info = ShotParameters(self._sight_angle, self._maximum_distance, self._distance_step)
        wind = WindInfo.create_only_wind_info(self._wind_velocity, self._wind_direction)
        calc = TrajectoryCalculator()
        data = calc.trajectory(ammo, weapon, atmosphere, shot_info, wind)
        self._trajectory_data = data


# usage example
if __name__ == '__main__':
    profile = Profile()
    tested_data = profile.update()

    for d in tested_data:
        distance = d.travelled_distance.convert(unit.DistanceMeter)
        path = d.drop.convert(unit.DistanceCentimeter)
        print(f'Distance: {distance}, Path: {path}')

    tested_data = profile.update(temperature=unit.Temperature(26, unit.TemperatureCelsius),
                                 pressure=unit.Pressure(1000, unit.PressureMmHg))
    distance = tested_data[-1].travelled_distance.convert(unit.DistanceMeter)
    path = tested_data[-1].drop.convert(unit.DistanceCentimeter)
    print(f'\nDistance: {distance}, Path: {path}')
