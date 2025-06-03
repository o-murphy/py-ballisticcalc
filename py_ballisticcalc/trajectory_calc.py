"""Bootstrap to load binary TrajectoryCalc, Vector extensions"""
from typing_extensions import Union, Final

from py_ballisticcalc.unit import Distance, PreferredUnits

# from py_ballisticcalc.logger import logger
# from py_ballisticcalc.trajectory_calc._trajectory_calc import (
#     Config,
#     get_correction,
#     calculate_energy,
#     calculate_ogw,
#     create_trajectory_row,
#     _TrajectoryDataFilter,
#     _WindSock
# )

cZeroFindingAccuracy: Final[float] = 0.000005
cMinimumVelocity: Final[float] = 50.0
cMaximumDrop: Final[float] = -15000
cMaxIterations: Final[int] = 60
cGravityConstant: Final[float] = -32.17405
cMinimumAltitude: Final[float] = -1410.748  # ft

_globalChartResolution: float = 0.2  # ft
_globalUsePowderSensitivity = False
_globalMaxCalcStepSizeFeet: float = 0.5


def get_global_max_calc_step_size() -> Distance:
    return PreferredUnits.distance(Distance.Foot(_globalMaxCalcStepSizeFeet))


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


# try:
#     # replace with cython based implementation
#     from py_ballisticcalc_exts.trajectory_calc import TrajectoryCalc  # type: ignore
# except ImportError as err:
#     """Fallback to pure python"""
#     from py_ballisticcalc.trajectory_calc._trajectory_calc import TrajectoryCalc
#
#     logger.debug(err)

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
import warnings

from typing_extensions import Optional, NamedTuple, Union, List, Tuple

from py_ballisticcalc.vector import Vector
from py_ballisticcalc.conditions import Atmo, Shot, Wind
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError
from py_ballisticcalc.logger import logger, get_debug
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Distance, Angular, Velocity, Weight, Energy, Pressure, Temperature, Unit


# __all__ = (
#     'TrajectoryCalc',
#     'Vector',
#     'Config',
#     'calculate_energy',
#     'calculate_ogw',
#     'get_correction',
#     'create_trajectory_row',
#     '_TrajectoryDataFilter',
#     '_WindSock',
# )


class CurvePoint(NamedTuple):
    """Coefficients for quadratic interpolation"""
    a: float
    b: float
    c: float


# Define the NamedTuple to match the config structure
class Config(NamedTuple):
    max_calc_step_size_feet: float
    chart_resolution: float
    cZeroFindingAccuracy: float
    cMinimumVelocity: float
    cMaximumDrop: float
    cMaxIterations: int
    cGravityConstant: float
    cMinimumAltitude: float


class BaseTrajData(NamedTuple):
    """Minimal data for one point in ballistic trajectory"""
    time: float
    position: Vector
    velocity: Vector
    mach: float


# pylint: disable=too-many-instance-attributes
class _TrajectoryDataFilter:
    """
    Determines when to record trajectory data points based on range and time.
    For specific points of interest, interpolates between integration steps to get the exact point.
    """
    filter: Union[TrajFlag, int]
    current_flag: Union[TrajFlag, int]
    seen_zero: Union[TrajFlag, int]
    time_of_last_record: float
    time_step: float
    range_step: float
    previous_mach: float
    previous_time: float
    previous_position: Vector
    previous_velocity: Vector
    previous_v_mach: float
    next_record_distance: float
    look_angle: float

    def __init__(self, filter_flags: Union[TrajFlag, int], range_step: float,
                 initial_position: Vector, initial_velocity: Vector, time_step: float = 0.0):
        """If a time_step is indicated, then we will record a row at least that often in the trajectory"""
        self.filter: Union[TrajFlag, int] = filter_flags
        self.current_flag: Union[TrajFlag, int] = TrajFlag.NONE
        self.seen_zero: Union[TrajFlag, int] = TrajFlag.NONE
        self.time_step: float = time_step
        self.range_step: float = range_step
        self.time_of_last_record: float = 0.0
        self.next_record_distance: float = 0.0
        self.previous_mach: float = 0.0
        self.previous_time: float = 0.0
        self.previous_position: Vector = initial_position
        self.previous_velocity: Vector = initial_velocity
        self.previous_v_mach: float = 0.0  # Previous velocity in Mach terms
        self.look_angle: float = 0.0

    def setup_seen_zero(self, height: float, barrel_elevation: float, look_angle: float) -> None:
        if height >= 0:
            self.seen_zero |= TrajFlag.ZERO_UP
        elif height < 0 and barrel_elevation < look_angle:
            self.seen_zero |= TrajFlag.ZERO_DOWN
        self.look_angle: float = look_angle

    def clear_current_flag(self):
        self.current_flag = TrajFlag.NONE

    # pylint: disable=too-many-positional-arguments
    def should_record(self, position: Vector, velocity: Vector, mach: float,
                      time: float) -> Optional[BaseTrajData]:
        # region DEBUG
        if get_debug():
            logger.debug(
                f"should_record called with time={time}, "
                f"position=({position.x}, {position.y}, {position.z}), "
                f"velocity=({velocity.x}, {velocity.y}, {velocity.z}), mach={mach}"
            )
        # endregion
        data = None
        if (self.range_step > 0) and (position.x >= self.next_record_distance):
            while self.next_record_distance + self.range_step < position.x:
                # Handle case where we have stepped past more than one record distance
                self.next_record_distance += self.range_step
            if position.x > self.previous_position.x:
                # Interpolate to get BaseTrajData at the record distance
                ratio = (self.next_record_distance - self.previous_position.x) / (position.x - self.previous_position.x)
                data = BaseTrajData(
                    time=self.previous_time + (time - self.previous_time) * ratio,
                    position=self.previous_position + (position - self.previous_position) * ratio,
                    velocity=self.previous_velocity + (velocity - self.previous_velocity) * ratio,
                    mach=self.previous_mach + (mach - self.previous_mach) * ratio
                )
            self.current_flag |= TrajFlag.RANGE
            self.next_record_distance += self.range_step
            self.time_of_last_record = time
        elif self.time_step > 0:
            self.check_next_time(time)
        self.check_zero_crossing(position)
        self.check_mach_crossing(velocity.magnitude(), mach)
        if bool(self.current_flag & self.filter) and data is None:
            data = BaseTrajData(time=time, position=position,
                                velocity=velocity, mach=mach)
        self.previous_time = time
        self.previous_position = position
        self.previous_velocity = velocity
        self.previous_mach = mach
        # region DEBUG
        if get_debug():
            if data is not None:
                logger.debug(
                    f"should_record returning BaseTrajData time={data.time}, "
                    f"position=({data.position.x}, {data.position.y}, {data.position.z}), "
                    f"velocity=({data.velocity.x}, {data.velocity.y}, {data.velocity.z}), mach={data.mach}"
                )
            else:
                logger.debug("should_record returning None")
        # endregion
        return data

    def check_next_time(self, time: float):
        if time > self.time_of_last_record + self.time_step:
            self.current_flag |= TrajFlag.RANGE
            self.time_of_last_record = time

    def check_mach_crossing(self, velocity: float, mach: float):
        current_v_mach = velocity / mach
        if self.previous_v_mach > 1 >= current_v_mach:  # (velocity / mach <= 1) and (previous_mach > 1)
            self.current_flag |= TrajFlag.MACH
        self.previous_v_mach = current_v_mach

    def check_zero_crossing(self, range_vector: Vector):
        if range_vector.x > 0:
            # Zero reference line is the sight line defined by look_angle
            reference_height = range_vector.x * math.tan(self.look_angle)
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
    """
    Currently this class assumes that requests for wind readings will only be made in order of increasing range.
    This assumption is violated if the projectile is blown or otherwise moves backwards.
    """
    winds: tuple['Wind', ...]
    current: int
    next_range: float

    def __init__(self, winds: Union[Tuple["Wind", ...], None]):
        """
        Initializes the _WindSock class.

        Args:
            winds (Union[Tuple[Wind, ...], None], optional): A tuple of Wind objects. Defaults to None.
        """
        self.winds: Tuple["Wind", ...] = winds or tuple()
        self.current: int = 0
        self.next_range: float = Wind.MAX_DISTANCE_FEET
        self._last_vector_cache: Union["Vector", None] = None
        self._length = len(self.winds)

        # Initialize cache correctly
        self.update_cache()

    def current_vector(self) -> "Vector":
        """
        Returns the current cached wind vector.

        Raises:
            RuntimeError: If no wind vector has been cached.

        Returns:
            Vector: The current cached wind vector.
        """
        if not self._last_vector_cache:
            raise RuntimeError("No cached wind vector")
        return self._last_vector_cache

    def update_cache(self) -> None:
        """Updates the cache only if needed or if forced during initialization."""
        if self.current < self._length:
            cur_wind = self.winds[self.current]
            self._last_vector_cache = cur_wind.vector
            self.next_range = cur_wind.until_distance >> Distance.Foot
        else:
            self._last_vector_cache = Vector(0.0, 0.0, 0.0)
            self.next_range = Wind.MAX_DISTANCE_FEET

    def vector_for_range(self, next_range: float) -> "Vector":
        """
        Updates the wind vector if `next_range` surpasses `self.next_range`.

        Args:
            next_range (float): The range to check against the current wind segment.

        Returns:
            Vector: The wind vector for the given range.
        """
        if next_range >= self.next_range:
            self.current += 1
            if self.current >= self._length:
                self._last_vector_cache = Vector(0.0, 0.0, 0.0)
                self.next_range = Wind.MAX_DISTANCE_FEET
            else:
                self.update_cache()  # This will trigger cache updates.
        return self.current_vector()


# pylint: disable=too-many-instance-attributes
class TrajectoryCalc:
    """
    All calculations are done in units of feet and fps.

    Attributes:
        barrel_azimuth (float): The azimuth angle of the barrel.
        barrel_elevation (float): The elevation angle of the barrel.
        twist (float): The twist rate of the barrel.
        gravity_vector (Vector): The gravity vector.
    """

    barrel_azimuth: float
    barrel_elevation: float
    twist: float
    gravity_vector: Vector

    def __init__(self, _config: Config):
        """
        Initializes the TrajectoryCalc class.

        Args:
            _config (Config): The configuration object.
        """
        self._config: Config = _config
        self.gravity_vector: Vector = Vector(.0, self._config.cGravityConstant, .0)

    @property
    def table_data(self) -> List[DragDataPoint]:
        """
        Gets the drag model table data.

        Returns:
            List[DragDataPoint]: A list of drag data points.
        """
        return self._table_data

    def get_calc_step(self, step: float = 0) -> float:
        """
        Keep step under max_calc_step_size

        Args:
            step (float, optional): proposed step size. Defaults to 0.

        Returns:
            float: step size for calculations (in feet)
        """
        preferred_step = self._config.max_calc_step_size_feet
        if step == 0:
            return preferred_step / 2.0
        return min(step, preferred_step) / 2.0

    def trajectory(self, shot_info: Shot, max_range: Distance, dist_step: Distance,
                   extra_data: bool = False, time_step: float = 0.0) -> List[TrajectoryData]:
        """
        Calculates the trajectory of a projectile.

        Args:
            shot_info (Shot): Information about the shot.
            max_range (Distance): The maximum range of the trajectory.
            dist_step (Distance): The distance step for calculations.
            extra_data (bool, optional): Flag to include extra data. Defaults to False.
            time_step (float, optional): The time step for calculations. Defaults to 0.0.

        Returns:
            List[TrajectoryData]: A list of trajectory data points.
        """
        filter_flags = TrajFlag.RANGE

        if extra_data:
            # dist_step = Distance.Foot(self._config.chart_resolution)
            filter_flags = TrajFlag.ALL

        self._init_trajectory(shot_info)
        return self._integrate(shot_info, max_range >> Distance.Foot,
                               dist_step >> Distance.Foot, filter_flags, time_step)

    def _init_trajectory(self, shot_info: Shot) -> None:
        """
        Initializes the trajectory calculation.

        Args:
            shot_info (Shot): Information about the shot.
        """
        self._bc: float = shot_info.ammo.dm.BC
        self._table_data: List[DragDataPoint] = shot_info.ammo.dm.drag_table
        self._curve: List[CurvePoint] = calculate_curve(self._table_data)

        # use calculation over list[double] instead of list[DragDataPoint]
        self.__mach_list: List[float] = _get_only_mach_data(self._table_data)

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
        self.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp) >> Velocity.FPS
        self.stability_coefficient = self.calc_stability_coefficient(shot_info.atmo)

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero

        Args:
            shot_info (Shot): Shot parameters
            distance (Distance): Zero distance

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance
        """
        self._init_trajectory(shot_info)

        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations

        distance_feet = distance >> Distance.Foot  # no need convert it twice
        zero_distance = math.cos(self.look_angle) * distance_feet
        height_at_zero = math.sin(self.look_angle) * distance_feet

        iterations_count = 0
        zero_finding_error = _cZeroFindingAccuracy * 2
        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > _cZeroFindingAccuracy and iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current self.barrel_elevation)
            try:
                t = self._integrate(shot_info, zero_distance, zero_distance, TrajFlag.NONE)[0]
                height = t.height >> Distance.Foot
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                last_distance_foot = e.last_distance >> Distance.Foot
                proportion = (last_distance_foot) / zero_distance
                height = (e.incomplete_trajectory[-1].height >> Distance.Foot) / proportion

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

    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List[TrajectoryData]:
        """
        Calculate trajectory for specified shot

        Args:
            shot_info (Shot):  Information about the shot.
            maximum_range (float): Feet down range to stop calculation
            record_step (float): Frequency (in feet down range) to record TrajectoryData
            filter_flags (Union[TrajFlag, int]): Flags to filter trajectory data.
            time_step (float, optional): If > 0 then record TrajectoryData after this many seconds elapse
                since last record, as could happen when trajectory is nearly vertical
                and there is too little movement downrange to trigger a record based on range.
                Defaults to 0.0

        Returns:
            List[TrajectoryData]: list of TrajectoryData, one for each dist_step, out to max_range
        """

        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = self._config.cMaximumDrop
        _cMinimumAltitude = self._config.cMinimumAltitude

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
        ).mul_by_const(velocity)  # type: ignore
        # endregion

        # min_step is used to handle situation, when record step is smaller than calc_step
        # in order to prevent range breaking too early
        min_step = min(self.calc_step, record_step)
        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=record_step,
                                            initial_position=range_vector, initial_velocity=velocity_vector,
                                            time_step=time_step)
        data_filter.setup_seen_zero(range_vector.y, self.barrel_elevation, self.look_angle)

        # region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        it = 0  # iteration counter
        while range_vector.x <= maximum_range + min_step:
            it += 1
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
                if (data := data_filter.should_record(range_vector, velocity_vector, mach, time)) is not None:
                    ranges.append(create_trajectory_row(data.time, data.position, data.velocity,
                                                        data.velocity.magnitude(), data.mach,
                                                        self.spin_drift(data.time), self.look_angle,
                                                        density_factor, drag, self.weight, data_filter.current_flag
                                                        ))
            # endregion

            # region Ballistic calculation step (point-mass)
            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            velocity_adjusted = velocity_vector - wind_vector
            velocity = velocity_adjusted.magnitude()  # Velocity relative to air
            # Time step is normalized by velocity so that we take smaller steps when moving faster
            delta_time = self.calc_step / max(1.0, velocity)
            # Drag is a function of air density and velocity relative to the air
            drag = density_factor * velocity * self.drag_by_mach(velocity / mach)
            # Bullet velocity changes due to both drag and gravity
            velocity_vector -= (velocity_adjusted * drag - self.gravity_vector) * delta_time  # type: ignore
            # Bullet position changes by velocity time_deltas the time step
            delta_range_vector = velocity_vector * delta_time
            # Update the bullet position
            range_vector += delta_range_vector  # type: ignore
            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_time

            if (
                    velocity < _cMinimumVelocity
                    or range_vector.y < _cMaximumDrop
                    or self.alt0 + range_vector.y < _cMinimumAltitude
            ):
                ranges.append(create_trajectory_row(
                    time, range_vector, velocity_vector,
                    velocity, mach, self.spin_drift(time), self.look_angle,
                    density_factor, drag, self.weight, data_filter.current_flag
                ))
                if velocity < _cMinimumVelocity:
                    reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    reason = RangeError.MaximumDropReached
                else:
                    reason = RangeError.MinimumAltitudeReached
                raise RangeError(reason, ranges)
                # break
            # endregion
        # endregion
        # Ensure that we have at least two data points in trajectory
        if len(ranges) < 2:
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity, mach, self.spin_drift(time), self.look_angle,
                density_factor, drag, self.weight, TrajFlag.NONE))
        logger.debug(f"euler py it {it}")
        return ranges

    def drag_by_mach(self, mach: float) -> float:
        """
        Calculates the drag coefficient at a given Mach number.

        The drag force is calculated using the following formula:
        Drag force = V^2 * Cd * AirDensity * S / 2m

        Where:
            - cStandardDensity of Air = 0.076474 lb/ft^3
            - S is cross-section = d^2 pi/4, where d is bullet diameter in inches
            - m is bullet mass in pounds
            - bc contains m/d^2 in units lb/in^2, which is multiplied by 144 to convert to lb/ft^2

        Thus:
            - The magic constant found here = StandardDensity * pi / (4 * 2 * 144)

        Args:
            mach (float): The Mach number.

        Returns:
            float: The drag coefficient at the given Mach number.
        """
        # cd = calculate_by_curve(self._table_data, self._curve, mach)
        # use calculation over list[double] instead of list[DragDataPoint]
        cd = _calculate_by_curve_and_mach_list(self.__mach_list, self._curve, mach)
        return cd * 2.08551e-04 / self._bc

    def spin_drift(self, time) -> float:
        """
        Litz spin-drift approximation

        Args:
            time: Time of flight

        Returns:
            windage due to spin drift, in feet
        """
        if (self.stability_coefficient != 0) and (self.twist != 0):
            sign = 1 if self.twist > 0 else -1
            return sign * (1.25 * (self.stability_coefficient + 1.2)
                           * math.pow(time, 1.83)) / 12
        return 0

    def calc_stability_coefficient(self, atmo: Atmo) -> float:
        """
        Calculates the Miller stability coefficient.

        Args:
            atmo (Atmo): Atmospheric conditions.

        Returns:
            float: The Miller stability coefficient.
        """
        if self.twist and self.length and self.diameter and atmo.pressure.raw_value:
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


# pylint: disable=too-many-positional-arguments
def create_trajectory_row(time: float, range_vector: Vector, velocity_vector: Vector,
                          velocity: float, mach: float, spin_drift: float, look_angle: float,
                          density_factor: float, drag: float, weight: float,
                          flag: Union[TrajFlag, int]) -> TrajectoryData:
    """
    Creates a TrajectoryData object representing a single row of trajectory data.

    Args:
        time (float): Time of flight.
        range_vector (Vector): Position vector.
        velocity_vector (Vector): Velocity vector.
        velocity (float): Velocity magnitude.
        mach (float): Mach number.
        spin_drift (float): Spin drift value.
        look_angle (float): Look angle value.
        density_factor (float): Density factor.
        drag (float): Drag value.
        weight (float): Weight value.
        flag (Union[TrajFlag, int]): Flag value.

    Returns:
        TrajectoryData: A TrajectoryData object representing the trajectory data.
    """
    windage = range_vector.z + spin_drift
    drop_adjustment = get_correction(range_vector.x, range_vector.y)
    windage_adjustment = get_correction(range_vector.x, windage)
    trajectory_angle = math.atan2(velocity_vector.y, velocity_vector.x)

    return TrajectoryData(
        time=time,
        distance=_new_feet(range_vector.x),
        velocity=_new_fps(velocity),
        mach=velocity / mach,
        height=_new_feet(range_vector.y),
        target_drop=_new_feet((range_vector.y - range_vector.x * math.tan(look_angle)) * math.cos(look_angle)),
        drop_adj=_new_rad(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=_new_feet(windage),
        windage_adj=_new_rad(windage_adjustment),
        look_distance=_new_feet(range_vector.x / math.cos(look_angle)),
        angle=_new_rad(trajectory_angle),
        density_factor=density_factor - 1,
        drag=drag,
        energy=_new_ft_lb(calculate_energy(weight, velocity)),
        ogw=_new_lb(calculate_ogw(weight, velocity)),
        flag=flag
    )


# pylint: disable protected-access
def _new_feet(v: float):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


# pylint: disable protected-access
def _new_fps(v: float):
    d = object.__new__(Velocity)
    d._value = v / 3.2808399
    d._defined_units = Unit.FPS
    return d


# pylint: disable protected-access
def _new_rad(v: float):
    d = object.__new__(Angular)
    d._value = v
    d._defined_units = Unit.Radian
    return d


# pylint: disable protected-access
def _new_ft_lb(v: float):
    d = object.__new__(Energy)
    d._value = v
    d._defined_units = Unit.FootPound
    return d


# pylint: disable protected-access
def _new_lb(v: float):
    d = object.__new__(Weight)
    d._value = v / 0.000142857143
    d._defined_units = Unit.Pound
    return d


def get_correction(distance: float, offset: float) -> float:
    """Calculates the sight adjustment in radians.

    Args:
        distance (float): The distance to the target in feet.
        offset (float): The offset from the target in feet.

    Returns:
        float: The sight adjustment in radians.
    """
    if distance != 0:
        return math.atan(offset / distance)
    return 0  # None


def calculate_energy(bullet_weight: float, velocity: float) -> float:
    """Calculates the kinetic energy of a projectile.

    Args:
        bullet_weight (float): The weight of the bullet in pounds.
        velocity (float): The velocity of the bullet in feet per second.

    Returns:
        float: The kinetic energy of the projectile in foot-pounds.
    """
    return bullet_weight * math.pow(velocity, 2) / 450400


def calculate_ogw(bullet_weight: float, velocity: float) -> float:
    """Calculates the optimal game weight for a projectile.

    Args:
        bullet_weight (float): The weight of the bullet in pounds.
        velocity (float): The velocity of the bullet in feet per second.

    Returns:
        float: The optimal game weight in pounds.
    """
    return math.pow(bullet_weight, 2) * math.pow(velocity, 3) * 1.5e-12


def calculate_curve(data_points: List[DragDataPoint]) -> List[CurvePoint]:
    """Piecewise quadratic interpolation of drag curve
    Args:
        data_points: List[{Mach, CD}] data_points in ascending Mach order
    Returns:
        List[CurvePoints] to interpolate drag coefficient
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


# # use ._get_only_mach_data with ._calculate_by_curve_and_mach_list because it's faster
# def calculate_by_curve(data: List[DragDataPoint], curve: List[CurvePoint], mach: float) -> float:
#     """
#     Binary search for drag coefficient based on Mach number
#     :param data: data
#     :param curve: Output of calculate_curve(data)
#     :param mach: Mach value for which we're searching for CD
#     :return float: drag coefficient
#     """
#     num_points = int(len(curve))
#     mlo = 0
#     mhi = num_points - 2
#
#     while mhi - mlo > 1:
#         mid = int(math.floor(mhi + mlo) / 2.0)
#         if data[mid].Mach < mach:
#             mlo = mid
#         else:
#             mhi = mid
#
#     if data[mhi].Mach - mach > mach - data[mlo].Mach:
#         m = mlo
#     else:
#         m = mhi
#     curve_m = curve[m]
#     return curve_m.c + mach * (curve_m.b + curve_m.a * mach)


# Function to convert a list of DragDataPoint to an array of doubles containing only Mach values
def _get_only_mach_data(data: List[DragDataPoint]) -> List[float]:
    """
    Extracts Mach values from a list of DragDataPoint objects.

    Args:
        data (List[DragDataPoint]): A list of DragDataPoint objects.

    Returns:
        List[float]: A list containing only the Mach values from the input data.
    """
    result = []
    for dp in data:
        result.append(dp.Mach)
    return result


def _calculate_by_curve_and_mach_list(mach_list: List[float], curve: List[CurvePoint], mach: float) -> float:
    """
    Calculates a value based on a piecewise quadratic curve and a list of Mach values.

    This function performs a binary search on the `mach_list` to find the segment
    of the `curve` relevant to the input `mach` number and then interpolates
    the value using the quadratic coefficients of that curve segment.

    Args:
        mach_list (List[float]): A sorted list of Mach values corresponding to the `curve` points.
        curve (List[CurvePoint]): A list of CurvePoint objects, where each object
            contains quadratic coefficients (a, b, c) for a Mach number segment.
        mach (float): The Mach number at which to calculate the value.

    Returns:
        float: The calculated value based on the interpolated curve at the given Mach number.
    """
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


__all__ = (
    'TrajectoryCalc',
    'get_global_max_calc_step_size',
    'set_global_max_calc_step_size',
    'reset_globals',
    'cZeroFindingAccuracy',
    'cMinimumVelocity',
    'cMaximumDrop',
    'cMaxIterations',
    'cGravityConstant',
    'cMinimumAltitude',
    'Config',
    'calculate_energy',
    'calculate_ogw',
    'get_correction',
    'create_trajectory_row',
    '_TrajectoryDataFilter',
    '_WindSock'
)
