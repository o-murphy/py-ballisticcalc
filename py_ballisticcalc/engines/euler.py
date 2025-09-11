"""Euler integration engine for ballistic trajectory calculations.

The Euler method is a first-order numerical integration technique.  While
less accurate and efficient than higher-order methods like Runge-Kutta,
the Euler method is easy to understand.

Classes:
    EulerIntegrationEngine: Concrete implementation using Euler's method

Key Features:
    - First-order numerical integration
    - Adaptive time stepping based on projectile velocity

Examples:
    >>> from py_ballisticcalc import Calculator
    >>> calc = Calculator(engine="py_ballisticcalc:EulerIntegrationEngine")

Mathematical Background:
    The Euler method approximates the solution to the differential equation
    dy/dt = f(t, y) using the formula:
    
    y(t + h) = y(t) + h * f(t, y(t))
    
    For ballistic calculations, this translates to updating position and
    velocity based on current acceleration values.

See Also:
    py_ballisticcalc.engines.rk4: More accurate RK4 integration
    py_ballisticcalc.engines.velocity_verlet: Energy-conservative integration
    py_ballisticcalc.engines.base_engine.BaseIntegrationEngine: Base class
"""

import math
import warnings

from typing_extensions import Union, List, override

from py_ballisticcalc.conditions import ShotProps
from py_ballisticcalc.engines.base_engine import (
    BaseEngineConfigDict,
    BaseIntegrationEngine,
    TrajectoryDataFilter,
    _WindSock,
)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import BaseTrajData, TrajectoryData, TrajFlag, HitResult
from py_ballisticcalc.vector import Vector

__all__ = ('EulerIntegrationEngine',)


class EulerIntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):
    """Euler integration engine for ballistic trajectory calculations.
    
    Attributes:
        DEFAULT_STEP: Default step size multiplier for integration (0.5).
        integration_step_count: Number of integration steps performed.
        
    Examples:
        >>> config = BaseEngineConfigDict(cMinimumVelocity=100.0)
        >>> engine = EulerIntegrationEngine(config)
    """

    DEFAULT_STEP = 0.5

    def __init__(self, config: BaseEngineConfigDict) -> None:
        """Initialize the Euler integration engine.
        
        Args:
            config: Configuration dictionary containing engine parameters.
                   See BaseEngineConfigDict for available options.
        """
        super().__init__(config)
        self.integration_step_count: int = 0

    @override
    def get_calc_step(self) -> float:
        """Get the base calculation step size for Euler integration.
        
        Calculates the effective step size by combining the base engine
        step multiplier with the Euler-specific DEFAULT_STEP constant.
        The step size directly affects accuracy and performance trade-offs.
        This is a distance-like quantity that is subsequently scaled by velocity
        to produce a time-like integration step.
        
        Returns:
            Base step size for integration calculations.

        Note:
            The step size is calculated as: `cStepMultiplier * DEFAULT_STEP`.
            Smaller step sizes increase accuracy but require more computation.
            The DEFAULT_STEP is sufficient to pass all unit tests.
        """
        return super().get_calc_step() * self.DEFAULT_STEP

    def time_step(self, base_step: float, velocity: float) -> float:
        """Calculate adaptive time step based on current projectile velocity.
        
        Implements adaptive time stepping where the time step is inversely
        related to projectile velocity. This helps maintain numerical stability
        and accuracy as the projectile slows down or speeds up.
        
        Args:
            base_step: Base step size from the integration engine.
            velocity: Current projectile velocity in fps.
            
        Returns:
            Adaptive time step for the current integration step.
            
        Formula:
            time_step = base_step / max(1.0, velocity)
            
        Examples:
            >>> config = BaseEngineConfigDict(cStepMultiplier=0.5)
            >>> engine = EulerIntegrationEngine(config)
            >>> engine.time_step(0.5, 2000.0)
            0.00025
            >>> engine.time_step(0.5, 100.0)
            0.005

        Note:
            The max(1.0, velocity) ensures that the time step never becomes
            excessively large, maintaining numerical stability even at very
            low velocities.
        """
        return base_step / max(1.0, velocity)

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
                for interpolating TrajectoryData.

        Returns:
            HitResult: Object describing the trajectory.
        """
        props.filter_flags = filter_flags
        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = -abs(self._config.cMaximumDrop)  # Ensure it's negative
        _cMinimumAltitude = self._config.cMinimumAltitude

        step_data: List[BaseTrajData] = []  # Data for interpolation (if dense_output is enabled)
        time: float = .0
        drag: float = .0
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

            # region Ballistic calculation step (point-mass)
            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            relative_velocity = velocity_vector - wind_vector
            relative_speed = relative_velocity.magnitude()  # Velocity relative to air
            # Time step is normalized by velocity so that we take smaller steps when moving faster
            delta_time = self.time_step(props.calc_step, relative_speed)
            # Drag is a function of air density and velocity relative to the air
            drag = density_ratio * relative_speed * props.drag_by_mach(relative_speed / mach)
            # Bullet velocity changes due to both drag and gravity
            velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time  # type: ignore[operator]
            # Bullet position changes by velocity time_deltas the time step
            delta_range_vector = velocity_vector * delta_time
            # Update the bullet position
            range_vector += delta_range_vector  # type: ignore[operator]
            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_time
            # endregion

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
        # endregion
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
        logger.debug(f"Euler ran {integration_step_count} iterations")
        self.integration_step_count += integration_step_count
        error = None
        if termination_reason is not None:
            error = RangeError(termination_reason, ranges)
        return HitResult(props, ranges, step_data, filter_flags > 0, error)
