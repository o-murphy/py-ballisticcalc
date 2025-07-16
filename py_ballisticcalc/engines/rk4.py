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
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.vector import Vector

__all__ = ('RK4IntegrationEngine',)


class RK4IntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):

    @override
    def get_calc_step(self, step: float = 0) -> float:
        # RK steps can be larger than calc_step default on Euler integrator
        # min_step ensures that with small record steps the loop runs far enough to get desired points
        # adjust Euler default step to RK4 algorithm
        # NOTE: pow(step, 0.5) recommended by https://github.com/serhiy-yevtushenko
        return super().get_calc_step(step) ** 0.5

    @override
    def _integrate(self, props: _ShotProps, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List[TrajectoryData]:
        """
        Calculate trajectory for specified shot

        Args:
            props (_ShotProps):  Information about the shot.
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
        time: float = .0
        # drag: float = .0

        # guarantee that mach and density_factor would be referenced before assignment
        mach: float = .0
        density_factor: float = .0

        # region Initialize wind-related variables to first wind reading (if any)
        wind_sock = _WindSock(props.winds)
        wind_vector = wind_sock.current_vector()
        # endregion

        # region Initialize velocity and position of projectile
        velocity = props.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -props.cant_cosine * props.sight_height, -props.cant_sine * props.sight_height)
        velocity_vector: Vector = Vector(
            math.cos(props.barrel_elevation_rad) * math.cos(props.barrel_azimuth_rad),
            math.sin(props.barrel_elevation_rad),
            math.cos(props.barrel_elevation_rad) * math.sin(props.barrel_azimuth_rad)
        ).mul_by_const(velocity)  # type: ignore
        # endregion

        min_step = min(props.calc_step, record_step)

        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=record_step,
                                            initial_position=range_vector, initial_velocity=velocity_vector,
                                            barrel_angle_rad=props.barrel_elevation_rad,
                                            look_angle_rad=props.look_angle_rad,
                                            time_step=time_step)

        # region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        termination_reason = None
        last_recorded_range = 0.0
        it = 0  # iteration counter
        while (range_vector.x <= maximum_range + min_step) or (
                last_recorded_range <= maximum_range - 1e-6):
            it += 1

            # Update wind reading at current point in trajectory
            if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            density_factor, mach = props.get_density_and_mach_for_altitude(range_vector.y)

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
            # Time step is normalized by velocity so that we take smaller steps when moving faster
            delta_time = props.calc_step / max(1.0, relative_speed)
            km = density_factor * props.drag_by_mach(relative_speed / mach)
            # drag = km * relative_speed

            # region RK4 integration
            def f(v: Vector) -> Vector:  # dv/dt
                # Bullet velocity changes due to both drag and gravity
                return self.gravity_vector - km * v * v.magnitude()  # type: ignore[operator]

            v1 = delta_time * f(relative_velocity)
            v2 = delta_time * f(relative_velocity + 0.5 * v1)  # type: ignore[operator]
            v3 = delta_time * f(relative_velocity + 0.5 * v2)  # type: ignore[operator]
            v4 = delta_time * f(relative_velocity + v3)  # type: ignore[operator]
            p1 = delta_time * velocity_vector
            p2 = delta_time * (velocity_vector + 0.5 * p1)  # type: ignore[operator]
            p3 = delta_time * (velocity_vector + 0.5 * p2)  # type: ignore[operator]
            p4 = delta_time * (velocity_vector + p3)  # type: ignore[operator]
            velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)  # type: ignore[operator]
            range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)  # type: ignore[operator]
            # endregion RK4 integration

            # region for Reference: Euler integration
            # velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time
            # delta_range_vector = velocity_vector * delta_time
            # range_vector += delta_range_vector
            # endregion Euler integration

            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_time

            if (
                    velocity < _cMinimumVelocity
                    or range_vector.y < _cMaximumDrop
                    or props.alt0 + range_vector.y < _cMinimumAltitude
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
        # Ensure that we have at least two data points in trajectory, or 1 if no filter_flags==NONE
        # ... as well as last point if we had an incomplete trajectory
        if (filter_flags and ((len(ranges) < 2) or termination_reason)) or len(ranges) == 0:
            ranges.append(self._make_row(
                props, time, range_vector, velocity_vector, mach, TrajFlag.NONE)
            )
        logger.debug(f"RK4 ran {it} iterations")
        if termination_reason is not None:
            raise RangeError(termination_reason, ranges)
        return ranges
