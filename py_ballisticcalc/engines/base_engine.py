"""Base integration engine for ballistic trajectory calculations.

The module serves as the core framework for the engine system, providing:
- Engine configuration management through BaseEngineConfig and BaseEngineConfigDict
- Abstract base class BaseIntegrationEngine implementing the EngineProtocol
- Trajectory data filtering and processing utilities

Classes:
    BaseEngineConfig: Dataclass configuration for engine parameters
    BaseEngineConfigDict: TypedDict version for flexible configuration
    BaseIntegrationEngine: Abstract base class for integration engines
    TrajectoryDataFilter: Utility for filtering and processing trajectory data
    _WindSock: Internal wind modeling utility
    _ZeroCalcStatus: Enumeration for zero-finding calculation status

Configuration Constants:
    cZeroFindingAccuracy: Maximum allowed error for zero-finding (feet)
    cMaxIterations: Maximum iterations for zero-finding algorithms
    cMinimumVelocity: Minimum velocity to continue trajectory calculation (fps)
    cGravityConstant: Gravitational acceleration constant (ft/s²)

Architecture:
    This module follows the strategy pattern, where BaseIntegrationEngine
    provides the common interface and algorithms, while concrete subclasses
    implement specific numerical integration methods (Euler, RK4, Verlet, etc.).
    
    The configuration system supports both dataclass and TypedDict formats
    for maximum flexibility in different usage contexts.

See Also:
    py_ballisticcalc.generics.engine.EngineProtocol: Protocol interface
    py_ballisticcalc.engines: Concrete engine implementations
    py_ballisticcalc.trajectory_data: Data structures for results
"""
from __future__ import annotations
import math
from typing import Sequence
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum, auto

from typing_extensions import List, NamedTuple, Optional, Tuple, TypedDict, TypeVar, Union

from py_ballisticcalc._compat import bisect_left_key
from py_ballisticcalc.conditions import Shot, ShotProps, Wind
from py_ballisticcalc.exceptions import ZeroFindingError, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import BaseTrajData, HitResult, TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Distance, Angular
from py_ballisticcalc.vector import Vector

__all__ = (
    'create_base_engine_config',
    'BaseEngineConfig',
    'BaseEngineConfigDict',
    'DEFAULT_BASE_ENGINE_CONFIG',
    'BaseIntegrationEngine',
    'TrajectoryDataFilter',
    '_WindSock',
    '_ZeroCalcStatus',
    'with_no_minimum_velocity',
    'with_max_drop_zero',
)

cZeroFindingAccuracy: float = 0.000005  # Max allowed slant-error in feet to end zero search
cMaxIterations: int = 40  # maximum number of iterations for zero search
cMinimumAltitude: float = -1500  # feet, below sea level
cMaximumDrop: float = -10000  # feet, maximum drop from the muzzle to continue trajectory
cMinimumVelocity: float = 50.0  # fps, minimum velocity to continue trajectory
cGravityConstant: float = -32.17405  # feet per second squared
cStepMultiplier: float = 1.0  # Multiplier for engine's default step, for changing integration speed & precision


@dataclass
class BaseEngineConfig:
    """Configuration dataclass for ballistic calculation engines.

    All parameters use imperial units (feet, fps) for internal calculations.

    Attributes:
        cZeroFindingAccuracy: Maximum allowed slant-error (in feet) for zero-finding.
                             Smaller values increase precision but may slow calculations.
                             Defaults to 0.000005 feet.
        cMaxIterations: Maximum iterations for iterative algorithms (zero-finding, etc.).
                       Prevents infinite loops in convergence algorithms.
                       Defaults to 40 iterations.
        cMinimumAltitude: Minimum altitude in feet below sea level to continue calculation.
                         Trajectory stops if projectile goes below this altitude.
                         Defaults to -1500 feet.
        cMaximumDrop: Maximum drop in feet from muzzle to continue calculation.
                     Trajectory stops if drop exceeds this value (negative number).
                     Defaults to -10000 feet.
        cMinimumVelocity: Minimum velocity in fps to continue calculation.
                         Trajectory stops when velocity falls below this threshold.
                         Defaults to 50.0 fps.
        cGravityConstant: Gravitational acceleration in ft/s².
                         Standard Earth gravity for ballistic calculations.
                         Defaults to -32.17405 ft/s².
        cStepMultiplier: Multiplier for engine's default integration step size.
                        Values < 1.0 increase precision but slow calculation.
                        Values > 1.0 decrease precision but speed calculation.
                        Defaults to 1.0.
    
    Examples:
        >>> config = BaseEngineConfig(
        ...     cMinimumVelocity=100.0,
        ...     cStepMultiplier=0.5  # Higher precision
        ... )
        
    Note:
        This dataclass is primarily used internally. For flexible configuration
        from dictionaries, use BaseEngineConfigDict with create_base_engine_config().
    """

    cZeroFindingAccuracy: float = cZeroFindingAccuracy
    cMaxIterations: int = cMaxIterations
    cMinimumAltitude: float = cMinimumAltitude
    cMaximumDrop: float = cMaximumDrop
    cMinimumVelocity: float = cMinimumVelocity
    cGravityConstant: float = cGravityConstant
    cStepMultiplier: float = cStepMultiplier


#: Default configuration instance using standard ballistic calculation parameters
DEFAULT_BASE_ENGINE_CONFIG: BaseEngineConfig = BaseEngineConfig()


class BaseEngineConfigDict(TypedDict, total=False):
    """TypedDict for flexible engine configuration from dictionaries.
    
    This TypedDict provides a flexible way to configure ballistic calculation
    engines using dictionary syntax. All fields are optional, allowing partial
    configuration where only specific parameters need to be overridden.
    
    When used with create_base_engine_config(), any unspecified fields will
    use their default values from DEFAULT_BASE_ENGINE_CONFIG.

    Note: All fields are Optional to support partial configuration.

    Fields:
        - cZeroFindingAccuracy: Maximum slant-error in feet for zero-finding precision.
        - cMaxIterations: Maximum iterations for convergence algorithms.
        - cMinimumAltitude: Minimum altitude in feet to continue calculation.
        - cMaximumDrop: Maximum drop in feet from muzzle to continue.
        - cMinimumVelocity: Minimum velocity in fps to continue calculation.
        - cGravityConstant: Gravitational acceleration in ft/s².
        - cStepMultiplier: Integration step size multiplier.

    Examples:
        >>> config_dict: BaseEngineConfigDict = {
        ...     'cMinimumVelocity': 100.0,
        ...     'cStepMultiplier': 0.8
        ... }
        >>> config = create_base_engine_config(config_dict)
        >>> # Using with Calculator
        >>> from py_ballisticcalc import Calculator
        >>> calc = Calculator(config=config_dict)
        
    See Also:
        - BaseEngineConfig: Type-safe dataclass version
        - create_base_engine_config: Factory function for BaseEngineConfig creation
    """

    cZeroFindingAccuracy: Optional[float]
    cMaxIterations: Optional[int]
    cMinimumAltitude: Optional[float]
    cMaximumDrop: Optional[float]
    cMinimumVelocity: Optional[float]
    cGravityConstant: Optional[float]
    cStepMultiplier: Optional[float]


def create_base_engine_config(interface_config: Optional[BaseEngineConfigDict] = None) -> BaseEngineConfig:
    """Create BaseEngineConfig from optional dictionary configuration.
    
    This factory function creates a BaseEngineConfig instance by merging
    default configuration values with user-provided overrides. It provides
    a convenient way to create engine configurations from dictionary data
    while ensuring all parameters have valid defaults.
    
    Args:
        interface_config: Optional dictionary containing configuration overrides.
                         If None, returns the default configuration.
                         Only specified fields will override defaults.
                         
    Returns:
        BaseEngineConfig instance with merged configuration values.
        
    Raises:
        TypeError: If interface_config is not None and not a dictionary.
        
    Examples:
        >>> # Using default configuration
        >>> config = create_base_engine_config()
        
        >>> # Overriding specific parameters
        >>> custom_config = create_base_engine_config({
        ...     'cMinimumVelocity': 75.0,
        ...     'cStepMultiplier': 0.5
        ... })
    """
    config = asdict(DEFAULT_BASE_ENGINE_CONFIG)
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return BaseEngineConfig(**config)


class TrajectoryDataFilter:
    """Record TrajectoryData rows based on TrajFlags and attribute steps.

    - Interpolates for requested points.
    - Assumes that .record() will be called sequentially in time across the trajectory.
    """

    EPSILON = 1e-6  # Range difference (in feet) significant enough to justify interpolation for data
    records: List[TrajectoryData] = []
    props: ShotProps
    filter: Union[TrajFlag, int]
    current_flag: Union[TrajFlag, int]
    seen_zero: Union[TrajFlag, int]
    time_of_last_record: float
    time_step: float
    range_step: float
    range_limit: float
    prev_data: Optional[BaseTrajData]
    prev_prev_data: Optional[BaseTrajData]
    next_record_distance: float
    look_angle_rad: float
    look_angle_tangent: float

    def __init__(self, props: ShotProps, filter_flags: Union[TrajFlag, int],
                 initial_position: Vector, initial_velocity: Vector,
                 barrel_angle_rad: float, look_angle_rad: float = 0.0,
                 range_limit: float = 0.0, range_step: float = 0.0, time_step: float = 0.0):
        """If a time_step > 0, then we will record a row at least that often in the trajectory."""
        self.records = []
        self.props = props
        self.filter = filter_flags
        self.seen_zero = TrajFlag.NONE
        self.time_step = time_step
        self.range_step = range_step
        self.range_limit = range_limit
        self.time_of_last_record = 0.0
        self.next_record_distance = 0.0
        self.prev_data = None
        self.prev_prev_data = None
        self.look_angle_rad = look_angle_rad
        self.look_angle_tangent = math.tan(look_angle_rad)
        if self.filter & TrajFlag.MACH:
            mach = props.get_density_and_mach_for_altitude(initial_position.y)[1]
            if initial_velocity.magnitude() < mach:
                # If we start below Mach 1, we won't look for Mach crossings
                self.filter &= ~TrajFlag.MACH
        if self.filter & TrajFlag.ZERO:
            if initial_position.y >= 0:
                # If shot starts above zero then we will only look for a ZERO_DOWN crossing through the line of sight.
                self.filter &= ~TrajFlag.ZERO_UP
            elif initial_position.y < 0 and barrel_angle_rad <= self.look_angle_rad:
                # If shot starts below zero and barrel points below line of sight we won't look for any crossings.
                self.filter &= ~(TrajFlag.ZERO | TrajFlag.MRT)

    def record(self, new_data: BaseTrajData):
        """For each integration step, creates TrajectoryData records based on filter/step criteria."""
        rows: List[Tuple[BaseTrajData, Union[TrajFlag, int]]] = []
        def add_row(data: BaseTrajData, flag: Union[TrajFlag, int]):
            """Add data, keeping `rows` sorted by time."""
            idx = bisect_left_key(rows, data.time, key=lambda r: r[0].time)
            if idx < len(rows):
                # If we match existing row's time then just add this flag to the row
                if abs(rows[idx][0].time - data.time) < BaseIntegrationEngine.SEPARATE_ROW_TIME_DELTA:
                    rows[idx] = (rows[idx][0], rows[idx][1] | flag)
                    return
                if idx > 0 and abs(rows[idx - 1][0].time - data.time) < BaseIntegrationEngine.SEPARATE_ROW_TIME_DELTA:
                    rows[idx - 1] = (rows[idx - 1][0], rows[idx - 1][1] | flag)
                    return
            rows.insert(idx, (data, flag))  # Insert at sorted position

        if new_data.time == 0.0:
            # Always record starting point
            add_row(new_data, TrajFlag.RANGE if (self.range_step > 0 or self.time_step > 0) else TrajFlag.NONE)
        else:
            #region RANGE steps
            if self.range_step > 0:
                while self.next_record_distance + self.range_step <= new_data.position.x:
                    new_row = None
                    record_distance = self.next_record_distance + self.range_step
                    if record_distance > self.range_limit + self.EPSILON:
                        self.range_step = -1  # Don't calculate range steps past range_limit
                        break
                    if abs(record_distance - new_data.position.x) < self.EPSILON:
                        new_row = new_data
                    elif self.prev_data is not None and self.prev_prev_data is not None:
                        new_row = BaseTrajData.interpolate('position.x', record_distance,
                                                            self.prev_prev_data, self.prev_data, new_data)
                    if new_row is not None:
                        self.next_record_distance += self.range_step
                        add_row(new_row, TrajFlag.RANGE)
                        self.time_of_last_record = new_row.time
                    else:
                        break  # Can't interpolate without previous data
            #endregion RANGE steps
            #region Time steps
            if self.time_step > 0 and self.prev_data is not None and self.prev_prev_data is not None:
                while self.time_of_last_record + self.time_step <= new_data.time:
                    self.time_of_last_record += self.time_step
                    new_row = BaseTrajData.interpolate('time', self.time_of_last_record,
                                                        self.prev_prev_data, self.prev_data, new_data)
                    add_row(new_row, TrajFlag.RANGE)
            #endregion Time steps
            if (self.filter & TrajFlag.APEX and self.prev_data is not None and self.prev_prev_data is not None
                                            and self.prev_data.velocity.y > 0 and new_data.velocity.y <= 0):
                # "Apex" is the point where the vertical component of velocity goes from positive to negative.
                new_row = BaseTrajData.interpolate('velocity.y', 0.0, self.prev_prev_data, self.prev_data, new_data)
                add_row(new_row, TrajFlag.APEX)
                self.filter &= ~TrajFlag.APEX  # Don't look for more apices

        self.records.extend([TrajectoryData.from_base_data(self.props, data, flag) for data, flag in rows])

        #region Points that must be interpolated on TrajectoryData instances
        if self.prev_data is not None and self.prev_prev_data is not None:
            compute_flags = TrajFlag.NONE
            if (self.filter & TrajFlag.MACH and self.prev_data is not None
                and new_data.velocity.magnitude() < new_data.mach):
                compute_flags |= TrajFlag.MACH
                self.filter &= ~TrajFlag.MACH  # Don't look for more Mach crossings
            #region ZERO checks (done on TrajectoryData objects so we can interpolate for .slant_height)
            if self.filter & TrajFlag.ZERO:
                # Zero reference line is the sight line defined by look_angle
                reference_height = new_data.position.x * self.look_angle_tangent
                # If we haven't seen ZERO_UP, we look for that first
                if self.filter & TrajFlag.ZERO_UP:
                    if new_data.position.y >= reference_height:
                        compute_flags |= TrajFlag.ZERO_UP
                        self.filter &= ~TrajFlag.ZERO_UP
                # We've crossed above sight line; now look for crossing back through it
                elif self.filter & TrajFlag.ZERO_DOWN:
                    if new_data.position.y < reference_height:
                        compute_flags |= TrajFlag.ZERO_DOWN
                        self.filter &= ~TrajFlag.ZERO_DOWN
            #endregion ZERO checks
            if compute_flags:
                # Instantiate TrajectoryData and interpolate
                t0 = TrajectoryData.from_base_data(self.props, new_data)
                t1 = TrajectoryData.from_base_data(self.props, self.prev_data)
                t2 = TrajectoryData.from_base_data(self.props, self.prev_prev_data)
                add_td = []
                if compute_flags & TrajFlag.MACH:
                    add_td.append(TrajectoryData.interpolate('mach', 1.0, t0, t1, t2, TrajFlag.MACH))
                    compute_flags &= ~TrajFlag.MACH
                if compute_flags & TrajFlag.ZERO:
                    add_td.append(TrajectoryData.interpolate('slant_height', 0.0, t0, t1, t2, compute_flags))
                for td in add_td:  # Add TrajectoryData, keeping `results` sorted by time.
                    idx = bisect_left_key(self.records, td.time, key=lambda r: r.time)
                    if idx < len(self.records):  # If we match existing row's time then just add this flag to the row
                        if abs(self.records[idx].time - td.time) < BaseIntegrationEngine.SEPARATE_ROW_TIME_DELTA:
                            self.records[idx] = td._replace(flag=self.records[idx].flag | td.flag)
                            continue
                        elif idx > 0 and abs(self.records[idx - 1].time - td.time) < BaseIntegrationEngine.SEPARATE_ROW_TIME_DELTA:
                            self.records[idx - 1] = td._replace(flag=self.records[idx - 1].flag | td.flag)
                            continue
                    self.records.insert(idx, td)  # Insert at sorted position
        #endregion
        self.prev_prev_data = self.prev_data
        self.prev_data = new_data


class _WindSock:
    """Winds in effect down range.
    
    Currently this class assumes that requests for wind readings will only be made in order of increasing range.
    This assumption is violated if the projectile is blown or otherwise moves backwards.
    """

    winds: Sequence[Wind]
    current_index: int
    next_range: float

    def __init__(self, winds: Optional[Sequence[Wind]]):
        """Initialize the _WindSock class.

        Args:
            winds: A sequence of Wind objects. Defaults to None.
        """
        self.winds: Sequence[Wind] = winds or tuple()
        self.current_index: int = 0
        self.next_range: float = Wind.MAX_DISTANCE_FEET
        self._last_vector_cache: Union[Vector, None] = None
        self._length = len(self.winds)

        # Initialize cache correctly
        self.update_cache()

    def current_vector(self) -> Vector:
        """Return the current cached wind vector.

        Raises:
            RuntimeError: If no wind vector has been cached.

        Returns:
            The current cached wind vector.
        """
        if not self._last_vector_cache:
            raise RuntimeError("No cached wind vector")
        return self._last_vector_cache

    def update_cache(self) -> None:
        """Update the cache only if needed or if forced during initialization."""
        if self.current_index < self._length:
            cur_wind = self.winds[self.current_index]
            self._last_vector_cache = cur_wind.vector
            self.next_range = cur_wind.until_distance >> Distance.Foot
        else:
            self._last_vector_cache = Vector(0.0, 0.0, 0.0)
            self.next_range = Wind.MAX_DISTANCE_FEET

    def vector_for_range(self, next_range: float) -> Vector:
        """Update the wind vector if `next_range` surpasses `self.next_range`.

        Args:
            next_range: The range to check against the current wind segment.

        Returns:
            The wind vector for the given range.
        """
        if next_range >= self.next_range:
            self.current_index += 1
            if self.current_index >= self._length:
                self._last_vector_cache = Vector(0.0, 0.0, 0.0)
                self.next_range = Wind.MAX_DISTANCE_FEET
            else:
                self.update_cache()  # This will trigger cache updates.
        return self.current_vector()


class _ZeroCalcStatus(Enum):
    DONE = auto()  # Zero angle found, just return it
    CONTINUE = auto()  # Continue searching for zero angle


class ZeroFindingProps(NamedTuple):
    status: _ZeroCalcStatus
    look_angle_rad: float
    slant_range_ft: Optional[float] = None
    target_x_ft: Optional[float] = None
    target_y_ft: Optional[float] = None
    start_height_ft: Optional[float] = None


def with_no_minimum_velocity(method):
    """Decorator to temporarily set minimum velocity to zero."""
    def wrapper(self, *args, **kwargs):
        restore = None
        if getattr(self._config, "cMinimumVelocity", None) != 0:
            restore = self._config.cMinimumVelocity
            self._config.cMinimumVelocity = 0
        try:
            return method(self, *args, **kwargs)
        finally:
            if restore is not None:
                self._config.cMinimumVelocity = restore
    return wrapper

def with_max_drop_zero(method):
    """Decorator to temporarily set maximum drop to zero."""
    def wrapper(self, *args, **kwargs):
        restore = None
        if getattr(self._config, "cMaximumDrop", None) != 0:
            restore = self._config.cMaximumDrop
            self._config.cMaximumDrop = 0
        try:
            return method(self, *args, **kwargs)
        finally:
            if restore is not None:
                self._config.cMaximumDrop = restore
    return wrapper


_BaseEngineConfigDictT = TypeVar("_BaseEngineConfigDictT", bound='BaseEngineConfigDict', covariant=True)


# pylint: disable=too-many-instance-attributes
class BaseIntegrationEngine(ABC, EngineProtocol[_BaseEngineConfigDictT]):
    """All calculations are done in imperial units (feet and fps)."""

    APEX_IS_MAX_RANGE_RADIANS: float = 0.0003  # Radians from vertical where the apex is max range
    ALLOWED_ZERO_ERROR_FEET: float = 1e-2  # Allowed range error (along sight line), in feet, for zero angle
    SEPARATE_ROW_TIME_DELTA: float = 1e-5  # Difference in seconds required for a TrajFlag to generate separate rows

    def __init__(self, _config: _BaseEngineConfigDictT):
        """Initialize the class.

        Args:
            _config: The configuration object.
        """
        self._config: BaseEngineConfig = create_base_engine_config(_config)
        self.gravity_vector: Vector = Vector(.0, self._config.cGravityConstant, .0)

    def get_calc_step(self) -> float:
        """Get step size for integration."""
        return self._config.cStepMultiplier

    def _init_trajectory(self, shot: Shot) -> ShotProps:
        """Convert Shot properties into floats dimensioned in internal units.

        Args:
            shot: Information about the shot.
        """
        props = ShotProps.from_shot(shot)
        props.calc_step = self.get_calc_step()
        return props

    def find_max_range(self, shot_info: Shot, angle_bracket_deg: Tuple[float, float] = (0, 90)) -> Tuple[
        Distance, Angular]:
        """Find the maximum range along shot_info.look_angle, and the launch angle to reach it.

        Args:
            shot_info: The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg: The angle bracket in degrees to search for max range. Defaults to (0, 90).

        Returns:
            The maximum slant-range and the launch angle to reach it.

        Raises:
            ValueError: If the angle bracket excludes the look_angle.
        """
        """
        TODO: Make sure user hasn't restricted angle bracket to exclude the look_angle.
            ... and check for weird situations, like backward-bending trajectories,
            where the max range occurs with launch angle less than the look angle.
        """
        props = self._init_trajectory(shot_info)
        return self._find_max_range(props, angle_bracket_deg)

    @with_max_drop_zero
    @with_no_minimum_velocity
    def _find_max_range(self, props: ShotProps, angle_bracket_deg: Tuple[float, float] = (0, 90)) -> Tuple[
        Distance, Angular]:
        """Find the maximum slant range via golden-section search.

        Args:
            props: The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg: The angle bracket in degrees to search for max range. Defaults to (0, 90).

        Returns:
            The maximum slant range and the launch angle to reach it.

        Raises:
            ValueError: If the angle bracket excludes the look_angle.
        """
        # region Virtually vertical shot
        if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            max_range = self._find_apex(props).slant_distance
            return max_range, Angular.Radian(props.look_angle_rad)
        # endregion Virtually vertical shot

        t_calls = 0
        def range_for_angle(angle_rad: float) -> float:
            """Return slant-distance minus slant-error (in feet) for given launch angle in radians."""
            props.barrel_elevation_rad = angle_rad
            nonlocal t_calls
            t_calls += 1
            #logger.debug(f"range_for_angle call #{t_calls} for angle {math.degrees(angle_rad)} degrees")
            hit = self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.ZERO_DOWN)
            cross = hit.flag(TrajFlag.ZERO_DOWN)
            if cross is None:
                warnings.warn(f'No ZERO_DOWN found for launch angle {angle_rad} rad.')
                return -9e9
            # Return value penalizes distance by slant height, which we want to be zero.
            return (cross.slant_distance >> Distance.Foot) - abs(cross.slant_height >> Distance.Foot)

        # region Golden-section search
        inv_phi = (math.sqrt(5) - 1) / 2  # 0.618...
        inv_phi_sq = inv_phi ** 2
        a, b = (math.radians(deg) for deg in angle_bracket_deg)
        h = b - a
        c = a + inv_phi_sq * h
        d = a + inv_phi * h
        yc = range_for_angle(c)
        yd = range_for_angle(d)
        for _ in range(self._config.cMaxIterations):
            if h < 1e-6:  # Angle tolerance in radians
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
        # endregion
        max_range_ft = range_for_angle(angle_at_max_rad)

        logger.debug(f"._find_max_range required {t_calls} trajectory calculations")
        return Distance.Feet(max_range_ft), Angular.Radian(angle_at_max_rad)

    def find_apex(self, shot_info: Shot) -> TrajectoryData:
        """Find the apex of the trajectory.

        Apex is defined as the point where the vertical component of velocity goes from positive to negative.

        Args:
            shot_info: The shot information.
        
        Returns:
            TrajectoryData: The trajectory data at the apex of the trajectory.
        
        Raises:
            SolverRuntimeError: If no apex is found in the trajectory data.
            ValueError: If barrel elevation is not > 0.
        """
        props = self._init_trajectory(shot_info)
        return self._find_apex(props)

    @with_no_minimum_velocity
    def _find_apex(self, props: ShotProps) -> TrajectoryData:
        """Find the apex of the trajectory.

        Args:
            props: The shot properties.

        Returns:
            TrajectoryData at the trajectory's apex (where velocity.y goes from positive to negative).            

        Raises:
            SolverRuntimeError: If no apex is found in the trajectory data.
            ValueError: If barrel elevation is not > 0.
        """
        if props.barrel_elevation_rad <= 0:
            raise ValueError("Barrel elevation must be greater than 0 to find apex.")
        hit = self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.APEX)
        apex = hit.flag(TrajFlag.APEX)
        if not apex:
            raise SolverRuntimeError("No apex flagged in trajectory data")
        return apex

    def _init_zero_calculation(self, props: ShotProps, distance: Distance) -> ZeroFindingProps:
        """Initialize the zero calculation for the given shot and distance, handling edge cases.

        Args:
            props: The shot information, with look_angle to the target.
            distance: The slant distance to the target.

        Returns:
            ZeroFindingProps
        """
        slant_range_ft = distance >> Distance.Foot
        target_x_ft = slant_range_ft * math.cos(props.look_angle_rad)
        target_y_ft = slant_range_ft * math.sin(props.look_angle_rad)
        start_height_ft = -props.sight_height_ft * props.cant_cosine

        # region Edge cases
        if abs(slant_range_ft) < self.ALLOWED_ZERO_ERROR_FEET:
            return ZeroFindingProps(_ZeroCalcStatus.DONE, look_angle_rad=props.look_angle_rad)
        if abs(slant_range_ft) < 2.0 * max(abs(start_height_ft), props.calc_step):
            # Very close shot; ignore gravity and drag
            return ZeroFindingProps(_ZeroCalcStatus.DONE,
                                    look_angle_rad=math.atan2(target_y_ft + start_height_ft, target_x_ft))
        if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            # Virtually vertical shot; just check if it can reach the target
            max_range = self._find_apex(props).slant_distance
            if (max_range >> Distance.Foot) < slant_range_ft:
                raise OutOfRangeError(distance, max_range, Angular.Radian(props.look_angle_rad))
            return ZeroFindingProps(_ZeroCalcStatus.DONE, look_angle_rad=props.look_angle_rad)
        # endregion Edge cases

        return ZeroFindingProps(_ZeroCalcStatus.CONTINUE,
                                props.look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)

    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool = False) -> Angular:
        """Find the barrel elevation needed to hit sight line at a specific distance.

        Args:
            shot_info: The shot information.
            distance: Slant distance to the target.
            lofted: If True, find the higher angle that hits the zero point.

        Returns:
            Barrel elevation needed to hit the zero point.
        """
        props = self._init_trajectory(shot_info)
        return self._find_zero_angle(props, distance, lofted)

    @with_no_minimum_velocity
    def _find_zero_angle(self, props: ShotProps, distance: Distance, lofted: bool = False) -> Angular:
        """Find barrel elevation needed to hit sight line at a specific distance.

        This method must use an algorithm that is guaranteed to succeed if a solution exists (e.g., ITP).

        Args:
            props: The shot information.
            distance: The distance to the target.
            lofted: If True, find the higher angle that hits the zero point.

        Returns:
            Barrel elevation needed to hit the zero point.
        """
        status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft = (
            self._init_zero_calculation(props, distance)
        )
        if status is _ZeroCalcStatus.DONE:
            return Angular.Radian(look_angle_rad)

        # Make mypy happy
        assert start_height_ft is not None
        assert target_x_ft is not None
        assert target_y_ft is not None
        assert slant_range_ft is not None

        # 1. Find the maximum possible range to establish a search bracket.
        # TODO: In many scenarios this is unnecessarily expensive: We can confirm that the target is within
        #      range without precisely determining the max range at the look angle, and Newton's method
        #      started at the look-angle would be faster.  However Newton's method fails in rare cases
        #      – see ZeroStudy.ipynb.
        max_range, angle_at_max = self._find_max_range(props)
        max_range_ft = max_range >> Distance.Foot
        angle_at_max_rad = angle_at_max >> Angular.Radian

        # 2. Handle edge cases based on max range.
        if slant_range_ft > max_range_ft:
            raise OutOfRangeError(distance, max_range, Angular.Radian(look_angle_rad))
        if abs(slant_range_ft - max_range_ft) < self.ALLOWED_ZERO_ERROR_FEET:
            return angle_at_max

        def error_at_distance(angle_rad: float) -> float:
            """Target miss (in feet) for given launch angle."""
            props.barrel_elevation_rad = angle_rad
            _res = self._integrate(props, target_x_ft, target_x_ft, filter_flags=TrajFlag.NONE)
            if _res.error is not None:
                logger.warning(f"Integrator error in error_at_distance({angle_rad}): {_res.error}")
            t = _res.trajectory[-1]
            if t.time == 0.0:
                logger.warning("Integrator returned initial point. Consider removing constraints.")
                return 9e9
            return (t.height >> Distance.Foot) - target_y_ft - abs((t.distance >> Distance.Foot) - target_x_ft)

        # 3. Establish search bracket for the zero angle.
        if lofted:
            low_angle, high_angle = angle_at_max_rad, math.radians(89.9)
        else:
            sight_height_adjust = 0.0
            if start_height_ft > 0:
                sight_height_adjust = math.atan2(start_height_ft, target_x_ft)
            low_angle, high_angle = look_angle_rad - sight_height_adjust, angle_at_max_rad

        f_low = error_at_distance(low_angle)
        f_high = error_at_distance(high_angle)

        if f_low * f_high >= 0:
            reason = f"No {'lofted' if lofted else 'low'} zero trajectory in elevation range "
            reason += f"({Angular.Radian(low_angle) >> Angular.Degree:.2f}, "
            reason += f"{Angular.Radian(high_angle) >> Angular.Degree:.2f} deg). "
            reason += f"Errors at bracket: f(low)={f_low:.2f}, f(high)={f_high:.2f}"
            raise ZeroFindingError(target_y_ft, 0, Angular.Radian(props.barrel_elevation_rad), reason=reason)

        # 4. Ridder's method implementation.  Absent bugs, this method is guaranteed to converge in
        #    log₂(range / accuracy) = log₂(π/2 / cZeroFindingAccuracy) iterations.
        # TODO: Consider replacing with ITP method
        for _ in range(self._config.cMaxIterations):
            mid_angle = (low_angle + high_angle) / 2.0
            f_mid = error_at_distance(mid_angle)

            # s is the updated point using the root of the linear function through (low_angle, f_low) and (high_angle, f_high)
            # and the quadratic function that passes through those points and (mid_angle, f_mid)
            s = math.sqrt(f_mid**2.0 - f_low * f_high)
            if s == 0.0:
                break  # Should not happen if f_low and f_high have opposite signs

            next_angle = mid_angle + (mid_angle - low_angle) * (math.copysign(1, f_low - f_high) * f_mid / s)
            if abs(next_angle - mid_angle) < self._config.cZeroFindingAccuracy:
                return Angular.Radian(next_angle)

            f_next = error_at_distance(next_angle)
            # Update the bracket
            if f_mid * f_next < 0:
                low_angle, f_low = mid_angle, f_mid
                high_angle, f_high = next_angle, f_next
            elif f_low * f_next < 0:
                high_angle, f_high = next_angle, f_next
            elif f_high * f_next < 0:
                low_angle, f_low = next_angle, f_next
            else:
                break  # If we are here, something is wrong, the root is not bracketed anymore

            if abs(high_angle - low_angle) < self._config.cZeroFindingAccuracy:
                return Angular.Radian((low_angle + high_angle) / 2)

        raise ZeroFindingError(target_y_ft, self._config.cMaxIterations, Angular.Radian((low_angle + high_angle) / 2),
                               reason="Ridder's method failed to converge."
        )

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """Find the barrel elevation needed to hit sight line at a specific distance.

        First tries iterative approach; if that fails then falls back on `_find_zero_angle`.

        Args:
            shot_info: The shot information.
            distance: The distance to the target.

        Returns:
            Barrel elevation to hit height zero at zero distance along sight line
        """
        props = self._init_trajectory(shot_info)
        try:
            return self._zero_angle(props, distance)
        except ZeroFindingError as e:
            logger.warning(f"Failed to find zero angle using base iterative method: {e}")
            # Fallback to guaranteed method
            return self._find_zero_angle(props, distance)

    def _zero_angle(self, props: ShotProps, distance: Distance) -> Angular:
        """Find barrel elevation needed for a particular zero.

        Args:
            props: Shot parameters
            distance: Sight distance to zero (i.e., along Shot.look_angle), a.k.a. slant range to target.

        Returns:
            Barrel elevation to hit height zero at zero distance along sight line
        """
        status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft = (
            self._init_zero_calculation(props, distance)
        )
        if status is _ZeroCalcStatus.DONE:
            return Angular.Radian(look_angle_rad)

        assert target_x_ft is not None  # Make mypy happy
        assert target_y_ft is not None  # Make mypy happy
        assert slant_range_ft is not None  # Make mypy happy
        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations

        #region Ensure we can see drop at the target distance when launching along slant angle.
        required_drop_ft = target_x_ft / 2.0 - target_y_ft
        restore_cMaximumDrop = None
        if abs(self._config.cMaximumDrop) < required_drop_ft:
            restore_cMaximumDrop = self._config.cMaximumDrop
            self._config.cMaximumDrop = required_drop_ft
        restore_cMinimumAltitude = None
        if (self._config.cMinimumAltitude - props.alt0_ft) > required_drop_ft:
            restore_cMinimumAltitude = self._config.cMinimumAltitude
            self._config.cMinimumAltitude = props.alt0_ft - required_drop_ft
        #endregion

        iterations_count = 0
        range_error_ft = 9e9  # Absolute value of error from target distance along sight line
        prev_range_error_ft = 9e9
        prev_height_error_ft = 9e9
        damping_factor = 1.0  # Start with no damping
        damping_rate = 0.7  # Damping rate for correction
        last_correction = 0.0
        height_error_ft = _cZeroFindingAccuracy * 2  # Absolute value of error from sight line in feet at zero distance

        while iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current props.barrel_elevation)
            t = self._integrate(props, target_x_ft, target_x_ft, filter_flags=TrajFlag.NONE)[-1]
            if t.time == 0.0:
                logger.warning("Integrator returned initial point. Consider removing constraints.")
                break

            current_distance = t.distance >> Distance.Foot  # Horizontal distance
            if 2 * current_distance < target_x_ft and props.barrel_elevation_rad == 0.0 and look_angle_rad < 1.5:
                # Degenerate case: little distance and zero elevation; try with some elevation
                props.barrel_elevation_rad = 0.01
                continue

            height_diff_ft = t.slant_height >> Distance.Foot
            look_dist_ft = t.slant_distance >> Distance.Foot
            range_diff_ft = look_dist_ft - slant_range_ft
            range_error_ft = math.fabs(range_diff_ft)
            height_error_ft = math.fabs(height_diff_ft)
            trajectory_angle = t.angle >> Angular.Radian  # Flight angle at current distance
            sensitivity = math.tan(props.barrel_elevation_rad - look_angle_rad) * math.tan(trajectory_angle - look_angle_rad)
            if sensitivity < -0.5:
                denominator = look_dist_ft
            else:
                denominator = look_dist_ft * (1 + sensitivity)
            if abs(denominator) > 1e-9:
                correction = -height_diff_ft / denominator
            else:
                raise ZeroFindingError(height_error_ft, iterations_count, Angular.Radian(props.barrel_elevation_rad),
                      'Correction denominator is zero')

            if range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # We're still trying to reach zero_distance
                if range_error_ft > prev_range_error_ft - 1e-6:  # We're not getting closer to zero_distance
                    raise ZeroFindingError(range_error_ft, iterations_count, Angular.Radian(props.barrel_elevation_rad),
                          'Distance non-convergent')
            elif height_error_ft > math.fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                damping_factor *= damping_rate  # Apply damping to prevent overcorrection
                if damping_factor < 0.3:
                    raise ZeroFindingError(height_error_ft, iterations_count, Angular.Radian(props.barrel_elevation_rad),
                          'Error non-convergent')
                logger.debug(f'Tightened damping to {damping_factor:.2f} after {iterations_count} iterations')
                props.barrel_elevation_rad -= last_correction  # Revert previous adjustment
                correction = last_correction
            elif damping_factor < 1.0:
                logger.debug('Resetting damping factor to 1.0')
                damping_factor = 1.0

            prev_range_error_ft = range_error_ft
            prev_height_error_ft = height_error_ft

            if height_error_ft > cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # Adjust barrel elevation to close height at zero distance
                applied_correction = correction * damping_factor
                props.barrel_elevation_rad += applied_correction
                last_correction = applied_correction
            else:  # Current barrel_elevation hit zero: success!
                break
            iterations_count += 1

        if restore_cMaximumDrop is not None:
            self._config.cMaximumDrop = restore_cMaximumDrop
        if restore_cMinimumAltitude is not None:
            self._config.cMinimumAltitude = restore_cMinimumAltitude

        result: Angular = Angular.Radian(props.barrel_elevation_rad)
        if height_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(height_error_ft, iterations_count, result)
        return result

    def integrate(self, shot_info: Shot,
                        max_range: Distance,
                        dist_step: Optional[Distance] = None,
                        time_step: float = 0.0,
                        filter_flags: Union[TrajFlag, int] = TrajFlag.NONE,
                        dense_output: bool = False,
                        **kwargs) -> HitResult:
        """Compute the trajectory for the given shot.

        Args:
            shot_info: The shot information.
            max_range: Maximum range of the trajectory (if float then treated as feet).
            dist_step: Distance step for recording RANGE TrajectoryData rows.
            time_step: Time step for recording trajectory data. Defaults to 0.0.
            filter_flags: Flags to filter trajectory data. Defaults to TrajFlag.RANGE.
            dense_output: If True, HitResult will save BaseTrajData for interpolating TrajectoryData.

        Returns:
            HitResult object for describing the trajectory.
        """
        props = self._init_trajectory(shot_info)
        props.filter_flags = filter_flags
        range_limit_ft = max_range >> Distance.Foot
        if dist_step is None:
            range_step_ft = range_limit_ft
        else:
            range_step_ft = dist_step >> Distance.Foot
        return self._integrate(props, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output, **kwargs)

    @abstractmethod
    def _integrate(self, props: ShotProps, range_limit_ft: float, range_step_ft: float,
                   time_step: float = 0.0, filter_flags: Union[TrajFlag, int] = TrajFlag.NONE,
                   dense_output: bool = False, **kwargs) -> HitResult:
        """Create HitResult for the specified shot.

        Args:
            props: Information specific to the shot.
            range_limit_ft: Feet down-range to stop calculation.
            range_step_ft: Frequency (in feet down-range) to record TrajectoryData.
            filter_flags: Bitfield for trajectory points of interest to record.
            time_step: If > 0 then record TrajectoryData after this many seconds elapse
                since last record, as could happen when trajectory is nearly vertical and there is too little
                movement down-range to trigger a record based on range.  (Defaults to 0.0)
            dense_output: If True, HitResult will save BaseTrajData at each integration step,
                for interpolating TrajectoryData.  Defaults to False.

        Returns:
            HitResult object describing the trajectory.
        """
        ...
