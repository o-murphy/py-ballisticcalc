# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum, auto

from typing_extensions import Optional, Any, NamedTuple, Union, List, Tuple, Dict, TypedDict, TypeVar

from py_ballisticcalc.logger import logger
from py_ballisticcalc.conditions import Atmo, Shot, Wind
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag, HitResult
from py_ballisticcalc.unit import Distance, Angular, Velocity, Weight, Energy, Pressure, Temperature, Unit
from py_ballisticcalc.vector import Vector

__all__ = (
    'create_base_engine_config',
    'BaseEngineConfig',
    'BaseEngineConfigDict',
    'DEFAULT_BASE_ENGINE_CONFIG',
    'BaseIntegrationEngine',
    'calculate_energy',
    'calculate_ogw',
    'get_correction',
    'create_trajectory_row',
    '_TrajectoryDataFilter',
    '_WindSock',
    'CurvePoint'
)

cZeroFindingAccuracy: float = 0.000005  # Max allowed slant-error in feet to end zero search
cMaxIterations: int = 60         # maximum number of iterations for zero search
cMinimumAltitude: float = -1500  # feet, below sea level
cMaximumDrop: float = -15000     # feet, maximum drop from the muzzle to continue trajectory
cMinimumVelocity: float = 50.0   # fps, minimum velocity to continue trajectory
cGravityConstant: float = -32.17405  # feet per second squared
cMaxCalcStepSizeFeet: float = 0.5


@dataclass
class BaseEngineConfig:
    cZeroFindingAccuracy: float = cZeroFindingAccuracy
    cMaxIterations: int = cMaxIterations
    cMinimumAltitude: float = cMinimumAltitude
    cMaximumDrop: float = cMaximumDrop
    cMinimumVelocity: float = cMinimumVelocity
    cGravityConstant: float = cGravityConstant
    cMaxCalcStepSizeFeet: float = cMaxCalcStepSizeFeet


DEFAULT_BASE_ENGINE_CONFIG: BaseEngineConfig = BaseEngineConfig()


class BaseEngineConfigDict(TypedDict, total=False):
    cZeroFindingAccuracy: Optional[float]
    cMaxIterations: Optional[int]
    cMinimumAltitude: Optional[float]
    cMaximumDrop: Optional[float]
    cMinimumVelocity: Optional[float]
    cGravityConstant: Optional[float]
    cMaxCalcStepSizeFeet: Optional[float]


def create_base_engine_config(interface_config: Optional[BaseEngineConfigDict] = None) -> BaseEngineConfig:
    config = asdict(DEFAULT_BASE_ENGINE_CONFIG)
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return BaseEngineConfig(**config)


class CurvePoint(NamedTuple):
    """Coefficients for quadratic interpolation"""
    a: float
    b: float
    c: float


class BaseTrajData(NamedTuple):
    """Minimal data for one point in ballistic trajectory"""
    time: float
    position: Vector
    velocity: Vector
    mach: float


class _TrajectoryDataFilter:
    """
    Determines when to record trajectory data points based on range and time.
    For range steps, interpolates between integration steps to get the exact point.
    There is no interpolation for other points of interest (APEX, MACH, ZERO), unless
        they correspond to a range step, in which case they are interpolated to the range step.
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
                 initial_position: Vector, initial_velocity: Vector,
                 barrel_angle_rad: float, look_angle_rad: float = 0.0,
                 time_step: float = 0.0):
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
        self.look_angle: float = look_angle_rad
        if self.filter & TrajFlag.ZERO:
            if initial_position.y >= 0:
                self.seen_zero |= TrajFlag.ZERO_UP
            elif initial_position.y < 0 and barrel_angle_rad < self.look_angle:
                self.seen_zero |= TrajFlag.ZERO_DOWN

    # pylint: disable=too-many-positional-arguments
    def should_record(self, position: Vector, velocity: Vector, mach: float,
                      time: float) -> Optional[BaseTrajData]:
        self.current_flag = TrajFlag.NONE
        data = None
        if (self.range_step > 0) and (position.x >= self.next_record_distance):
            while self.next_record_distance + self.range_step < position.x:
                # Handle case where we have stepped past more than one record distance
                self.next_record_distance += self.range_step
            if position.x > self.previous_position.x:
                # Interpolate to get BaseTrajData at the record distance
                ratio = (self.next_record_distance - self.previous_position.x) / (
                        position.x - self.previous_position.x)
                data = BaseTrajData(
                    time=self.previous_time + (time - self.previous_time) * ratio,
                    position=self.previous_position + (  # type: ignore[operator]
                            position - self.previous_position) * ratio,
                    velocity=self.previous_velocity + (  # type: ignore[operator]
                            velocity - self.previous_velocity) * ratio,
                    mach=self.previous_mach + (mach - self.previous_mach) * ratio
                )
            self.current_flag |= TrajFlag.RANGE
            self.next_record_distance += self.range_step
            self.time_of_last_record = time
        elif self.time_step > 0:
            self.check_next_time(time)
        if self.filter & TrajFlag.ZERO:
            self.check_zero_crossing(position)
        if self.filter & TrajFlag.MACH:
            self.check_mach_crossing(velocity.magnitude(), mach)
        if self.filter & TrajFlag.APEX:
            self.check_apex(velocity)
        if bool(self.current_flag & self.filter) and data is None:
            data = BaseTrajData(time=time, position=position,
                                velocity=velocity, mach=mach)
        self.previous_time = time
        self.previous_position = position
        self.previous_velocity = velocity
        self.previous_mach = mach
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
        # Especially with non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        #   self.seen_zero prevents recording more than one.
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

    def check_apex(self, velocity_vector: Vector):
        """
        The apex is defined as the point, after launch, where the vertical component of velocity
            goes from positive to negative.
        """
        if velocity_vector.y <= 0 and self.previous_velocity.y > 0:
            self.current_flag |= TrajFlag.APEX


class _WindSock:
    """
    Currently this class assumes that requests for wind readings will only be made in order of increasing range.
    This assumption is violated if the projectile is blown or otherwise moves backwards.
    """
    winds: tuple['Wind', ...]
    current_index: int
    next_range: float

    def __init__(self, winds: Union[Tuple["Wind", ...], None]):
        """
        Initializes the _WindSock class.

        Args:
            winds (Union[Tuple[Wind, ...], None], optional): A tuple of Wind objects. Defaults to None.
        """
        self.winds: Tuple["Wind", ...] = winds or tuple()
        self.current_index: int = 0
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
        if self.current_index < self._length:
            cur_wind = self.winds[self.current_index]
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
            self.current_index += 1
            if self.current_index >= self._length:
                self._last_vector_cache = Vector(0.0, 0.0, 0.0)
                self.next_range = Wind.MAX_DISTANCE_FEET
            else:
                self.update_cache()  # This will trigger cache updates.
        return self.current_vector()


_BaseEngineConfigDictT = TypeVar("_BaseEngineConfigDictT", bound='BaseEngineConfigDict', covariant=True)

# pylint: disable=too-many-instance-attributes
class BaseIntegrationEngine(ABC, EngineProtocol[_BaseEngineConfigDictT]):
    """
    All calculations are done in imperial units of feet and fps.

    Attributes:
        barrel_azimuth (float): The azimuth angle of the barrel.
        barrel_elevation (float): The elevation angle of the barrel.
        twist (float): The twist rate of barrel rifling, in inches of length to make one full rotation.
        gravity_vector (Vector): The gravity vector.
    """
    APEX_IS_MAX_RANGE_RADIANS: float = 0.02  # Radians from vertical where the apex is max range
    ALLOWED_ZERO_ERROR_FEET: float = 1e-2  # Allowed range error (along sight line), in feet, for zero angle

    barrel_azimuth_rad: float
    barrel_elevation_rad: float
    twist: float
    gravity_vector: Vector
    _table_data: List[DragDataPoint]

    def __init__(self, _config: _BaseEngineConfigDictT):
        """
        Initializes the TrajectoryCalc class.

        Args:
            _config (BaseEngineConfig): The configuration object.
        """
        self._config: BaseEngineConfig = create_base_engine_config(_config)
        self.gravity_vector: Vector = Vector(.0, self._config.cGravityConstant, .0)
        self._table_data = []

    def get_calc_step(self, step: float = 0) -> float:
        """
        Keep step under max_calc_step_size

        Args:
            step (float, optional): proposed step size. Defaults to 0.

        Returns:
            float: step size for calculations (in feet)
        """
        preferred_step = self._config.cMaxCalcStepSizeFeet
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
        self._table_data = shot_info.ammo.dm.drag_table
        self._curve: List[CurvePoint] = calculate_curve(self._table_data)

        # use calculation over list[double] instead of list[DragDataPoint]
        self.__mach_list: List[float] = _get_only_mach_data(self._table_data)

        self.look_angle_rad = shot_info.look_angle >> Angular.Radian
        self.twist = shot_info.weapon.twist >> Distance.Inch
        self.length = shot_info.ammo.dm.length >> Distance.Inch
        self.diameter = shot_info.ammo.dm.diameter >> Distance.Inch
        self.weight = shot_info.ammo.dm.weight >> Weight.Grain
        self.barrel_elevation_rad = shot_info.barrel_elevation >> Angular.Radian
        self.barrel_azimuth_rad = shot_info.barrel_azimuth >> Angular.Radian
        self.sight_height = shot_info.weapon.sight_height >> Distance.Foot
        self.cant_cosine = math.cos(shot_info.cant_angle >> Angular.Radian)
        self.cant_sine = math.sin(shot_info.cant_angle >> Angular.Radian)
        self.alt0 = shot_info.atmo.altitude >> Distance.Foot
        self.calc_step = self.get_calc_step()
        self.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp) >> Velocity.FPS
        self.stability_coefficient = self.calc_stability_coefficient(shot_info.atmo)

    def find_max_range(self, shot_info: Shot, angle_bracket_deg: Tuple[float, float] = (0, 90)) -> Tuple[Distance, Angular]:
        """
        Finds the maximum horizontal range and the launch angle to reach it, via golden-section search.

        Args:
            shot_info (Shot): The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg (Tuple[float, float], optional): The angle bracket in degrees to search for the maximum range.
                                                               Defaults to (0, 90).

        Returns:
            Tuple[Distance, Angular]: The maximum range and the launch angle to reach it.

        Raises:
            ValueError: If the angle bracket excludes the look_angle.
        """
        restore_cMaximumDrop = None
        if self._config.cMaximumDrop:
            restore_cMaximumDrop = self._config.cMaximumDrop
            self._config.cMaximumDrop = 0  # We want to run trajectory until it returns to horizontal
        self._init_trajectory(shot_info)

        t_calls = 0
        cache: Dict[float, float] = {}
        def range_for_angle(angle_rad: float) -> float:
            """Horizontal range to zero (in feet) for given launch angle in radians."""
            if angle_rad in cache:
                return cache[angle_rad]
            self.barrel_elevation_rad = angle_rad
            nonlocal t_calls
            t_calls += 1
            logger.debug(f"range_for_angle call #{t_calls} for angle {math.degrees(angle_rad)} degrees")
            try:
                t = self._integrate(shot_info, 9e9, 9e9, TrajFlag.NONE)[-1]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
            cache[angle_rad] = t.distance >> Distance.Foot
            return cache[angle_rad]

        #region Golden-section search
        inv_phi = (math.sqrt(5) - 1) / 2  # 0.618...
        inv_phi_sq = inv_phi**2
        a, b = (math.radians(deg) for deg in angle_bracket_deg)
        h = b - a
        c = a + inv_phi_sq * h
        d = a + inv_phi * h
        yc = range_for_angle(c)
        yd = range_for_angle(d)
        for _ in range(100): # 100 iterations is more than enough for high precision
            if h < 1e-5: # Angle tolerance in radians
                break
            if yc > yd:
                b, d, yd = d, c, yc
                h = b - a
                c = a + inv_phi_sq * h
                yc = range_for_angle(c)
            else:
                a, c, yc = c, d, yd
                h = b - a
                d = a + inv_phi * h
                yd = range_for_angle(d)
        angle_at_max_rad = (a + b) / 2
        #endregion
        max_range_ft = range_for_angle(angle_at_max_rad)

        if restore_cMaximumDrop is not None:
            self._config.cMaximumDrop = restore_cMaximumDrop
        logger.debug(f".find_max_range required {t_calls} trajectory calculations")
        return Distance.Feet(max_range_ft), Angular.Radian(angle_at_max_rad)

    def find_apex(self, shot_info: Shot) -> TrajectoryData:
        """Returns the TrajectoryData at the trajectory's apex (where velocity.y goes from positive to negative).
            Have to ensure cMinimumVelocity is 0 for this to work."""
        self._init_trajectory(shot_info)
        restoreMinVelocity = None
        if self._config.cMinimumVelocity > 0:
            restoreMinVelocity = self._config.cMinimumVelocity
            self._config.cMinimumVelocity = 0.
        self.barrel_elevation_rad = self.look_angle_rad
        try:
            t = HitResult(shot_info,
                          self._integrate(shot_info, 9e9, 9e9, TrajFlag.APEX), extra=True)
        except RangeError as e:
            if e.last_distance is None:
                raise e
            t = HitResult(shot_info, e.incomplete_trajectory, extra=True)
        if restoreMinVelocity is not None:
            self._config.cMinimumVelocity = restoreMinVelocity
        apex = t.flag(TrajFlag.APEX)
        if not apex:
            raise SolverRuntimeError("No apex flagged in trajectory data")
        return apex

    class _ZeroCalcStatus(Enum):
        DONE = auto()  # Zero angle found, just return it
        CONTINUE = auto()  # Continue searching for zero angle

    def _init_zero_calculation(self, shot_info: Shot, distance: Distance) -> Tuple[_ZeroCalcStatus, Any]:
        """
        Initializes the zero calculation for the given shot and distance.
        Handles edge cases.

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.

        Returns:
            Tuple[_ZeroCalcStatus, Any]: If _ZeroCalcStatus.DONE, second value is Angular.Radian zero angle.
                Otherwise, it is a tuple of the variables.
        """
        self._init_trajectory(shot_info)

        look_angle = shot_info.look_angle >> Angular.Radian
        target_look_dist_ft = distance >> Distance.Foot
        target_x_ft = target_look_dist_ft * math.cos(look_angle)
        target_y_ft = target_look_dist_ft * math.sin(look_angle)
        start_height = -self.sight_height * self.cant_cosine

        # region Edge cases
        if abs(target_look_dist_ft) < self.ALLOWED_ZERO_ERROR_FEET:
            return self._ZeroCalcStatus.DONE, shot_info.look_angle
        if abs(target_look_dist_ft) < 2.0 * max(abs(start_height), self.calc_step):
            # Very close shot; ignore gravity and drag
            return self._ZeroCalcStatus.DONE, Angular.Radian(math.atan2(target_y_ft + start_height, target_x_ft))
        if abs(self.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            # Virtually vertical shot; just check if it can reach the target
            max_range = self.find_apex(shot_info).look_distance
            if (max_range >> Distance.Foot) < target_look_dist_ft:
                raise OutOfRangeError(distance, max_range, shot_info.look_angle)
            return self._ZeroCalcStatus.DONE, shot_info.look_angle
        # endregion Edge cases

        return self._ZeroCalcStatus.CONTINUE, (
            look_angle, target_look_dist_ft, target_x_ft, target_y_ft, start_height
        )

    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool=False) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance,
            using unimodal root-finding that is guaranteed to succeed if a solution exists (e.g., Ridder's method).

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.
            lofted (bool, optional): If True, find the higher angle that hits the zero point.

        Returns:
            Angular: The required barrel elevation.
        """
        raise NotImplementedError("find_zero_angle not yet implemented in BaseIntegrationEngine.")

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero

        Args:
            shot_info (Shot): Shot parameters
            distance (Distance): Sight distance to zero (i.e., along Shot.look_angle),
                                 a.k.a. slant range to target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance along sight line
        """
        status, result = self._init_zero_calculation(shot_info, distance)
        if status is self._ZeroCalcStatus.DONE:
            return result
        look_angle_rad, target_look_dist_ft, target_x_ft, target_y_ft, start_height_ft = result

        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations

        zero_distance = (distance >> Distance.Foot) * math.cos(look_angle_rad)  # Horizontal distance

        iterations_count = 0
        range_error_ft = 9e9  # Absolute value of error from target distance along sight line
        prev_range_error_ft = 9e9
        prev_height_error_ft = 9e9
        slant_error_ft = _cZeroFindingAccuracy * 2  # Absolute value of error from sight line in feet at zero distance
        range_limit = False  # Flag to avoid 1st-order correction when instability detected

        while iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current self.barrel_elevation)
            try:
                t = self._integrate(shot_info, target_x_ft, target_x_ft, TrajFlag.NONE)[-1]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
            if t.time == 0.0:
                logger.warning("Integrator returned initial point. Consider removing constraints.")
                break

            current_distance = t.distance >> Distance.Foot  # Horizontal distance
            if 2 * current_distance < zero_distance and self.barrel_elevation_rad == 0.0 and look_angle_rad < 1.5:
                # Degenerate case: little distance and zero elevation; try with some elevation
                self.barrel_elevation_rad = 0.01
                continue

            slant_diff_ft = t.target_drop >> Distance.Foot
            look_dist_ft = t.look_distance >> Distance.Foot
            horizontal_ft = t.distance >> Distance.Foot  # Horizontal distance
            trajectory_angle = t.angle >> Angular.Radian  # Flight angle at current distance
            sensitivity = math.tan(self.barrel_elevation_rad) * math.tan(trajectory_angle)
            if -1.5 < sensitivity < -0.5 and not range_limit:  # TODO: Find good bounds for this
                # Scenario too unstable for 1st order iteration
                logger.warning("Unstable scenario detected in zero_angle(); probably won't converge...")
                range_limit = True  # Scenario too unstable for 1st-order correction
            elif abs(sensitivity) > 1000 and not range_limit:  # TODO: Find good bounds for this
                logger.debug("High sensitivity; using slant correction")
                range_limit = True  # Scenario too unstable for 1st-order correction

            if range_limit or horizontal_ft == 0:
                if abs(look_dist_ft) > 1e-6:
                    correction = -slant_diff_ft / look_dist_ft
                else:
                    correction = -slant_diff_ft  # Avoid division by zero
            else:
                correction = -slant_diff_ft / (horizontal_ft * (1 + sensitivity))  # 1st order correction

            range_diff_ft = look_dist_ft - target_look_dist_ft
            range_error_ft = math.fabs(range_diff_ft)
            slant_error_ft = math.fabs(slant_diff_ft)

            if range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # We're still trying to reach zero_distance
                if range_error_ft > prev_range_error_ft - 1e-6:  # We're not getting closer to zero_distance
                    raise ZeroFindingError(slant_diff_ft, iterations_count, Angular.Radian(self.barrel_elevation_rad),
                                           'Distance non-convergent.')
            elif slant_error_ft > math.fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                raise ZeroFindingError(slant_diff_ft, iterations_count, Angular.Radian(self.barrel_elevation_rad),
                                       'Error non-convergent.')

            prev_range_error_ft = range_error_ft
            prev_height_error_ft = slant_error_ft

            if slant_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # Adjust barrel elevation to close height at zero distance
                self.barrel_elevation_rad += correction
            else:  # Current barrel_elevation hit zero!
                break
            iterations_count += 1

        if slant_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(slant_error_ft, iterations_count, Angular.Radian(self.barrel_elevation_rad))
        return Angular.Radian(self.barrel_elevation_rad)

    @abstractmethod
    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List[TrajectoryData]:
        """
        Calculate trajectory for specified shot.  Requirements:
        - If filter_flags==TrajFlag.NONE, then must return a list of exactly one TrajectoryData where:
            - .distance = maximum_range if reached, else last calculated point.
        - If filter_flags & TrajFlag.RANGE, then return must include a RANGE entry for each record_step reached,
            starting at zero (initial conditions).  If time_step > 0, must also include RANGE entries per that spec.
        - For each other filter_flag: Return list must include a row with the flag if it exists in the trajectory.
            Do not duplicate rows: If two flags occur at the exact same time, mark the row with both flags.

        Args:
            shot_info (Shot): Information specific to the shot.
            maximum_range (float): Feet down-range to stop calculation
            record_step (float): Frequency (in feet down-range) to record TrajectoryData
            filter_flags (Union[TrajFlag, int]): Bitfield for trajectory points of interest to record.
            time_step (float, optional): If > 0 then record TrajectoryData after this many seconds elapse
                since last record, as could happen when trajectory is nearly vertical
                and there is too little movement down-range to trigger a record based on range.
                Defaults to 0.0

        Returns:
            List[TrajectoryData]: list of TrajectoryData
        """
        raise NotImplementedError

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
                          density_ratio: float, drag: float, weight: float,
                          flag: Union[TrajFlag, int]) -> TrajectoryData:
    """
    Creates a TrajectoryData object representing a single row of trajectory data.

    Args:
        time (float): Time of flight in seconds.
        range_vector (Vector): Position vector in feet.
        velocity_vector (Vector): Velocity vector in fps.
        velocity (float): Velocity magnitude in fps.
        mach (float): Mach number.
        spin_drift (float): Spin drift in feet.
        look_angle (float): Look angle in radians.
        density_ratio (float): Density ratio (rho / rho_0).
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
        target_drop=_new_feet(range_vector.y * math.cos(look_angle) - range_vector.x * math.sin(look_angle)),
        drop_adj=_new_rad(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=_new_feet(windage),
        windage_adj=_new_rad(windage_adjustment),
        look_distance=_new_feet(range_vector.x * math.cos(look_angle) + range_vector.y * math.sin(look_angle)),
        angle=_new_rad(trajectory_angle),
        density_factor=density_ratio - 1,
        drag=drag,
        energy=_new_ft_lb(calculate_energy(weight, velocity)),
        ogw=_new_lb(calculate_ogw(weight, velocity)),
        flag=flag
    )


def _new_feet(v: float):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


def _new_fps(v: float):
    d = object.__new__(Velocity)
    d._value = v / 3.2808399
    d._defined_units = Unit.FPS
    return d


def _new_rad(v: float):
    d = object.__new__(Angular)
    d._value = v
    d._defined_units = Unit.Radian
    return d


def _new_ft_lb(v: float):
    d = object.__new__(Energy)
    d._value = v
    d._defined_units = Unit.FootPound
    return d


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
    return [dp.Mach for dp in data]


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
