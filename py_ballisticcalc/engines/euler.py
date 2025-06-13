# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
import warnings

from typing_extensions import Union, List, override

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.engines.base_engine import (BaseIntegrationEngine, _TrajectoryDataFilter,
                                                  _WindSock, create_trajectory_row)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.vector import Vector

__all__ = ('EulerIntegrationEngine',)


# pylint: disable=too-many-instance-attributes
class EulerIntegrationEngine(BaseIntegrationEngine):
    """
    All calculations are done in units of feet and fps.

    Attributes:
        barrel_azimuth (float): The azimuth angle of the barrel.
        barrel_elevation (float): The elevation angle of the barrel.
        twist (float): The twist rate of the barrel.
        gravity_vector (Vector): The gravity vector.
    """

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
        time: float = .0
        drag: float = .0

        # guarantee that mach and density_factor would be referenced before assignment
        mach: float = .0
        density_factor: float = .0

        # region Initialize wind-related variables to first wind reading (if any)
        wind_sock = _WindSock(shot_info.winds)
        wind_vector = wind_sock.current_vector()
        # endregion

        # region Initialize velocity and position of projectile
        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
        velocity_vector: Vector = Vector(
            math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth),
            math.sin(self.barrel_elevation),
            math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth)
        ).mul_by_const(velocity)  # type: ignore
        # endregion

        # min_step is used to handle situation, when record step is smaller than calc_step
        # in order to prevent range breaking too early
        min_step = min(self.calc_step, record_step)
        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=record_step,
                                            initial_position=range_vector, initial_velocity=velocity_vector,
                                            time_step=time_step)
        data_filter.setup_seen_zero(range_vector.y, self.barrel_elevation, self.look_angle)

        # region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        last_recorded_range = 0.0
        it = 0  # iteration counter
        while (range_vector.x <= maximum_range + min_step) or (
                filter_flags and last_recorded_range <= maximum_range - 1e-6):
            it += 1

            # Update wind reading at current point in trajectory
            if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(
                self.alt0 + range_vector.y)

            # region Check whether to record TrajectoryData row at current point
            if filter_flags:  # require check before call to improve performance

                # Record TrajectoryData row
                if (data := data_filter.should_record(range_vector, velocity_vector, mach, time)) is not None:
                    ranges.append(create_trajectory_row(data.time, data.position, data.velocity,
                                                        data.velocity.magnitude(), data.mach,
                                                        self.spin_drift(data.time), self.look_angle,
                                                        density_factor, drag, self.weight, data_filter.current_flag
                                                        ))
                    last_recorded_range = data.position.x
            # endregion

            # region Ballistic calculation step (point-mass)
            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            velocity_adjusted = velocity_vector - wind_vector
            velocity = velocity_adjusted.magnitude()  # Velocity relative to air
            # Time step is normalized by velocity so that we take smaller steps when moving faster
            delta_time = self.calc_step / max(1.0, velocity)
            # Drag is a function of air density and velocity relative to the air
            drag = density_factor * velocity * self.drag_by_mach(velocity / mach)
            # Bullet velocity changes due to both drag and gravity
            velocity_vector -= (velocity_adjusted * drag - self.gravity_vector) * delta_time  # type: ignore
            # Bullet position changes by velocity time_deltas the time step
            delta_range_vector = velocity_vector * delta_time
            # Update the bullet position
            range_vector += delta_range_vector  # type: ignore
            velocity = velocity_vector.magnitude()  # Velocity relative to ground
            time += delta_time

            if (
                    velocity < _cMinimumVelocity
                    or range_vector.y < _cMaximumDrop
                    or self.alt0 + range_vector.y < _cMinimumAltitude
            ):
                ranges.append(create_trajectory_row(
                    time, range_vector, velocity_vector,
                    velocity, mach, self.spin_drift(time), self.look_angle,
                    density_factor, drag, self.weight, data_filter.current_flag
                ))
                if velocity < _cMinimumVelocity:
                    reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    reason = RangeError.MaximumDropReached
                else:
                    reason = RangeError.MinimumAltitudeReached
                raise RangeError(reason, ranges)
                # break
            # endregion
        # endregion
        # Ensure that we have at least two data points in trajectory
        if len(ranges) < 2:
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity, mach, self.spin_drift(time), self.look_angle,
                density_factor, drag, self.weight, TrajFlag.NONE))
        logger.debug(f"euler py it {it}")
        return ranges
