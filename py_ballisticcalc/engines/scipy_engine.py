"""Computes trajectory using SciPy's solve_ivp.
Uses SciPy's root_scalar to get specific (TrajFlag) trajectory points,
    and for .find_zero_angle(), which can find both the flat and lofted trajectories.
Uses SciPy's minimize_scalar to .find_max_range() for any shot.

TODO:
 * Cache ._integrate() results across .find_zero_angle() and .find_max_range() calls.
    ... but between calls would have to determine whether any relevant shot parameters changed.
    * Store max_range, zero_angle, and even full cache in the shot_info?
        * Confirm cache is valid with a single ._integrate check?
        ... or handle any breaking change to Shot values to clear the cache?
    * Or define hash code of all relevant Shot parameters, and use that to check
        whether integrator cache and _init_trajectory is valid?
"""
import math
import warnings
from dataclasses import dataclass, asdict
from typing import Literal, Any, Callable
from typing_extensions import Union, Tuple, List, Optional, override

import numpy as np

from py_ballisticcalc.conditions import Shot, Wind
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine, BaseEngineConfigDict, BaseEngineConfig
from py_ballisticcalc.engines.base_engine import create_trajectory_row
from py_ballisticcalc.exceptions import OutOfRangeError, RangeError, ZeroFindingError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Distance, Angular
from py_ballisticcalc.vector import Vector

__all__ = ('SciPyIntegrationEngine',
           'SciPyEngineConfig',
           'SciPyEngineConfigDict',
           'WindSock',
           'DEFAULT_SCIPY_ENGINE_CONFIG')

# This block would update warning format globally for the lib; use logging.warning instead
# def custom_warning_format(message, category, filename, lineno, file=None, line=None):
#     return f"{category.__name__}: {message}\n"
# warnings.formatwarning = custom_warning_format


# type of event callback
SciPyEventFunctionT = Callable[[float, Any], np.floating]  # possibly Callable[[float, np.ndarray], np.floating]
# SciPyEventFunctionWithArgsT = Callable[[float, np.ndarray, float, float], np.floating]

# typed scipy event with expected attributes
@dataclass
class SciPyEvent:
    func: SciPyEventFunctionT
    terminal: bool = False
    direction: Literal[-1, 0, 1] = 0

    def __call__(self, t: float, s: Any) -> np.floating:  # possibly s: np.ndarray
        return self.func(t, s)

# decorator that simply wraps SciPyEventFunctionT to SciPyEvent
#   to ensure that event object has expected attrs
def scipy_event(
        terminal: bool = False,
        direction: Literal[-1, 0, 1] = 0
) -> Callable[[SciPyEventFunctionT], SciPyEvent]:
    """
    A decorator to create a SciPy solve_ivp compatible event object.

    Args:
        terminal (bool): Whether to terminate integration when the event occurs.
                         Defaults to False.
        direction (Literal[-1, 0, 1]): Direction of the zero-crossing to trigger the event.
                                       -1: Function crosses from positive to negative.
                                        0: Any direction.
                                        1: Function crosses from negative to positive.
                                       Defaults to 0.

    Returns:
        Callable: A decorator that transforms a standard event function
                  into a SciPyEvent object, which is callable and carries
                  the 'terminal' and 'direction' metadata.
    """

    def wrapper(func: SciPyEventFunctionT) -> SciPyEvent:
        """These lines dynamically add attributes to the function object.
        Type checkers (like MyPy) might complain that 'func' doesn't inherently
        have 'terminal' or 'direction' attributes defined in its type signature
        (SciPyEventFunction). This is a common pattern for how SciPy's solve_ivp
        expects event functions to be configured.
        You might see 'type: ignore[attr-defined]' in very strict environments
        to suppress these warnings, but for this specific SciPy idiom,
        it's often understood.
        func.terminal = terminal  # type: ignore[attr-defined]
        func.direction = direction  # type: ignore[attr-defined]
        """
        return SciPyEvent(func, terminal, direction)

    return wrapper


class WindSock:
    """Finds wind vector in effect at any distance down-range."""

    def __init__(self, winds: Union[Tuple["Wind", ...], None]):
        # Sort winds by range, ascending
        self.winds = None
        if isinstance(winds, Wind):
            self.winds = [winds]
        elif isinstance(winds, (tuple, list)):
            self.winds = sorted(winds, key=lambda w: w.until_distance.raw_value)

    def wind_at_distance(self, distance: float) -> Optional[Vector]:
        """Returns wind vector at specified distance, where distance is in feet."""
        if not self.winds:
            return None
        distance *= 12.0  # Convert distance to inches (distance.raw_value)
        for wind in self.winds:  # TODO: use binary search for performance
            if distance <= wind.until_distance.raw_value:
                return wind.vector
        return None


INTEGRATION_METHOD = Literal["RK23", "RK45", "DOP853", "Radau", "BDF", "LSODA"]

DEFAULT_MAX_TIME: float = 90.0  # Max flight time to simulate before stopping integration
DEFAULT_RELATIVE_TOLERANCE: float = 1e-8  # Default relative tolerance (rtol) for integration
DEFAULT_ABSOLUTE_TOLERANCE: float = 1e-6  # Default absolute tolerance (atol) for integration
DEFAULT_INTEGRATION_METHOD: INTEGRATION_METHOD = 'RK45'  # Default integration method for solve_ivp


@dataclass
class SciPyEngineConfig(BaseEngineConfig):
    """
    Configuration for the SciPy integration engine.

    Attributes:
        max_time (float, optional): Maximum time to simulate in seconds.
                                    Defaults to DEFAULT_MAX_TIME.
        relative_tolerance (float, optional): Relative tolerance for integration (rtol).
                                                    Defaults to DEFAULT_RELATIVE_ERROR_TOLERANCE.
        absolute_tolerance (float, optional): Absolute tolerance for integration (atol).
                                                    Defaults to DEFAULT_ABSOLUTE_ERROR_TOLERANCE.
        integration_method (Literal): Integration method to use with solve_ivp.
                                      Defaults to DEFAULT_INTEGRATION_METHOD.
    """
    max_time: float = DEFAULT_MAX_TIME
    relative_tolerance: float = DEFAULT_RELATIVE_TOLERANCE
    absolute_tolerance: float = DEFAULT_ABSOLUTE_TOLERANCE
    integration_method: INTEGRATION_METHOD = DEFAULT_INTEGRATION_METHOD


class SciPyEngineConfigDict(BaseEngineConfigDict, total=False):
    """
    Typed dictionary for configuring the SciPy integration engine.

    Attributes:
        max_time (float, optional): Maximum time to simulate in seconds.
                                    Defaults to DEFAULT_MAX_TIME.
        relative_tolerance (float, optional): Relative tolerance for integration (rtol).
                                                    Defaults to DEFAULT_RELATIVE_ERROR_TOLERANCE.
        absolute_tolerance (float, optional): Absolute tolerance for integration (atol).
                                                    Defaults to None, which uses the default from solve_ivp.
        integration_method (Literal): Integration method to use with solve_ivp.
                                      Defaults to DEFAULT_INTEGRATION_METHOD.
    """
    max_time: float
    relative_tolerance: float
    absolute_tolerance: float
    integration_method: INTEGRATION_METHOD


DEFAULT_SCIPY_ENGINE_CONFIG: SciPyEngineConfig = SciPyEngineConfig()


def create_scipy_engine_config(interface_config: Optional[BaseEngineConfigDict] = None) -> SciPyEngineConfig:
    config = asdict(DEFAULT_SCIPY_ENGINE_CONFIG)
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return SciPyEngineConfig(**config)


# pylint: disable=import-outside-toplevel,unused-argument,too-many-statements
class SciPyIntegrationEngine(BaseIntegrationEngine[SciPyEngineConfigDict]):
    """Integration engine using SciPy's solve_ivp for trajectory calculations."""
    HitZero: str = "Hit Zero"  # Special non-exceptional termination reason

    @override
    def __init__(self, _config: SciPyEngineConfigDict):
        """
        Initializes the SciPyIntegrationEngine.

        Args:
            _config (SciPyEngineConfigDict): Configuration dictionary for the engine.
        """
        self._config: SciPyEngineConfig = create_scipy_engine_config(_config)
        self.gravity_vector: Vector = Vector(.0, self._config.cGravityConstant, .0)
        self._table_data = []
        from py_ballisticcalc.helpers import get_bisect_left_key_func
        self.bisect_left_key_func = get_bisect_left_key_func()  # Bisect function for compatibility with Python < 3.10

    @override
    def find_max_range(self, shot_info: Shot, angle_bracket_deg: Tuple[float, float] = (0.0, 90.0)) -> Tuple[
            Distance, Angular]:
        """
        Finds the maximum range along the look_angle and the launch angle to reach it.

        Args:
            shot_info (Shot): The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg (Tuple[float, float], optional): The angle bracket in degrees to search for the maximum range.
                                                               Defaults to (0, 90).

        Returns:
            Tuple[Distance, Angular]: The maximum range and the launch angle to reach it.

        Raises:
            ImportError: If SciPy is not installed.
            ValueError: If the angle bracket excludes the look_angle.
            OutOfRangeError: If we fail to find a max range.

        TODO: Make sure user hasn't restricted angle bracket to exclude the look_angle.
            ... and check for weird situations, like backward-bending trajectories,
            where the max range occurs with launch angle less than the look angle.
        """
        try:
            from scipy.optimize import minimize_scalar  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("SciPy is required for SciPyIntegrationEngine.") from e

        self._init_trajectory(shot_info)

        # region Virtually vertical shot
        if abs(self.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            max_range = self.find_apex(shot_info).look_distance
            return max_range, Angular.Radian(self.look_angle_rad)
        # endregion Virtually vertical shot

        def range_for_angle(angle_rad: float) -> float:
            """Returns range to zero (in feet) for given launch angle in radians."""
            if abs(self.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
                return self.find_apex(shot_info).look_distance >> Distance.Foot
            self.barrel_elevation_rad = angle_rad
            try:
                t = self._integrate(shot_info, 9e9, 9e9, TrajFlag.NONE, stop_at_zero=True)[-1]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
            return (t.look_distance >> Distance.Foot) - (t.target_drop >> Distance.Foot)

        res = minimize_scalar(lambda angle_rad: -range_for_angle(angle_rad),
                              bounds=(float(max(self.look_angle_rad, math.radians(angle_bracket_deg[0]))),
                                      math.radians(angle_bracket_deg[1])),
                              method='bounded')  # type: ignore

        if not res.success:
            raise OutOfRangeError(Distance.Foot(0), note=res.message)
        logger.debug(f"SciPy.find_max_range required {res.nfev} trajectory calculations")
        angle_at_max_rad = res.x
        max_range_ft = -res.fun  # Negate because we minimized the negative range
        return Distance.Feet(max_range_ft), Angular.Radian(angle_at_max_rad)

    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool = False) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance,
            using SciPy's root_scalar.

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.
            lofted (bool, optional): If True, find the higher angle that hits the zero point.

        Returns:
            Angular: The required barrel elevation.

        Raises:
            ImportError: If SciPy is not installed.
            OutOfRangeError: If distance exceeds max range at Shot.look_angle.
            ZeroFindingError
        """
        try:
            from scipy.optimize import root_scalar  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("SciPy is required for SciPyIntegrationEngine.") from e

        status, result = self._init_zero_calculation(shot_info, distance)
        if status is self._ZeroCalcStatus.DONE:
            return result
        look_angle, target_look_dist_ft, target_x_ft, target_y_ft, start_height = result

        max_range, angle_at_max = self.find_max_range(shot_info)
        max_range_ft = max_range >> Distance.Foot

        if target_look_dist_ft > max_range_ft:
            raise OutOfRangeError(distance, max_range, Angular.Radian(look_angle))
        if abs(target_look_dist_ft - max_range_ft) < self.ALLOWED_ZERO_ERROR_FEET:
            return angle_at_max

        def error_at_distance(angle_rad: float) -> float:
            """
            Vertical error (in feet) at the target's horizontal distance.
            (= projectile's height minus the line-of-sight's height at that distance.)
            """
            self.barrel_elevation_rad = angle_rad
            try:
                # Integrate to find the projectile's state at the target's horizontal distance.
                t = self._integrate(shot_info, target_x_ft, target_x_ft, TrajFlag.NONE)[-1]
                if t.time == 0.0:
                    logger.warning("Integrator returned initial point. Consider removing constraints.")
                    return -1e6  # Large negative error to discourage this angle.
                return (t.height >> Distance.Foot) - target_y_ft
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
                if t.time == 0.0:
                    logger.warning("Integrator returned initial point. Consider removing constraints.")
                    return -1e6  # Large negative error to discourage this angle.
                return -abs(t.target_drop >> Distance.Foot) - abs((t.look_distance >> Distance.Foot) - target_look_dist_ft)

        if lofted:
            angle_bracket = (angle_at_max >> Angular.Radian, math.radians(90.0))
        else:
            sight_height_adjust = 0.0
            if start_height > 0:  # Lower bound can be less than look angle
                sight_height_adjust = math.atan2(start_height, target_x_ft)
            angle_bracket = (self.look_angle_rad - sight_height_adjust, angle_at_max >> Angular.Radian)

        try:
            sol = root_scalar(error_at_distance, bracket=angle_bracket, method='brentq')
        except ValueError as e:
            raise ZeroFindingError(target_y_ft, 0, Angular.Radian(self.barrel_elevation_rad),
                                   reason=f"No {'lofted' if lofted else 'low'} zero trajectory in elevation range " +
                                          f"({Angular.Radian(angle_bracket[0])>>Angular.Degree}," +
                                          f" {Angular.Radian(angle_bracket[1])>>Angular.Degree} degrees. {e}")
        if not sol.converged:
            raise ZeroFindingError(target_y_ft, 0, Angular.Radian(self.barrel_elevation_rad),
                                   reason=f"Root-finder failed to converge: {sol.flag} with {sol}")
        return Angular.Radian(sol.root)

    @override
    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero.
            Falls back on .find_zero_angle().

        Args:
            shot_info (Shot): Shot parameters
            distance (Distance): Sight distance to zero (i.e., along Shot.look_angle),
                                 a.k.a. slant range to target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance
        """

        status, result = self._init_zero_calculation(shot_info, distance)
        if status is self._ZeroCalcStatus.DONE:
            return result
        look_angle, target_look_dist_ft, target_x_ft, target_y_ft, start_height = result

        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations
        iterations_count = 0
        range_error_ft = 9e9  # Absolute value of error from target distance along sight line
        prev_range_error_ft = 9e9
        prev_height_error_ft = 9e9
        slant_error_ft = _cZeroFindingAccuracy * 2  # Absolute value of error from sight line in feet at zero distance

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

            slant_diff_ft = t.target_drop >> Distance.Foot
            look_dist_ft = t.look_distance >> Distance.Foot
            horizontal_ft = t.distance >> Distance.Foot  # Horizontal distance
            trajectory_angle = t.angle >> Angular.Radian  # Flight angle at current distance
            sensitivity = math.tan(self.barrel_elevation_rad) * math.tan(trajectory_angle)
            if -1.5 < sensitivity < -0.5:  # TODO: Find good bounds for this
                # Scenario too unstable for 1st order iteration
                logger.debug("Unstable scenario detected in zero_angle(); calling find_zero_angle()")
                break
            elif abs(sensitivity) > 1000:  # TODO: Find good bounds for this
                logger.debug("High sensitivity; using slant correction")
                if abs(look_dist_ft) > 1e-6:
                    correction = -slant_diff_ft / look_dist_ft
                else:
                    correction = -slant_diff_ft  # Avoid division by zero; or maybe should break?
            elif horizontal_ft != 0:  # TODO: Use vertical difference instead of slant difference?
                correction = -slant_diff_ft / (horizontal_ft * (1 + sensitivity))  # 1st order correction
            else:
                break

            range_diff_ft = look_dist_ft - target_look_dist_ft
            range_error_ft = math.fabs(range_diff_ft)
            slant_error_ft = math.fabs(slant_diff_ft)

            logger.debug(f'Zero step {iterations_count}: slant_error={slant_diff_ft}\t range_error={range_diff_ft} '
                         f'\t{self.barrel_elevation_rad}rad\t at {look_dist_ft}ft. Correction={correction}rads')

            if range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # We're still trying to reach zero_distance
                if range_error_ft > prev_range_error_ft - 1e-6:  # We're not getting closer to zero_distance
                    # raise ZeroFindingError(zero_error, iterations_count, Angular.Radian(self.barrel_elevation), 'Distance non-convergent.')
                    break
            elif slant_error_ft > math.fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                # raise ZeroFindingError(zero_error, iterations_count, Angular.Radian(self.barrel_elevation), 'Error non-convergent.')
                break

            prev_range_error_ft = range_error_ft
            prev_height_error_ft = slant_error_ft

            if slant_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # Adjust barrel elevation to close height at zero distance
                self.barrel_elevation_rad += correction
            else:  # Current barrel_elevation hit zero!
                break
            iterations_count += 1

        if slant_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
            return self.find_zero_angle(shot_info, distance)
            # # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            # raise ZeroFindingError(zero_error, iterations_count, Angular.Radian(self.barrel_elevation))
        return Angular.Radian(self.barrel_elevation_rad)

    @override
    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0, stop_at_zero: bool = False) -> List[
        TrajectoryData]:
        """
        Calculate trajectory for specified shot

        Args:
            shot_info (Shot):  Information about the shot
            maximum_range (float): Feet down range to stop calculation
            record_step (float): Frequency (in feet down range) to record TrajectoryData
            filter_flags (Union[TrajFlag, int]): Bitfield for requesting special trajectory points
            time_step (float, optional): Maximum time (in seconds) between TrajectoryData records

        Returns:
            List[TrajectoryData]: list of TrajectoryData, one for each dist_step, out to max_range
        """

        try:
            from scipy.integrate import solve_ivp  # type: ignore[import-untyped]
            from scipy.optimize import root_scalar  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("SciPy and numpy are required for SciPyIntegrationEngine.") from e

        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = self._config.cMaximumDrop
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: List[TrajectoryData] = []  # Record of TrajectoryData points to return

        wind_sock = WindSock(shot_info.winds)

        # region Initialize velocity and position of projectile
        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        # s = [x, y, z, vx, vy, vz]
        s0 = [.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height,
              math.cos(self.barrel_elevation_rad) * math.cos(self.barrel_azimuth_rad) * velocity,
              math.sin(self.barrel_elevation_rad) * velocity,
              math.cos(self.barrel_elevation_rad) * math.sin(self.barrel_azimuth_rad) * velocity]

        # endregion

        # region SciPy integration
        def diff_eq(t, s):
            """
            Defines the dynamics of the bullet for integration.
            :param t: Time (not used in this case, but required by solve_ivp)
            :param y: State vector [x, y, z, vx, vy, vz]
            :return: Derivative of state vector
            """
            x, y, z = s[:3]  # pylint: disable=unused-variable
            vx, vy, vz = s[3:]
            velocity_vector = Vector(vx, vy, vz)
            wind_vector = wind_sock.wind_at_distance(x)
            if wind_vector is None:
                relative_velocity = velocity_vector
            else:
                relative_velocity = velocity_vector - wind_vector
            relative_speed = relative_velocity.magnitude()
            density_factor, mach = shot_info.atmo.get_density_and_mach_for_altitude(self.alt0 + y)
            km = density_factor * self.drag_by_mach(relative_speed / mach)
            drag = km * relative_speed

            # Derivatives
            dxdt = vx
            dydt = vy
            dzdt = vz
            dvxdt = -drag * relative_velocity.x
            dvydt = self.gravity_vector.y - drag * relative_velocity.y
            dvzdt = -drag * relative_velocity.z
            return [dxdt, dydt, dzdt, dvxdt, dvydt, dvzdt]

        # endregion SciPy integration

        @scipy_event(terminal=True)
        def event_max_range(t: float, s: Any) -> np.floating:  # Stop when x crosses maximum_range
            return s[0] - (maximum_range + 1)  # +1 to ensure we cross the threshold

        max_drop = max(_cMaximumDrop, _cMinimumAltitude - self.alt0)

        @scipy_event(terminal=True, direction=-1)
        def event_max_drop(t: float, s: Any) -> np.floating:  # Stop when y crosses max_drop
            return s[1] - max_drop

        @scipy_event(terminal=True)
        def event_min_velocity(t: float, s: Any) -> np.floating:  # Stop when velocity < _cMinimumVelocity
            v = np.linalg.norm(s[3:6])
            return v - _cMinimumVelocity

        traj_events: List[SciPyEvent] = [event_max_range, event_max_drop, event_min_velocity]

        def event_zero_crossing(t: float, s: Any) -> np.floating:  # Look for trajectory crossing sight line
            # Solve for y = x * tan(look_angle)
            return s[1] - s[0] * math.tan(self.look_angle_rad)

        if filter_flags & TrajFlag.ZERO:
            zero_crossing = scipy_event(terminal=False, direction=0)(event_zero_crossing)
            traj_events.append(zero_crossing)
        if stop_at_zero:
            zero_crossing_stop = scipy_event(terminal=True, direction=-1)(event_zero_crossing)
            traj_events.append(zero_crossing_stop)

        sol = solve_ivp(diff_eq, (0, self._config.max_time), s0,
                        method=self._config.integration_method, dense_output=True,
                        rtol=self._config.relative_tolerance,
                        atol=self._config.absolute_tolerance,
                        events=traj_events)  # type: ignore[arg-type]

        if not sol.success:  # Integration failed
            raise RangeError(f"SciPy integration failed: {sol.message}", ranges)

        if sol.sol is None:
            logger.error("No solution found by SciPy integration.")
            raise RuntimeError(f"No solution found by SciPy integration: {sol.message}")

        logger.debug(f"SciPy integration complete with {sol.nfev} function calls.")
        termination_reason = None
        if sol.status == 1 and sol.t_events:  # A termination event occurred
            if len(sol.t_events) > 0:
                if sol.t_events[0].size > 0:  # Expected termination event: we reached requested range
                    #logger.debug(f"Integration stopped at max range: {sol.t_events[0][0]}")
                    pass
                elif sol.t_events[1].size > 0:  # event_max_drop
                    y = sol.sol(sol.t_events[1][0])[1]  # Get y at max drop event
                    if y < _cMaximumDrop:
                        termination_reason = RangeError.MaximumDropReached
                    else:
                        termination_reason = RangeError.MinimumAltitudeReached
                elif sol.t_events[2].size > 0:  # event_min_velocity
                    termination_reason = RangeError.MinimumVelocityReached
                elif (stop_at_zero and len(traj_events) > 3 and sol.t_events[-1].size > 0 and
                      traj_events[-1].func is event_zero_crossing):
                    termination_reason = self.HitZero

        # region Find requested TrajectoryData points
        if sol.sol is not None and sol.status != -1:
            def make_row(t: float, state: np.ndarray, flag: Union[TrajFlag, int]) -> TrajectoryData:
                """Helper function to create a TrajectoryData row."""
                position = Vector(*state[0:3])
                velocity = Vector(*state[3:6])
                velocity_magnitude = velocity.magnitude()
                density_factor, mach = shot_info.atmo.get_density_and_mach_for_altitude(self.alt0 + position[1])
                drag = density_factor * velocity_magnitude * self.drag_by_mach(velocity_magnitude / mach)
                return create_trajectory_row(t, position, velocity, velocity_magnitude, mach, self.spin_drift(t),
                                             self.look_angle_rad, density_factor, drag, self.weight, flag
                )

            if sol.t[-1] == 0:
                # If the last time is 0, we only have the initial state
                ranges.append(make_row(sol.t[0], sol.y[:, 0], TrajFlag.RANGE))
                return ranges

            # List of distances at which we want to record the trajectory data
            desired_xs = np.arange(0, maximum_range + record_step, record_step)
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
            states_at_x: List[np.ndarray] = []
            t_at_x: List[float] = []
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
                        return sol.sol(t)[0] - x_target  # pylint: disable=cell-var-from-loop

                    t_lo, t_hi = t_vals[idx - 1], t_vals[idx]
                    res = root_scalar(x_minus_target, bracket=(t_lo, t_hi), method='brentq')
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
            if termination_reason and t_at_x and t_at_x[-1] < sol.t[-1]:
                t_at_x.append(sol.t[-1])
                states_at_x.append(sol.y[:, -1])  # Last state at the end of integration

            states_at_x_arr_t: np.ndarray[Any, np.dtype[np.float64]] = np.array(states_at_x,
                                                  dtype=np.float64).T  # shape: (state_dim, num_points)
            for i in range(states_at_x_arr_t.shape[1]):
                ranges.append(make_row(t_at_x[i], states_at_x_arr_t[:, i], TrajFlag.RANGE))
            ranges.sort(key=lambda t: t.time)  # Sort by time

            if time_step > 0.0:
                time_of_last_record = 0.0
                for next_record in range(1, len(ranges)):
                    while ranges[next_record].time - time_of_last_record > time_step:
                        time_of_last_record += time_step
                        ranges.append(make_row(time_of_last_record, sol.sol(time_of_last_record), TrajFlag.RANGE))
                ranges.sort(key=lambda t: t.time)  # Sort by time

            # region Find TrajectoryData points requested by filter_flags
            if filter_flags:
                def add_row(time, state, flag):
                    """Add a row to ranges, keeping it sorted by time.
                       If row this time already exists then add this flag to it."""
                    idx = self.bisect_left_key_func(ranges, time, key=lambda r: r.time)
                    if idx < len(ranges) and ranges[idx].time == time:
                        ranges[idx] = make_row(time, state, ranges[idx].flag | flag)  # Update flag if time matches
                    else:
                        ranges.insert(idx, make_row(time, state, flag))  # Insert at sorted position

                # Make sure ranges are sorted by time before this check:
                if filter_flags & TrajFlag.MACH and ranges[0].mach > 1.0 and ranges[-1].mach < 1.0:
                    def mach_minus_one(t):
                        """Returns the Mach number at time t minus 1."""
                        state = sol.sol(t)
                        x, y = state[:2]
                        relative_velocity = Vector(*state[3:])
                        if (wind_vector := wind_sock.wind_at_distance(x)) is not None:
                            relative_velocity = relative_velocity - wind_vector
                        relative_speed = relative_velocity.magnitude()
                        _, mach = shot_info.atmo.get_density_and_mach_for_altitude(self.alt0 + y)
                        return (relative_speed / mach) - 1.0

                    try:
                        res = root_scalar(mach_minus_one, bracket=(t_vals[0], t_vals[-1]))
                        if res.converged:
                            add_row(res.root, sol.sol(res.root), TrajFlag.MACH)
                    except ValueError:
                        logger.debug("No Mach crossing found")

                if (filter_flags & TrajFlag.ZERO and sol.t_events and len(sol.t_events) > 3
                                                 and sol.t_events[-1].size > 0):
                    tan_look_angle = math.tan(self.look_angle_rad)
                    for t_cross in sol.t_events[-1]:
                        state = sol.sol(t_cross)
                        # To determine crossing direction, sample after the crossing
                        dt = 1e-8  # Small time offset
                        state_after = sol.sol(t_cross + dt)
                        y_after = state_after[1] - state_after[0] * tan_look_angle
                        if y_after > 0:
                            direction = TrajFlag.ZERO_UP
                        else:
                            direction = TrajFlag.ZERO_DOWN
                        add_row(t_cross, state, direction)

                if filter_flags & TrajFlag.APEX:
                    def vy(t):
                        """Returns the vertical velocity at time t."""
                        return sol.sol(t)[4]

                    try:
                        res = root_scalar(vy, bracket=(t_vals[0], t_vals[-1]))
                        if res.converged:
                            add_row(res.root, sol.sol(res.root), TrajFlag.APEX)
                    except ValueError:
                        logger.debug("No apex found for trajectory")

                ranges.sort(key=lambda t: t.time)  # Sort by time
            # endregion Find TrajectoryData points requested by filter_flags
        # endregion Find requested TrajectoryData points

        if termination_reason not in (None, self.HitZero):
            assert termination_reason is not None  # for mypy
            raise RangeError(termination_reason, ranges)

        return ranges
