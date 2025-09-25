"""Runge-Kutta 4th order integration engine for ballistic trajectory calculations.

The RK4 method is the default integration engine for py_ballisticcalc due to its
optimal balance of accuracy, stability, and performance.

Classes:
    RK4IntegrationEngine: Concrete implementation using 4th-order Runge-Kutta

Examples:
    >>> # Use with Calculator (default engine)
    >>> from py_ballisticcalc import Calculator
    >>> calc = Calculator()  # Uses RK4 by default

Mathematical Background:
    The RK4 method approximates the solution to dy/dt = f(t, y) using:
    
    k₁ = h * f(tₙ, yₙ)
    k₂ = h * f(tₙ + h/2, yₙ + k₁/2)
    k₃ = h * f(tₙ + h/2, yₙ + k₂/2)
    k₄ = h * f(tₙ + h, yₙ + k₃)
    
    yₙ₊₁ = yₙ + (k₁ + 2k₂ + 2k₃ + k₄)/6
    
    This provides fourth-order accuracy, meaning the local truncation error
    is proportional to h⁵ (where h is the step size).

Algorithm Properties:
    - Order: 4 (local truncation error is O(h⁵))
    - Explicit method: No equation solving required
    - Four function evaluations per step
    - Fixed step size (not adaptive)

See Also:
    py_ballisticcalc.engines.euler: Simpler but less accurate method
    py_ballisticcalc.engines.scipy_engine: Adaptive high-precision methods
    py_ballisticcalc.engines.velocity_verlet: Energy-conservative method
    py_ballisticcalc.engines.base_engine.BaseIntegrationEngine: Base class
"""

import math
import warnings

from typing_extensions import Union, List, override

from py_ballisticcalc.conditions import ShotProps
from py_ballisticcalc.engines.base_engine import (
    BaseIntegrationEngine,
    BaseEngineConfigDict,
    TrajectoryDataFilter,
    _WindSock,
)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import BaseTrajData, TrajectoryData, TrajFlag, HitResult
from py_ballisticcalc.vector import Vector

__all__ = ('RK4IntegrationEngine',)


class RK4IntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):
    """Runge-Kutta 4th order integration engine for ballistic trajectory calculations.
    
    Attributes:
        integration_step_count: Number of integration steps performed.

    Examples:
        >>> config = BaseEngineConfigDict(cMinimumVelocity=0.0)
        >>> engine = RK4IntegrationEngine(config)
    """

    DEFAULT_TIME_STEP = 0.0025

    def __init__(self, config: BaseEngineConfigDict) -> None:
        """Initialize the RK4 integration engine.
        
        Args:
            config: Configuration dictionary containing engine parameters.
                   See BaseEngineConfigDict for available options.
                   Common settings include cStepMultiplier for accuracy control
                   and cMinimumVelocity for termination conditions.

        Examples:
            >>> precise_config = BaseEngineConfigDict(
            ...     cStepMultiplier=0.5,  # Smaller steps
            ...     cMinimumVelocity=20.0  # Continue to lower velocities
            ... )
            >>> precise_engine = RK4IntegrationEngine(precise_config)
        """
        super().__init__(config)
        self.integration_step_count: int = 0
        self.trajectory_count = 0  # Number of trajectories calculated

    @override
    def get_calc_step(self) -> float:
        """Get the calculation step size for RK4 integration.
        
        Returns:
            Time-step size (in seconds) for integration calculations.
            
        Mathematical Context:
            The step size directly affects the accuracy and computational cost:
            - Smaller steps: Higher accuracy, more computation
            - Larger steps: Lower accuracy, faster computation
            - RK4's O(h⁵) error means accuracy improves rapidly with smaller h
            
        Examples:
            >>> config = BaseEngineConfigDict(cStepMultiplier=0.5)
            >>> engine = RK4IntegrationEngine(config)
            >>> engine.get_calc_step()
            0.00125
            
        Note:
            For RK4, the relationship between step size and accuracy is:
            - Halving the step size reduces error by ~32× (2⁵)
            - Default step size is sufficient to pass unit tests.
        """
        return super().get_calc_step() * self.DEFAULT_TIME_STEP

    @override
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
                enabling accurate interpolation of TrajectoryData points.

        Returns:
            HitResult: Object describing the trajectory.
        """
        self.trajectory_count += 1
        props.filter_flags = filter_flags
        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = -abs(self._config.cMaximumDrop)  # Ensure it's negative
        _cMinimumAltitude = self._config.cMinimumAltitude

        step_data: List[BaseTrajData] = []  # Data for interpolation (if dense_output is enabled)
        time: float = .0
        mach: float = .0
        density_ratio: float = .0

        # region Initialize wind-related variables to first wind reading (if any)
        wind_sock = _WindSock(props.winds)
        wind_vector = wind_sock.current_vector()
        # endregion

        # region Initialize velocity and position of projectile
        velocity = props.muzzle_velocity_fps
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -props.cant_cosine * props.sight_height_ft, -props.cant_sine * props.sight_height_ft)
        velocity_vector: Vector = Vector(
            math.cos(props.barrel_elevation_rad) * math.cos(props.barrel_azimuth_rad),
            math.sin(props.barrel_elevation_rad),
            math.cos(props.barrel_elevation_rad) * math.sin(props.barrel_azimuth_rad)
        ).mul_by_const(velocity)  # type: ignore
        _cMaximumDrop += min(0, range_vector.y)  # Adjust max drop downward if above muzzle height
        # endregion

        data_filter = TrajectoryDataFilter(props=props, filter_flags=filter_flags,
                                    initial_position=range_vector, initial_velocity=velocity_vector,
                                    barrel_angle_rad=props.barrel_elevation_rad, look_angle_rad=props.look_angle_rad,
                                    range_limit=range_limit_ft, range_step=range_step_ft, time_step=time_step
        )

        # region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        termination_reason = None
        integration_step_count = 0
        # Cubic interpolation requires 3 points, so we will need at least 3 steps
        while (range_vector.x <= range_limit_ft) or integration_step_count < 3:
            integration_step_count += 1

            # Update wind reading at current point in trajectory
            if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            density_ratio, mach = props.get_density_and_mach_for_altitude(range_vector.y)

            # region Record current step
            data = BaseTrajData(time=time, position=range_vector, velocity=velocity_vector, mach=mach)
            data_filter.record(data)
            if dense_output:
                step_data.append(data)
            # endregion

            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            relative_velocity = velocity_vector - wind_vector
            relative_speed = relative_velocity.magnitude()  # Velocity relative to air
            delta_time = props.calc_step
            k_m = density_ratio * props.drag_by_mach(relative_speed / mach)
            # drag = k_m * relative_speed  # This is the "drag rate." Multiply by velocity to get "drag acceleration."

            # region RK4 integration
            def f(v: Vector) -> Vector:  # dv/dt (acceleration)
                # Bullet velocity changes due to both drag and gravity
                return self.gravity_vector - k_m * v * v.magnitude()  # type: ignore[operator]

            v1 = f(relative_velocity)
            v2 = f(relative_velocity + 0.5 * delta_time * v1)  # type: ignore[operator]
            v3 = f(relative_velocity + 0.5 * delta_time * v2)  # type: ignore[operator]
            v4 = f(relative_velocity + delta_time * v3)  # type: ignore[operator]
            p1 = velocity_vector
            p2 = velocity_vector + 0.5 * delta_time * v1  # type: ignore[operator]
            p3 = velocity_vector + 0.5 * delta_time * v2  # type: ignore[operator]
            p4 = velocity_vector + delta_time * v3  # type: ignore[operator]
            velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (delta_time / 6.0)  # type: ignore[operator]
            range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (delta_time / 6.0)  # type: ignore[operator]
            # endregion RK4 integration

            # region for Reference: Euler integration
            # velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time
            # delta_range_vector = velocity_vector * delta_time
            # range_vector += delta_range_vector
            # endregion Euler integration

            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_time

            if (velocity < _cMinimumVelocity
                or (velocity_vector.y <= 0 and range_vector.y < _cMaximumDrop)
                or (velocity_vector.y <= 0 and props.alt0_ft + range_vector.y < _cMinimumAltitude)
            ):
                if velocity < _cMinimumVelocity:
                    termination_reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    termination_reason = RangeError.MaximumDropReached
                else:
                    termination_reason = RangeError.MinimumAltitudeReached
                break
        # endregion Trajectory Loop
        data = BaseTrajData(time=time, position=range_vector, velocity=velocity_vector, mach=mach)
        data_filter.record(data)
        if dense_output:
            step_data.append(data)
        # Ensure that we have at least two data points in trajectory,
        # ... as well as last point if we had an incomplete trajectory
        ranges = data_filter.records
        if (filter_flags and ((len(ranges) < 2) or termination_reason)) or len(ranges) == 1:
            if len(ranges) > 0 and ranges[-1].time == time:  # But don't duplicate the last point.
                pass
            else:
                ranges.append(TrajectoryData.from_props(
                    props, time, range_vector, velocity_vector, mach, TrajFlag.NONE)
                )
        logger.debug(f"RK4 ran {integration_step_count} iterations")
        self.integration_step_count += integration_step_count
        error = None
        if termination_reason is not None:
            error = RangeError(termination_reason, ranges)
        return HitResult(props, ranges, step_data, filter_flags > 0, error)
