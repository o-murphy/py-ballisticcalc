"""Computes trajectory using SciPy's solve_ivp; uses SciPy's root_scalar to get specific points.
TODO:
 * Use SciPy.optimize for zero_angle() override
"""
import math
import warnings
from dataclasses import dataclass, asdict
from typing import Literal, Any

from typing_extensions import Union, Tuple, List, Optional, override

from py_ballisticcalc.conditions import Shot, Wind
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine, BaseEngineConfigDict, BaseEngineConfig
from py_ballisticcalc.engines.base_engine import create_trajectory_row
from py_ballisticcalc.exceptions import RangeError, ZeroFindingError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Distance, Angular
from py_ballisticcalc.vector import Vector

__all__ = ('SciPyIntegrationEngine',
           'SciPyEngineConfig',
           'SciPyEngineConfigDict',
           'WindSock',
           'DEFAULT_SCIPY_ENGINE_CONFIG')


# TODO: don't recomended to update warning format globally for the lib, use logging.warning instead
# def custom_warning_format(message, category, filename, lineno, file=None, line=None):
#     return f"{category.__name__}: {message}\n"
# warnings.formatwarning = custom_warning_format


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
DEFAULT_INTEGRATION_METHOD: INTEGRATION_METHOD = 'LSODA'  # Default integration method for solve_ivp


@dataclass
class SciPyEngineConfig(BaseEngineConfig):
    """
    Configuration for the SciPy integration engine.

    Attributes:
        max_time (float, optional): Maximum time to simulate in seconds.
                                    Defaults to DEFAULT_MAX_TIME.
        relative_error_tolerance (float, optional): Relative tolerance for integration (rtol).
                                                    Defaults to DEFAULT_RELATIVE_ERROR_TOLERANCE.
        absolute_error_tolerance (float, optional): Absolute tolerance for integration (atol).
                                                    Defaults to DEFAULT_ABSOLUTE_ERROR_TOLERANCE.
        integration_method (Literal): Integration method to use with solve_ivp.
                                      Defaults to DEFAULT_INTEGRATION_METHOD.
    """
    max_time: float = DEFAULT_MAX_TIME
    relative_error_tolerance: float = DEFAULT_RELATIVE_TOLERANCE
    absolute_error_tolerance: float = DEFAULT_ABSOLUTE_TOLERANCE
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

    @override
    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero.

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
        previous_distance = 0.0
        previous_error = 1e+10  # Very large number
        zero_finding_error = _cZeroFindingAccuracy * 2
        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > _cZeroFindingAccuracy:
            # Check height of trajectory at the zero distance (using current self.barrel_elevation)
            try:
                t = self._integrate(shot_info, zero_distance, zero_distance, TrajFlag.NONE)[0]
                height = t.height >> Distance.Foot
                current_distance = zero_distance
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                last_distance_foot = e.last_distance >> Distance.Foot
                proportion = last_distance_foot / zero_distance
                current_distance = e.incomplete_trajectory[-1].look_distance >> Distance.Foot
                height = (e.incomplete_trajectory[-1].height >> Distance.Foot) / proportion

            signed_error = height - height_at_zero

            # print(f"Zero finding iteration {iterations_count}: error={signed_error}\t{self.barrel_elevation} radians \tat {current_distance} feet.")

            if math.fabs(previous_error) < math.fabs(signed_error) and \
                    (self._config.relative_error_tolerance > 1e-13 or self._config.absolute_error_tolerance > 1e-13):
                # This seems to occur when we need less error tolerance in the integrator
                if self._config.relative_error_tolerance > 1e-13:
                    self._config.relative_error_tolerance *= 0.1
                if self._config.absolute_error_tolerance > 1e-13:
                    self._config.absolute_error_tolerance *= 0.1
                # print(f"Reducing error tolerances: rtol={self._config.relative_error_tolerance}\t atol={self._config.absolute_error_tolerance}")
                previous_error = 1e+10  # Reset previous error to a large value
                continue  # Recompute with new tolerances

            zero_finding_error = math.fabs(signed_error)
            if (prev_range := math.fabs(
                    previous_distance - zero_distance)) > 1e-2:  # We're still trying to reach zero_distance
                if math.fabs(current_distance - zero_distance) > prev_range + 1e-2:
                    raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self.barrel_elevation),
                                           'Distance non-convergent. ')
            elif zero_finding_error > math.fabs(previous_error):
                # If error is increasing, we are diverging; stop to avoid infinite loop
                raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self.barrel_elevation),
                                       'Error non-convergent. ')
            previous_distance = current_distance
            previous_error = signed_error

            if zero_finding_error > _cZeroFindingAccuracy:
                # Adjust barrel elevation to close height at zero distance
                self.barrel_elevation -= math.atan2(height - height_at_zero, zero_distance)
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1
            # if iterations_count >= _cMaxIterations:
            #     break
        if zero_finding_error > _cZeroFindingAccuracy:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self.barrel_elevation))

        return Angular.Radian(self.barrel_elevation)

    @override
    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List[TrajectoryData]:
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
            import numpy as np
        except ImportError as e:
            raise ImportError("SciPy and numpy is required for SciPyIntegrationEngine.") from e

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
              math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth) * velocity,
              math.sin(self.barrel_elevation) * velocity,
              math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth) * velocity]

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
            density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(self.alt0 + y)
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

        def event_max_range(t, s):  # Stop when x crosses maximum_range
            return s[0] - (maximum_range + 1)  # +1 to ensure we cross the threshold

        event_max_range.terminal = True  # type: ignore[attr-defined]

        max_drop = max(_cMaximumDrop, _cMinimumAltitude - self.alt0)

        def event_max_drop(t, s):  # Stop when y crosses max_drop
            return s[1] - max_drop

        event_max_drop.terminal = True  # type: ignore[attr-defined]
        event_max_drop.direction = -1  # type: ignore[attr-defined]

        def event_min_velocity(t, s):  # Stop when velocity < _cMinimumVelocity
            v = np.linalg.norm(s[3:6])
            return v - _cMinimumVelocity

        event_min_velocity.terminal = True  # type: ignore[attr-defined]

        traj_events = [event_max_range, event_max_drop, event_min_velocity]

        if filter_flags & TrajFlag.ZERO:
            def zero_crossing(t, s):  # Look for trajectory crossing sight line
                # Solve for y = x * tan(look_angle)
                return s[1] - s[0] * math.tan(self.look_angle)

            zero_crossing.terminal = False  # type: ignore[attr-defined]
            zero_crossing.direction = 0  # type: ignore[attr-defined]
            traj_events.append(zero_crossing)

        sol = solve_ivp(diff_eq, (0, self._config.max_time), s0,
                        method=self._config.integration_method, dense_output=True,
                        rtol=self._config.relative_error_tolerance,
                        atol=self._config.absolute_error_tolerance,
                        events=traj_events)

        if not sol.success:  # Integration failed
            raise RangeError(f"SciPy integration failed: {sol.message}", ranges)

        if sol.sol is None:
            logger.error("No solution found by SciPy integration.")
            raise RuntimeError(f"No solution found by SciPy integration: {sol.message}", sol.message)

        if sol.t_events is None:
            raise RuntimeError("")

        logger.debug(f"SciPy integration complete with {sol.nfev} function calls.")
        termination_reason = None
        if sol.status == 1:  # A termination event occurred
            if len(sol.t_events) > 0:
                # if sol.t_events[0].size > 0:  # Typical termination event
                #     logger.debug(f"Integration stopped at max range: {sol.t_events[0][0]}")
                if sol.t_events[1].size > 0:  # event_max_drop
                    y = sol.sol(sol.t_events[1][0])[1]  # Get y at max drop event
                    if y < _cMaximumDrop:
                        termination_reason = RangeError.MaximumDropReached
                    else:
                        termination_reason = RangeError.MinimumAltitudeReached
                elif sol.t_events[2].size > 0:  # event_min_velocity
                    termination_reason = RangeError.MinimumVelocityReached

        # region Find requested TrajectoryData points
        if sol.sol is not None and sol.status != -1:
            def make_row(t: float, state: np.ndarray, flag: Union[TrajFlag, int]) -> TrajectoryData:
                """Helper function to create a TrajectoryData row."""
                position = Vector(*state[0:3])
                velocity = Vector(*state[3:6])
                velocity_magnitude = velocity.magnitude()
                density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(self.alt0 + position[1])
                drag = density_factor * velocity_magnitude * self.drag_by_mach(velocity_magnitude / mach)
                return create_trajectory_row(t, position, velocity, velocity_magnitude, mach,
                                             self.spin_drift(t), self.look_angle, density_factor, drag, self.weight,
                                             flag
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
            # Interpolate to find the time when each desired x is reached
            # t_at_x: np.ndarray = np.interp(desired_xs, x_vals, t_vals)  # FIX: accidentally not commented

            # region Basic approach to interpolate for desired x values:
            # # This is not very good: distance from requested x varies by ~1% of max_range
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
                    # warnings.warn(
                    #     f"Requested range exceeds computed trajectory, which only reaches {PreferredUnits.distance(Distance.Feet(x_vals[-1]))}",
                    #     RuntimeWarning)
                    continue
                if idx == 0:
                    if filter_flags == TrajFlag.NONE:
                        continue  # Don't record first point
                    t_root = t_vals[0]
                else:
                    t_lo, t_hi = t_vals[idx - 1], t_vals[idx]

                    # Use root_scalar to find t where x(t) == x_target
                    def x_minus_target(t):  # Function for root finding: x(t) - x_target
                        return sol.sol(t)[0] - x_target  # pylint: disable=cell-var-from-loop

                    res = root_scalar(x_minus_target, bracket=(t_lo, t_hi),
                                      method='brentq')  # , xtol=1e-14, rtol=1e-14)
                    # #region Newton's method to find root
                    # def dxdt(t):
                    #     return sol.sol(t)[3]  # vx(t)
                    # res = root_scalar(x_minus_target, fprime=dxdt, bracket=[t_lo, t_hi],
                    #                   x0=0.5 * (t_lo + t_hi),  # Initial guess for Newton's method
                    #                   method='newton', xtol=1e-14, rtol=1e-14)
                    # #endregion Newton's method to find root
                    if not res.converged:
                        logger.warning(f"Could not find root for requested distance {x_target}")
                        continue
                    t_root = res.root
                state = sol.sol(t_root)
                t_at_x.append(t_root)
                states_at_x.append(state)
            # region Root-finding approach to interpolate for desired x values

            # If we ended with an event then also grab the last point calculated
            if termination_reason is not None and len(t_vals) > 1 and t_vals[0] != t_vals[-1]:
                t_at_x.append(sol.t[-1])  # Last time point
                states_at_x.append(sol.y[:, -1])  # Last state at the end of integration

            # don't implicit change the states_at_x type from List[float] to ndarray
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
                if filter_flags & TrajFlag.MACH and ranges[0].mach > 1.0 and ranges[-1].mach < 1.0:
                    def mach_minus_one(t):
                        """Returns the Mach number at time t minus 1."""
                        state = sol.sol(t)
                        x, y = state[:2]
                        relative_velocity = Vector(*state[3:])
                        if (wind_vector := wind_sock.wind_at_distance(x)) is not None:
                            relative_velocity = relative_velocity - wind_vector
                        relative_speed = relative_velocity.magnitude()
                        _, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(self.alt0 + y)
                        return (relative_speed / mach) - 1.0

                    try:
                        res = root_scalar(mach_minus_one, bracket=(t_vals[0], t_vals[-1]))
                        if res.converged:
                            ranges.append(make_row(res.root, sol.sol(res.root), TrajFlag.MACH))
                    except ValueError:
                        logger.debug("No Mach crossing found")

                if filter_flags & TrajFlag.ZERO and len(sol.t_events) > 3 and sol.t_events[-1].size > 0:
                    tan_look_angle = math.tan(self.look_angle)
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
                        ranges.append(make_row(t_cross, state, direction))

                if filter_flags & TrajFlag.APEX:
                    def vy(t):
                        """Returns the vertical velocity at time t."""
                        return sol.sol(t)[4]

                    try:
                        res = root_scalar(vy, bracket=(t_vals[0], t_vals[-1]))
                        if res.converged:
                            ranges.append(make_row(res.root, sol.sol(res.root), TrajFlag.APEX))
                    except ValueError:
                        logger.debug("No apex found for trajectory")

                ranges.sort(key=lambda t: t.time)  # Sort by time
                # endregion Find TrajectoryData points requested by filter_flags
            # endregion Find requested TrajectoryData points

            if termination_reason is not None:
                raise RangeError(termination_reason, ranges)

        # endregion Process the solution
        return ranges
