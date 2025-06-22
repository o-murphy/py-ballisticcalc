# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
import warnings
from dataclasses import dataclass, field
from typing import Optional, Generator, Tuple

from typing_extensions import Union, List, override

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.engines.base_engine import (
    BaseIntegrationEngine,
    _TrajectoryDataFilter,
    _WindSock,
    # create_trajectory_row,
    _new_feet, _new_lb, _new_rad, _new_ft_lb, _new_fps,
    calculate_energy, get_correction, calculate_ogw
)
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
        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = self._config.cMaximumDrop
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: List[TrajectoryData] = []  # Record of TrajectoryData points to return
        data_filter: Optional[_TrajectoryDataFilter] = None

        # min_step is used to handle situation, when record step is smaller than calc_step
        # in order to prevent range breaking too early
        min_step = min(self.calc_step, record_step)
        last_recorded_range = 0.0

        data_point = None
        range_error_reason = None

        def is_done():
            nonlocal min_step
            return (range_vector.x > maximum_range + min_step) or (
                    filter_flags and last_recorded_range > maximum_range - 1e-6)

        def is_range_error():
            if velocity < _cMinimumVelocity:
                return RangeError.MinimumVelocityReached
            elif range_vector.y < _cMaximumDrop:
                return RangeError.MaximumDropReached
            elif self.alt0 + range_vector.y < _cMinimumAltitude:
                return RangeError.MinimumAltitudeReached

        gen = self._generate(shot_info)
        data_point = next(gen)
        (time, range_vector, velocity_vector, velocity, mach, density_factor, drag) = data_point
        it = 1
        # for it, data_point in enumerate(gen := self._generate(shot_info)):
        while True:
            if is_done():
                break

            if range_error_reason := is_range_error():
                break

            if filter_flags:  # require check before call to improve performance

                if not data_filter:
                    # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
                    data_filter = _TrajectoryDataFilter(
                        filter_flags=filter_flags, range_step=record_step,
                        initial_position=range_vector,
                        initial_velocity=velocity_vector,
                        time_step=time_step)
                    data_filter.setup_seen_zero(range_vector.y, self.barrel_elevation, self.look_angle)

                # region Check whether to record TrajectoryData row at current point

                # Record TrajectoryData row
                if (data := data_filter.should_record(range_vector, velocity_vector, mach, time)) is not None:
                    ranges.append(self.create_trajectory_row(
                        data.time, data.position, data.velocity, data.velocity.magnitude(),
                        data.mach, density_factor, drag, data_filter.current_flag
                    ))
                    last_recorded_range = data.position.x
                # endregion

            data_point = next(gen)
            (time, range_vector, velocity_vector, velocity, mach, density_factor, drag) = data_point


        # Ensure that we have at least two data points in trajectory
        if range_error_reason or len(ranges) < 2:
            (time, range_vector, velocity_vector, velocity, mach, density_factor, drag) = data_point
            ranges.append(self.create_trajectory_row(
                time, range_vector, velocity_vector, velocity,
                mach, density_factor, drag, TrajFlag.NONE
            ))

        if range_error_reason:
            raise RangeError(range_error_reason, ranges)

        logger.debug(f"euler py it {it}")
        return ranges

    # @override
    def _generate(self, shot_info: Shot) -> Generator[
        Tuple[float, Vector, Vector, float, float, float, float], None, None]:

        """
        Generate trajectory data for a specified shot.

        This method calculates the trajectory step by step and yields
        'GENERATOR_RETURN_TYPE' objects containing various ballistic parameters
        at each step.

        Args:
            shot_info (Shot): An object containing all necessary information about the shot,
                              such as projectile characteristics, initial velocity, and environmental conditions.

        Yields:
            Tuple[float, Vector, Vector, float, float, float, float]: A tuple representing a single
            point in the trajectory, with elements in the following order:
            1.  **time** (float): The time elapsed since the shot was fired (in seconds).
            2.  **range_vector** (Vector): The current position of the projectile as a vector (e.g., in feet).
            3.  **velocity_vector** (Vector): The current velocity of the projectile as a vector (e.g., in feet per second).
            4.  **velocity** (float): The current velocity magnitude (e.g., in feet per second).
            5.  **mach** (float): The current Mach number of the projectile.
            6.  **density_factor** (float): A factor representing the air density at the current altitude.
            7.  **drag** (float): The drag force acting on the projectile at the current state.

        Note:
            This is a generator function, meaning it yields data points iteratively
            rather than returning a complete list. This is useful for processing
            large trajectories efficiently. The exact stopping conditions and step
            logic are implemented within the method's body.
        """

        time: float = .0
        drag: float = .0

        # guarantee that mach and density_factor would be referenced before assignment
        mach: float  # = .0
        density_factor: float  # = .0

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

        # region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        while True:

            # Update wind reading at current point in trajectory
            if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(
                self.alt0 + range_vector.y)

            yield (
                time, range_vector, velocity_vector, velocity,
                mach, density_factor, drag
            )

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

    def create_trajectory_row(self, time: float, range_vector: Vector, velocity_vector: Vector,
                              velocity: float,
                              mach: float,
                              density_factor: float, drag: float,
                              flag: Union[TrajFlag, int]) -> TrajectoryData:

        """
        Creates a TrajectoryData object representing a single row of trajectory data.

        Args:
            time (float): Time of flight.
            range_vector (Vector): Position vector.
            velocity_vector (Vector): Velocity vector.
            velocity (float): Velocity magnitude.
            mach (float): Mach number.
            density_factor (float): Density factor.
            drag (float): Drag value.
            flag (Union[TrajFlag, int]): Flag value.

        Returns:
            TrajectoryData: A TrajectoryData object representing the trajectory data.
        """
        spin_drift = self.spin_drift(time)
        windage = range_vector.z + spin_drift
        drop_adjustment = get_correction(range_vector.x, range_vector.y)
        windage_adjustment = get_correction(range_vector.x, windage)
        trajectory_angle = math.atan2(velocity_vector.y, velocity_vector.x)

        return TrajectoryData(
            time=time,
            distance=_new_feet(range_vector.x),
            velocity=_new_fps(velocity),
            mach=velocity / mach,
            height=_new_feet(range_vector.y),
            target_drop=_new_feet(
                (range_vector.y - range_vector.x * math.tan(self.look_angle)) * math.cos(self.look_angle)),
            drop_adj=_new_rad(drop_adjustment - (self.look_angle if range_vector.x else 0)),
            windage=_new_feet(windage),
            windage_adj=_new_rad(windage_adjustment),
            look_distance=_new_feet(range_vector.x / math.cos(self.look_angle)),
            angle=_new_rad(trajectory_angle),
            density_factor=density_factor - 1,
            drag=drag,
            energy=_new_ft_lb(calculate_energy(self.weight, velocity)),
            ogw=_new_lb(calculate_ogw(self.weight, velocity)),
            flag=flag
        )
