# Refactored EulerIntegrationEngine with scipy-like event logic

import math
from typing import Optional, List, Dict, NamedTuple, Protocol, TypedDict, Any, Union

from typing_extensions import override

from py_ballisticcalc import logger
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.engines.base_engine import (
    BaseIntegrationEngine, create_trajectory_row, BaseEngineConfigDict, _WindSock
)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.vector import Vector


class TrajectoryState(NamedTuple):
    """Minimal data for one point in ballistic trajectory"""
    time: float
    position: Vector
    velocity: Vector
    mach_fps: float


class IntegratorEventFunc(Protocol):
    """
    Protocol for event functions.
    Event functions should return a scalar value, where a zero-crossing indicates an event.
    """
    terminal: bool  # If True, the integration stops when this event occurs.
    flag: TrajFlag  # Trajectory flag to associate with the event.

    def __call__(self, time: float, position: Vector, velocity: Vector, mach_fps: float, **kwargs: Any) -> float: ...


class IntegratorEvent(TypedDict):
    """
    Typed dictionary to store information about an integrator event.
    """
    func: IntegratorEventFunc
    args: Dict[str, Any]
    # next_threshold is used for events that trigger at regular intervals (e.g., range_step, time_step)
    next_threshold: Optional[float]


# --- Event Functions ---
# These functions define the conditions for various events.
# They should return a value that crosses zero when the event occurs.

def zero_crossing_event(time: float, position: Vector, velocity: Vector, mach: float, look_angle: float) -> float:
    """Returns the elevation relative to the line of sight. The event occurs when the value is 0."""
    reference_height = position.x * math.tan(look_angle)
    return position.y - reference_height


zero_crossing_event.terminal = False
zero_crossing_event.flag = TrajFlag.ZERO


def mach_crossing_event(time: float, position: Vector, velocity: Vector, mach_fps: float) -> float:
    """Returns (speed - Mach). The event occurs when the value is 0 (passing Mach 1)."""
    # Use velocity.magnitude() for the actual speed relative to the ground
    return velocity.magnitude() - mach_fps


mach_crossing_event.terminal = False
mach_crossing_event.flag = TrajFlag.MACH


def apex_event(time: float, position: Vector, velocity: Vector, mach_fps: float) -> float:
    """Returns the vertical component of the velocity. The event occurs when the value is 0 (vertex)."""
    return velocity.y


apex_event.terminal = False
apex_event.flag = TrajFlag.APEX


def min_velocity_event(time: float, position: Vector, velocity: Vector, mach_fps: float,
                       min_velocity_threshold: float) -> float:
    """Returns (speed - threshold). The event occurs when the value is 0."""
    return velocity.magnitude() - min_velocity_threshold


min_velocity_event.terminal = True
min_velocity_event.flag = TrajFlag.NONE


def max_drop_event(time: float, position: Vector, velocity: Vector, mach_fps: float,
                   max_drop_threshold: float) -> float:
    """
    Returns (current decline - maximum decline). The event occurs when the value is 0.
    Assumes max_drop_threshold is an absolute negative Y coordinate.
    """
    return position.y - max_drop_threshold


max_drop_event.terminal = True
max_drop_event.flag = TrajFlag.NONE


def min_altitude_event(time: float, position: Vector, velocity: Vector, mach_fps: float, initial_altitude: float,
                       min_altitude_threshold: float) -> float:
    """
    Returns (current_altitude - minimum_altitude). The event occurs when the value is 0.
    Current altitude is initial_altitude + position.y (where position.y is change in altitude).
    """
    return (initial_altitude + position.y) - min_altitude_threshold


min_altitude_event.terminal = True
min_altitude_event.flag = TrajFlag.NONE


def range_step_event(time: float, position: Vector, velocity: Vector, mach_fps: float,
                     next_record_distance: float) -> float:
    """Returns (current_x_distance - next_record_distance)."""
    return position.x - next_record_distance


range_step_event.terminal = False
range_step_event.flag = TrajFlag.RANGE


def time_step_event(time: float, position: Vector, velocity: Vector, mach_fps: float, next_record_time: float) -> float:
    """Returns (current_time - next_record_time)."""
    return time - next_record_time


time_step_event.terminal = False
time_step_event.flag = TrajFlag.RANGE  # Using RANGE flag for time-based recording


class EventHandler:
    def __init__(self, func, args: dict, flag: Union[TrajFlag, int], terminal: bool):
        self.func = func
        self.args = args
        self.flag = flag
        self.terminal = terminal
        self.last_val: Optional[float] = None

    def evaluate(self, state: TrajectoryState) -> float:
        val = self.func(state.time, state.position, state.velocity, state.mach_fps, **self.args)
        return val

    def check_event(self, current_val: float) -> bool:
        if self.last_val is None:
            self.last_val = current_val
            return False
        triggered = self.last_val * current_val <= 0 and abs(self.last_val) > 1e-12
        self.last_val = current_val
        return triggered


class EulerIntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):
    def __init__(self, config: BaseEngineConfigDict) -> None:
        super().__init__(config)
        self._event_handlers: List[EventHandler] = []

    def _setup_events(self, record_step, time_step, initial_state: TrajectoryState, filter_flags):
        # Standard events
        if filter_flags & TrajFlag.ZERO:
            self._event_handlers.append(
                EventHandler(zero_crossing_event, {"look_angle": self.look_angle}, TrajFlag.ZERO, False))
        if filter_flags & TrajFlag.MACH:
            self._event_handlers.append(EventHandler(mach_crossing_event, {}, TrajFlag.MACH, False))
        if filter_flags & TrajFlag.APEX:
            self._event_handlers.append(EventHandler(apex_event, {}, TrajFlag.APEX, False))

        # Terminal events
        self._event_handlers.extend([
            EventHandler(min_velocity_event, {"min_velocity_threshold": self._config.cMinimumVelocity}, TrajFlag.NONE,
                         True),
            EventHandler(max_drop_event, {"max_drop_threshold": self._config.cMaximumDrop}, TrajFlag.NONE, True),
            EventHandler(min_altitude_event, {
                "initial_altitude": self.alt0,
                "min_altitude_threshold": self._config.cMinimumAltitude
            }, TrajFlag.NONE, True)
        ])

        # POI events
        if record_step > 0:
            self._event_handlers.append(EventHandler(range_step_event, {
                "next_record_distance": initial_state.position.x + record_step
            }, TrajFlag.RANGE, False))
        if time_step > 0:
            self._event_handlers.append(EventHandler(time_step_event, {
                "next_record_time": initial_state.time + time_step
            }, TrajFlag.RANGE, False))

    def _clear_events(self):
        self._event_handlers = []

    def _process_events(self, prev_state: TrajectoryState, curr_state: TrajectoryState) -> Optional[str]:
        for handler in self._event_handlers:
            try:
                prev_val = handler.evaluate(prev_state)
                curr_val = handler.evaluate(curr_state)
            except Exception:
                continue

            if handler.check_event(curr_val):
                interp = self._interpolate_event_point(
                    prev_state.time, prev_state.position, prev_state.velocity, prev_state.mach_fps,
                    curr_state.time, curr_state.position, curr_state.velocity, curr_state.mach_fps,
                    handler.func, handler.args
                )
                if interp:
                    self._ranges.append(create_trajectory_row(
                        interp.time, interp.position, interp.velocity,
                        interp.velocity.magnitude(), interp.mach_fps,
                        self.spin_drift(interp.time), self.look_angle,
                        self._density_factor, self._drag, self.weight, handler.flag))
                    # Advance next thresholds if needed
                    if handler.func == range_step_event:
                        handler.args["next_record_distance"] += self._record_step
                    elif handler.func == time_step_event:
                        handler.args["next_record_time"] += self._time_step
                    if handler.terminal:
                        return self._map_event_to_error(handler.func)
        return None

    def _map_event_to_error(self, func) -> str:
        if func == min_velocity_event:
            return RangeError.MinimumVelocityReached
        elif func == max_drop_event:
            return RangeError.MaximumDropReached
        elif func == min_altitude_event:
            return RangeError.MinimumAltitudeReached
        return "RangeError.UnknownTermination"

    @override
    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: int, time_step: float = 0.0) -> List[TrajectoryData]:
        self._ranges = []
        self._record_step = record_step
        self._time_step = time_step

        wind_sock = _WindSock(shot_info.winds)
        wind_vector = wind_sock.current_vector()

        velocity = self.muzzle_velocity
        position = Vector(0.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
        velocity_vector = Vector(
            math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth),
            math.sin(self.barrel_elevation),
            math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth)
        ).mul_by_const(velocity)

        time = 0.0
        self._density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(self.alt0 + position.y)
        state = TrajectoryState(time, position, velocity_vector, mach)
        self._ranges.append(create_trajectory_row(
            time, position, velocity_vector, velocity_vector.magnitude(), mach,
            self.spin_drift(time), self.look_angle,
            self._density_factor, 0.0, self.weight, TrajFlag.RANGE))

        self._setup_events(record_step, time_step, state, filter_flags)

        it = 0
        termination_reason = None
        while state.position.x <= maximum_range and it < 100000:
            it += 1

            if state.position.x >= wind_sock.next_range:
                wind_vector = wind_sock.vector_for_range(state.position.x)

            vel_rel_air = state.velocity - wind_vector
            vel_mag = vel_rel_air.magnitude()
            if vel_mag < 1e-6:
                termination_reason = RangeError.MinimumVelocityReached
                break

            delta_time = self.calc_step / max(1.0, vel_mag)
            self._density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(
                self.alt0 + state.position.y)
            self._drag = self._density_factor * vel_mag * self.drag_by_mach(vel_mag / max(mach, 1e-6))
            accel = self.gravity_vector - vel_rel_air * self._drag

            new_velocity = state.velocity + accel * delta_time
            new_position = state.position + new_velocity * delta_time
            new_time = state.time + delta_time

            next_state = TrajectoryState(new_time, new_position, new_velocity, mach)

            if termination_reason := self._process_events(state, next_state):
                break

            state = next_state

        self._clear_events()
        if termination_reason is not None:
            raise RangeError(termination_reason, self._ranges)
        return self._ranges

    def _interpolate_event_point(self, t0: float, r0: Vector, v0: Vector, m0: float,
                                 t1: float, r1: Vector, v1: Vector, m1: float,
                                 event_func: IntegratorEventFunc, event_args: Dict[str, Any]) -> Optional[TrajectoryState]:
        """
        Helper function for event point interpolation using a bisection method.
        Finds the exact time and state where the event function crosses zero between t0 and t1.
        """
        tolerance = 1e-7  # Increased tolerance for more precision
        max_iterations = 50  # Increased iterations for better convergence

        if abs(t1 - t0) < 1e-12:  # Avoid division by zero if time step is too small
            return None

        low_t, high_t = t0, t1
        # Calculate initial event values
        try:
            low_val = event_func(t0, r0, v0, m0, **event_args)
            high_val = event_func(t1, r1, v1, m1, **event_args)
        except (ZeroDivisionError, ValueError) as e:
            logger.warning(f"Error calculating event function during interpolation: {e}")
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
                mid_val = event_func(mid_t, mid_r, mid_v, mid_m, **event_args)
            except (ZeroDivisionError, ValueError) as e:
                logger.warning(f"Error calculating event function at mid-point during interpolation: {e}")
                return None

            if abs(mid_val) < tolerance:
                # Found the event point within tolerance
                return TrajectoryState(time=mid_t, position=mid_r, velocity=mid_v, mach_fps=mid_m)
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
        return TrajectoryState(time=mid_t, position=mid_r, velocity=mid_v, mach_fps=mid_m)
