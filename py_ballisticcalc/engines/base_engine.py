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

import contextlib
import functools
import math
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import Any, Concatenate, NamedTuple, NoReturn, ParamSpec, TypedDict, TypeVar

from py_ballisticcalc.conditions import Wind
from py_ballisticcalc.constants import cGravityImperial
from py_ballisticcalc.exceptions import InterceptionError, OutOfRangeError, SolverRuntimeError, ZeroFindingError
from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.logger import logger
from py_ballisticcalc.shot import Shot, ShotProps, _exact_direction
from py_ballisticcalc.trajectory_data import BaseTrajData, HitResult, TrajectoryData, TrajectoryStep, TrajFlag
from py_ballisticcalc.unit import Angular, Distance
from py_ballisticcalc.vector import Vector

__all__ = (
    "DEFAULT_BASE_ENGINE_CONFIG",
    "RAW_KEY_GETTERS",
    "BaseEngineConfig",
    "BaseEngineConfigDict",
    "BaseIntegrationEngine",
    "TrajectoryDataFilter",
    "_WindSock",
    "_ZeroCalcStatus",
    "create_base_engine_config",
    "with_max_drop_zero",
    "with_no_minimum_velocity",
)

cZeroFindingAccuracy: float = 0.000005  # Max allowed slant-error in feet to end zero search
cMaxIterations: int = 40  # maximum number of iterations for zero search
cMinimumAltitude: float = -1500  # feet, below sea level
cMaximumDrop: float = -10000  # feet, maximum drop from the muzzle to continue trajectory
cMinimumVelocity: float = 50.0  # fps, minimum velocity to continue trajectory
cGravityConstant: float = -cGravityImperial  # feet per second squared
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
        cGravityConstant: Gravitational acceleration in ft/s², along the vertical axis (y up), so it MUST be
                         a finite NEGATIVE number (gravity pulls down). Zero, positive, NaN and infinite values
                         raise ValueError, when the config is created and whenever the field is assigned later.
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

    def __setattr__(self, name: str, value: Any) -> None:
        # Validates on construction and on every later assignment (the engines read the config at each call).
        if name == "cGravityConstant":
            try:
                valid = math.isfinite(value) and value < 0
            except TypeError:
                valid = False
            if not valid:
                raise ValueError(
                    f"cGravityConstant must be a finite negative number (ft/s^2, gravity pulls down along -y; "
                    f"default {cGravityConstant}), got {value!r}"
                )
        super().__setattr__(name, value)


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
        - cGravityConstant: Gravitational acceleration in ft/s²; must be finite and negative (ValueError otherwise).
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

    cZeroFindingAccuracy: float
    cMaxIterations: int
    cMinimumAltitude: float
    cMaximumDrop: float
    cMinimumVelocity: float
    cGravityConstant: float
    cStepMultiplier: float


def create_base_engine_config(interface_config: BaseEngineConfigDict | None = None) -> BaseEngineConfig:
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
    """Emit requested rows and events from accepted trajectory intervals.

    Integrators call :meth:`record_initial` once followed by
    :meth:`record_step` for every accepted interval.  Every query is evaluated
    from the interval's endpoint Hermite model.  Rows are intentionally not
    merged by a time tolerance: a scheduled sample and a physical event are
    distinct observations unless the caller explicitly gives them the same
    state and flags.
    """

    EPSILON = 1e-6  # Range difference (in feet) significant enough to justify interpolation for data
    records: list[TrajectoryData]
    props: ShotProps
    filter: TrajFlag | int
    time_of_last_record: float
    time_step: float
    range_step: float
    range_limit: float
    prev_data: BaseTrajData | None
    next_record_distance: float
    look_angle_tangent: float

    def __init__(
        self,
        props: ShotProps,
        filter_flags: TrajFlag | int,
        range_limit: float = 0.0,
        range_step: float = 0.0,
        time_step: float = 0.0,
    ):
        """If a time_step > 0, then we will record a row at least that often in the trajectory."""
        self.records = []
        self.props = props
        self.filter = filter_flags
        self.time_step = time_step
        self.range_step = range_step
        self.range_limit = range_limit
        self.time_of_last_record = 0.0
        self.next_record_distance = 0.0
        self.prev_data = None
        self.look_angle_tangent = math.tan(props.look_angle_rad)

    def init(self, data: BaseTrajData):
        if self.filter & TrajFlag.MACH:
            mach = self.props.get_density_and_mach_for_altitude(data.position.y)[1]
            if data.velocity.magnitude() < mach:
                # If we start below Mach 1, we won't look for Mach crossings
                self.filter &= ~TrajFlag.MACH
        if self.filter & TrajFlag.ZERO:
            if data.position.y >= 0:
                # If shot starts above zero then we will only look for a ZERO_DOWN crossing through the line of sight.
                self.filter &= ~TrajFlag.ZERO_UP
            elif data.position.y < 0 and self.props.barrel_elevation_rad <= self.props.look_angle_rad:
                # If shot starts below zero and barrel points below line of sight we won't look for any crossings.
                self.filter &= ~(TrajFlag.ZERO | TrajFlag.MRT)

    def _append(self, data: BaseTrajData, flag: TrajFlag | int) -> None:
        self.records.append(TrajectoryData.from_base_data(self.props, data, flag))

    def record_initial(self, data: BaseTrajData) -> None:
        """Record the launch state before any accepted interval exists."""
        if self.prev_data is not None:
            raise RuntimeError("TrajectoryDataFilter was initialized twice")
        self.init(data)
        self._append(data, TrajFlag.RANGE if (self.range_step > 0 or self.time_step > 0) else TrajFlag.NONE)
        self.prev_data = data

    def finalize(self, termination_reason: str | None = None):
        if (
            termination_reason
            and self.prev_data is not None
            and (not self.records or self.prev_data.time != self.records[-1].time)
        ):
            self.records.append(
                TrajectoryData.from_props(
                    self.props,
                    self.prev_data.time,
                    self.prev_data.position,
                    self.prev_data.velocity,
                    self.prev_data.mach,
                    TrajFlag.NONE,
                )
            )

    def record_step(self, start: BaseTrajData, end: BaseTrajData) -> None:
        """Emit all scheduled samples and one-shot events between *start* and *end*."""
        if self.prev_data is None:
            self.record_initial(start)
        elif start != self.prev_data:
            raise ValueError("Trajectory steps must be contiguous")

        step = TrajectoryStep(start, end)
        rows: list[tuple[BaseTrajData, TrajFlag | int]] = []

        def add(data: BaseTrajData, flag: TrajFlag | int) -> None:
            rows.append((data, flag))

        def emit_time_rows(until: float, exclusive: bool) -> None:
            """Emit the time rows due up to *until* (strictly before it when *exclusive*) on the current clock."""
            if self.time_step <= 0:
                return
            while self.time_of_last_record + self.time_step <= until:
                record_time = self.time_of_last_record + self.time_step
                if exclusive and not record_time < until:
                    break
                self.time_of_last_record = record_time
                if record_time >= start.time:
                    add(step.at_time(record_time), TrajFlag.RANGE)

        if self.range_step > 0:
            while self.next_record_distance + self.range_step <= end.position.x:
                distance = self.next_record_distance + self.range_step
                if distance > self.range_limit + self.EPSILON:
                    self.range_step = -1
                    break
                if distance >= start.position.x - self.EPSILON:
                    sample = step.at_x(distance)
                    # RANGE restarts the time schedule from its own time, so the time rows due strictly before
                    # it are emitted first (a wide step may hold both); same order as bclibc's emit_time_rows.
                    emit_time_rows(sample.time, True)
                    add(sample, TrajFlag.RANGE)
                    # RANGE and TIME samples share one "last record" clock:
                    # a time schedule starts from the most recently emitted
                    # RANGE row, matching the long-standing filter contract.
                    self.time_of_last_record = sample.time
                self.next_record_distance = distance

        emit_time_rows(end.time, False)

        if self.filter & TrajFlag.APEX and start.velocity.y > 0.0 >= end.velocity.y:
            add(step.at_value(lambda data: data.velocity.y, 0.0), TrajFlag.APEX)
            self.filter &= ~TrajFlag.APEX

        mach_ratio = lambda data: data.velocity.magnitude() / data.mach
        if self.filter & TrajFlag.MACH and mach_ratio(start) > 1.0 > mach_ratio(end):
            add(step.at_value(mach_ratio, 1.0), TrajFlag.MACH)
            self.filter &= ~TrajFlag.MACH

        sight_height = lambda data: data.position.y - data.position.x * self.look_angle_tangent
        if self.filter & TrajFlag.ZERO_UP and sight_height(start) < 0.0 < sight_height(end):
            add(step.at_value(sight_height, 0.0), TrajFlag.ZERO_UP)
            self.filter &= ~TrajFlag.ZERO_UP
        elif self.filter & TrajFlag.ZERO_DOWN and sight_height(start) > 0.0 > sight_height(end):
            add(step.at_value(sight_height, 0.0), TrajFlag.ZERO_DOWN)
            self.filter &= ~TrajFlag.ZERO_DOWN

        for data, flag in sorted(rows, key=lambda row: row[0].time):
            self._append(data, flag)
        self.prev_data = end

    def record(self, data: BaseTrajData) -> None:
        """Compatibility adapter for callers that still provide endpoints."""
        if self.prev_data is None:
            self.record_initial(data)
        else:
            self.record_step(self.prev_data, data)


#: Keys of `BaseIntegrationEngine.integrate_raw_at` (the spelling of the Cython engines): the raw `BaseTrajData` field they read.
#: Raw units: seconds, feet, feet per second; `mach` is the local speed of sound (fps), as in `BaseTrajData`.
RAW_KEY_GETTERS: dict[str, Callable[[BaseTrajData], float]] = {
    "time": lambda d: d.time,
    "mach": lambda d: d.mach,
    "position.x": lambda d: d.position.x,
    "position.y": lambda d: d.position.y,
    "position.z": lambda d: d.position.z,
    "velocity.x": lambda d: d.velocity.x,
    "velocity.y": lambda d: d.velocity.y,
    "velocity.z": lambda d: d.velocity.z,
}


def _with_key_value(data: BaseTrajData, key_attribute: str, value: float) -> BaseTrajData:
    """`data` with the key field set to exactly `value` (the root solve only converges the time)."""
    if key_attribute == "time":
        return data._replace(time=value)
    if key_attribute == "mach":
        return data._replace(mach=value)
    top, component = key_attribute.split(".")
    return data._replace(**{top: getattr(data, top)._replace(**{component: value})})


class _SinglePointFound(Exception):
    """Raised by `_SinglePointFilter` from inside an integrator's step loop to end it at the requested point."""

    def __init__(self, data: BaseTrajData):
        super().__init__("target point found")
        self.data = data


class _SinglePointFilter(TrajectoryDataFilter):
    """Stands in for the `TrajectoryDataFilter` of an integration to find ONE point: the first step that brackets a key value.

    The integrators hand every accepted step to `record_step`; this filter ends the integration by raising
    `_SinglePointFound` (carrying the point) as soon as a step's end values bracket the target (ends included), so the
    integrators' loops carry no extra work.  The point is located on the cubic Hermite of that step
    (`TrajectoryStep`, the convention of the filter rows and `HitResult.get_at`); only a step that cannot be interpolated
    (not increasing in time) falls back to the 3-point PCHIP over the step and the one before it.
    This mirrors bclibc's `BCLIBC_SinglePointHandler::handle_step`.  `prev_data` is the last accepted point.
    """

    def __init__(self, *args: Any, key_attribute: str, target_value: float, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.key_attribute = key_attribute
        self.target_value = target_value
        self._get = RAW_KEY_GETTERS[key_attribute]
        self._before: BaseTrajData | None = None

    def record_initial(self, data: BaseTrajData) -> None:
        """Remember the launch state; no row is recorded."""
        self.prev_data = data

    def record_step(self, start: BaseTrajData, end: BaseTrajData) -> None:
        get, target = self._get, self.target_value
        k0, k1 = get(start), get(end)
        if (k0 <= target <= k1) or (k1 <= target <= k0):
            raise _SinglePointFound(self._locate(start, end))
        self._before = start
        self.prev_data = end

    def _locate(self, start: BaseTrajData, end: BaseTrajData) -> BaseTrajData:
        key, target = self.key_attribute, self.target_value
        try:
            step = TrajectoryStep(start, end)
        except ValueError:  # degenerate step
            if self._before is not None:
                try:
                    return BaseTrajData.interpolate(key, target, self._before, start, end)  # type: ignore[arg-type]
                except ZeroDivisionError:
                    pass
            return end
        data = step.at_time(target) if key == "time" else step.at_value(self._get, target)
        return _with_key_value(data, key, target)


class _WindSock:
    """Winds in effect down range.

    Currently this class assumes that requests for wind readings will only be made in order of increasing range.
    This assumption is violated if the projectile is blown or otherwise moves backwards.
    """

    winds: Sequence[Wind]
    current_index: int
    next_range: float

    def __init__(self, winds: Sequence[Wind]):
        """Initialize the _WindSock class.

        Args:
            winds: A sequence of Wind objects. Defaults to None.
        """
        self.winds: Sequence[Wind] = winds or ()
        self.current_index: int = 0
        self.next_range: float = Wind.MAX_DISTANCE_FEET
        self._last_vector_cache: Vector | None = None
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
    slant_range_ft: float | None = None
    target_x_ft: float | None = None
    target_y_ft: float | None = None
    start_height_ft: float | None = None


_P = ParamSpec("_P")
_R = TypeVar("_R")


_Self = TypeVar("_Self", bound="BaseIntegrationEngine")


def with_no_minimum_velocity(
    method: Callable[Concatenate[_Self, _P], _R],
) -> Callable[Concatenate[_Self, _P], _R]:
    """Decorator to temporarily set minimum velocity to zero."""

    @functools.wraps(method)
    def wrapper(self: _Self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        restore = None
        if self._config.cMinimumVelocity != 0:
            restore = self._config.cMinimumVelocity
            self._config.cMinimumVelocity = 0
        try:
            return method(self, *args, **kwargs)
        finally:
            if restore is not None:
                self._config.cMinimumVelocity = restore

    return wrapper


def with_max_drop_zero(
    method: Callable[Concatenate[_Self, _P], _R],
) -> Callable[Concatenate[_Self, _P], _R]:
    """Decorator to temporarily set maximum drop to zero."""

    @functools.wraps(method)
    def wrapper(self: _Self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        restore = None
        if self._config.cMaximumDrop != 0:
            restore = self._config.cMaximumDrop
            self._config.cMaximumDrop = 0
        try:
            return method(self, *args, **kwargs)
        finally:
            if restore is not None:
                self._config.cMaximumDrop = restore

    return wrapper


_DOWNHILL_LAST_DROP_FT = 1e6
"""Drop below the muzzle (feet) down to which `_first_zero_down` follows a downhill shot."""
_DOWNHILL_MAX_FLIGHT_TIME_S = 600.0
"""Longest flight (s) `_first_zero_down` follows a downhill shot in search of its crossing of the line of sight (as in
bclibc).  Realistic flights are under ~400 s; a probe that exceeds it reports "no crossing" instead of being integrated
until the (lifted) drop limit, which for a steep line of sight takes minutes."""


# pylint: disable=too-many-instance-attributes
class BaseIntegrationEngine(ABC, EngineProtocol):
    """All calculations are done in imperial units (feet and fps)."""

    APEX_IS_MAX_RANGE_RADIANS: float = 0.0003  # Radians from vertical where the apex is max range
    ALLOWED_ZERO_ERROR_FEET: float = 1e-2  # Allowed range error (along sight line), in feet, for zero angle

    def __init__(self, config: BaseEngineConfigDict | None) -> None:
        """Initialize the class.

        Args:
            config: The configuration object.
        """
        self._config: BaseEngineConfig = create_base_engine_config(config)
        self.gravity_vector: Vector = Vector(0.0, self._config.cGravityConstant, 0.0)

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

    def find_max_range(
        self, shot_info: Shot, angle_bracket_deg: tuple[float, float] = (0, 90)
    ) -> tuple[Distance, Angular]:
        """Find the maximum range along shot_info.look_angle, and the launch angle to reach it.

        Args:
            shot_info: The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg: The angle bracket in degrees to search for max range. Defaults to (0, 90).

        Returns:
            The maximum slant-range and the launch angle to reach it.
            If no launch angle of the bracket crosses the line of sight (e.g., the bracket lies below the look angle,
            it is degenerate, or the shot starts below `cMinimumAltitude`), the range is 0 ft and the angle is
            meaningless.  `find_zero_angle` / `find_zero_point` then raise `OutOfRangeError` with a max_range of 0 ft.

        Note:
            Does not check for weird situations, like backward-bending trajectories,
            where the max range occurs with launch angle less than the look angle.
        """
        props = self._init_trajectory(shot_info)
        return self._find_max_range(props, angle_bracket_deg)

    @with_max_drop_zero
    @with_no_minimum_velocity
    def _find_max_range(
        self, props: ShotProps, angle_bracket_deg: tuple[float, float] = (0, 90)
    ) -> tuple[Distance, Angular]:
        """Find the maximum slant range via golden-section search.

        Args:
            props: The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg: The angle bracket in degrees to search for max range. Defaults to (0, 90).

        Returns:
            The maximum slant range and the launch angle to reach it.
            0 ft if no launch angle of the bracket crosses the line of sight (the angle is then meaningless).
        """
        # region Virtually vertical shot
        if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            max_range = self._find_apex(props).slant_distance
            return max_range, Angular.Radian(props.look_angle_rad)
        # endregion Virtually vertical shot

        t_calls = 0

        def range_for_angle(angle_rad: float) -> float:
            """Return slant-distance minus slant-error (in feet) for given launch angle in radians."""
            props.set_aim(angle_rad)
            nonlocal t_calls
            t_calls += 1
            # logger.debug(f"range_for_angle call #{t_calls} for angle {math.degrees(angle_rad)} degrees")
            cross = self._first_zero_down(props)
            if cross is None:
                warnings.warn(f"No ZERO_DOWN found for launch angle {angle_rad} rad.")
                return 0.0  # No crossing counts as zero range (as in bclibc), not an internal sentinel.
            # Return value penalizes distance by slant height, which we want to be zero.
            return (cross.slant_distance >> Distance.Foot) - abs(cross.slant_height >> Distance.Foot)

        # region Golden-section search
        inv_phi = (math.sqrt(5) - 1) / 2  # 0.618...
        inv_phi_sq = inv_phi**2
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

    @contextlib.contextmanager
    def _zero_search_limits(self, props: ShotProps, target_x_ft: float, target_y_ft: float) -> Iterator[None]:
        """Widen the drop and altitude limits, for the duration of a shot, to what is needed to follow it to the target.

        A zero search fires shots that fall well below the muzzle before they reach the target (the flat edge of a bracket,
        the first Newton guess); a tight `cMaximumDrop` or `cMinimumAltitude` ends them short.  The limits are only widened,
        never narrowed, and restored on exit (same as `zero_search_*` in bclibc).
        """
        required_drop_ft = target_x_ft / 2.0 - target_y_ft
        restore_drop, restore_altitude = self._config.cMaximumDrop, self._config.cMinimumAltitude
        if abs(restore_drop) < required_drop_ft:
            self._config.cMaximumDrop = required_drop_ft
        if (props.alt0_ft - restore_altitude) < required_drop_ft:
            self._config.cMinimumAltitude = props.alt0_ft - required_drop_ft
        try:
            yield
        finally:
            self._config.cMaximumDrop, self._config.cMinimumAltitude = restore_drop, restore_altitude

    def _first_zero_down(self, props: ShotProps, **integrate_kwargs: Any) -> TrajectoryData | None:
        """Return the point where the shot comes back down through the line of sight, or None if it never does.

        Used by the maximum-range search, which runs with `cMaximumDrop` 0 ("stop at muzzle level"): a shot is stopped
        when it falls below the muzzle, which is right for a level or uphill line of sight, as the shot crosses it above
        the muzzle.  A downhill line of sight lies *below* the muzzle: every shot was stopped before it got there, and the
        search found no crossing at any elevation but a near-vertical one.  For a downhill look angle the shot is
        integrated with the drop (and minimum altitude) limit lifted to `_DOWNHILL_LAST_DROP_FT`, bounded to
        `_DOWNHILL_MAX_FLIGHT_TIME_S` of flight, and stopped at the crossing.  The first crossing does not depend on the
        limit, so a level or uphill look angle is untouched and so are all results that did not hit the limit.

        Args:
            props: The shot, with its barrel elevation set.
            **integrate_kwargs: Passed on to `_integrate` (the SciPy engine asks it to stop at the crossing).
        """
        # The flight after the first crossing cannot change it: the integrators stop there (the SciPy engine is asked by its caller).
        integrate_kwargs.setdefault("stop_at_zero_down", True)
        if props.look_angle_rad < 0.0:
            # The limits are lifted below, so a flight time bound ends a shot that never crosses (the integrators stop at
            # `max_flight_time_s` without an error; the SciPy engine has its own, shorter, `max_time`).
            integrate_kwargs.setdefault("max_flight_time_s", _DOWNHILL_MAX_FLIGHT_TIME_S)
            # A shot that cannot rise above the line of sight never crosses it: the highest it gets above the line, in
            # vacuum (drag only lowers it), is its start height over the line plus (v sin(elevation - look))^2 / (2 g cos(look)).
            # (Without this a shot launched at or below the line would be integrated until the drop limit; wind is ignored.)
            v_perp = props.muzzle_velocity_fps * math.sin(props.barrel_elevation_rad - props.look_angle_rad)
            height = -props.cant_cosine * props.sight_height_ft * math.cos(props.look_angle_rad)
            g = abs(self._config.cGravityConstant)
            if v_perp > 0.0 and g > 0.0:
                height += v_perp * v_perp / (2.0 * g * math.cos(props.look_angle_rad))
            if height <= 0.0:
                return None
        if props.look_angle_rad >= 0.0:
            return self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.ZERO_DOWN, **integrate_kwargs).flag(
                TrajFlag.ZERO_DOWN
            )
        # Downhill: integrate once with the drop and minimum-altitude limits lifted.  The flight stops at the crossing, so
        # a shot that crosses costs no more than it needs, and the flight time bound ends one that never does.
        restore_drop, restore_altitude = self._config.cMaximumDrop, self._config.cMinimumAltitude
        try:
            self._config.cMaximumDrop = _DOWNHILL_LAST_DROP_FT
            self._config.cMinimumAltitude = min(restore_altitude, props.alt0_ft - _DOWNHILL_LAST_DROP_FT)
            return self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.ZERO_DOWN, **integrate_kwargs).flag(
                TrajFlag.ZERO_DOWN
            )
        finally:
            self._config.cMaximumDrop, self._config.cMinimumAltitude = restore_drop, restore_altitude

    def integrate_raw_at(
        self, shot_info: Shot, key_attribute: str, target_value: float
    ) -> tuple[BaseTrajData, TrajectoryData]:
        """Integrate the trajectory until a key attribute reaches a target value; return the point where it does.

        Same API as `integrate_raw_at` of the cythonized engines (which wrap bclibc's `integrate_at`).  The shot is
        integrated up to the first accepted step whose end values bracket the target (ends included), then the crossing
        is located on the cubic Hermite interpolant of that step (end positions with the end velocities as slopes; velocity
        is its derivative, `mach` is linear), the convention of the filter rows and `HitResult.get_at`.  A crossing inside
        the first step is found, and a target equal to the launch value (time 0, `position.x` 0) returns the launch state.
        The first crossing is the first step that brackets, so for a key that is not monotone (`position.y`, `velocity.y`,
        `position.z`, ...) it is the first one in flight, e.g. the rising crossing of a height.

        Args:
            shot_info: The shot information.
            key_attribute: The raw field to track: 'time', 'mach', 'position.x', 'position.y', 'position.z',
                'velocity.x', 'velocity.y' or 'velocity.z'.  Raw units (seconds, feet, feet per second): `mach` is the
                speed of sound at the point (fps), as in `BaseTrajData`, not a Mach number.
            target_value: The value the key must reach.

        Returns:
            The interpolated raw point and the same point as `TrajectoryData`.

        Raises:
            InterceptionError: If the integration ends (range, minimum velocity, maximum drop or altitude) before the key
                reaches the value.  `last_data` is the last integrated point as `(BaseTrajData, TrajectoryData)`.
            AttributeError: If `key_attribute` is not one of the keys above.
        """
        if key_attribute not in RAW_KEY_GETTERS:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")
        props = self._init_trajectory(shot_info)
        filters: list[_SinglePointFilter] = []

        def make_filter(*args: Any, **kwargs: Any) -> _SinglePointFilter:
            filters.append(_SinglePointFilter(*args, key_attribute=key_attribute, target_value=target_value, **kwargs))
            return filters[-1]

        try:
            self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.NONE, filter_factory=make_filter)
        except _SinglePointFound as found:
            return found.data, TrajectoryData.from_base_data(props, found.data)
        if not filters:
            raise NotImplementedError(f"{type(self).__name__}._integrate does not support the 'filter_factory' hook")
        return self._raise_not_intercepted(props, filters[0].prev_data)

    @staticmethod
    def _raise_not_intercepted(props: ShotProps, last: BaseTrajData | None) -> NoReturn:
        """Raise the `InterceptionError` of a target that was not reached, carrying the last integrated point."""
        if last is None:
            raise SolverRuntimeError("Integration produced no trajectory data")
        raise InterceptionError(
            "Intercept point not found for target key and value", (last, TrajectoryData.from_base_data(props, last))
        )

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
            # Very close shot; ignore gravity and drag.
            # `start_height_ft` is the (negative) height of the bore relative to the line of sight, so the straight
            # line from the bore to the target on the line of sight rises by `target_y_ft - start_height_ft`.
            # (Adding it, as this once did, points the bore away from the line of sight for a sight above the bore
            # and misses the line of sight by twice the sight height.)
            if props.cant_sine != 0.0:
                # With a cant the bore is also offset sideways by `sight height * sin(cant)`, so the straight line to
                # the target is not in the vertical plane.  The shot of the exact canted frame (see `Shot`) that
                # crosses the line of sight at the target is pitched in its sight plane by
                # `r = atan2(h cos L, D + h cos(cant) sin L)` (h the sight height, D the slant distance, L the look
                # angle); the angle returned is the elevation of that barrel.  (Without a cant this is the
                # `atan2` below.)  A very high sight on a steep cant can need a pitch whose elevation cannot be aimed back
                # (`Shot.barrel_elevation` setter): the call still answers with that elevation.
                h_ft = props.sight_height_ft
                pitch = math.atan2(
                    h_ft * math.cos(props.look_angle_rad),
                    slant_range_ft + h_ft * props.cant_cosine * math.sin(props.look_angle_rad),
                )
                elevation, _ = _exact_direction(props.look_angle_rad, props.cant_cosine, props.cant_sine, pitch)
                return ZeroFindingProps(_ZeroCalcStatus.DONE, look_angle_rad=elevation)
            return ZeroFindingProps(
                _ZeroCalcStatus.DONE, look_angle_rad=math.atan2(target_y_ft - start_height_ft, target_x_ft)
            )
        if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            # Virtually vertical shot; just check if it can reach the target
            max_range = self._find_apex(props).slant_distance
            if (max_range >> Distance.Foot) < slant_range_ft:
                raise OutOfRangeError(distance, max_range, Angular.Radian(props.look_angle_rad))
            return ZeroFindingProps(_ZeroCalcStatus.DONE, look_angle_rad=props.look_angle_rad)
        # endregion Edge cases

        return ZeroFindingProps(
            _ZeroCalcStatus.CONTINUE, props.look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft
        )

    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool = False) -> Angular:
        """Find the barrel elevation needed to hit sight line at a specific distance.

        Args:
            shot_info: The shot information.
            distance: Slant distance to the target.
            lofted: If True, find the higher angle that hits the zero point.


        Note:
            - A zero distance shorter than 0.01 ft (`ALLOWED_ZERO_ERROR_FEET`; the threshold is in feet whatever the
              units of `distance`) is not aimed: the look angle is returned, which misses the line of sight by the
              sight height, because the zero cannot be measured that close.
            - A target closer than `2 * max(|sight height * cos(cant)|, calc step)` (in feet) is solved geometrically:
              the straight line from the bore to the target on the line of sight, ignoring gravity and drag.
            - A negative distance is not supported (aim backwards with the look angle): it raises `ZeroFindingError`
              (unless it is that close, see above).
            - The miss at the target is not continuous for a lofted shot near the vertical (a shot that falls short and one that
              carries past the target differ by thousands of feet).  If the only sign change the search finds is such a
              jump, not a zero, it raises `ZeroFindingError` ("No continuous ... zero") instead of returning an angle that
              misses: the error at the returned angle is more than 45% (`CONTINUOUS_ROOT_RATIO`) of the smaller of the
              errors at the ends of the search bracket.
            - Cant is part of the shot: the sight height is rotated by it (the bore is `sight height * cos(cant)` below
              the line of sight and `sight height * sin(cant)` beside it).  The unknown of the search is the total
              barrel elevation `E` in the vertical plane; the barrel azimuth follows from it in the exact canted model
              (see `Shot.barrel_elevation`), so the shot fired at the returned elevation hits the line of sight at the
              target in height, for a low and for a lofted zero alike.  The windage at the target is a result (a
              canted barrel points sideways and the shot drifts), never a condition.  To fire a returned elevation `a`
              set `shot.barrel_elevation = a`.  An elevation the canted sight plane cannot reach (`|E| > asin(R)`,
              see `Shot`) cannot be set that way and raises `ValueError`.

        Returns:
            Barrel elevation needed to hit the zero point.
        """
        props = self._init_trajectory(shot_info)
        return self._find_zero_ridder(props, distance, lofted)[0]

    def find_zero_point(
        self, shot_info: Shot, distance: Distance, lofted: bool = False
    ) -> tuple[Angular, TrajectoryData]:
        """Find a zero trajectory and return its solved angle and terminal point.

        Args:
            shot_info: The shot information.
            distance: Slant distance to the target.
            lofted: If True, find the higher trajectory that hits the zero point.


        Note:
            - A zero distance shorter than 0.01 ft (`ALLOWED_ZERO_ERROR_FEET`; the threshold is in feet whatever the
              units of `distance`) is not aimed: the look angle is returned, which misses the line of sight by the
              sight height, because the zero cannot be measured that close.
            - A target closer than `2 * max(|sight height * cos(cant)|, calc step)` (in feet) is solved geometrically:
              the straight line from the bore to the target on the line of sight, ignoring gravity and drag.
            - A negative distance is not supported (aim backwards with the look angle): it raises `ZeroFindingError`
              (unless it is that close, see above).
            - The miss at the target is not continuous for a lofted shot near the vertical (a shot that falls short and one that
              carries past the target differ by thousands of feet).  If the only sign change the search finds is such a
              jump, not a zero, it raises `ZeroFindingError` ("No continuous ... zero") instead of returning an angle that
              misses: the error at the returned angle is more than 45% (`CONTINUOUS_ROOT_RATIO`) of the smaller of the
              errors at the ends of the search bracket.
            - Cant is part of the shot: the sight height is rotated by it (the bore is `sight height * cos(cant)` below
              the line of sight and `sight height * sin(cant)` beside it).  The unknown of the search is the total
              barrel elevation `E` in the vertical plane; the barrel azimuth follows from it in the exact canted model
              (see `Shot.barrel_elevation`), so the shot fired at the returned elevation hits the line of sight at the
              target in height, for a low and for a lofted zero alike.  The windage at the target is a result (a
              canted barrel points sideways and the shot drifts), never a condition.  To fire a returned elevation `a`
              set `shot.barrel_elevation = a`.  An elevation the canted sight plane cannot reach (`|E| > asin(R)`,
              see `Shot`) cannot be set that way and raises `ValueError`.

        Returns:
            The solved barrel elevation and the terminal RANGE point from the
            successful zero-finding iteration.

        Raises:
            SolverRuntimeError: If a zero-angle fast path did not integrate a
                trajectory and therefore has no trajectory point to return.
                This is the case for a distance shorter than 0.01 ft, a close target and a zero at the maximum range.
        """
        props = self._init_trajectory(shot_info)
        angle, point = self._find_zero_ridder(props, distance, lofted)
        if point is None:
            raise SolverRuntimeError("Zero-angle fast path did not evaluate a trajectory point")
        return angle, point

    # A bracketed root that ends on the angle tolerance must leave a miss of at most this fraction of the smaller bracket-end
    # error; a larger miss is a discontinuity of the error function, not a zero (see `_require_continuous_root`).
    # Measured on the zero grid (all pure-Python engines and SciPy): real roots leave at most 0.1 (7e-6 for the Python solvers;
    # SciPy's adaptive integrator makes its error noisy at the 0.1 ft level), jumps at least 2.0; this is their log-midpoint.
    CONTINUOUS_ROOT_RATIO = 0.45

    def _require_continuous_root(
        self,
        root_error_ft: float,
        bracket_errors_ft: tuple[float, float],
        angle_rad: float,
        iterations_count: int,
        lofted: bool,
    ) -> None:
        """Raise `ZeroFindingError` if a bracketed root that did not meet the accuracy is a discontinuity.

        The zero error function is not continuous: a lofted shot near the vertical can fall back short of the target or
        carry past it, and the error jumps (by thousands of feet) between those.  A sign change at such a jump is not a
        zero, but a bisection converges on it all the same.  A real root leaves an error that the angle tolerance makes
        tiny against the errors at the ends of the search bracket (<= 7e-6 of the smaller one on the measured grid for the
        Python solvers, <= 0.1 for the noisier SciPy engine); at a jump it stays of their order (>= 2).  The test is scale free:
        `|f(root)| > CONTINUOUS_ROOT_RATIO * min(|f(low)|, |f(high)|)`.

        Args:
            root_error_ft: The error at the angle the search ended on (feet).
            bracket_errors_ft: The errors at the two ends of the initial search bracket (opposite signs).
            angle_rad: The angle the search ended on.
            iterations_count: Number of iterations done.
            lofted: Whether a lofted zero was searched.

        Raises:
            ZeroFindingError: If the error at the angle is comparable to the bracket-end errors.
        """
        if abs(root_error_ft) <= self.CONTINUOUS_ROOT_RATIO * min(abs(bracket_errors_ft[0]), abs(bracket_errors_ft[1])):
            return
        raise ZeroFindingError(
            abs(root_error_ft),
            iterations_count,
            Angular.Radian(angle_rad),
            reason=f"No continuous {'lofted' if lofted else 'low'} zero: the error at the returned angle "
            f"({math.degrees(angle_rad):.4f} deg), {root_error_ft:.2f} ft, is comparable to the bracket-end errors "
            f"f(low)={bracket_errors_ft[0]:.2f}, f(high)={bracket_errors_ft[1]:.2f} (a discontinuity, not a root)",
        )

    @with_no_minimum_velocity
    def _find_zero_ridder(
        self,
        props: ShotProps,
        distance: Distance,
        lofted: bool = False,
    ) -> tuple[Angular, TrajectoryData | None]:
        """Find barrel elevation needed to hit sight line at a specific distance.

        This method uses Ridder's bracketed root-finding algorithm, which is
        guaranteed to converge when a root is bracketed.

        Args:
            props: The shot information.
            distance: The distance to the target.
            lofted: If True, find the higher angle that hits the zero point.

        Returns:
            The solved barrel elevation and, when the solver evaluated one,
            the corresponding terminal trajectory point.
        """
        status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft = self._init_zero_calculation(
            props, distance
        )
        if status is _ZeroCalcStatus.DONE:
            return Angular.Radian(look_angle_rad), None

        # Make the type checker happy
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
            return angle_at_max, None

        last_point: TrajectoryData | None = None

        def error_at_distance(angle_rad: float) -> float:
            """Target miss (in feet) for given launch angle."""
            nonlocal last_point
            props.set_aim(angle_rad)
            with self._zero_search_limits(props, target_x_ft, target_y_ft):
                _res = self._integrate(props, target_x_ft, target_x_ft, filter_flags=TrajFlag.NONE)
            if _res.error is not None:
                logger.warning(f"Integrator error in error_at_distance({angle_rad}): {_res.error}")
            t = _res.records[-1]
            last_point = t
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
        bracket_errors = (f_low, f_high)  # scale of the error function, for the discontinuity check

        if f_low * f_high >= 0:
            reason = f"No {'lofted' if lofted else 'low'} zero trajectory in elevation range "
            reason += f"({Angular.Radian(low_angle) >> Angular.Degree:.2f}, "
            reason += f"{Angular.Radian(high_angle) >> Angular.Degree:.2f} deg). "
            reason += f"Errors at bracket: f(low)={f_low:.2f}, f(high)={f_high:.2f}"
            raise ZeroFindingError(target_y_ft, 0, Angular.Radian(props.aim_elevation_rad), reason=reason)

        # 4. Ridder's method implementation.
        # cZeroFindingAccuracy is a height tolerance in feet; use a separate
        # constant for angle-bracket convergence so the two are not conflated.
        # (Passing e.g. cZeroFindingAccuracy=0.1 ft would otherwise mean a
        # 0.1 rad = 5.7° angle bracket tolerance and a completely wrong answer.)
        angle_tol = 1e-7  # rad — ~0.000006°, independent of height accuracy
        for iteration in range(self._config.cMaxIterations):
            mid_angle = (low_angle + high_angle) / 2.0
            f_mid = error_at_distance(mid_angle)
            if abs(f_mid) < self._config.cZeroFindingAccuracy:
                assert last_point is not None
                return Angular.Radian(mid_angle), last_point

            # s is the updated point using the root of the linear function through (low_angle, f_low) and (high_angle, f_high)
            # and the quadratic function that passes through those points and (mid_angle, f_mid)
            s = math.sqrt(f_mid**2.0 - f_low * f_high)
            if s == 0.0:
                break  # Should not happen if f_low and f_high have opposite signs

            next_angle = mid_angle + (mid_angle - low_angle) * (math.copysign(1, f_low - f_high) * f_mid / s)
            f_next = error_at_distance(next_angle)
            if abs(f_next) < self._config.cZeroFindingAccuracy:
                assert last_point is not None
                return Angular.Radian(next_angle), last_point

            if abs(next_angle - mid_angle) < angle_tol:
                assert last_point is not None
                self._require_continuous_root(f_next, bracket_errors, next_angle, iteration + 1, lofted)
                return Angular.Radian(next_angle), last_point

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

            if abs(high_angle - low_angle) < angle_tol:
                # ``last_point`` is the already-integrated ``next_angle``
                # candidate.  It avoids a final, redundant shot while keeping
                # the angle and point from the same trajectory evaluation.
                assert last_point is not None
                self._require_continuous_root(f_next, bracket_errors, next_angle, iteration + 1, lofted)
                return Angular.Radian(next_angle), last_point

        raise ZeroFindingError(
            target_y_ft,
            self._config.cMaxIterations,
            Angular.Radian((low_angle + high_angle) / 2),
            reason="Ridder's method failed to converge.",
        )

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """Find the barrel elevation needed to hit sight line at a specific distance.

        First tries the damped Newton solver; if that fails then falls back on
        `_find_zero_ridder`.

        Args:
            shot_info: The shot information.
            distance: The distance to the target.


        Note:
            - A zero distance shorter than 0.01 ft (`ALLOWED_ZERO_ERROR_FEET`; the threshold is in feet whatever the
              units of `distance`) is not aimed: the look angle is returned, which misses the line of sight by the
              sight height, because the zero cannot be measured that close.
            - A target closer than `2 * max(|sight height * cos(cant)|, calc step)` (in feet) is solved geometrically:
              the straight line from the bore to the target on the line of sight, ignoring gravity and drag.
            - A negative distance is not supported (aim backwards with the look angle): it raises `ZeroFindingError`
              (unless it is that close, see above).
            - The miss at the target is not continuous for a lofted shot near the vertical (a shot that falls short and one that
              carries past the target differ by thousands of feet).  If the only sign change the search finds is such a
              jump, not a zero, it raises `ZeroFindingError` ("No continuous ... zero") instead of returning an angle that
              misses: the error at the returned angle is more than 45% (`CONTINUOUS_ROOT_RATIO`) of the smaller of the
              errors at the ends of the search bracket.
            - Cant is part of the shot: the sight height is rotated by it (the bore is `sight height * cos(cant)` below
              the line of sight and `sight height * sin(cant)` beside it).  The unknown of the search is the total
              barrel elevation `E` in the vertical plane; the barrel azimuth follows from it in the exact canted model
              (see `Shot.barrel_elevation`), so the shot fired at the returned elevation hits the line of sight at the
              target in height, for a low and for a lofted zero alike.  The windage at the target is a result (a
              canted barrel points sideways and the shot drifts), never a condition.  To fire a returned elevation `a`
              set `shot.barrel_elevation = a`.  An elevation the canted sight plane cannot reach (`|E| > asin(R)`,
              see `Shot`) cannot be set that way and raises `ValueError`.

        Returns:
            Barrel elevation to hit height zero at zero distance along sight line.
        """
        props = self._init_trajectory(shot_info)
        try:
            return self._find_zero_newton(props, distance)[0]
        except ZeroFindingError as e:
            logger.warning(f"Failed to find zero angle using base iterative method: {e}")
            # Fallback to guaranteed method
            return self._find_zero_ridder(props, distance)[0]

    def zero_point(self, shot_info: Shot, distance: Distance) -> tuple[Angular, TrajectoryData]:
        """Return the zero angle and the trajectory point used to determine it.

        This is the terminal RANGE point from the successful zero-finding
        iteration.  It performs no final re-integration after finding the
        angle, so it is useful to callers that need both the zero geometry and
        its ballistic state.

        Args:
            shot_info: The shot information.
            distance: Slant distance to the zero point.

        Returns:
            A pair of the lower-arc barrel elevation and the trajectory point
            from the successful zero-finding iteration.

        Raises:
            SolverRuntimeError: If a zero-angle fast path did not integrate a
                trajectory and therefore has no trajectory point to return.
        """
        props = self._init_trajectory(shot_info)
        try:
            # Bypass optional-engine overrides while this API is limited to
            # the pure-Python solver path.
            angle, point = BaseIntegrationEngine._find_zero_newton(self, props, distance)
        except ZeroFindingError as error:
            logger.warning(f"Failed to find zero point using base iterative method: {error}")
            angle, point = BaseIntegrationEngine._find_zero_ridder(self, props, distance, False)
        if point is None:
            raise SolverRuntimeError("Zero-angle fast path did not evaluate a trajectory point")
        return angle, point

    def _find_zero_newton(self, props: ShotProps, distance: Distance) -> tuple[Angular, TrajectoryData | None]:
        """Find barrel elevation with the damped Newton-style zero solver.

        Args:
            props: Shot parameters
            distance: Sight distance to zero (i.e., along Shot.look_angle), a.k.a. slant range to target.

        Returns:
            The solved barrel elevation and, when the solver evaluated one,
            the corresponding terminal trajectory point.
        """
        status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, _start_height_ft = (
            self._init_zero_calculation(props, distance)
        )
        if status is _ZeroCalcStatus.DONE:
            return Angular.Radian(look_angle_rad), None

        assert target_x_ft is not None  # Make the type checker happy
        assert target_y_ft is not None  # Make the type checker happy
        assert slant_range_ft is not None  # Make the type checker happy
        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations

        iterations_count = 0
        range_error_ft = 9e9  # Absolute value of error from target distance along sight line
        prev_range_error_ft = 9e9
        prev_height_error_ft = 9e9
        damping_factor = 1.0  # Start with no damping
        damping_rate = 0.7  # Damping rate for correction
        last_correction = 0.0
        height_error_ft = _cZeroFindingAccuracy * 2  # Absolute value of error from sight line in feet at zero distance
        point: TrajectoryData | None = None

        # Ensure we can see drop at the target distance when launching along slant angle.  The limits are restored on every
        # exit of the loop: the raises, and any exception out of an integration, included.
        with self._zero_search_limits(props, target_x_ft, target_y_ft):
            while iterations_count < _cMaxIterations:
                # Check height of trajectory at the zero distance (using current props.barrel_elevation)
                t = self._integrate(props, target_x_ft, target_x_ft, filter_flags=TrajFlag.NONE)[-1]
                point = t
                if t.time == 0.0:
                    logger.warning("Integrator returned initial point. Consider removing constraints.")
                    break

                current_distance = t.distance >> Distance.Foot  # Horizontal distance
                if 2 * current_distance < target_x_ft and props.aim_elevation_rad == 0.0 and look_angle_rad < 1.5:
                    # Degenerate case: little distance and zero elevation; try with some elevation
                    props.set_aim(0.01)
                    continue

                height_diff_ft = t.slant_height >> Distance.Foot
                look_dist_ft = t.slant_distance >> Distance.Foot
                range_diff_ft = look_dist_ft - slant_range_ft
                range_error_ft = math.fabs(range_diff_ft)
                height_error_ft = math.fabs(height_diff_ft)
                trajectory_angle = t.angle >> Angular.Radian  # Flight angle at current distance
                sensitivity = math.tan(props.aim_elevation_rad - look_angle_rad) * math.tan(
                    trajectory_angle - look_angle_rad
                )
                if sensitivity < -0.5:
                    denominator = look_dist_ft
                else:
                    denominator = look_dist_ft * (1 + sensitivity)
                if abs(denominator) > 1e-9:
                    correction = -height_diff_ft / denominator
                else:
                    raise ZeroFindingError(
                        height_error_ft,
                        iterations_count,
                        Angular.Radian(props.aim_elevation_rad),
                        "Correction denominator is zero",
                    )

                if range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                    # We're still trying to reach zero_distance
                    if range_error_ft > prev_range_error_ft - 1e-6:  # We're not getting closer to zero_distance
                        raise ZeroFindingError(
                            range_error_ft,
                            iterations_count,
                            Angular.Radian(props.aim_elevation_rad),
                            "Distance non-convergent",
                        )
                elif height_error_ft > math.fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                    damping_factor *= damping_rate  # Apply damping to prevent overcorrection
                    if damping_factor < 0.3:
                        raise ZeroFindingError(
                            height_error_ft,
                            iterations_count,
                            Angular.Radian(props.aim_elevation_rad),
                            "Error non-convergent",
                        )
                    logger.debug(f"Tightened damping to {damping_factor:.2f} after {iterations_count} iterations")
                    props.set_aim(props.aim_elevation_rad - last_correction)  # Revert previous adjustment
                    correction = last_correction
                elif damping_factor < 1.0:
                    logger.debug("Resetting damping factor to 1.0")
                    damping_factor = 1.0

                prev_range_error_ft = range_error_ft
                prev_height_error_ft = height_error_ft

                if height_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                    # Adjust barrel elevation to close height at zero distance
                    applied_correction = correction * damping_factor
                    props.set_aim(props.aim_elevation_rad + applied_correction)
                    last_correction = applied_correction
                else:  # Current barrel_elevation hit zero: success!
                    break
                iterations_count += 1

        result: Angular = Angular.Radian(props.aim_elevation_rad)
        if height_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(height_error_ft, iterations_count, result)
        assert point is not None
        return result, point

    def integrate(
        self,
        shot_info: Shot,
        max_range: Distance,
        dist_step: Distance | None = None,
        time_step: float = 0.0,
        filter_flags: TrajFlag | int = TrajFlag.NONE,
        dense_output: bool = False,
        **kwargs,
    ) -> HitResult:
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
    def _integrate(
        self,
        props: ShotProps,
        range_limit_ft: float,
        range_step_ft: float,
        time_step: float = 0.0,
        filter_flags: TrajFlag | int = TrajFlag.NONE,
        dense_output: bool = False,
        **kwargs,
    ) -> HitResult:
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
