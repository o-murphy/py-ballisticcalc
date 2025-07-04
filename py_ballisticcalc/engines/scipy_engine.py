"""Computes trajectory using SciPy's solve_ivp.
Uses SciPy's root_scalar to get specific (TrajFlag) trajectory points,
    and for .find_zero_angle(), which can find both the flat and lofted trajectories.
Uses SciPy's minimize_scalar to .find_max_range() for any shot.

TODO:
 * Preserve/cache find_max_range value for multiple find_zero_angle() calls
    ... but have to determine whether any relevant shot parameters changed.
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


# This block would update warning format globally for the lib; use logging.warning instead
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

    def find_max_range(self, shot_info: Shot, angle_bracket_deg: Tuple[float, float] = (0.1, 89.9)) -> Tuple[float, float]:
        """
        Finds the maximum horizontal range and the launch angle to reach it.

        Args:
            shot_info (Shot): The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg (Tuple[float, float], optional): The angle bracket in degrees to search for the maximum range.
                                                               Defaults to (0.1, 89.9).

        Returns:
            Tuple[float, float]: The maximum range in feet and the launch angle in radians to reach it.
        """
        try:
            from scipy.optimize import minimize_scalar  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("SciPy is required for SciPyIntegrationEngine.") from e

        restore_cMaximumDrop = None
        if self._config.cMaximumDrop:
            restore_cMaximumDrop = self._config.cMaximumDrop
            self._config.cMaximumDrop = 0  # We want to run trajectory until it returns to horizontal
        self._init_trajectory(shot_info)
        def range_for_angle(angle_rad: float) -> float:
            """Returns horizontal range to zero (in feet) for given launch angle in radians."""
            self.barrel_elevation = angle_rad
            try:
                t = self._integrate(shot_info, 9e9, 9e9, TrajFlag.NONE)[0]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]
            return t.distance >> Distance.Foot

        res = minimize_scalar(lambda angle_rad: -range_for_angle(angle_rad),
                               bounds=(math.radians(angle_bracket_deg[0]), math.radians(angle_bracket_deg[1])),
                               method='bounded')

        if restore_cMaximumDrop is not None:
            self._config.cMaximumDrop = restore_cMaximumDrop

        if not res.success:
            raise ZeroFindingError(note=f"Could not find maximum range: {res.message}")

        angle_at_max_rad = res.x
        max_range_ft = -res.fun  # Negate because we minimized the negative range
        return max_range_ft, angle_at_max_rad

    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool=False) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance,
            using SciPy's root_scalar.

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): The distance to the target.
            lofted (bool, optional): If True, find the higher angle that hits the zero point.

        Returns:
            Angular: The required barrel elevation.
        """
        try:
            from scipy.optimize import root_scalar  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("SciPy is required for SciPyIntegrationEngine.") from e

        self._init_trajectory(shot_info)

        target_slant_dist_ft = distance >> Distance.Foot
        target_x_ft = target_slant_dist_ft * math.cos(self.look_angle)
        target_y_ft = target_slant_dist_ft * math.sin(self.look_angle)

        def error_at_distance(angle_rad: float) -> float:
            """
            Vertical error (in feet) at the target's horizontal distance.
            (= projectile's height minus the line-of-sight's height at that distance.)
            """
            self.barrel_elevation = angle_rad
            try:
                # Integrate to find the projectile's state at the target's horizontal distance.
                t = self._integrate(shot_info, target_x_ft, target_x_ft, TrajFlag.NONE)[0]
                return (t.height >> Distance.Foot) - target_y_ft
            except RangeError:
                # If the projectile doesn't reach the target, it's a very large negative error.
                return -1e6

        max_range_ft, angle_at_max_rad = self.find_max_range(shot_info)
        if target_x_ft > max_range_ft:
            raise ZeroFindingError(note=f"Target distance {target_x_ft:.1f} ft is beyond max range {max_range_ft:.1f} ft.")

        if lofted:
            angle_bracket = (angle_at_max_rad, math.radians(89.9))
        else:
            angle_bracket = (self.look_angle, angle_at_max_rad)

        try:
            sol = root_scalar(error_at_distance, bracket=angle_bracket, method='brentq')
        except ValueError as e:
            raise ZeroFindingError(note=f"Could find {'lofted' if lofted else 'low'} trajectory to zero. Details: {e}")
        if not sol.converged:
            raise ZeroFindingError(note=f"Root-finder failed to converge: {sol.flag}")

        return Angular.Radian(sol.root)


    @override
    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero.
            Falls back on .find_zero_angle().

        Args:
            shot_info (Shot): Shot parameters
            distance (Distance): Sight distance to zero (i.e., along self.look_angle)

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance
        """
        self._init_trajectory(shot_info)

        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations

        zero_distance = (distance >> Distance.Foot) * math.cos(self.look_angle)  # Horizontal distance

        iterations_count = 0
        previous_elevation = self.barrel_elevation
        previous_distance = 0.0
        previous_error = 1e+10  # Very large number
        zero_error = _cZeroFindingAccuracy * 2  # Absolute value of vertical error in feet

        while iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current self.barrel_elevation)
            try:
                t = self._integrate(shot_info, zero_distance, zero_distance, TrajFlag.NONE)[0]
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                t = e.incomplete_trajectory[-1]

            current_distance = t.distance >> Distance.Foot  # Horizontal distance
            if current_distance < 1 and self.barrel_elevation == 0.0:
                # Degenerate case: little distance and zero elevation; try with some elevation
                self.barrel_elevation = 0.01
                continue

            height = t.height >> Distance.Foot
            trajectory_angle = t.angle >> Angular.Radian    # Flight angle at current distance
            #signed_error = height - height_at_zero
            signed_error = height - math.tan(self.look_angle) * current_distance
            sensitivity = math.tan(self.barrel_elevation) * math.tan(trajectory_angle)
            if -1.5 < sensitivity < -0.5:
                # Scenario too unstable for 1st order iteration
                break
            else:
                correction = -signed_error / (current_distance * (1 + sensitivity))  # 1st order correction

            #print(f'Zero step {iterations_count}: error={signed_error} '
            #      f'\t{self.barrel_elevation}rad\t at {current_distance}ft. Correction={correction}rads')

            zero_error = math.fabs(signed_error)
            if (prev_range := math.fabs(previous_distance - zero_distance)) > 1e-2:  # We're still trying to reach zero_distance
                if math.fabs(current_distance - zero_distance) > prev_range + 1e-2:  # We're not getting closer to zero_distance
                    # raise ZeroFindingError(zero_error, iterations_count, Angular.Radian(self.barrel_elevation), 'Distance non-convergent.')
                    break
            elif zero_error > math.fabs(previous_error):  # Error is increasing, we are diverging
                if self._config.relative_error_tolerance > 1.1e-13 or self._config.absolute_error_tolerance > 1.1e-13:
                    # Tighten the error tolerance in the integrator and let's try again
                    if self._config.relative_error_tolerance > 1.1e-13:
                        self._config.relative_error_tolerance *= 0.1
                    if self._config.absolute_error_tolerance > 1.1e-13:
                        self._config.absolute_error_tolerance *= 0.1
                    #print(f"Reducing error tolerances: rtol={self._config.relative_error_tolerance}\t atol={self._config.absolute_error_tolerance}")
                    previous_error = 1e+10  # Reset previous error to a large value
                    self.barrel_elevation = previous_elevation  # Keep the elevation that's closer to zero
                    continue  # Recompute with new tolerances
                # If error is increasing, we are diverging; stop to avoid infinite loop
                # raise ZeroFindingError(zero_error, iterations_count, Angular.Radian(self.barrel_elevation), 'Error non-convergent.')
                break

            previous_distance = current_distance
            previous_error = signed_error
            previous_elevation = self.barrel_elevation

            if zero_error > _cZeroFindingAccuracy or math.fabs(current_distance - zero_distance) > 1:
                # Adjust barrel elevation to close height at zero distance
                self.barrel_elevation += correction
            else:  # Current barrel_elevation hit zero!
                break
            iterations_count += 1
        if zero_error > _cZeroFindingAccuracy:
            return self.find_zero_angle(shot_info, distance)
            # # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            # raise ZeroFindingError(zero_error, iterations_count, Angular.Radian(self.barrel_elevation))
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
            raise RuntimeError("SciPy integration solution have not t_events")

        logger.debug(f"SciPy integration complete with {sol.nfev} function calls.")
        termination_reason = None
        if sol.status == 1:  # A termination event occurred
            if len(sol.t_events) > 0:
                # if sol.t_events[0].size > 0:  # Expected termination event: we reached requested range
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
            if termination_reason is not None and len(t_vals) > 1 and t_vals[0] != t_vals[-1] \
                and (filter_flags != TrajFlag.NONE or len(t_at_x) == 0):  # ... unless we already got one and don't want others
                t_at_x.append(sol.t[-1])  # Last time point
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
