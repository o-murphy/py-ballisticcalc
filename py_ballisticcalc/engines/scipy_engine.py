import math
import warnings
from typing_extensions import Union, Tuple, List, Optional, override
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import root_scalar

from py_ballisticcalc.conditions import Shot, Wind
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine, _TrajectoryDataFilter, create_trajectory_row
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.vector import Vector

__all__ = ('SciPyIntegrationEngine',)


class WindSock():
    """Returns wind vector for an arbitrary location down-range."""
    def __init__(self, winds: Union[Tuple["Wind", ...], None]):
        # winds is a tuple of Wind objects
        # Sort winds by range, ascending
        self.winds = None
        if isinstance(winds, Wind):
            self.winds = [winds]
        elif isinstance(winds, (tuple, list)):
            self.winds = sorted(winds, key=lambda w: w.until_distance.raw_value)

    def wind_at_distance(self, distance: float) -> Optional[Vector]:
        """Returns wind vector at specified distance."""
        if not self.winds:
            return None
        for wind in self.winds:  # TODO: use binary search for performance
            if wind.until_distance.raw_value <= distance:
                return wind.vector
        return self.winds[-1].vector


class SciPyIntegrationEngine(BaseIntegrationEngine):

    @override
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

        mach: float = .0
        drag: float = .0
        density_factor: float = .0
        wind_sock = WindSock(shot_info.winds)

        #region Initialize velocity and position of projectile
        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        # s = [x, y, z, vx, vy, vz]
        s0 = [.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height,
              math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth) * velocity,
              math.sin(self.barrel_elevation) * velocity,
              math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth) * velocity]
        #endregion

        #region SciPy integration
        def diff_eq(t, s):
            """
            Defines the dynamics of the bullet for integration.
            :param t: Time (not used in this case, but required by solve_ivp)
            :param y: State vector [x, y, z, vx, vy, vz]
            :return: Derivative of state vector
            """
            x, y, z = s[:3]
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
        #endregion SciPy integration

        def event_max_range(t, s):  # Stop when x crosses maximum_range
            return s[0] - (maximum_range + 1)  # +1 to ensure we cross the threshold
        event_max_range.terminal = True  # type: ignore[attr-defined]

        max_drop = max(_cMaximumDrop, _cMinimumAltitude - self.alt0)
        def event_max_drop(t, s):  # Stop when y crosses max_drop
            return s[1] - max_drop
        event_max_drop.terminal = True  # type: ignore[attr-defined]

        def event_min_velocity(t, s):  # Stop when velocity < _cMinimumVelocity
            v = np.linalg.norm(s[3:6])
            return v - _cMinimumVelocity
        event_min_velocity.terminal = True  # type: ignore[attr-defined]

        t_max = 50.0  # Arbitrary large time limit to ensure integration completes

        sol = solve_ivp(diff_eq, (0, t_max), s0, method='RK45', dense_output=True,
                        events=[event_max_range, event_max_drop, event_min_velocity])

        #region Process the solution
        # List of distances at which we want to record the trajectory data
        desired_xs = np.arange(0, maximum_range + record_step, record_step)
        # Get x and t arrays from the solution
        x_vals = sol.y[0]
        t_vals = sol.t
        # Interpolate to find the time when each desired x is reached
        t_at_x = np.interp(desired_xs, x_vals, t_vals)
        if sol.sol is not None:
            #region Basic approach to interpolate for desired x values:
            # # This is not very good: distance from requested x varies by ~1% of max_range
            # states_at_x = sol.sol(t_at_x)  # shape: (state_dim, len(desired_xs))
            # for i in range(states_at_x.shape[1]):
            #     t = t_at_x[i]
            #     position = Vector(*states_at_x[0:3, i])  # [x, y, z]
            #     velocity = Vector(*states_at_x[3:6, i])  # [vx, vy, vz]
            #     velocity_magnitude = velocity.magnitude()
            #     density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(self.alt0 + position[1])
            #     ranges.append(create_trajectory_row(t, position, velocity, velocity_magnitude, mach,
            #                                         self.spin_drift(t), self.look_angle,
            #                                         density_factor, drag, self.weight, TrajFlag.RANGE
            #                                         )
            #                  )
            #endregion Basic approach to interpolate for desired x values
            #region Root-finding approach to interpolate for desired x values:
            states_at_x = []
            t_at_x = []
            for x_target in desired_xs:
                idx = np.searchsorted(x_vals, x_target)  # Find bracketing indices for x_target
                if idx < 0 or idx >= len(x_vals):
                    logger.warning(f"Requested distance {x_target} out of bounds computed: [{x_vals[0]}, {x_vals[-1]}]")
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
                    res = root_scalar(x_minus_target, bracket=[t_lo, t_hi], method='brentq', xtol=1e-14, rtol=1e-14)
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
            # Convert to arrays for easier handling
            t_at_x = np.array(t_at_x)
            states_at_x = np.array(states_at_x).T  # shape: (state_dim, num_points)
            for i in range(states_at_x.shape[1]):
                t = t_at_x[i]
                position = Vector(*states_at_x[0:3, i])
                velocity = Vector(*states_at_x[3:6, i])
                velocity_magnitude = velocity.magnitude()
                density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(self.alt0 + position[1])
                ranges.append(create_trajectory_row(
                    t, position, velocity, velocity_magnitude, mach,
                    self.spin_drift(t), self.look_angle,
                    density_factor, drag, self.weight, TrajFlag.RANGE
                ))
            #endregion Root-finding approach to interpolate for desired x values
        else:
            logger.warning("No solution found by SciPy integration.")
        #endregion Process the solution

        # if (
        #         velocity < _cMinimumVelocity
        #         or range_vector.y < _cMaximumDrop
        #         or self.alt0 + range_vector.y < _cMinimumAltitude
        # ):
        #     ranges.append(create_trajectory_row(
        #         time, range_vector, velocity_vector,
        #         velocity, mach, self.spin_drift(time), self.look_angle,
        #         density_factor, drag, self.weight, data_filter.current_flag
        #     ))
        #     if velocity < _cMinimumVelocity:
        #         reason = RangeError.MinimumVelocityReached
        #     elif range_vector.y < _cMaximumDrop:
        #         reason = RangeError.MaximumDropReached
        #     else:
        #         reason = RangeError.MinimumAltitudeReached
        #     raise RangeError(reason, ranges)
        #     # break
        logger.debug(f"Done scipy integration")
        return ranges
