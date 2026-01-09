"""SciPy-based integration engine for high-performance ballistic trajectory calculations.

This module provides the SciPyIntegrationEngine class, which leverages SciPy's
advanced numerical integration capabilities for computing ballistic trajectories
with exceptional accuracy and adaptive error control. The engine uses SciPy's
solve_ivp function for trajectory integration and associated optimization functions
for zero-finding and maximum range calculations.

Key Features:
    - Adaptive step-size control with multiple integration methods
    - High-precision error tolerance controls (relative and absolute)
    - Event detection for trajectory analysis
    - Support for all standard SciPy integration methods (RK23, RK45, DOP853, etc.)
    - Advanced optimization algorithms for zero-finding and range calculation

Suggested Integration Methods:
    RK23: Explicit Runge-Kutta method of order 3(2) with adaptive step control
    RK45: Explicit Runge-Kutta method of order 5(4) (default, good balance)
    DOP853: Explicit Runge-Kutta method of order 8(5,3) (high precision)
    Radau: Implicit Runge-Kutta method of Radau IIA family (stiff systems)
    BDF: Implicit multi-step method (backward differentiation formula)
    LSODA: Adams/BDF method with automatic stiffness detection

Performance Characteristics:
    - Highest precision among all available engines
    - Adaptive step sizing reduces computational overhead
    - Requires scipy and numpy dependencies

Configuration:
    The engine supports extensive configuration through SciPyEngineConfigDict,
    including integration method selection and tolerance settings.
    All standard BaseEngineConfigDict options are also supported.

Examples:
    >>> from py_ballisticcalc.engines.scipy_engine import SciPyIntegrationEngine
    >>> from py_ballisticcalc.engines.scipy_engine import SciPyEngineConfigDict
    >>>
    >>> # High-precision configuration
    >>> config = SciPyEngineConfigDict(
    ...     integration_method='DOP853',
    ...     relative_tolerance=1e-10,
    ...     absolute_tolerance=1e-12
    ... )
    >>> engine = SciPyIntegrationEngine(config)

    >>> # Using with Calculator
    >>> from py_ballisticcalc import Calculator
    >>> calc = Calculator(engine='scipy_engine')

Note:
    This engine requires scipy and numpy to be installed. Install with:
    `pip install py_ballisticcalc[scipy]` or `pip install scipy numpy`
"""

from __future__ import annotations

# Standard library imports
import math
import warnings
from dataclasses import dataclass, asdict
from bisect import bisect_left, bisect_right
from typing import Any, Callable, Literal, TYPE_CHECKING
from typing_extensions import override
from collections.abc import Sequence

# Third-party imports
try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    from scipy.optimize import root_scalar, minimize_scalar  # type: ignore[import-untyped]
    from scipy.integrate import solve_ivp  # type: ignore[import-untyped]

    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

# Local imports
from py_ballisticcalc.conditions import Wind
from py_ballisticcalc.engines.base_engine import (
    BaseEngineConfig,
    BaseEngineConfigDict,
    BaseIntegrationEngine,
    _ZeroCalcStatus,
    with_no_minimum_velocity,
)
from py_ballisticcalc.exceptions import OutOfRangeError, RangeError, ZeroFindingError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.shot import ShotProps
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag, TrajectoryData
from py_ballisticcalc.unit import Angular, Distance
from py_ballisticcalc.vector import Vector

__all__ = (
    "SciPyIntegrationEngine",
    "SciPyEngineConfig",
    "SciPyEngineConfigDict",
    "ScipyWindSock",
    "DEFAULT_SCIPY_ENGINE_CONFIG",
    "create_scipy_engine_config",
)

# This block would update warning format globally for the lib; use logging.warning instead
# def custom_warning_format(message, category, filename, lineno, file=None, line=None):
#     return f"{category.__name__}: {message}\n"
# warnings.formatwarning = custom_warning_format


# type of event callback
if TYPE_CHECKING:
    SciPyEventFunctionT = Callable[[float, Any], np.floating]
else:
    SciPyEventFunctionT = Callable[[float, Any], Any]


# typed scipy event with expected attributes
@dataclass(frozen=True)
class SciPyEvent:
    """Event object for SciPy solve_ivp integration with trajectory detection.

    This dataclass wraps event functions for use with SciPy's solve_ivp integrator,
    providing a callable interface with terminal and direction control attributes.
    Events are used to detect specific trajectory conditions like zero crossings,
    maximum range, or other significant points during integration.

    The SciPyEvent object implements the callable protocol, making it compatible
    with SciPy's event detection system while maintaining type safety and
    providing clear configuration for event behavior.

    Attributes:
        func: The event function that takes time and state, returns float.
              Zero crossings of this function trigger the event.
        terminal: If True, integration stops when this event occurs.
                 If False, integration continues after detecting the event.
        direction: Controls which zero-crossing directions trigger the event:
                  -1: Function crosses from positive to negative
                   0: Any direction (default)
                   1: Function crosses from negative to positive

    Examples:
        >>> def zero_crossing(t, y):
        ...     return y[1]  # Detect when y-position crosses zero
        >>> event = SciPyEvent(zero_crossing, terminal=True, direction=-1)
        >>> # Event will stop integration when projectile hits ground

    See Also:
        scipy_event: Decorator for creating SciPyEvent objects
        scipy.integrate.solve_ivp: SciPy integration function using events

    Note:
        The callable interface allows SciPyEvent objects to be used directly
        as event functions in SciPy's solve_ivp, while the dataclass structure
        provides clear access to event configuration parameters.
    """

    func: SciPyEventFunctionT
    terminal: bool = False
    direction: Literal[-1, 0, 1] = 0

    def __call__(self, t: float, s: Any) -> np.floating:  # possibly s: np.ndarray
        """Call the wrapped event function with time and state parameters.

        Args:
            t: Current integration time in seconds.
            s: Current state vector (typically position and velocity).

        Returns:
            Function value whose zero crossings trigger the event.
        """
        return self.func(t, s)


def scipy_event(
    terminal: bool = False, direction: Literal[-1, 0, 1] = 0
) -> Callable[[SciPyEventFunctionT], SciPyEvent]:
    """Decorator to create SciPy solve_ivp compatible event objects.

    This decorator transforms a standard event function into a SciPyEvent object
    that is compatible with SciPy's solve_ivp event detection system. The decorator
    configures event behavior including termination conditions and zero-crossing
    direction sensitivity.

    Event functions are used to detect specific conditions during trajectory
    integration, such as when a projectile crosses the sight line, reaches
    maximum altitude, or hits the ground. The solve_ivp integrator monitors
    these functions and can terminate integration or record event occurrences.

    Args:
        terminal: Whether to terminate integration when the event occurs.
                 True: Stop integration immediately when event is detected
                 False: Continue integration, but record the event occurrence
                 Defaults to False.
        direction: Direction of zero-crossing that triggers the event.
                  -1: Function value crosses from positive to negative
                   0: Any direction triggers the event (default)
                   1: Function value crosses from negative to positive
                  This allows selective detection of upward vs downward
                  crossings for more precise trajectory analysis.

    Returns:
        A decorator function that transforms event functions into SciPyEvent objects.
        The returned decorator preserves the original function while adding
        the necessary attributes for SciPy integration.

    Examples:
        >>> @scipy_event(terminal=True, direction=-1)
        ... def ground_impact(t, y):
        ...     '''Detect when projectile hits ground (y=0, falling)'''
        ...     return y[1]  # y-position

    Mathematical Background:
        Event detection in numerical integration monitors functions g(t, y)
        and detects when g(t, y) = 0. The direction parameter controls
        whether to detect:
        - g'(t) < 0 (function decreasing through zero)
        - g'(t) > 0 (function increasing through zero)
        - Both directions

    See Also:
        SciPyEvent: The event object created by this decorator
        scipy.integrate.solve_ivp: SciPy integration with event detection

    Note:
        This decorator follows SciPy's event function protocol while providing
        type safety and clear configuration. The wrapped function must accept
        (time, state) parameters and return a scalar value.
    """

    def wrapper(func: SciPyEventFunctionT) -> SciPyEvent:
        """Wrapper function that creates the SciPyEvent object."""
        return SciPyEvent(func, terminal, direction)

    return wrapper


class ScipyWindSock:
    """Optimized wind vector calculator using binary search for O(log n) lookups.

    This implementation pre-processes wind data during initialization to enable
    fast binary search lookups during trajectory integration. The original
    implementation used linear search which becomes a bottleneck when:
    - Multiple wind zones are defined (>3 zones)
    - Integration requires thousands of wind lookups
    - High-precision methods with many evaluation points are used

    Key optimizations:
    1. Pre-sorted distance thresholds for binary search
    2. Parallel arrays avoid object lookups during integration
    3. Single wind optimization (no search needed)
    4. Distance conversion done once during lookup

    Attributes:
        winds: Original Wind objects (kept for reference)
        _distances: Pre-computed distance thresholds in inches (sorted)
        _vectors: Corresponding wind vectors (parallel array)
        _single_wind: Cached vector for single-wind optimization

    Examples:
        >>> from py_ballisticcalc.conditions import Wind
        >>> from py_ballisticcalc.unit import Distance, Velocity, Angular
        >>>
        >>> # Multiple wind zones
        >>> winds = [
        ...     Wind(velocity=Velocity.MPH(10), direction_from=Angular.Degree(0),
        ...          until_distance=Distance.Yard(100)),
        ...     Wind(velocity=Velocity.MPH(15), direction_from=Angular.Degree(45),
        ...          until_distance=Distance.Yard(300)),
        ...     Wind(velocity=Velocity.MPH(20), direction_from=Angular.Degree(90),
        ...          until_distance=Distance.Yard(600))
        ... ]
        >>> wind_sock = WindSock(winds)
        >>>
        >>> # Fast O(log n) lookup at 250 yards (convert to feet first)
        >>> wind_vector = wind_sock.wind_at_distance(250.0 * 3.0)

    Performance Characteristics:
        - No winds: O(1) - immediate return
        - Single wind: O(1) - cached vector
        - Multiple winds: O(log n) - binary search

    Memory overhead:
        - 2 additional arrays: distances (float) and vectors (Vector refs)
        - Minimal compared to performance gain
    """

    __slots__ = ("winds", "_distances", "_vectors", "_single_wind")

    def __init__(self, winds: Wind | Sequence[Wind | None]) -> None:
        """Initialize WindSock with optimized data structures for fast lookups.

        Args:
            winds: Single Wind object, sequence of Wind objects, or None.
                  If sequence, will be sorted by until_distance automatically.

        Note:
            Wind objects are sorted by range during initialization, so the
            order provided doesn't matter. This ensures binary search correctness.
        """
        self.winds: list[Wind] | None = None
        self._distances: list[float] = []
        self._vectors: list[Vector] = []
        self._single_wind: Vector | None = None

        # Normalize input to list
        if winds is None:
            return
        elif isinstance(winds, Wind):
            self.winds = [winds]
        elif isinstance(winds, (tuple, list)):
            if not winds:  # Empty sequence
                return
            # Sort by distance (ascending) for binary search
            self.winds = sorted(winds, key=lambda w: w.until_distance.raw_value)
        else:
            raise TypeError(f"winds must be Wind, Sequence[Wind], or None, got {type(winds)}")

        # Pre-process for fast lookups
        if self.winds:
            if len(self.winds) == 1:
                # Single wind optimization - no search needed
                self._single_wind = self.winds[0].vector
            else:
                # Build parallel arrays for binary search
                # Store distances in inches (raw_value) to avoid conversion in hot path
                self._distances = [w.until_distance.raw_value for w in self.winds]
                self._vectors = [w.vector for w in self.winds]

    def wind_at_distance(self, distance_ft: float) -> Vector | None:
        """Get wind vector at specified downrange distance (in feet).

        This method is called thousands of times during trajectory integration,
        so it's highly optimized:
        - Early return for no winds
        - Cached return for single wind
        - Binary search for multiple winds

        Args:
            distance_ft: Downrange distance in feet.

        Returns:
            Wind Vector at the specified distance, or None if no winds defined.
            Returns the wind vector from the first zone whose until_distance
            is >= the query distance.

        Algorithm:
            Uses bisect_right to find the insertion point for distance in the
            sorted _distances array. This gives us the index of the first wind
            zone that extends beyond our query distance, which is exactly what
            we need.

        Performance:
            - No winds: O(1) - single comparison
            - Single wind: O(1) - cached lookup
            - N winds: O(log N) - binary search

        Examples:
            >>> # At 150 yards (450 feet)
            >>> wind = wind_sock.wind_at_distance(450.0)
            >>>
            >>> # Binary search finds correct zone automatically
            >>> wind = wind_sock.wind_at_distance(800.0)  # Falls in 300-600 yard zone
        """
        # Fast path: no winds defined
        if not self.winds:
            return None

        # Fast path: single wind zone (most common case)
        if self._single_wind is not None:
            return self._single_wind

        # Convert feet to inches (Wind.until_distance.raw_value is in inches)
        distance_inches = distance_ft * 12.0

        # Binary search: find first zone where distance <= zone.until_distance
        # bisect_right returns index where distance_inches would be inserted
        # to keep list sorted, which gives us the correct wind zone
        idx = bisect_right(self._distances, distance_inches)

        # If idx < len, we found a zone; otherwise use last zone
        if idx < len(self._vectors):
            return self._vectors[idx]

        # Beyond all defined zones - conventionally return None or last wind
        # Original implementation returned None, keeping that behavior
        return None

    def __repr__(self) -> str:
        """String representation for debugging."""
        if not self.winds:
            return "WindSock(no winds)"
        elif self._single_wind is not None:
            return f"WindSock(single wind: {self._single_wind})"
        else:
            return f"WindSock({len(self.winds)} wind zones)"

    def __len__(self) -> int:
        """Return number of wind zones."""
        return len(self.winds) if self.winds else 0


INTEGRATION_METHOD = Literal["RK23", "RK45", "DOP853", "Radau", "BDF", "LSODA"]

DEFAULT_MAX_TIME: float = 90.0  # Max flight time to simulate before stopping integration
DEFAULT_RELATIVE_TOLERANCE: float = 1e-8  # Default relative tolerance (rtol) for integration
DEFAULT_ABSOLUTE_TOLERANCE: float = 1e-6  # Default absolute tolerance (atol) for integration
DEFAULT_INTEGRATION_METHOD: INTEGRATION_METHOD = "RK45"  # Default integration method for solve_ivp


@dataclass
class SciPyEngineConfig(BaseEngineConfig):
    """Configuration dataclass for the SciPy integration engine.

    This configuration class extends BaseEngineConfig with SciPy-specific parameters.

    Attributes:
        max_time: Maximum simulation time in seconds before terminating integration.
                 Prevents infinite integration in pathological cases.
                 Defaults to DEFAULT_MAX_TIME (90.0 seconds).
        relative_tolerance: Relative tolerance for integration error control (rtol).
                           Controls relative accuracy of the solution.
                           Smaller values increase precision but require more computation.
                           Defaults to DEFAULT_RELATIVE_TOLERANCE (1e-8).
        absolute_tolerance: Absolute tolerance for integration error control (atol).
                           Controls absolute accuracy near zero values.
                           Smaller values increase precision for small quantities.
                           Defaults to DEFAULT_ABSOLUTE_TOLERANCE (1e-6).
        integration_method: SciPy integration method for solve_ivp.
                           Recommended methods:
                           - 'RK45': 4th/5th order Runge-Kutta (default, good balance)
                           - 'RK23': 2nd/3rd order Runge-Kutta (faster, less accurate)
                           - 'DOP853': 8th order Runge-Kutta (highest precision)
                           - 'Radau': Implicit method for stiff systems
                           - 'BDF': Backward differentiation for stiff systems
                           - 'LSODA': Automatic stiffness detection
                           Defaults to DEFAULT_INTEGRATION_METHOD ('RK45').

    Examples:
        >>> # High-precision configuration
        >>> config = SciPyEngineConfig(
        ...     integration_method='DOP853',
        ...     relative_tolerance=1e-12,
        ...     absolute_tolerance=1e-14,
        ...     max_time=120.0
        ... )

    Integration Method Selection:
        - RK45: Best general-purpose method, good accuracy/speed balance
        - RK23: Faster but less accurate, suitable for rough calculations
        - DOP853: Highest accuracy, slower, for precision-critical applications
        - Radau/BDF: For stiff differential equations (rare in ballistics)
        - LSODA: Automatic method selection based on problem characteristics

    Error Control:
        The adaptive error control uses both relative and absolute tolerances:
            `error_estimate ≤ atol + rtol * |solution|`
        Lower tolerances provide higher accuracy but increase computation time.

    See Also:
        - BaseEngineConfig: Base configuration with standard ballistic parameters
        - SciPyEngineConfigDict: TypedDict version for flexible configuration
        - scipy.integrate.solve_ivp: Underlying SciPy integration function

    Note:
        All BaseEngineConfig parameters (cMinimumVelocity, cStepMultiplier, etc.)
        are inherited and remain available for ballistic-specific configuration.
    """

    max_time: float = DEFAULT_MAX_TIME
    relative_tolerance: float = DEFAULT_RELATIVE_TOLERANCE
    absolute_tolerance: float = DEFAULT_ABSOLUTE_TOLERANCE
    integration_method: INTEGRATION_METHOD = DEFAULT_INTEGRATION_METHOD


class SciPyEngineConfigDict(BaseEngineConfigDict, total=False):
    """TypedDict for flexible SciPy integration engine configuration.

    This TypedDict provides a flexible dictionary-based interface for configuring
    the SciPy integration engine. All fields are optional (total=False), allowing
    partial configuration with automatic fallback to default values.

    Attributes:
        max_time: Maximum simulation time in seconds before terminating integration.
                 Prevents runaway calculations in edge cases.
                 If not specified, uses DEFAULT_MAX_TIME (90.0 seconds).
        relative_tolerance: Relative tolerance for integration error control (rtol).
                           Controls the relative accuracy of the numerical solution.
                           Smaller values provide higher precision at computational cost.
                           If not specified, uses DEFAULT_RELATIVE_TOLERANCE (1e-8).
        absolute_tolerance: Absolute tolerance for integration error control (atol).
                           Controls absolute accuracy, particularly important near zero.
                           Smaller values improve precision for small quantities.
                           If not specified, uses DEFAULT_ABSOLUTE_TOLERANCE (1e-6).
        integration_method: SciPy solve_ivp integration method selection.
                           If not specified, uses DEFAULT_INTEGRATION_METHOD ('RK45').

    Examples:
        >>> # Minimal configuration - uses defaults for unspecified fields
        >>> config: SciPyEngineConfigDict = {
        ...     'integration_method': 'DOP853'  # High precision
        ... }
    """

    max_time: float
    relative_tolerance: float
    absolute_tolerance: float
    integration_method: INTEGRATION_METHOD


DEFAULT_SCIPY_ENGINE_CONFIG: SciPyEngineConfig = SciPyEngineConfig()


def create_scipy_engine_config(interface_config: BaseEngineConfigDict | None = None) -> SciPyEngineConfig:
    config = asdict(DEFAULT_SCIPY_ENGINE_CONFIG)
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return SciPyEngineConfig(**config)


# pylint: disable=import-outside-toplevel,unused-argument,too-many-statements
class SciPyIntegrationEngine(BaseIntegrationEngine):
    """High-performance ballistic trajectory integration engine using SciPy's solve_ivp.

    Examples:
        >>> from py_ballisticcalc.engines.scipy_engine import SciPyIntegrationEngine, SciPyEngineConfigDict
        >>>
        >>> # High-precision configuration
        >>> config = SciPyEngineConfigDict(
        ...     integration_method='DOP853',
        ...     relative_tolerance=1e-10,
        ...     absolute_tolerance=1e-12
        ... )
        >>> engine = SciPyIntegrationEngine(config)
        >>>
        >>> # Using with Calculator
        >>> from py_ballisticcalc import Calculator
        >>> calc = Calculator(engine='scipy_engine')

    Note:
        Requires scipy and numpy packages. Install with:
        `pip install py_ballisticcalc[scipy]` or `pip install scipy numpy`
    """

    HitZero: str = "Hit Zero"  # Specific non-exceptional termination reason

    @override
    def __init__(self, config: SciPyEngineConfigDict | None) -> None:
        """Initialize the SciPy integration engine with configuration.

        Sets up the engine with the provided configuration dictionary, initializing
        all necessary parameters for high-precision ballistic trajectory calculations.
        The configuration is converted to a structured format with appropriate
        defaults for any unspecified parameters.

        Args:
            _config: Configuration dictionary containing engine parameters.
                    Can include SciPy-specific options (integration_method,
                    tolerances, max_time) as well as all standard [`BaseEngineConfigDict`](py_ballisticcalc.base_engine.BaseEngineConfigDict).

                    parameters (cMinimumVelocity, cStepMultiplier, etc.).

                    SciPy-specific parameters:
                    - integration_method: SciPy method ('RK45', 'DOP853', etc.)
                    - relative_tolerance: Relative error tolerance (rtol)
                    - absolute_tolerance: Absolute error tolerance (atol)
                    - max_time: Maximum simulation time in seconds

                    Standard ballistic parameters:
                    - cMinimumVelocity: Minimum velocity to continue calculation
                    - cStepMultiplier: Integration step size multiplier
                    - cGravityConstant: Gravitational acceleration
                    - And other BaseEngineConfigDict parameters

        Raises:
            ImportError: If scipy or numpy packages are not available.
            ValueError: If configuration contains invalid parameters.

        Examples:
            >>> config = SciPyEngineConfigDict(
            ...     integration_method='DOP853',
            ...     relative_tolerance=1e-10,
            ...     cMinimumVelocity=50.0
            ... )
            >>> engine = SciPyIntegrationEngine(config)

        Attributes Initialized:
            - _config: Complete configuration with defaults applied
            - gravity_vector: Gravitational acceleration vector
            - integration_step_count: Counter for integration steps (debugging)
            - trajectory_count: Counter for calculated trajectories (debugging)
            - eval_points: list of evaluation points (debugging/analysis)

        Note:
            The configuration is processed through create_scipy_engine_config()
            which applies defaults for any unspecified parameters. This ensures
            the engine always has a complete, valid configuration.
        """

        # dependencies guard
        if not _HAS_NUMPY:
            raise ImportError("Numpy is required for SciPyIntegrationEngine.")
        if not _HAS_SCIPY:
            raise ImportError("SciPy is required for SciPyIntegrationEngine.")

        self._config: SciPyEngineConfig = create_scipy_engine_config(config)  # type: ignore
        self.gravity_vector: Vector = Vector(0.0, self._config.cGravityConstant, 0.0)
        self.integration_step_count = 0  # Number of evaluations of diff_eq during ._integrate()
        self.trajectory_count = 0  # Number of trajectories calculated
        self.eval_points: list[float] = []  # Points at which diff_eq is called

    @override
    @with_no_minimum_velocity
    def _find_max_range(
        self, props: ShotProps, angle_bracket_deg: tuple[float, float] = (0.0, 90.0)
    ) -> tuple[Distance, Angular]:
        """Find the maximum range along the look_angle and the launch angle to reach it.

        Args:
            props: The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg: The angle bracket in degrees to search for max range.  Defaults to (0, 90).

        Returns:
            The maximum range and the launch angle to reach it.

        Raises:
            ImportError: If SciPy is not installed.
            ValueError: If the angle bracket excludes the look_angle.
            OutOfRangeError: If we fail to find a max range.
        """

        # region Virtually vertical shot
        if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            max_range = self._find_apex(props).slant_distance
            return max_range, Angular.Radian(props.look_angle_rad)
        # endregion Virtually vertical shot

        def range_for_angle(angle_rad: float) -> float:
            """Return slant-distance minus slant-error (in feet) for given launch angle in radians."""
            if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
                return self._find_apex(props).slant_distance >> Distance.Foot
            props.barrel_elevation_rad = angle_rad
            hit = self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.ZERO_DOWN, stop_at_zero=True)
            cross = hit.flag(TrajFlag.ZERO_DOWN)
            if cross is None:
                warnings.warn(f"No ZERO_DOWN found for launch angle {angle_rad} rad.")
                return -9e9
            # Return value penalizes distance by slant height, which we want to be zero.
            return (cross.slant_distance >> Distance.Foot) - abs(cross.slant_height >> Distance.Foot)

        res = minimize_scalar(
            lambda angle_rad: -range_for_angle(angle_rad),
            bounds=(
                float(max(props.look_angle_rad, math.radians(angle_bracket_deg[0]))),
                math.radians(angle_bracket_deg[1]),
            ),
            method="bounded",
        )  # type: ignore

        if not res.success:
            raise OutOfRangeError(Distance.Foot(0), note=res.message)
        logger.debug(f"SciPy._find_max_range required {res.nfev} trajectory calculations")
        angle_at_max_rad = res.x
        max_range_ft = -res.fun  # Negate because we minimized the negative range
        return Distance.Feet(max_range_ft), Angular.Radian(angle_at_max_rad)

    @override
    @with_no_minimum_velocity
    def _find_zero_angle(self, props: ShotProps, distance: Distance, lofted: bool = False) -> Angular:
        """Find the barrel elevation needed to hit sight line at a specific distance, using SciPy's `root_scalar`.

        Args:
            props: The shot information.
            distance: Slant distance to the target.
            lofted: If True, find the higher angle that hits the zero point.  Default is False.

        Returns:
            Barrel elevation needed to hit the zero point.

        Raises:
            ImportError: If SciPy is not installed.
            OutOfRangeError: If distance exceeds max range at Shot.look_angle.
            ZeroFindingError: If no solution is found within the angle bracket.
        """

        status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft = self._init_zero_calculation(
            props, distance
        )
        if status is _ZeroCalcStatus.DONE:
            return Angular.Radian(look_angle_rad)

        # region Make mypy happy
        assert start_height_ft is not None
        assert target_x_ft is not None
        assert target_y_ft is not None
        assert slant_range_ft is not None
        # endregion Make mypy happy

        # 1. Find the maximum possible range to establish a search bracket.
        max_range, angle_at_max = self._find_max_range(props)
        max_range_ft = max_range >> Distance.Foot

        # 2. Handle edge cases based on max range.
        if slant_range_ft > max_range_ft:
            raise OutOfRangeError(distance, max_range, Angular.Radian(look_angle_rad))
        if abs(slant_range_ft - max_range_ft) < self.ALLOWED_ZERO_ERROR_FEET:
            return angle_at_max

        def error_at_distance(angle_rad: float) -> float:
            """Target miss (in feet) for given launch angle."""
            props.barrel_elevation_rad = angle_rad
            # Integrate to find the projectile's state at the target's horizontal distance.
            t = self._integrate(props, target_x_ft, target_x_ft, filter_flags=TrajFlag.NONE)[-1]
            if t.time == 0.0:
                logger.warning("Integrator returned initial point. Consider removing constraints.")
                return -1e6  # Large negative error to discourage this angle.
            # return -abs(t.slant_height >> Distance.Foot) - abs((t.slant_distance >> Distance.Foot) - slant_range_ft)
            return (t.height >> Distance.Foot) - target_y_ft - abs((t.distance >> Distance.Foot) - target_x_ft)

        # 3. Establish search bracket for the zero angle.
        if lofted:
            angle_bracket = (angle_at_max >> Angular.Radian, math.radians(90.0))
        else:
            sight_height_adjust = 0.0
            if start_height_ft > 0:  # Lower bound can be less than look angle
                sight_height_adjust = math.atan2(start_height_ft, target_x_ft)
            angle_bracket = (props.look_angle_rad - sight_height_adjust, angle_at_max >> Angular.Radian)

        try:
            sol = root_scalar(error_at_distance, bracket=angle_bracket, method="brentq")
        except ValueError as e:
            raise ZeroFindingError(
                target_y_ft,
                0,
                Angular.Radian(props.barrel_elevation_rad),
                reason=f"No {'lofted' if lofted else 'low'} zero trajectory in elevation range "
                + f"({Angular.Radian(angle_bracket[0]) >> Angular.Degree},"
                + f" {Angular.Radian(angle_bracket[1]) >> Angular.Degree} degrees. {e}",
            )
        if not sol.converged:
            raise ZeroFindingError(
                target_y_ft,
                0,
                Angular.Radian(props.barrel_elevation_rad),
                reason=f"Root-finder failed to converge: {sol.flag} with {sol}",
            )
        return Angular.Radian(sol.root)

    @override
    def _zero_angle(self, props: ShotProps, distance: Distance) -> Angular:
        """Find barrel elevation needed for a particular zero.

        Falls back on ._find_zero_angle().

        Args:
            props: Shot parameters
            distance: Sight distance to zero (i.e., along Shot.look_angle),
                                 a.k.a. slant range to target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance
        """
        try:
            return super()._zero_angle(props, distance)
        except ZeroFindingError as e:
            logger.warning(f"Failed to find zero angle using base iterative method: {e}")
            # Fallback to SciPy's root_scalar method
            return self._find_zero_angle(props, distance)

    @override
    def _integrate(
        self,
        props: ShotProps,
        range_limit_ft: float,
        range_step_ft: float,
        time_step: float = 0.0,
        filter_flags: TrajFlag | int = TrajFlag.NONE,
        dense_output: bool = False,
        stop_at_zero: bool = False,
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
                for interpolating TrajectoryData.  Default is False.
            stop_at_zero: If True, stop integration when trajectory crosses the sight line.  Default is False.

        Returns:
            HitResult: Object describing the trajectory.
        """
        self.trajectory_count += 1

        props.filter_flags = filter_flags
        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = -abs(self._config.cMaximumDrop)  # Ensure it's negative
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: list[TrajectoryData] = []  # Record of TrajectoryData points to return

        wind_sock = ScipyWindSock(props.winds)
        coriolis_fn = props.coriolis.coriolis_acceleration_local if props.coriolis and props.coriolis.full_3d else None

        # region Initialize velocity and position of projectile
        velocity = props.muzzle_velocity_fps
        # x: downrange distance, y: drop, z: windage
        # s = [x, y, z, vx, vy, vz]
        s0 = [
            0.0,
            -props.cant_cosine * props.sight_height_ft,
            -props.cant_sine * props.sight_height_ft,
            math.cos(props.barrel_elevation_rad) * math.cos(props.barrel_azimuth_rad) * velocity,
            math.sin(props.barrel_elevation_rad) * velocity,
            math.cos(props.barrel_elevation_rad) * math.sin(props.barrel_azimuth_rad) * velocity,
        ]
        _cMaximumDrop += min(0, s0[1])  # Adjust max drop downward if above muzzle height
        # endregion

        # region SciPy integration
        gravity_y = self.gravity_vector.y

        def diff_eq(t, s):
            x, y, _ = s[:3]
            vx, vy, vz = s[3:]

            wind = wind_sock.wind_at_distance(x)
            if wind is None:
                rel_vx, rel_vy, rel_vz = vx, vy, vz
            else:
                rel_vx = vx - wind.x
                rel_vy = vy - wind.y
                rel_vz = vz - wind.z

            # magnitude()  # much faster than Vector(*rel_vx).magnitude()
            relative_speed = math.sqrt(rel_vx * rel_vx + rel_vy * rel_vy + rel_vz * rel_vz)

            density_ratio, mach = props.get_density_and_mach_for_altitude(y)
            k_m = density_ratio * props.drag_by_mach(relative_speed / mach)
            drag = k_m * relative_speed

            if coriolis_fn:
                cor = coriolis_fn(Vector(vx, vy, vz))
                cor_x, cor_y, cor_z = cor.x, cor.y, cor.z
            else:
                cor_x = cor_y = cor_z = 0.0

            # # Derivatives
            # dxdt = vx
            # dydt = vy
            # dzdt = vz
            # dvxdt = cor_x - drag * rel_vx
            # dvydt = gravity_y + cor_y - drag * rel_vy
            # dvzdt = cor_z - drag * rel_vz
            return [vx, vy, vz, cor_x - drag * rel_vx, gravity_y + cor_y - drag * rel_vy, cor_z - drag * rel_vz]

        # endregion SciPy integration

        @scipy_event(terminal=True)
        def event_max_range(t: float, s: Any) -> np.floating:  # Stop when x crosses maximum_range
            return s[0] - (range_limit_ft + 1)  # +1 to ensure we cross the threshold

        max_drop = max(_cMaximumDrop, _cMinimumAltitude - props.alt0_ft)  # Smallest allowed y coordinate (ft)

        @scipy_event(terminal=True, direction=-1)
        def event_max_drop(t: float, s: Any) -> np.floating:  # Stop when y crosses down through max_drop
            if s[4] > 0:  # Don't apply condition while v.y>0
                return np.float64(1.0)
            return s[1] - max_drop + 1e-9  # +epsilon so that we actually cross

        @scipy_event(terminal=True)
        def event_min_velocity(t: float, s: Any) -> np.floating:  # Stop when velocity < _cMinimumVelocity
            v = np.linalg.norm(s[3:6])
            return v - _cMinimumVelocity

        # TODO: If _cMinimumVelocity<=0 then: either don't add this event, or always return 0.
        traj_events: list[SciPyEvent] = [event_max_range, event_max_drop, event_min_velocity]

        slant_sine = math.sin(props.look_angle_rad)
        slant_cosine = math.cos(props.look_angle_rad)

        def event_zero_crossing(t: float, s: Any) -> np.floating:  # Look for trajectory crossing sight line
            return s[1] * slant_cosine - s[0] * slant_sine  # Compute slant_height

        if filter_flags & TrajFlag.ZERO:
            zero_crossing = scipy_event(terminal=False, direction=0)(event_zero_crossing)
            traj_events.append(zero_crossing)
        if stop_at_zero:
            zero_crossing_stop = scipy_event(terminal=True, direction=-1)(event_zero_crossing)
            traj_events.append(zero_crossing_stop)

        sol = solve_ivp(
            diff_eq,
            (0, self._config.max_time),
            s0,  # type: ignore[arg-type]
            method=self._config.integration_method,
            dense_output=True,
            rtol=self._config.relative_tolerance,
            atol=self._config.absolute_tolerance,
            events=traj_events,  # type: ignore[arg-type]
        )  # type: ignore[arg-type]

        if not sol.success:  # Integration failed
            raise RangeError(f"SciPy integration failed: {sol.message}", ranges)

        if sol.sol is None:
            logger.error("No solution found by SciPy integration.")
            raise RuntimeError(f"No solution found by SciPy integration: {sol.message}")

        logger.debug(f"SciPy integration via {self._config.integration_method} done with {sol.nfev} function calls.")
        termination_reason = None
        if sol.status == 1 and sol.t_events:  # A termination event occurred
            if len(sol.t_events) > 0:
                if sol.t_events[0].size > 0:  # Expected termination event: we reached requested range
                    # logger.debug(f"Integration stopped at max range: {sol.t_events[0][0]}")
                    pass
                elif sol.t_events[1].size > 0:  # event_max_drop
                    y = sol.sol(sol.t_events[1][0])[1]  # Get y at max drop event
                    if y < _cMaximumDrop + 1e-9:
                        termination_reason = RangeError.MaximumDropReached
                    else:
                        termination_reason = RangeError.MinimumAltitudeReached
                elif sol.t_events[2].size > 0:  # event_min_velocity
                    termination_reason = RangeError.MinimumVelocityReached
                elif (
                    stop_at_zero
                    and len(traj_events) > 3
                    and sol.t_events[-1].size > 0
                    and traj_events[-1].func is event_zero_crossing
                ):
                    termination_reason = self.HitZero

        # region Find requested TrajectoryData points
        if sol.sol is not None and sol.status != -1:

            def make_row(t: float, state: np.ndarray, flag: TrajFlag | int) -> TrajectoryData:
                """Helper function to create a TrajectoryData row."""
                position = Vector(*state[0:3])
                velocity = Vector(*state[3:6])
                _, mach = props.get_density_and_mach_for_altitude(position[1])
                return TrajectoryData.from_props(props, t, position, velocity, mach, flag)

            if sol.t[-1] == 0:
                # If the last time is 0, we only have the initial state
                ranges.append(make_row(sol.t[0], sol.y[:, 0], TrajFlag.RANGE))
            else:
                # List of distances at which we want to record the trajectory data, based on range_step
                desired_xs = np.arange(0, range_limit_ft + range_step_ft, range_step_ft)
                # Get x and t arrays from the solution
                x_vals = sol.y[0]
                t_vals = sol.t

                # region Basic approach to interpolate for desired x values:
                # # This is not very good: distance from requested x varies by ~1% of max_range
                # t_at_x: np.ndarray = np.interp(desired_xs, x_vals, t_vals)
                # states_at_x = sol.sol(t_at_x)  # shape: (state_dim, len(desired_xs))
                # for i in range(states_at_x.shape[1]):
                #     ranges.append(make_row(t_at_x[i], states_at_x[:, i], TrajFlag.RANGE))
                # endregion Basic approach to interpolate for desired x values

                # region Root-finding approach to interpolate for desired x values:
                warnings.simplefilter("once")  # Only issue one warning
                states_at_x: list[np.ndarray] = []
                t_at_x: list[float] = []
                for x_target in desired_xs:
                    idx = np.searchsorted(x_vals, x_target)  # Find bracketing indices for x_target
                    if idx < 0 or idx >= len(x_vals):
                        # warnings.warn("Requested range exceeds computed trajectory" +
                        #                f", which only reaches {PreferredUnits.distance(Distance.Feet(x_vals[-1]))}",
                        #                RuntimeWarning)
                        continue
                    if idx == 0:
                        t_root = t_vals[0]
                    else:
                        # Use root_scalar to find t where x(t) == x_target
                        def x_minus_target(t):  # Function for root finding: x(t) - x_target
                            return sol.sol(t)[0] - x_target  # type: ignore  # pylint: disable=cell-var-from-loop

                        t_lo, t_hi = t_vals[idx - 1], t_vals[idx]
                        res = root_scalar(x_minus_target, bracket=(t_lo, t_hi), method="brentq")
                        if not res.converged:
                            logger.warning(f"Could not find root for requested distance {x_target}")
                            continue
                        t_root = res.root
                    state = sol.sol(t_root)
                    t_at_x.append(t_root)
                    states_at_x.append(state)
                # endregion Root-finding approach to interpolate for desired x values

                # If we ended with an exceptional event then also record the last point calculated
                #   (if it is not already recorded).
                if termination_reason and ((len(t_at_x) == 0) or (t_at_x and t_at_x[-1] < sol.t[-1])):
                    t_at_x.append(sol.t[-1])
                    states_at_x.append(sol.y[:, -1])  # Last state at the end of integration

                states_at_x_arr_t: np.ndarray[Any, np.dtype[np.float64]] = np.array(
                    states_at_x, dtype=np.float64
                ).T  # shape: (state_dim, num_points)
                for i in range(states_at_x_arr_t.shape[1]):
                    ranges.append(make_row(t_at_x[i], states_at_x_arr_t[:, i], TrajFlag.RANGE))
                ranges.sort(key=lambda t: t.time)  # Sort by time

                if time_step > 0.0:
                    time_of_last_record = 0.0
                    for next_record in range(1, len(ranges)):
                        while ranges[next_record].time - time_of_last_record > time_step + self.SEPARATE_ROW_TIME_DELTA:
                            time_of_last_record += time_step
                            ranges.append(make_row(time_of_last_record, sol.sol(time_of_last_record), TrajFlag.RANGE))
                        time_of_last_record = ranges[next_record].time
                    ranges.sort(key=lambda t: t.time)  # Sort by time

            # region Find TrajectoryData points requested by filter_flags
            if filter_flags:

                def add_row(time, state, flag):
                    """Add a row to ranges, keeping it sorted by time.
                    If a row with (approximately) this time already exists then add this flag to it.
                    """
                    idx = bisect_left(ranges, time, key=lambda r: r.time)
                    if idx < len(ranges):
                        # If we match existing row's time then just add this flag to the row
                        if abs(ranges[idx].time - time) < self.SEPARATE_ROW_TIME_DELTA:
                            ranges[idx] = make_row(time, state, ranges[idx].flag | flag)
                            return
                        if idx > 0 and abs(ranges[idx - 1].time - time) < self.SEPARATE_ROW_TIME_DELTA:
                            ranges[idx - 1] = make_row(time, state, ranges[idx - 1].flag | flag)
                            return
                    ranges.insert(idx, make_row(time, state, flag))  # Insert at sorted position

                # Make sure ranges are sorted by time before this check:
                if filter_flags & TrajFlag.MACH and ranges[0].mach >= 1.0 and ranges[-1].mach < 1.0:

                    def mach_minus_one(t):
                        """Return the Mach number at time t minus 1."""
                        state = sol.sol(t)  # type: ignore[reportOptionalMemberAccess]
                        x, y = state[:2]
                        relative_velocity = Vector(*state[3:])
                        if (wind_vector := wind_sock.wind_at_distance(x)) is not None:
                            relative_velocity = relative_velocity - wind_vector
                        relative_speed = relative_velocity.magnitude()
                        _, mach = props.get_density_and_mach_for_altitude(y)
                        return (relative_speed / mach) - 1.0

                    try:
                        t_vals = sol.t
                        res = root_scalar(mach_minus_one, bracket=(t_vals[0], t_vals[-1]))
                        if res.converged:
                            add_row(res.root, sol.sol(res.root), TrajFlag.MACH)
                    except ValueError:
                        logger.debug("No Mach crossing found")

                if (
                    filter_flags & TrajFlag.ZERO
                    and sol.t_events
                    and len(sol.t_events) > 3
                    and sol.t_events[-1].size > 0
                ):
                    for t_cross in sol.t_events[-1]:
                        state = sol.sol(t_cross)
                        # To determine crossing direction, sample after the crossing
                        dt = 1e-8  # Small time offset
                        state_after = sol.sol(t_cross + dt)
                        y_after = event_zero_crossing(t_cross + dt, state_after)
                        if y_after > 0:
                            direction = TrajFlag.ZERO_UP
                        else:
                            direction = TrajFlag.ZERO_DOWN
                        add_row(t_cross, state, direction)

                if filter_flags & TrajFlag.APEX:

                    def vy(t):
                        """Return the vertical velocity at time t."""
                        return sol.sol(t)[4]  # type: ignore[reportOptionalMemberAccess]

                    try:
                        t_vals = sol.t
                        res = root_scalar(vy, bracket=(t_vals[0], t_vals[-1]))
                        if res.converged:
                            add_row(res.root, sol.sol(res.root), TrajFlag.APEX)
                    except ValueError:
                        logger.debug("No apex found for trajectory")

                ranges.sort(key=lambda t: t.time)  # Sort by time
            # endregion Find TrajectoryData points requested by filter_flags
        # endregion Find requested TrajectoryData points
        error = None
        if termination_reason is not None and termination_reason is not self.HitZero:
            error = RangeError(termination_reason, ranges)
        return HitResult(props, ranges, None, filter_flags > 0, error)
