# Refactored IntegrationEngine with scipy-like event logic
import logging
import math
from dataclasses import dataclass
from typing import Optional, List, NamedTuple, Any, Union, Callable, Literal

from typing_extensions import override

from py_ballisticcalc import logger
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.engines.base_engine import (
    BaseIntegrationEngine,
    BaseEngineConfigDict,
    _WindSock,
    _new_feet,
    _new_fps,
    _new_rad,
    _new_ft_lb,
    _new_lb,
    calculate_energy,
    calculate_ogw,
    get_correction,
)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.vector import Vector


logger.setLevel(logging.DEBUG)


class TrajectoryState(NamedTuple):
    """Minimal data for one point in ballistic trajectory"""

    time: float
    position: Vector
    velocity: Vector
    mach_fps: float


IntegratorEventFunc = Callable[[TrajectoryState, Any], float]

MAX_ITERATIONS_LIMIT = 1e6


@dataclass(unsafe_hash=True)
class IntegratorEvent:
    """
    Protocol for event functions.
    Event functions should return a scalar value, where a zero-crossing indicates an event.
    """

    func: IntegratorEventFunc
    terminal: bool = False
    direction: Literal[-1, 0, 1] = 0
    flag: Union[TrajFlag, int] = TrajFlag.NONE

    def __call__(self, s: TrajectoryState, **kwargs) -> float:
        return self.func(s, **kwargs)


def integrator_event(
    terminal: bool = False,
    direction: Literal[-1, 0, 1] = 0,
    flag: Union[TrajFlag, int] = TrajFlag.NONE,
) -> Callable[[IntegratorEventFunc], IntegratorEvent]:
    def decorator(func: IntegratorEventFunc) -> IntegratorEvent:
        return IntegratorEvent(func, terminal, direction, flag)

    return decorator


# --- Event Functions ---
# These functions define the conditions for various events.
# They should return a value that crosses zero when the event occurs.


@integrator_event(terminal=False, flag=TrajFlag.ZERO)
def zero_crossing_event(state: TrajectoryState, look_angle=float) -> float:
    """Returns the elevation relative to the line of sight. The event occurs when the value is 0."""
    reference_height = state.position.x * math.tan(look_angle)
    return state.position.y - reference_height


@integrator_event(terminal=False, flag=TrajFlag.MACH)
def mach_crossing_event(state: TrajectoryState) -> float:
    """Returns (speed - Mach). The event occurs when the value is 0 (passing Mach 1)."""
    return state.velocity.magnitude() - state.mach_fps


@integrator_event(terminal=False, direction=-1, flag=TrajFlag.APEX)
def apex_event(state: TrajectoryState) -> float:
    """Returns the vertical component of the velocity. The event occurs when the value is 0 (vertex)."""
    return state.velocity.y


@integrator_event(terminal=True, direction=-1, flag=TrajFlag.NONE)
def min_velocity_event(state: TrajectoryState, min_velocity_threshold: float) -> float:
    """Returns (speed - threshold). The event occurs when the value is 0."""
    return state.velocity.magnitude() - min_velocity_threshold


@integrator_event(terminal=True, direction=-1, flag=TrajFlag.NONE)
def max_drop_event(state: TrajectoryState, max_drop_threshold: float) -> float:
    """
    Returns (current decline - maximum decline). The event occurs when the value is 0.
    Assumes max_drop_threshold is an absolute negative Y coordinate.
    """
    return state.position.y - max_drop_threshold


@integrator_event(terminal=True, direction=-1, flag=TrajFlag.NONE)
def min_altitude_event(
    state: TrajectoryState, initial_altitude: float, min_altitude_threshold: float
) -> float:
    """
    Returns (current_altitude - minimum_altitude). The event occurs when the value is 0.
    Current altitude is initial_altitude + position.y (where position.y is change in altitude).
    """
    return (initial_altitude + state.position.y) - min_altitude_threshold


@integrator_event(terminal=False, direction=1, flag=TrajFlag.RANGE)
def range_step_event(state: TrajectoryState, next_record_distance: float) -> float:
    """Returns (current_x_distance - next_record_distance)."""
    return state.position.x - next_record_distance


@integrator_event(terminal=False, direction=1, flag=TrajFlag.RANGE)
def time_step_event(state: TrajectoryState, next_record_time: float) -> float:
    """Returns (current_time - next_record_time)."""
    return state.time - next_record_time


@integrator_event(terminal=True, direction=0, flag=TrajFlag.RANGE)
def max_range_event(state: TrajectoryState, max_range_threshold: float) -> float:
    """Returns (current_time - next_record_time)."""
    return state.position.x - (max_range_threshold + 1)


class EventHandler:
    def __init__(self, func: IntegratorEvent, **kwargs):
        self.func = func
        self.kwargs = kwargs
        self.last_val: Optional[float] = None

    def __call__(self, state: TrajectoryState) -> float:
        return self.func(state, **self.kwargs)

    def check_event(self, current_val: float) -> bool:
        if self.last_val is None:
            self.last_val = current_val
            return False
        triggered = self.last_val * current_val <= 0 and abs(self.last_val) > 1e-12
        self.last_val = current_val
        return triggered


MAP_EVENT_TO_ERR = {
    min_velocity_event: RangeError.MinimumVelocityReached,
    min_altitude_event: RangeError.MinimumAltitudeReached,
    max_drop_event: RangeError.MaximumDropReached,
    max_range_event: None,  # is not error
}


class EventBasedIntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):
    def __init__(self, config: BaseEngineConfigDict) -> None:
        super().__init__(config)
        self._event_handlers: List[EventHandler] = []

    def _add_event_handler(self, event_func_proto: IntegratorEvent, **kwargs):
        # Check if an EventHandler for this specific function and kwargs already exists
        for handler in self._event_handlers:
            if handler.func is event_func_proto and handler.kwargs == kwargs:
                logger.warning(
                    f"Event handler {event_func_proto.func.__name__} with kwargs {kwargs} already exists, skipping addition."
                )
                return  # Already exists, do nothing

        self._event_handlers.append(EventHandler(event_func_proto, **kwargs))

    def _setup_events(
        self,
        maximum_range,
        record_step,
        time_step,
        initial_state: TrajectoryState,
        filter_flags,
    ):
        # Standard events

        if filter_flags & TrajFlag.ZERO:
            self._add_event_handler(zero_crossing_event, look_angle=self.look_angle_rad)
        if filter_flags & TrajFlag.MACH:
            self._add_event_handler(mach_crossing_event)
        if filter_flags & TrajFlag.APEX:
            self._add_event_handler(apex_event)

        self._add_event_handler(max_range_event, max_range_threshold=maximum_range)

        # Terminal events
        self._add_event_handler(
            min_velocity_event, min_velocity_threshold=self._config.cMinimumVelocity
        )
        max_drop = max(
            self._config.cMaximumDrop, self._config.cMinimumAltitude - self.alt0
        )
        self._add_event_handler(max_drop_event, max_drop_threshold=max_drop)
        self._add_event_handler(
            min_altitude_event,
            initial_altitude=self.alt0,
            min_altitude_threshold=self._config.cMinimumAltitude,
        )

        # POI events
        if record_step > 0:
            self._add_event_handler(
                range_step_event,
                next_record_distance=initial_state.position.x + record_step,
            )
        if time_step > 0:
            self._add_event_handler(
                time_step_event, next_record_time=initial_state.time + time_step
            )

    def _clear_events(self):
        self._event_handlers = []

    def _process_events(
        self, prev_state: TrajectoryState, curr_state: TrajectoryState
    ) -> Optional[EventHandler]:
        for handler in self._event_handlers:
            try:
                prev_val = handler(prev_state)
                curr_val = handler(curr_state)
            except Exception as e:  # Added e for logging
                logger.warning(
                    f"Error evaluating event function {handler.func.__name__}: {e}"
                )  # Log error details
                continue

            if handler.check_event(curr_val):
                # --- THIS IS THE CRUCIAL PART TO UNCOMMENT AND USE ---
                if handler.func.direction != 0:
                    # If direction is 1, it must go from prev_val < 0 to curr_val >= 0 (increasing)
                    # If direction is -1, it must go from prev_val > 0 to curr_val <= 0 (decreasing)
                    if (
                        handler.func.direction == 1 and prev_val > curr_val
                    ):  # Was decreasing, but wanted increasing
                        continue
                    if (
                        handler.func.direction == -1 and prev_val < curr_val
                    ):  # Was increasing, but wanted decreasing
                        continue
                # --- END OF CRUCIAL PART ---

                interp = self._interpolate_event_point(prev_state, curr_state, handler)

                if interp:
                    # Advance next thresholds if needed
                    if not handler.func == max_range_event:
                        self.create_trajectory_row(interp, handler.func.flag)
                    if handler.func == range_step_event:
                        handler.kwargs["next_record_distance"] += self._record_step
                    elif handler.func == time_step_event:
                        handler.kwargs["next_record_time"] += self._time_step
                    if handler.func.terminal:
                        return handler
        return None

    def _step(self, state: TrajectoryState) -> TrajectoryState:
        raise NotImplementedError

    @override
    def _integrate(
        self,
        shot_info: Shot,
        maximum_range: float,
        record_step: float,
        filter_flags: int,
        time_step: float = 0.0,
    ) -> List[TrajectoryData]:
        self._ranges = []
        self._record_step = record_step
        self._time_step = time_step

        self._shot_info = shot_info
        self._wind_sock = _WindSock(shot_info.winds)

        velocity = self.muzzle_velocity
        position = Vector(
            0.0,
            -self.cant_cosine * self.sight_height,
            -self.cant_sine * self.sight_height,
        )
        velocity_vector = Vector(
            math.cos(self.barrel_elevation_rad) * math.cos(self.barrel_azimuth_rad),
            math.sin(self.barrel_elevation_rad),
            math.cos(self.barrel_elevation_rad) * math.sin(self.barrel_azimuth_rad),
        ).mul_by_const(velocity)

        time = 0.0
        density_ratio, mach = shot_info.atmo.get_density_and_mach_for_altitude(
            self.alt0 + position.y
        )
        state = TrajectoryState(time, position, velocity_vector, mach)
        self.create_trajectory_row(state, TrajFlag.RANGE)

        self._setup_events(maximum_range, record_step, time_step, state, filter_flags)

        it = 0
        termination_reason = None

        while it < MAX_ITERATIONS_LIMIT:
            it += 1
            next_state = self._step(state)
            if terminator := self._process_events(state, next_state):
                termination_reason = MAP_EVENT_TO_ERR.get(
                    terminator.func, "UnknownTermination"
                )
                break

            state = next_state
        self._clear_events()

        logger.debug(f"Euler ran {it} iterations")

        if termination_reason is not None:
            raise RangeError(termination_reason, self._ranges)
        if it >= MAX_ITERATIONS_LIMIT:
            raise RangeError("MaximumIterationLimitReached", self._ranges)

        # temp
        if (filter_flags and ((len(self._ranges) < 2) or termination_reason)) or len(
            self._ranges
        ) == 0:
            self.create_trajectory_row(state, TrajFlag.NONE)
        return self._ranges

    def _interpolate_event_point(
        self,
        prev_state: TrajectoryState,
        current_state: TrajectoryState,
        handler: EventHandler,
    ) -> Optional[TrajectoryState]:
        """
        Helper function for event point interpolation using a bisection method.
        Finds the exact time and state where the event function crosses zero between t0 and t1.
        """
        t0, r0, v0, m0 = prev_state
        t1, r1, v1, m1 = current_state
        event_func, event_args = handler.func, handler.kwargs

        tolerance = 1e-7  # Increased tolerance for more precision
        max_iterations = 50  # Increased iterations for better convergence

        if abs(t1 - t0) < 1e-12:  # Avoid division by zero if time step is too small
            return None

        low_t, high_t = t0, t1
        # Calculate initial event values
        try:
            low_val = event_func(prev_state, **event_args)
            high_val = event_func(current_state, **event_args)
        except (ZeroDivisionError, ValueError) as e:
            logger.warning(
                f"Error calculating event function during interpolation: {e}"
            )
            return None

        # If values have the same sign or high_val is exactly zero, it means the crossing might have
        # just occurred or been on the boundary. We care if a sign change is happening.
        # If low_val is positive and high_val is also positive, no crossing (for events designed to go from - to +).
        # If low_val is negative and high_val is also negative, no crossing.
        # So low_val * high_val must be <= 0 for a crossing.
        if low_val * high_val > 0:
            return None

        # If low_val is already zero, it means the event might have triggered at the previous point.
        # For *interpolation*, we are looking for a crossing *within* the interval (t0, t1].
        # If we need to capture events that are exactly at t0, it should be handled before calling interpolation.
        if abs(low_val) < tolerance:
            # If the start point is already the event, no need to bisect in the interval
            # This can happen if a previous interpolation already found this point.
            # Or if t0 is exactly the point where the event function is zero.
            # Returning the initial state directly can be an option or carefully check if it was already recorded.
            pass  # Continue with bisection, it will converge to t0 if that's the zero.

        # Binary search to find the exact point
        for _ in range(max_iterations):
            mid_t = (low_t + high_t) / 2.0

            # Linearly interpolate position, velocity, and mach_fps at mid_t
            # This assumes linear change over the small time step, which is reasonable for Euler.
            ratio = (mid_t - t0) / (t1 - t0)
            mid_r = r0 + (r1 - r0) * ratio
            mid_v = v0 + (v1 - v0) * ratio
            mid_m = m0 + (m1 - m0) * ratio

            try:
                mid_val = event_func(
                    TrajectoryState(mid_t, mid_r, mid_v, mid_m), **event_args
                )
            except (ZeroDivisionError, ValueError) as e:
                logger.warning(
                    f"Error calculating event function at mid-point during interpolation: {e}"
                )
                return None

            if abs(mid_val) < tolerance:
                # Found the event point within tolerance
                return TrajectoryState(mid_t, mid_r, mid_v, mid_m)
            elif low_val * mid_val < 0:  # Event is in the first half [low_t, mid_t]
                high_t = mid_t
                high_val = mid_val  # Update high_val for next iteration
            else:  # Event is in the second half [mid_t, high_t]
                low_t = mid_t
                low_val = mid_val  # Update low_val for next iteration

        # If max_iterations reached, return the midpoint of the final interval
        # This is a fallback if exact zero is not found within tolerance.
        # It's important to pick a point that best approximates the event.
        mid_t = (low_t + high_t) / 2.0
        ratio = (mid_t - t0) / (t1 - t0)
        mid_r = r0 + (r1 - r0) * ratio
        mid_v = v0 + (v1 - v0) * ratio
        mid_m = m0 + (m1 - m0) * ratio
        return TrajectoryState(mid_t, mid_r, mid_v, mid_m)

    def create_trajectory_row(
        self, state: TrajectoryState, flag: Union[TrajFlag, int]
    ) -> TrajectoryData:
        """
        Creates a TrajectoryData object representing a single row of trajectory data.

        Args:
            state (TrajectoryState):
            flag (Union[TrajFlag, int]): Flag value.

        Returns:
            TrajectoryData: A TrajectoryData object representing the trajectory data.
        """

        velocity_vector = state.velocity
        range_vector = state.position

        spin_drift = self.spin_drift(state.time)
        velocity = velocity_vector.magnitude()
        windage = range_vector.z + spin_drift
        drop_adjustment = get_correction(range_vector.x, range_vector.y)
        windage_adjustment = get_correction(range_vector.x, windage)
        trajectory_angle = math.atan2(velocity_vector.y, velocity_vector.x)

        density_ratio, mach_fps = (
            self._shot_info.atmo.get_density_and_mach_for_altitude(
                self.alt0 + range_vector.y
            )
        )
        drag = density_ratio * velocity * self.drag_by_mach(velocity / mach_fps)

        self._ranges.append(TrajectoryData(
            time=state.time,
            distance=_new_feet(range_vector.x),
            velocity=_new_fps(velocity),
            mach=velocity / mach_fps,
            height=_new_feet(range_vector.y),
            slant_height=_new_feet(
                (range_vector.y - range_vector.x * math.tan(self.look_angle_rad))
                * math.cos(self.look_angle_rad)
            ),
            drop_adj=_new_rad(
                drop_adjustment - (self.look_angle_rad if range_vector.x else 0)
            ),
            windage=_new_feet(windage),
            windage_adj=_new_rad(windage_adjustment),
            slant_distance=_new_feet(range_vector.x / math.cos(self.look_angle_rad)),
            angle=_new_rad(trajectory_angle),
            density_ratio=density_ratio - 1,
            drag=drag,
            energy=_new_ft_lb(calculate_energy(self.weight, velocity)),
            ogw=_new_lb(calculate_ogw(self.weight, velocity)),
            flag=flag,
        ))


class EulerIntegrationEngine(EventBasedIntegrationEngine):
    @override
    def _step(self, state: TrajectoryState) -> TrajectoryState:
        if state.position.x >= self._wind_sock.next_range:
            wind_vector = self._wind_sock.vector_for_range(state.position.x)
        else:
            wind_vector = self._wind_sock.current_vector()

        vel_rel_air = state.velocity - wind_vector
        vel_mag = vel_rel_air.magnitude()

        delta_time = self.calc_step / max(1.0, vel_mag)
        density_ratio, mach_fps = (
            self._shot_info.atmo.get_density_and_mach_for_altitude(
                self.alt0 + state.position.y
            )
        )
        drag = (
            density_ratio * vel_mag * self.drag_by_mach(vel_mag / max(mach_fps, 1e-6))
        )
        accel = self.gravity_vector - vel_rel_air * drag

        new_velocity = state.velocity + accel * delta_time
        new_position = state.position + new_velocity * delta_time
        new_time = state.time + delta_time

        return TrajectoryState(new_time, new_position, new_velocity, mach_fps)


class RK4IntegrationEngine(EventBasedIntegrationEngine):
    @override
    def get_calc_step(self, step: float = 0) -> float:
        # RK steps can be larger than calc_step default on Euler integrator
        # min_step ensures that with small record steps the loop runs far enough to get desired points
        # adjust Euler default step to RK4 algorithm
        # NOTE: pow(step, 0.5) recommended by https://github.com/serhiy-yevtushenko
        return super().get_calc_step(step) ** 0.5

    @override
    def _step(self, state: TrajectoryState) -> TrajectoryState:
        if state.position.x >= self._wind_sock.next_range:
            wind_vector = self._wind_sock.vector_for_range(state.position.x)
        else:
            wind_vector = self._wind_sock.current_vector()

        velocity_vector = state.velocity
        # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
        relative_velocity = velocity_vector - wind_vector
        relative_speed = relative_velocity.magnitude()  # Velocity relative to air
        # Time step is normalized by velocity so that we take smaller steps when moving faster
        delta_time = self.calc_step / max(1.0, relative_speed)
        density_ratio, mach_fps = (
            self._shot_info.atmo.get_density_and_mach_for_altitude(
                self.alt0 + state.position.y
            )
        )
        km = density_ratio * self.drag_by_mach(relative_speed / mach_fps)

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
        new_velocity = velocity_vector + (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)  # type: ignore[operator]
        new_position = state.position + (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)  # type: ignore[operator]
        # endregion RK4 integration

        # region for Reference: Euler integration
        # velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time
        # delta_range_vector = velocity_vector * delta_time
        # range_vector += delta_range_vector
        # endregion Euler integration

        # new_position = velocity_vector.magnitude()  # Velocity relative to ground
        new_time = state.time + delta_time

        return TrajectoryState(new_time, new_position, new_velocity, mach_fps)
