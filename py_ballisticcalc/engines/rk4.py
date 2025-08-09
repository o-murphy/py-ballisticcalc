import math
import warnings

from typing_extensions import Union, List, override

from py_ballisticcalc.engines.base_engine import (
    BaseIntegrationEngine,
    BaseEngineConfigDict,
    _TrajectoryDataFilter,
    _WindSock,
    _ShotProps
)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import HitResult, TrajectoryData, TrajFlag
from py_ballisticcalc.vector import Vector

__all__ = ('RK4IntegrationEngine',)


class RK4IntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):
    """Runge-Kutta 4th order integration engine for ballistic calculations."""
    # TODO: This can be increased as soon as TrajectoryDataFilter can interpolate for more than
    #   one point between .should_record() calls.  At DEFAULT_TIME_STEP=0.005 it doesn't generate
    #   a RANGE record for every yard and this fails test_danger_space.py::test_danger_space.
    DEFAULT_TIME_STEP = 0.0015

    def __init__(self, config: BaseEngineConfigDict):
        super().__init__(config)
        self.integration_step_count = 0
        self.trajectory_count = 0  # Number of trajectories calculated

    @override
    def get_calc_step(self) -> float:
        return super().get_calc_step() * self.DEFAULT_TIME_STEP

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
        self.trajectory_count += 1
        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = -abs(self._config.cMaximumDrop)  # Ensure it's negative
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: List[TrajectoryData] = []  # Record of TrajectoryData points to return
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
        # endregion

        min_step = min(props.calc_step, range_step_ft)

        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=range_step_ft,
                                            initial_position=range_vector, initial_velocity=velocity_vector,
                                            barrel_angle_rad=props.barrel_elevation_rad,
                                            look_angle_rad=props.look_angle_rad,
                                            time_step=time_step
        )

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
        # endregion Trajectory Loop
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
        logger.debug(f"RK4 ran {self.integration_step_count - start_integration_step_count} iterations")
        error = None
        if termination_reason is not None:
            error = RangeError(termination_reason, ranges)
        return HitResult(props.shot, ranges, filter_flags > 0, error)
