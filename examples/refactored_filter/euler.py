# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
import warnings
from typing import Generator, Tuple

from typing_extensions import override

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine, _WindSock, BaseIntegrationState
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
    def _generate_next_state(self, state: BaseIntegrationState):
        """
        Generate trajectory data for a specified shot.

        This method calculates the trajectory step by step and yields
        'GENERATOR_RETURN_TYPE' objects containing various ballistic parameters
        at each step.

        Args:
            state (BaseIntegrationState): An object containing all necessary information about the shot,
                              such as projectile characteristics, initial velocity, and environmental conditions.

        Note:
            This is a generator function, meaning it yields data points iteratively
            rather than returning a complete list. This is useful for processing
            large trajectories efficiently. The exact stopping conditions and step
            logic are implemented within the method's body.
        """

        # region Ballistic calculation step (point-mass)
        # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
        velocity_adjusted = state.velocity_vector - state.wind_vector
        velocity = velocity_adjusted.magnitude()  # Velocity relative to air
        # Time step is normalized by velocity so that we take smaller steps when moving faster
        delta_time = self.calc_step / max(1.0, velocity)
        # Drag is a function of air density and velocity relative to the air
        state.drag = state.density_factor * velocity * self.drag_by_mach(velocity / state.mach)

        # Bullet velocity changes due to both drag and gravity
        state.velocity_vector -= (velocity_adjusted * state.drag - self.gravity_vector) * delta_time  # type: ignore

        # Bullet position changes by velocity time_deltas the time step
        delta_range_vector = state.velocity_vector * delta_time
        # Update the bullet position
        state.range_vector += delta_range_vector  # type: ignore

        state.velocity = state.velocity_vector.magnitude()  # Velocity relative to ground
        state.time += delta_time

        # Update wind reading at current point in trajectory
        if state.range_vector.x >= state.wind_sock.next_range:  # require check before call to improve performance
            state.wind_vector = state.wind_sock.vector_for_range(state.range_vector.x)

        # Update air density at current point in trajectory
        state.density_factor, state.mach = state.shot_info.atmo.get_density_factor_and_mach_for_altitude(
            self.alt0 + state.range_vector.y)

    # @override
    # def _integration_generator(self, shot_info: Shot) -> Generator[
    #     Tuple[float, Vector, Vector, float, float, float, float], None, None]:
    #     """
    #     Generate trajectory data for a specified shot.
    #
    #     This method calculates the trajectory step by step and yields
    #     'GENERATOR_RETURN_TYPE' objects containing various ballistic parameters
    #     at each step.
    #
    #     Args:
    #         shot_info (Shot): An object containing all necessary information about the shot,
    #                           such as projectile characteristics, initial velocity, and environmental conditions.
    #
    #     Yields:
    #         Tuple[float, Vector, Vector, float, float, float, float]: A tuple representing a single
    #         point in the trajectory, with elements in the following order:
    #         1.  **time** (float): The time elapsed since the shot was fired (in seconds).
    #         2.  **range_vector** (Vector): The current position of the projectile as a vector (e.g., in feet).
    #         3.  **velocity_vector** (Vector): The current velocity of the projectile as a vector (e.g., in feet per second).
    #         4.  **velocity** (float): The current velocity magnitude (e.g., in feet per second).
    #         5.  **mach** (float): The current Mach number of the projectile.
    #         6.  **density_factor** (float): A factor representing the air density at the current altitude.
    #         7.  **drag** (float): The drag force acting on the projectile at the current state.
    #
    #     Note:
    #         This is a generator function, meaning it yields data points iteratively
    #         rather than returning a complete list. This is useful for processing
    #         large trajectories efficiently. The exact stopping conditions and step
    #         logic are implemented within the method's body.
    #     """
    #
    #     time: float = .0
    #     drag: float = .0
    #
    #     # guarantee that mach and density_factor would be referenced before assignment
    #     mach: float  # = .0
    #     density_factor: float  # = .0
    #
    #     # region Initialize wind-related variables to first wind reading (if any)
    #     wind_sock = _WindSock(shot_info.winds)
    #     wind_vector = wind_sock.current_vector()
    #     # endregion
    #
    #     # region Initialize velocity and position of projectile
    #     velocity = self.muzzle_velocity
    #     # x: downrange distance, y: drop, z: windage
    #     range_vector = Vector(.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
    #     velocity_vector: Vector = Vector(
    #         math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth),
    #         math.sin(self.barrel_elevation),
    #         math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth)
    #     ).mul_by_const(velocity)  # type: ignore
    #     # endregion
    #
    #     # region Trajectory Loop
    #     warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
    #     while True:
    #
    #         # Update wind reading at current point in trajectory
    #         if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
    #             wind_vector = wind_sock.vector_for_range(range_vector.x)
    #
    #         # Update air density at current point in trajectory
    #         density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(
    #             self.alt0 + range_vector.y)
    #
    #         yield (
    #             time, range_vector, velocity_vector, velocity,
    #             mach, density_factor, drag
    #         )
    #
    #         # region Ballistic calculation step (point-mass)
    #         # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
    #         velocity_adjusted = velocity_vector - wind_vector
    #         velocity = velocity_adjusted.magnitude()  # Velocity relative to air
    #         # Time step is normalized by velocity so that we take smaller steps when moving faster
    #         delta_time = self.calc_step / max(1.0, velocity)
    #         # Drag is a function of air density and velocity relative to the air
    #         drag = density_factor * velocity * self.drag_by_mach(velocity / mach)
    #         # Bullet velocity changes due to both drag and gravity
    #         velocity_vector -= (velocity_adjusted * drag - self.gravity_vector) * delta_time  # type: ignore
    #         # Bullet position changes by velocity time_deltas the time step
    #         delta_range_vector = velocity_vector * delta_time
    #         # Update the bullet position
    #         range_vector += delta_range_vector  # type: ignore
    #         velocity = velocity_vector.magnitude()  # Velocity relative to ground
    #         time += delta_time
