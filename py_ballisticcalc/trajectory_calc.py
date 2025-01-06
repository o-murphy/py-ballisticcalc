# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
from dataclasses import dataclass

from typing_extensions import NamedTuple, Union, List, Final, Tuple

from py_ballisticcalc.conditions import Atmo, Shot, Wind
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.munition import Ammo
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Distance, Angular, Velocity, Weight, Energy, Pressure, Temperature, PreferredUnits

cZeroFindingAccuracy: Final[float] = 0.000005
cMinimumVelocity: Final[float] = 50.0
cMaximumDrop: Final[float] = -15000
cMaxIterations: Final[float] = 20
cGravityConstant: Final[float] = -32.17405

_globalUsePowderSensitivity = False
_globalMaxCalcStepSizeFeet: float = 0.5


def get_global_max_calc_step_size() -> Distance:
    return PreferredUnits.distance(Distance.Foot(_globalMaxCalcStepSizeFeet))


def get_global_use_powder_sensitivity() -> bool:
    return _globalUsePowderSensitivity


def reset_globals() -> None:
    # pylint: disable=global-statement
    global _globalUsePowderSensitivity, _globalMaxCalcStepSizeFeet
    _globalUsePowderSensitivity = False
    _globalMaxCalcStepSizeFeet = 0.5


def set_global_max_calc_step_size(value: Union[float, Distance]) -> None:
    # pylint: disable=global-statement
    global _globalMaxCalcStepSizeFeet
    if (_value := PreferredUnits.distance(value)).raw_value <= 0:
        raise ValueError("_globalMaxCalcStepSize have to be > 0")
    _globalMaxCalcStepSizeFeet = _value >> Distance.Foot


def set_global_use_powder_sensitivity(value: bool) -> None:
    # pylint: disable=global-statement
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

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def mul_by_const(self, a: float) -> 'Vector':
        return Vector(self.x * a, self.y * a, self.z * a)

    def mul_by_vector(self, b: 'Vector') -> float:
        return self.x * b.x + self.y * b.y + self.z * b.z

    def add(self, b: 'Vector') -> 'Vector':
        return Vector(self.x + b.x, self.y + b.y, self.z + b.z)

    def subtract(self, b: 'Vector') -> 'Vector':
        return Vector(self.x - b.x, self.y - b.y, self.z - b.z)

    def negate(self) -> 'Vector':
        return Vector(-self.x, -self.y, -self.z)

    def normalize(self) -> 'Vector':
        m = self.magnitude()
        if math.fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.mul_by_const(1.0 / m)

    # def __add__(self, other: 'Vector') -> 'Vector':
    #     return self.add(other)
    #
    # def __radd__(self, other: 'Vector') -> 'Vector':
    #     return self.add(other)
    #
    # def __iadd__(self, other: 'Vector') -> 'Vector':
    #     return self.add(other)
    #
    # def __sub__(self, other: 'Vector') -> 'Vector':
    #     return self.subtract(other)
    #
    # def __rsub__(self, other: 'Vector') -> 'Vector':
    #     return self.subtract(other)
    #
    # def __isub__(self, other: 'Vector') -> 'Vector':
    #     return self.subtract(other)

    def __mul__(self, other: Union[int, float, 'Vector']) -> Union[float, 'Vector']:
        if isinstance(other, (int, float)):
            return self.mul_by_const(other)
        if isinstance(other, Vector):
            return self.mul_by_vector(other)
        raise TypeError(other)

    # def __rmul__(self, other: Union[int, float, 'Vector']) -> Union[float, 'Vector']:
    #     return self.__mul__(other)
    #
    # def __imul__(self, other: Union[int, float, 'Vector']) -> Union[float, 'Vector']:
    #     return self.__mul__(other)
    #
    # def __neg__(self) -> 'Vector':
    #     return self.negate()

    # aliases more efficient than wrappers
    __add__ = add
    __radd__ = add
    __iadd__ = add
    __sub__ = subtract
    __rsub__ = subtract
    __isub__ = subtract
    __rmul__ = __mul__
    __imul__ = __mul__
    __neg__ = negate


# Define the NamedTuple to match the config structure
class Config(NamedTuple):
    use_powder_sensitivity: bool
    max_calc_step_size_feet: float
    cZeroFindingAccuracy: float
    cMinimumVelocity: float
    cMaximumDrop: float
    cMaxIterations: float
    cGravityConstant: float


class _TrajectoryDataFilter:
    def __init__(self, filter_flags: TrajFlag,
                 ranges_length: int):
        self.filter: TrajFlag = filter_flags
        self.current_flag: TrajFlag = TrajFlag.NONE
        self.seen_zero: TrajFlag = TrajFlag.NONE
        self.current_item: int = 0
        self.ranges_length: int = ranges_length
        self.previous_mach: float = 0.0
        self.next_range_distance: float = 0.0

    def setup_seen_zero(self, height: float, barrel_elevation: float, look_angle: float) -> None:
        if height >= 0:
            self.seen_zero |= TrajFlag.ZERO_UP
        elif height < 0 and barrel_elevation < look_angle:
            self.seen_zero |= TrajFlag.ZERO_DOWN

    def clear_current_flag(self):
        self.current_flag = TrajFlag.NONE

    # pylint: disable=too-many-positional-arguments
    def should_record(self,
                      range_vector: Vector,
                      velocity: float,
                      mach: float,
                      step: float,
                      look_angle: float) -> bool:
        self.check_zero_crossing(range_vector, look_angle)
        self.check_mach_crossing(velocity, mach)
        self.check_next_range(range_vector.x, step)
        return bool(self.current_flag & self.filter)

    def should_break(self) -> bool:
        return self.current_item == self.ranges_length

    def check_next_range(self, next_range: float, step: float):
        # Next range check
        if next_range >= self.next_range_distance:
            self.current_flag |= TrajFlag.RANGE
            self.next_range_distance += step
            self.current_item += 1

    def check_mach_crossing(self, velocity: float, mach: float):
        # Mach crossing check
        current_mach = velocity / mach
        if self.previous_mach > 1 >= current_mach:  # (velocity / mach <= 1) and (previous_mach > 1)
            self.current_flag |= TrajFlag.MACH
        self.previous_mach = current_mach

    def check_zero_crossing(self, range_vector: Vector, look_angle: float):
        # Zero-crossing checks

        if range_vector.x > 0:
            # Zero reference line is the sight line defined by look_angle
            reference_height = range_vector.x * math.tan(look_angle)
            # If we haven't seen ZERO_UP, we look for that first
            if not (self.seen_zero & TrajFlag.ZERO_UP):  # pylint: disable=superfluous-parens
                if range_vector.y >= reference_height:
                    self.current_flag |= TrajFlag.ZERO_UP
                    self.seen_zero |= TrajFlag.ZERO_UP
            # We've crossed above sight line; now look for crossing back through it
            elif not (self.seen_zero & TrajFlag.ZERO_DOWN):  # pylint: disable=superfluous-parens
                if range_vector.y < reference_height:
                    self.current_flag |= TrajFlag.ZERO_DOWN
                    self.seen_zero |= TrajFlag.ZERO_DOWN


class _WindSock:
    def __init__(self, winds: Tuple[Wind, ...]):
        self.winds: Tuple[Wind, ...] = winds
        self.current: int = 0
        self.next_range: float = Wind.MAX_DISTANCE_FEET
        self._last_vector_cache: Union[Vector, None] = None
        self._length = len(winds)
        self.current_vector()

    def current_vector(self) -> Vector:
        if self._length < 1:
            self._last_vector_cache = Vector(.0, .0, .0)
        else:
            cur_wind = self.winds[self.current]
            self._last_vector_cache = wind_to_vector(cur_wind)
            self.next_range = cur_wind.until_distance >> Distance.Foot
        return self._last_vector_cache

    def vector_for_range(self, next_range: float):
        if next_range >= self.next_range:
            self.current += 1
            if self.current >= self._length:  # No more winds listed after this range
                self.next_range = Wind.MAX_DISTANCE_FEET
                self._last_vector_cache = Vector(.0, .0, .0)
            return self.current_vector()
        return self._last_vector_cache


class ZeroFindingError(RuntimeError):
    """
    Exception for zero-finding issues.
    Contains:
    - Zero finding error magnitude
    - Iteration count
    - Last barrel elevation (Angular instance)
    """

    def __init__(self,
                 zero_finding_error: float,
                 iterations_count: int,
                 last_barrel_elevation: Angular):
        """
        Parameters:
        - zero_finding_error: The error magnitude (float)
        - iterations_count: The number of iterations performed (int)
        - last_barrel_elevation: The last computed barrel elevation (Angular)
        """
        self.zero_finding_error: float = zero_finding_error
        self.iterations_count: int = iterations_count
        self.last_barrel_elevation: Angular = last_barrel_elevation
        super().__init__(f'Zero vertical error {zero_finding_error} '
                         f'feet, after {iterations_count} iterations.')


# pylint: disable=too-many-instance-attributes
class TrajectoryCalc:
    """All calculations are done in units of feet and fps"""

    # the attributes have to be defined before usage
    barrel_azimuth: float
    barrel_elevation: float
    twist: float

    def __init__(self, ammo: Ammo, _config: Config):
        self.ammo: Ammo = ammo
        self.__config: Config = _config

        self._bc: float = self.ammo.dm.BC
        self._table_data: List[DragDataPoint] = ammo.dm.drag_table
        self._curve: List[CurvePoint] = calculate_curve(self._table_data)
        self.gravity_vector: Vector = Vector(.0, _config.cGravityConstant, .0)

        # use calculation over list[double] instead of list[DragDataPoint]
        self.__mach_list: List[float] = _get_only_mach_data(self._table_data)

    @property
    def table_data(self) -> List[DragDataPoint]:
        """:return: List[DragDataPoint]"""
        return self._table_data

    def get_calc_step(self, step: float = 0):
        """Keep step under max_calc_step_size
        :param step: proposed step size
        :return: step size for calculations (in feet)
        """
        preferred_step = self.__config.max_calc_step_size_feet
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
        if self.__config.use_powder_sensitivity:
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

        _cZeroFindingAccuracy = self.__config.cZeroFindingAccuracy
        _cMaxIterations = self.__config.cMaxIterations

        distance_feet = distance >> Distance.Foot  # no need convert it twice
        zero_distance = math.cos(self.look_angle) * distance_feet
        height_at_zero = math.sin(self.look_angle) * distance_feet
        maximum_range = zero_distance - 1.5 * self.calc_step
        # self.barrel_azimuth = 0.0
        # self.barrel_elevation = math.atan(height_at_zero / zero_distance)
        # self.twist = 0.0

        iterations_count = 0
        zero_finding_error = _cZeroFindingAccuracy * 2
        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > _cZeroFindingAccuracy and iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current self.barrel_elevation)
            t = self._trajectory(shot_info, maximum_range, zero_distance, TrajFlag.NONE)[0]
            height = t.height >> Distance.Foot
            zero_finding_error = math.fabs(height - height_at_zero)
            if zero_finding_error > _cZeroFindingAccuracy:
                # Adjust barrel elevation to close height at zero distance
                self.barrel_elevation -= (height - height_at_zero) / zero_distance
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1

        if zero_finding_error > _cZeroFindingAccuracy:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self.barrel_elevation))
        return Angular.Radian(self.barrel_elevation)

    def _trajectory(self, shot_info: Shot, maximum_range: float, step: float,
                    filter_flags: TrajFlag) -> List[TrajectoryData]:
        """Calculate trajectory for specified shot
        :param maximum_range: Feet down range to stop calculation
        :param step: Frequency (in feet down range) to record TrajectoryData
        :return: list of TrajectoryData, one for each dist_step, out to max_range
        """
        _cMinimumVelocity = self.__config.cMinimumVelocity
        _cMaximumDrop = self.__config.cMaximumDrop

        ranges: List[TrajectoryData] = []  # Record of TrajectoryData points to return
        time: float = .0
        drag: float = .0

        # guarantee that mach and density_factor would be referenced before assignment
        mach: float = .0
        density_factor: float = .0

        # region Initialize wind-related variables to first wind reading (if any)
        wind_sock = _WindSock(shot_info.winds)
        wind_vector = wind_sock.current_vector()
        # endregion

        # region Initialize velocity and position of projectile
        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
        velocity_vector: Vector = Vector(
            math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth),
            math.sin(self.barrel_elevation),
            math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth)
        ) * velocity  # type: ignore
        # endregion

        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags,
                                            ranges_length=int(maximum_range / step) + 1)
        data_filter.setup_seen_zero(range_vector.y, self.barrel_elevation, self.look_angle)

        # region Trajectory Loop
        while range_vector.x <= maximum_range + self.calc_step:
            data_filter.clear_current_flag()

            # Update wind reading at current point in trajectory
            if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(
                self.alt0 + range_vector.y)

            # region Check whether to record TrajectoryData row at current point
            if filter_flags:  # require check before call to improve performance

                # Record TrajectoryData row
                if data_filter.should_record(range_vector, velocity, mach, step, self.look_angle):
                    ranges.append(create_trajectory_row(
                        time, range_vector, velocity_vector,
                        velocity, mach, self.spin_drift(time), self.look_angle,
                        density_factor, drag, self.weight, data_filter.current_flag
                    ))
                    if data_filter.should_break():
                        break

            # endregion

            # region Ballistic calculation step (point-mass)
            # Time step is set to advance bullet calc_step distance along x axis
            delta_time = self.calc_step / velocity_vector.x
            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            velocity_adjusted = velocity_vector - wind_vector
            velocity = velocity_adjusted.magnitude()  # Velocity relative to air
            # Drag is a function of air density and velocity relative to the air
            drag = density_factor * velocity * self.drag_by_mach(velocity / mach)
            # Bullet velocity changes due to both drag and gravity
            velocity_vector -= (velocity_adjusted * drag - self.gravity_vector) * delta_time  # type: ignore
            # Bullet position changes by velocity time_deltas the time step
            delta_range_vector = Vector(self.calc_step,
                                        velocity_vector.y * delta_time,
                                        velocity_vector.z * delta_time)
            # Update the bullet position
            range_vector += delta_range_vector
            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_range_vector.magnitude() / velocity

            if velocity < _cMinimumVelocity or range_vector.y < _cMaximumDrop:
                break
            # endregion

        # endregion
        # If filter_flags == 0 then all we want is the ending value
        if not filter_flags:
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity, mach, self.spin_drift(time), self.look_angle,
                density_factor, drag, self.weight, TrajFlag.NONE))
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
        # cd = calculate_by_curve(self._table_data, self._curve, mach)
        # use calculation over list[double] instead of list[DragDataPoint]
        cd = _calculate_by_curve_and_mach_list(self.__mach_list, self._curve, mach)
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
    # no need convert it twice
    wind_velocity_fps = wind.velocity >> Velocity.FPS
    wind_direction_rad = wind.direction_from >> Angular.Radian
    # Downrange (x-axis) wind velocity component:
    range_component = wind_velocity_fps * math.cos(wind_direction_rad)
    # Cross (z-axis) wind velocity component:
    cross_component = wind_velocity_fps * math.sin(wind_direction_rad)
    return Vector(range_component, 0, cross_component)


# pylint: disable=too-many-positional-arguments
def create_trajectory_row(time: float, range_vector: Vector, velocity_vector: Vector,
                          velocity: float, mach: float, spin_drift: float, look_angle: float,
                          density_factor: float, drag: float, weight: float, flag: TrajFlag) -> TrajectoryData:
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
        flag=flag.value
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


def calculate_curve(data_points: List[DragDataPoint]) -> List[CurvePoint]:
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


# use get_only_mach_data with calculate_by_curve_and_mach_data cause it faster
def calculate_by_curve(data: List[DragDataPoint], curve: List[CurvePoint], mach: float) -> float:
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


# Function to convert a list of DragDataPoint to an array of doubles containing only Mach values
def _get_only_mach_data(data: List[DragDataPoint]) -> List[float]:
    result = []
    for dp in data:
        result.append(dp.Mach)
    return result


def _calculate_by_curve_and_mach_list(mach_list: List[float], curve: List[CurvePoint], mach: float) -> float:
    num_points = len(curve)
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = (mhi + mlo) // 2
        if mach_list[mid] < mach:
            mlo = mid
        else:
            mhi = mid

    if mach_list[mhi] - mach > mach - mach_list[mlo]:
        m = mlo
    else:
        m = mhi
    curve_m = curve[m]
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)


try:
    # replace with cython based implementation
    from py_ballisticcalc_exts import (TrajectoryCalc, ZeroFindingError, Vector,  # type: ignore
                                       get_global_max_calc_step_size,
                                       get_global_use_powder_sensitivity,
                                       set_global_max_calc_step_size,
                                       set_global_use_powder_sensitivity,
                                       reset_globals,
                                       )

    from .logger import logger

    logger.debug("Binary modules found, running in binary mode")
except ImportError as error:
    import warnings
    warnings.warn("Library running in pure python mode. "
                  "For better performance install 'py_ballisticcalc.exts' binary package")

__all__ = (
    'TrajectoryCalc',
    'ZeroFindingError',
    'Vector',
    'get_global_max_calc_step_size',
    'get_global_use_powder_sensitivity',
    'set_global_max_calc_step_size',
    'set_global_use_powder_sensitivity',
    'reset_globals',
    'cZeroFindingAccuracy',
    'cMinimumVelocity',
    'cMaximumDrop',
    'cMaxIterations',
    'cGravityConstant',
    'Config',
)
