# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
import warnings

from typing_extensions import Union, List, override

from py_ballisticcalc.engines.base_engine import (
    BaseIntegrationEngine,
    _TrajectoryDataFilter,
    _WindSock,
    BaseEngineConfigDict, _ShotProps
)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag, HitResult
from py_ballisticcalc.vector import Vector

__all__ = ('EulerIntegrationEngine',)


class EulerIntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):
    """Euler integration engine for ballistic calculations."""
    DEFAULT_STEP = 0.5

    def __init__(self, config: BaseEngineConfigDict):
        super().__init__(config)
        self.integration_step_count = 0

    @override
    def get_calc_step(self) -> float:
        return super().get_calc_step() * self.DEFAULT_STEP

    def time_step(self, base_step: float, velocity: float) -> float:
        """Calculate time step based on current projectile speed."""
        return base_step / max(1.0, velocity)

    @override
    def _integrate(self, props: _ShotProps, range_limit_ft: float, range_step_ft: float,
                   time_step: float = 0.0, filter_flags: Union[TrajFlag, int] = TrajFlag.NONE,
                   dense_output: bool = False, **kwargs) -> HitResult:
        """
        Creates HitResult for the specified shot.

        Args:
            props (Shot): Information specific to the shot.
            range_limit_ft (float): Feet down-range to stop calculation.
            range_step_ft (float): Frequency (in feet down-range) to record TrajectoryData.
            filter_flags (Union[TrajFlag, int]): Bitfield for trajectory points of interest to record.
            time_step (float, optional): If > 0 then record TrajectoryData after this many seconds elapse
                since last record, as could happen when trajectory is nearly vertical and there is too little
                movement down-range to trigger a record based on range.  (Defaults to 0.0)
            dense_output (bool, optional): If True, HitResult will save BaseTrajData at each integration step,
                for interpolating TrajectoryData.

        Returns:
            HitResult: Object describing the trajectory.
        """
        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = -abs(self._config.cMaximumDrop)  # Ensure it's negative
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: List[TrajectoryData] = []  # Record of TrajectoryData points to return
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
        # endregion

        # Ensure one iteration when record step is smaller than calc_step
        min_step = min(props.calc_step, range_step_ft)

        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=range_step_ft,
                                            initial_position=range_vector, initial_velocity=velocity_vector,
                                            barrel_angle_rad=props.barrel_elevation_rad,
                                            look_angle_rad=props.look_angle_rad,
                                            time_step=time_step)

        # region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        termination_reason = None
        last_recorded_range = 0.0
        start_integration_step_count = self.integration_step_count
        while (range_vector.x <= range_limit_ft + min_step) or (
                last_recorded_range <= range_limit_ft - 1e-6):
            self.integration_step_count += 1

            # Update wind reading at current point in trajectory
            if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            density_ratio, mach = props.get_density_and_mach_for_altitude(range_vector.y)

            # region Check whether to record TrajectoryData row at current point
            if (data := data_filter.should_record(range_vector, velocity_vector, mach, time)) is not None:
                ranges.append(self._make_row(
                    props, data.time, data.position, data.velocity, data.mach, data_filter.current_flag)
                )
                last_recorded_range = data.position.x
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
                or range_vector.y < _cMaximumDrop
                or props.alt0_ft + range_vector.y < _cMinimumAltitude
            ):
                if velocity < _cMinimumVelocity:
                    termination_reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    termination_reason = RangeError.MaximumDropReached
                else:
                    termination_reason = RangeError.MinimumAltitudeReached
                break
        # endregion
        if (data := data_filter.should_record(range_vector, velocity_vector, mach, time)) is not None:
            ranges.append(self._make_row(
                props, data.time, data.position, data.velocity, data.mach, data_filter.current_flag)
            )
        # Ensure that we have at least two data points in trajectory, or 1 if filter_flags==NONE
        # ... as well as last point if we had an incomplete trajectory
        if (filter_flags and ((len(ranges) < 2) or termination_reason)) or len(ranges) == 0:
            if len(ranges) > 0 and ranges[-1].time == time:  # But don't duplicate the last point.
                pass
            else:
                ranges.append(self._make_row(
                    props, time, range_vector, velocity_vector, mach, TrajFlag.NONE)
                )
        logger.debug(f"Euler ran {self.integration_step_count - start_integration_step_count} iterations")
        error = None
        if termination_reason is not None:
            error = RangeError(termination_reason, ranges)
        return HitResult(props.shot, ranges, filter_flags > 0, error)
