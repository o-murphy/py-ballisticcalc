from py_ballisticcalc.lib.atmosphere import Atmosphere
from py_ballisticcalc.lib.drag import BallisticCoefficient, DragTableG7
from py_ballisticcalc.lib.projectile import ProjectileWithDimensions
from py_ballisticcalc.lib.weapon import Ammunition, ZeroInfo, TwistInfo, TwistRight, WeaponWithTwist
from py_ballisticcalc.lib.wind import create_only_wind_info
from py_ballisticcalc.lib.shot_parameters import ShotParameters
from py_ballisticcalc.lib.trajectory_calculator import TrajectoryCalculator
from py_ballisticcalc.lib.bmath.unit import *


cdef class Profile(object):
    cdef int _drag_table, _twist_direction
    cdef list _custom_drag_function
    cdef list _calculated_drag_function
    cdef list _trajectory_data
    cdef float _humidity
    cdef _bc_value, _bullet_diameter, _bullet_length, _bullet_weight
    cdef _muzzle_velocity, _zero_distance, _maximum_distance, _distance_step
    cdef _altitude, _pressure, _temperature
    cdef _twist, _sight_height, _sight_angle
    cdef _wind_velocity, _wind_direction
    cdef _maximum_step_size

    def __init__(self,
                 bc_value: float = 0.223,
                 drag_table: int = DragTableG7,
                 bullet_diameter: (float, int) = (0.308, DistanceInch),
                 bullet_length: (float, int) = (1.2, DistanceInch),
                 bullet_weight: (float, int) = (167, WeightGrain),
                 muzzle_velocity: (float, int) = (800, VelocityMPS),
                 altitude: (float, int) = (0, DistanceMeter),
                 pressure: (float, int) = (760, PressureMmHg),
                 temperature: (float, int) = (15, TemperatureCelsius),
                 humidity: float = 0.5,
                 zero_distance: (float, int) = (100, DistanceMeter),
                 twist: (float, int) = (11, DistanceInch),
                 twist_direction: int = TwistRight,
                 sight_height: (float, int) = (90, DistanceMillimeter),
                 sight_angle: (float, int) = (0, AngularMOA),
                 maximum_distance: (float, int) = (1000, DistanceMeter),
                 distance_step: (float, int) = (100, DistanceMeter),
                 wind_velocity: (float, int) = (0, VelocityKMH),
                 wind_direction: (float, int) = (0, AngularDegree),
                 custom_drag_function: list[dict[str, float]] = [],
                 maximum_step_size: (float, int) = (1, DistanceFoot)
                 ):
        self._bc_value = bc_value
        self._drag_table = drag_table
        self._bullet_diameter = Distance(*bullet_diameter)
        self._bullet_length = Distance(*bullet_length)
        self._bullet_weight = Weight(*bullet_weight)
        self._muzzle_velocity = Velocity(*muzzle_velocity)
        self._altitude = Distance(*altitude)
        self._pressure = Pressure(*pressure)
        self._temperature = Temperature(*temperature)
        self._humidity = humidity
        self._zero_distance = Distance(*zero_distance)
        self._twist = Distance(*twist)
        self._twist_direction = twist_direction
        self._sight_height = Distance(*sight_height)
        self._sight_angle = Angular(*sight_angle)
        self._maximum_distance = Distance(*maximum_distance)
        self._distance_step = Distance(*distance_step)
        self._wind_velocity = Velocity(*wind_velocity)
        self._wind_direction = Angular(*wind_direction)
        self._maximum_step_size = Distance(*maximum_step_size)

        self._trajectory_data = []

        if not custom_drag_function:
            custom_drag_function = []
        self._custom_drag_function = custom_drag_function

    def calculate_trajectory(self):
        self.make_calculator()
        return self._trajectory_data

    def calculate_drag_table(self):
        self.make_drag_table()

    cdef make_bc(self):
        return BallisticCoefficient(self._bc_value, self._drag_table,
                                    self._bullet_weight, self._bullet_diameter,
                                    self._custom_drag_function)

    cdef make_drag_table(self):
        cdef bc
        bc = self.make_bc()

    cdef make_calculator(self):
        cdef bc, projectile, ammo, atmo, zero, twist, weapon, wind, calc, angle, shot, data
        bc = self.make_bc()
        projectile = ProjectileWithDimensions(bc, self._bullet_diameter, self._bullet_length, self._bullet_weight)
        ammo = Ammunition(projectile, self._muzzle_velocity)
        atmo = Atmosphere(self._altitude, self._pressure, self._temperature, self._humidity)
        zero = ZeroInfo(self._zero_distance, True, True, ammo, atmo)
        twist = TwistInfo(self._twist_direction, self._twist)
        weapon = WeaponWithTwist(self._sight_height, zero, twist)
        wind = create_only_wind_info(self._wind_velocity, self._wind_direction)
        calc = TrajectoryCalculator()
        calc.set_maximum_calculator_step_size(self._maximum_step_size)
        angle = calc.sight_angle(ammo, weapon, atmo)
        shot = ShotParameters(angle, self._maximum_distance, self._distance_step)
        data = calc.trajectory(ammo, weapon, atmo, shot, wind)
        self._trajectory_data = data

    cpdef float bc_value(self):
        return self._bc_value

    cpdef set_bc_value(self, value: float):
        self._bc_value = value

    cpdef int drag_table(self):
        return self._drag_table

    cpdef set_drag_table(self, drag_table: int):
        self._drag_table = drag_table

    cpdef bullet_diameter(self):
        return self._bullet_diameter

    cpdef set_bullet_diameter(self, value: float, units: int):
        self._bullet_diameter = Distance(value, units)

    cpdef bullet_length(self):
        return self._bullet_length

    cpdef set_bullet_length(self, value: float, units: int):
        self._bullet_length = Distance(value, units)

    cpdef bullet_weight(self):
        return self._bullet_weight

    cpdef set_bullet_weight(self, value: float, units: int):
        self._bullet_weight = Weight(value, units)

    cpdef muzzle_velocity(self):
        return self._muzzle_velocity

    cpdef set_muzzle_velocity(self, value: float, units: int):
        self._muzzle_velocity = Velocity(value, units)

    cpdef altitude(self):
        return self._altitude

    cpdef set_altitude(self, value: float, units: int):
        self._altitude = Distance(value, units)

    cpdef pressure(self):
        return self._pressure

    cpdef set_pressure(self, value: float, units: int):
        self._pressure = Pressure(value, units)

    cpdef temperature(self):
        return self._temperature

    cpdef set_temperature(self, value: float, units: int):
        self._temperature = Temperature(value, units)

    cpdef float humidity(self):
        return self._humidity

    cpdef set_humidity(self, value: float):
        self._humidity = value

    cpdef zero_distance(self):
        return self._zero_distance

    cpdef set_zero_distance(self, value: float, units: int):
        self._zero_distance = Distance(value, units)

    cpdef twist(self):
        return self._twist

    cpdef set_twist(self, value: float, units: int):
        self._twist = Distance(value, units)

    cpdef int twist_direction(self):
        return self._twist_direction

    cpdef set_twist_direction(self, direction: int):
        self._twist_direction = direction

    cpdef sight_height(self):
        return self._sight_height

    cpdef set_sight_height(self, value: float, units: int):
        self._sight_height = Distance(value, units)

    cpdef sight_angle(self):
        return self._sight_angle

    cpdef set_sight_angle(self, value: float, units: int):
        self._sight_angle = Angular(value, units)

    cpdef maximum_distance(self):
        return self._maximum_distance

    cpdef set_maximum_distance(self, value: float, units: int):
        self._maximum_distance = Distance(value, units)

    cpdef distance_step(self):
        return self._distance_step

    cpdef set_distance_step(self, value: float, units: int):
        self._distance_step = Distance(value, units)

    cpdef wind_velocity(self):
        return self._wind_velocity

    cpdef set_wind_velocity(self, value: float, units: int):
        self._wind_velocity = Velocity(value, units)

    cpdef wind_direction(self):
        return self._wind_direction

    cpdef set_wind_direction(self, value: float, units: int):
        self._wind_direction = Angular(value, units)

    cpdef custom_drag_function(self):
        return self._custom_drag_function

    cpdef set_custom_drag_function(self, data: list[dict[str, float]]):
        self._custom_drag_function = data
        self._drag_table = 0
        self._bc_value = 0

    cpdef maximum_step_size(self):
        return self._maximum_step_size

    cpdef set_maximum_step_size(self, value: float, units: int):
        self._maximum_step_size = Distance(value, units)
