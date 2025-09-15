"""Velocity Verlet integration engine for ballistic trajectory calculations.

The Velocity Verlet algorithm is a symplectic integrator that conserves energy in physical systems.

Classes:
    VelocityVerletIntegrationEngine: Concrete implementation using Velocity Verlet method

Examples:
    >>> from py_ballisticcalc import Calculator
    >>> calc = Calculator(engine="py_ballisticcalc:VelocityVerletIntegrationEngine")

Mathematical Background:
    The Velocity Verlet method updates position and velocity using:
    ```
    x(t + dt) = x(t) + v(t)*dt + 0.5*a(t)*dt²
    v(t + dt) = v(t) + 0.5*[a(t) + a(t + dt)]*dt
    ```
    This approach ensures that position and velocity remain synchronized
    and that the total energy of the system is conserved over long periods.

Algorithm Properties:
    - Order: 2 (local truncation error is O(h³))
    - Symplectic: Preserves the symplectic structure of Hamiltonian systems
    - Time-reversible: Running the algorithm backward recovers original state
    - Energy-conserving: Total energy is preserved over long integration periods
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

__all__ = ('VelocityVerletIntegrationEngine',)


class VelocityVerletIntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):
    """Velocity Verlet integration engine for ballistic trajectory calculations.
    
    Algorithm Details:
        The method uses a two-stage approach:
            1. Update position using current velocity and acceleration.
            2. Update velocity using average of current and new acceleration.
        This ensures velocity and position remain properly synchronized
        and conserves the total energy of the system.
    
    Attributes:
        DEFAULT_TIME_STEP: Default time step multiplier.
        integration_step_count: Number of integration steps performed.
        
    See Also:
        - RK4IntegrationEngine: Higher accuracy alternative
        - EulerIntegrationEngine: Simpler alternative
        - SciPyIntegrationEngine: Adaptive methods
    """

    DEFAULT_TIME_STEP = 0.0005

    def __init__(self, config: BaseEngineConfigDict) -> None:
        """Initialize the Velocity Verlet integration engine.
        
        Args:
            config: Configuration dictionary containing engine parameters.
                   See BaseEngineConfigDict for available options.
                   
        Examples:
            >>> config = BaseEngineConfigDict(
            ...     cStepMultiplier=0.5,
            ...     cMinimumVelocity=10.0
            ... )
            >>> engine = VelocityVerletIntegrationEngine(config)
        """
        super().__init__(config)
        self.integration_step_count: int = 0

    @override
    def get_calc_step(self) -> float:
        """Get the calculation step size for Velocity Verlet integration.
        
        Combines the base engine step multiplier with the Verlet-specific
        DEFAULT_TIME_STEP to determine the effective integration step size.
        
        Returns:
            Effective step size for Velocity Verlet integration.
            
        Formula:
            step_size = base_step_multiplier × DEFAULT_TIME_STEP
            
        Note:
            The small DEFAULT_TIME_STEP value is chosen to ensure
            that this engine can pass all unit tests, despite most of them
            being highly dissipative rather than conservative of energy.
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
            dense_output: If True, HitResult will save BaseTrajData at each integration step.

        Returns:
            HitResult: Object describing the trajectory.
        """
        props.filter_flags = filter_flags
        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = -abs(self._config.cMaximumDrop)  # Ensure it's negative
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: List[TrajectoryData] = []  # Record of TrajectoryData points to return
        step_data: List[BaseTrajData] = []  # Data for interpolation (if dense_output is enabled)
        time: float = .0
        drag: float = .0
        mach: float = .0
        density_ratio: float = .0

        # region Initialize wind-related variables to first wind reading (if any)
        wind_sock = _WindSock(props.winds)
        wind_vector = wind_sock.current_vector()
        # endregion

        # region Initialize position, velocity, and acceleration
        relative_speed = props.muzzle_velocity_fps
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -props.cant_cosine * props.sight_height_ft, -props.cant_sine * props.sight_height_ft)
        velocity_vector: Vector = Vector(
            math.cos(props.barrel_elevation_rad) * math.cos(props.barrel_azimuth_rad),
            math.sin(props.barrel_elevation_rad),
            math.cos(props.barrel_elevation_rad) * math.sin(props.barrel_azimuth_rad)
        ).mul_by_const(relative_speed)  # type: ignore
        _cMaximumDrop += min(0, range_vector.y)  # Adjust max drop downward if above muzzle height
        # Acceleration:
        density_ratio, mach = props.get_density_and_mach_for_altitude(range_vector.y)
        relative_velocity = velocity_vector - wind_vector
        relative_speed = relative_velocity.magnitude()
        drag = density_ratio * relative_speed * props.drag_by_mach(relative_speed / mach)
        acceleration_vector = self.gravity_vector - drag * relative_velocity  # type: ignore[operator]
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
            delta_time = props.calc_step
            # Drag is a function of air density and velocity relative to the air
            drag = density_ratio * relative_speed * props.drag_by_mach(relative_speed / mach)

            # region Verlet integration
            # 1. Update position using acceleration from the current step
            range_vector += (velocity_vector * delta_time +                           # type: ignore[operator]
                             acceleration_vector * delta_time * delta_time * 0.5)     # type: ignore[operator]
            # 2. Calculate the new acceleration a(t+Δt) at the new position
            new_acceleration_vector = self.gravity_vector - drag * relative_velocity  # type: ignore[operator]
            # 3. Update velocity using the average of the old a(t) and new a(t+Δt) accelerations
            velocity_vector += (acceleration_vector + new_acceleration_vector) * 0.5 * delta_time  # type: ignore
            acceleration_vector = new_acceleration_vector
            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_time
            # endregion Verlet integration
            # endregion ballistic calculation step

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
        logger.debug(f"Velocity Verlet ran {integration_step_count} iterations")
        self.integration_step_count += integration_step_count
        error = None
        if termination_reason is not None:
            error = RangeError(termination_reason, ranges)
        return HitResult(props, ranges, step_data, filter_flags > 0, error)
