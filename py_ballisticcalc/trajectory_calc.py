# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
from dataclasses import dataclass
from typing import NamedTuple

from .drag_model import DragDataPoint
from .conditions import Atmo, Shot, Wind
from .munition import Ammo
from .trajectory_data import TrajectoryData, TrajFlag
from .unit import Distance, Angular, Velocity, Weight, Energy, Pressure, Temperature, PreferredUnits

__all__ = (
    'TrajectoryCalc',
    'get_global_max_calc_step_size',
    'get_global_use_powder_sensitivity',
    'set_global_max_calc_step_size',
    'set_global_use_powder_sensitivity',
    'reset_globals'
)

cZeroFindingAccuracy = 0.000005
cMinimumVelocity = 50.0
cMaximumDrop = -15000
cMaxIterations = 20
cGravityConstant = -32.17405

_globalUsePowderSensitivity = False
_globalMaxCalcStepSize = Distance.Foot(0.5)


def get_global_max_calc_step_size() -> Distance:
    return _globalMaxCalcStepSize


def get_global_use_powder_sensitivity() -> bool:
    return _globalUsePowderSensitivity


def reset_globals() -> None:
    global _globalUsePowderSensitivity, _globalMaxCalcStepSize
    _globalUsePowderSensitivity = False
    _globalMaxCalcStepSize = Distance.Foot(0.5)


def set_global_max_calc_step_size(value: [float, Distance]) -> None:
    global _globalMaxCalcStepSize
    if (_value := PreferredUnits.distance(value)).raw_value <= 0:
        raise ValueError("_globalMaxCalcStepSize have to be > 0")
    _globalMaxCalcStepSize = PreferredUnits.distance(value)


def set_global_use_powder_sensitivity(value: bool) -> None:
    global _globalUsePowderSensitivity
    if not isinstance(value, bool):
        raise TypeError(f"set_global_use_powder_sensitivity {value=} is not a boolean")
    _globalUsePowderSensitivity = value


class CurvePoint(NamedTuple):
    """Coefficients for quadratic interpolation"""
    a: float
    b: float
    c: float


@dataclass
class Vector:
    x: float
    y: float
    z: float

    def magnitude(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def mul_by_const(self, a: float):
        return Vector(self.x * a, self.y * a, self.z * a)

    def mul_by_vector(self, b: 'Vector'):
        return self.x * b.x + self.y * b.y + self.z * b.z

    def add(self, b: 'Vector'):
        return Vector(self.x + b.x, self.y + b.y, self.z + b.z)

    def subtract(self, b: 'Vector'):
        return Vector(self.x - b.x, self.y - b.y, self.z - b.z)

    def negate(self):
        return Vector(-self.x, -self.y, -self.z)

    def normalize(self):
        m = self.magnitude()
        if math.fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.mul_by_const(1.0 / m)

    def __add__(self, other: 'Vector'):
        return self.add(other)

    def __radd__(self, other: 'Vector'):
        return self.add(other)

    def __iadd__(self, other: 'Vector'):
        return self.add(other)

    def __sub__(self, other: 'Vector'):
        return self.subtract(other)

    def __rsub__(self, other: 'Vector'):
        return self.subtract(other)

    def __isub__(self, other: 'Vector'):
        return self.subtract(other)

    def __mul__(self, other: [int, float, 'Vector']):
        if isinstance(other, (int, float)):
            return self.mul_by_const(other)
        if isinstance(other, Vector):
            return self.mul_by_vector(other)
        raise TypeError(other)

    def __rmul__(self, other: [int, float, 'Vector']):
        return self.__mul__(other)

    def __imul__(self, other):
        return self.__mul__(other)

    def __neg__(self):
        return self.negate()


class TrajectoryCalc:
    """All calculations are done in units of feet and fps"""

    def __init__(self, ammo: Ammo):
        self.ammo = ammo
        self._bc = self.ammo.dm.BC
        self._table_data = ammo.dm.drag_table
        self._curve = calculate_curve(self._table_data)
        self.gravity_vector = Vector(.0, cGravityConstant, .0)

    @staticmethod
    def get_calc_step(step: float = 0):
        """Keep step under max_calc_step_size
        :param step: proposed step size
        :return: step size for calculations (in feet)
        """
        preferred_step = _globalMaxCalcStepSize >> Distance.Foot
        if step == 0:
            return preferred_step / 2.0
        return min(step, preferred_step) / 2.0

    def trajectory(self, shot_info: Shot, max_range: Distance, dist_step: Distance,
                   extra_data: bool = False):
        filter_flags = TrajFlag.RANGE

        if extra_data:
            dist_step = Distance.Foot(0.2)
            filter_flags = TrajFlag.ALL

        self._init_trajectory(shot_info)
        return self._trajectory(shot_info, max_range >> Distance.Foot, dist_step >> Distance.Foot, filter_flags)

    def _init_trajectory(self, shot_info: Shot):
        self.look_angle = shot_info.look_angle >> Angular.Radian
        self.twist = shot_info.weapon.twist >> Distance.Inch
        self.length = shot_info.ammo.dm.length >> Distance.Inch
        self.diameter = shot_info.ammo.dm.diameter >> Distance.Inch
        self.weight = shot_info.ammo.dm.weight >> Weight.Grain
        self.barrel_elevation = shot_info.barrel_elevation >> Angular.Radian
        self.barrel_azimuth = shot_info.barrel_azimuth >> Angular.Radian
        self.sight_height = shot_info.weapon.sight_height >> Distance.Foot
        self.cant_cosine = math.cos(shot_info.cant_angle >> Angular.Radian)
        self.cant_sine = math.sin(shot_info.cant_angle >> Angular.Radian)
        self.alt0 = shot_info.atmo.altitude >> Distance.Foot
        self.calc_step = self.get_calc_step()
        if _globalUsePowderSensitivity:
            self.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.temperature) >> Velocity.FPS
        else:
            self.muzzle_velocity = shot_info.ammo.mv >> Velocity.FPS
        self.stability_coefficient = self.calc_stability_coefficient(shot_info.atmo)

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """Iterative algorithm to find barrel elevation needed for a particular zero
        :param shot_info: Shot parameters
        :param distance: Zero distance
        :return: Barrel elevation to hit height zero at zero distance
        """
        self._init_trajectory(shot_info)

        zero_distance = math.cos(self.look_angle) * (distance >> Distance.Foot)
        height_at_zero = math.sin(self.look_angle) * (distance >> Distance.Foot)
        maximum_range = zero_distance - 1.5 * self.calc_step
        self.barrel_azimuth = 0.0
        self.barrel_elevation = math.atan(height_at_zero / zero_distance)
        self.twist = 0

        iterations_count = 0
        zero_finding_error = cZeroFindingAccuracy * 2
        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > cZeroFindingAccuracy and iterations_count < cMaxIterations:
            # Check height of trajectory at the zero distance (using current self.barrel_elevation)
            t = self._trajectory(shot_info, maximum_range, zero_distance, TrajFlag.NONE)[0]
            height = t.height >> Distance.Foot
            zero_finding_error = math.fabs(height - height_at_zero)
            if zero_finding_error > cZeroFindingAccuracy:
                # Adjust barrel elevation to close height at zero distance
                self.barrel_elevation -= (height - height_at_zero) / zero_distance
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1

        if zero_finding_error > cZeroFindingAccuracy:
            # TODO: Don't raise exception; return a tuple that contains the error so caller can check how close zero is
            raise Exception(f'Zero vertical error {zero_finding_error} feet, after {iterations_count} iterations.')
        return Angular.Radian(self.barrel_elevation)

    def _trajectory(self, shot_info: Shot, maximum_range: float, step: float,
                    filter_flags: TrajFlag) -> list[TrajectoryData]:
        """Calculate trajectory for specified shot
        :param maximum_range: Feet down range to stop calculation
        :param step: Frequency (in feet down range) to record TrajectoryData
        :return: list of TrajectoryData, one for each dist_step, out to max_range
        """
        ranges = []  # Record of TrajectoryData points to return
        ranges_length = int(maximum_range / step) + 1
        time = 0
        previous_mach = .0
        drag = 0

        # region Initialize wind-related variables to first wind reading (if any)
        len_winds = len(shot_info.winds)
        current_wind = 0
        current_item = 0
        next_range_distance = .0
        next_wind_range = Wind.MAX_DISTANCE_FEET
        if len_winds < 1:
            wind_vector = Vector(.0, .0, .0)
        else:
            wind_vector = wind_to_vector(shot_info.winds[0])
            next_wind_range = shot_info.winds[0].until_distance >> Distance.Foot
        # endregion

        # region Initialize velocity and position of projectile
        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
        velocity_vector = Vector(math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth),
                                 math.sin(self.barrel_elevation),
                                 math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth)) * velocity
        # endregion

        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        seen_zero = TrajFlag.NONE  # Record when we see each zero crossing, so we only register one
        if range_vector.y >= 0:
            seen_zero |= TrajFlag.ZERO_UP  # We're starting above zero; we can only go down
        elif range_vector.y < 0 and self.barrel_elevation < self.look_angle:
            seen_zero |= TrajFlag.ZERO_DOWN  # We're below and pointing down from look angle; no zeroes!

        # region Trajectory Loop
        while range_vector.x <= maximum_range + self.calc_step:
            _flag = TrajFlag.NONE

            # Update wind reading at current point in trajectory
            if range_vector.x >= next_wind_range:
                current_wind += 1
                if current_wind >= len_winds:  # No more winds listed after this range
                    wind_vector = Vector(.0, .0, .0)
                    next_wind_range = Wind.MAX_DISTANCE_FEET
                else:
                    wind_vector = wind_to_vector(shot_info.winds[current_wind])
                    next_wind_range = shot_info.winds[current_wind].until_distance >> Distance.Foot

            # Update air density at current point in trajectory
            density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(
                self.alt0 + range_vector.y)

            # region Check whether to record TrajectoryData row at current point
            if filter_flags:
                # Zero-crossing checks
                if range_vector.x > 0:
                    # Zero reference line is the sight line defined by look_angle
                    reference_height = range_vector.x * math.tan(self.look_angle)
                    # If we haven't seen ZERO_UP, we look for that first
                    if not seen_zero & TrajFlag.ZERO_UP:
                        if range_vector.y >= reference_height:
                            _flag |= TrajFlag.ZERO_UP
                            seen_zero |= TrajFlag.ZERO_UP
                    # We've crossed above sight line; now look for crossing back through it
                    elif not seen_zero & TrajFlag.ZERO_DOWN:
                        if range_vector.y < reference_height:
                            _flag |= TrajFlag.ZERO_DOWN
                            seen_zero |= TrajFlag.ZERO_DOWN

                # Mach crossing check
                if (velocity / mach <= 1) and (previous_mach > 1):
                    _flag |= TrajFlag.MACH

                # Next range check
                if range_vector.x >= next_range_distance:
                    _flag |= TrajFlag.RANGE
                    next_range_distance += step
                    current_item += 1

                # Record TrajectoryData row
                if _flag & filter_flags:
                    ranges.append(create_trajectory_row(
                        time, range_vector, velocity_vector,
                        velocity, mach, self.spin_drift(time), self.look_angle,
                        density_factor, drag, self.weight, _flag.value
                    ))
                    if current_item == ranges_length:
                        break
            # endregion

            previous_mach = velocity / mach

            # region Ballistic calculation step (point-mass)
            # Time step is set to advance bullet calc_step distance along x axis
            delta_time = self.calc_step / velocity_vector.x
            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            velocity_adjusted = velocity_vector - wind_vector
            velocity = velocity_adjusted.magnitude()  # Velocity relative to air
            # Drag is a function of air density and velocity relative to the air
            drag = density_factor * velocity * self.drag_by_mach(velocity / mach)
            # Bullet velocity changes due to both drag and gravity
            velocity_vector -= (velocity_adjusted * drag - self.gravity_vector) * delta_time
            # Bullet position changes by velocity times the time step
            delta_range_vector = Vector(self.calc_step,
                                        velocity_vector.y * delta_time,
                                        velocity_vector.z * delta_time)
            # Update the bullet position
            range_vector += delta_range_vector
            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_range_vector.magnitude() / velocity

            if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                break
            # endregion
        # endregion
        # If filter_flags == 0 then all we want is the ending value
        if not filter_flags:
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity, mach, self.spin_drift(time), self.look_angle,
                density_factor, drag, self.weight, _flag.value))
        return ranges

    def drag_by_mach(self, mach: float) -> float:
        """ Drag force = V^2 * Cd * AirDensity * S / 2m where:
                cStandardDensity of Air = 0.076474 lb/ft^3
                S is cross-section = d^2 pi/4, where d is bullet diameter in inches
                m is bullet mass in pounds
            bc contains m/d^2 in units lb/in^2, which we multiply by 144 to convert to lb/ft^2
            Thus: The magic constant found here = StandardDensity * pi / (4 * 2 * 144)
        :return: Drag coefficient at the given mach number
        """
        cd = calculate_by_curve(self._table_data, self._curve, mach)
        return cd * 2.08551e-04 / self._bc

    def spin_drift(self, time) -> float:
        """Litz spin-drift approximation
        :param time: Time of flight
        :return: windage due to spin drift, in feet
        """
        if self.twist != 0:
            sign = 1 if self.twist > 0 else -1
            return sign * (1.25 * (self.stability_coefficient + 1.2)
                           * math.pow(time, 1.83)) / 12
        return 0

    def calc_stability_coefficient(self, atmo: Atmo) -> float:
        """Miller stability coefficient"""
        if self.twist and self.length and self.diameter:
            twist_rate = math.fabs(self.twist) / self.diameter
            length = self.length / self.diameter
            # Miller stability formula
            sd = 30 * self.weight / (
                    math.pow(twist_rate, 2) * math.pow(self.diameter, 3) * length * (1 + math.pow(length, 2))
            )
            # Velocity correction factor
            fv = math.pow(self.muzzle_velocity / 2800, 1.0 / 3.0)
            # Atmospheric correction
            ft = atmo.temperature >> Temperature.Fahrenheit
            pt = atmo.pressure >> Pressure.InHg
            ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
            return sd * fv * ftp
        return 0


def wind_to_vector(wind: Wind) -> Vector:
    """Calculate wind vector to add to projectile velocity vector each iteration:
        Aerodynamic drag is function of velocity relative to the air stream.

    Wind angle of zero is blowing from behind shooter
    Wind angle of 90-degree is blowing towards shooter's right

    NOTE: Presently we can only define Wind in the x-z plane, not any vertical component.
    """
    # Downrange (x-axis) wind velocity component:
    range_component = (wind.velocity >> Velocity.FPS) * math.cos(wind.direction_from >> Angular.Radian)
    # Cross (z-axis) wind velocity component:
    cross_component = (wind.velocity >> Velocity.FPS) * math.sin(wind.direction_from >> Angular.Radian)
    return Vector(range_component, 0, cross_component)


def create_trajectory_row(time: float, range_vector: Vector, velocity_vector: Vector,
                          velocity: float, mach: float, spin_drift: float, look_angle: float,
                          density_factor: float, drag: float, weight: float, flag: int) -> TrajectoryData:
    """
    Create a TrajectoryData object representing a single row of trajectory data.

    :param time: Time of flight.
    :param range_vector: Vector representing range.
    :param velocity_vector: Vector representing velocity.
    :param velocity: Velocity value.
    :param mach: Mach number.
    :param spin_drift: Spin drift value.
    :param look_angle: Look angle value.
    :param density_factor: Density factor.
    :param drag: Drag value.
    :param weight: Weight value.
    :param flag: Flag value.

    :return: A TrajectoryData object representing the trajectory data.
    """
    windage = range_vector.z + spin_drift
    drop_adjustment = get_correction(range_vector.x, range_vector.y)
    windage_adjustment = get_correction(range_vector.x, windage)
    trajectory_angle = math.atan(velocity_vector.y / velocity_vector.x)

    return TrajectoryData(
        time=time,
        distance=Distance.Foot(range_vector.x),
        velocity=Velocity.FPS(velocity),
        mach=velocity / mach,
        height=Distance.Foot(range_vector.y),
        target_drop=Distance.Foot((range_vector.y - range_vector.x * math.tan(look_angle)) * math.cos(look_angle)),
        drop_adj=Angular.Radian(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=Distance.Foot(windage),
        windage_adj=Angular.Radian(windage_adjustment),
        look_distance=Distance.Foot(range_vector.x / math.cos(look_angle)),
        angle=Angular.Radian(trajectory_angle),
        density_factor=density_factor - 1,
        drag=drag,
        energy=Energy.FootPound(calculate_energy(weight, velocity)),
        ogw=Weight.Pound(calculate_ogw(weight, velocity)),
        flag=flag
    )


def get_correction(distance: float, offset: float) -> float:
    """:return: Sight adjustment in radians"""
    if distance != 0:
        return math.atan(offset / distance)
    return 0  # None


def calculate_energy(bullet_weight: float, velocity: float) -> float:
    """:return: energy in ft-lbs"""
    return bullet_weight * math.pow(velocity, 2) / 450400


def calculate_ogw(bullet_weight: float, velocity: float) -> float:
    """:return: Optimal Game Weight in pounds"""
    return math.pow(bullet_weight, 2) * math.pow(velocity, 3) * 1.5e-12


def calculate_curve(data_points: list[DragDataPoint]) -> list[CurvePoint]:
    """Piecewise quadratic interpolation of drag curve
    :param data_points: List[{Mach, CD}] data_points in ascending Mach order
    :return: List[CurvePoints] to interpolate drag coefficient
    """
    # rate, x1, x2, x3, y1, y2, y3, a, b, c
    # curve = []
    # curve_point
    # num_points, len_data_points, len_data_range

    rate = (data_points[1].CD - data_points[0].CD
            ) / (data_points[1].Mach - data_points[0].Mach)
    curve = [CurvePoint(0, rate, data_points[0].CD - data_points[0].Mach * rate)]
    len_data_points = int(len(data_points))
    len_data_range = len_data_points - 1

    for i in range(1, len_data_range):
        x1 = data_points[i - 1].Mach
        x2 = data_points[i].Mach
        x3 = data_points[i + 1].Mach
        y1 = data_points[i - 1].CD
        y2 = data_points[i].CD
        y3 = data_points[i + 1].CD
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_point = CurvePoint(a, b, c)
        curve.append(curve_point)

    num_points = len_data_points
    rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
           (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
    curve_point = CurvePoint(
        0, rate, data_points[num_points - 1].CD - data_points[num_points - 2].Mach * rate
    )
    curve.append(curve_point)
    return curve


def calculate_by_curve(data: list, curve: list, mach: float) -> float:
    """
    Binary search for drag coefficient based on Mach number
    :param data: data
    :param curve: Output of calculate_curve(data)
    :param mach: Mach value for which we're searching for CD
    :return float: drag coefficient
    """
    num_points = int(len(curve))
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = int(math.floor(mhi + mlo) / 2.0)
        if data[mid].Mach < mach:
            mlo = mid
        else:
            mhi = mid

    if data[mhi].Mach - mach > mach - data[mlo].Mach:
        m = mlo
    else:
        m = mhi
    curve_m = curve[m]
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)
