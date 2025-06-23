from typing_extensions import override

from typing_extensions import override

from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine, BaseIntegrationState

__all__ = ('RK4IntegrationEngine',)


class RK4IntegrationEngine(BaseIntegrationEngine):

    @override
    def get_calc_step(self, step: float = 0) -> float:
        # adjust Euler default step to RK4 algorythm
        # NOTE: pow(step, 0.5) recommended by https://github.com/serhiy-yevtushenko
        return super().get_calc_step(step) ** 0.5

    @override
    def _generate_next_state(self, state: BaseIntegrationState) -> None:
        # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
        relative_velocity = state.velocity_vector - state.wind_vector
        relative_speed = relative_velocity.magnitude()  # Velocity relative to air
        # Time step is normalized by velocity so that we take smaller steps when moving faster
        delta_time = self.calc_step / max(1.0, relative_speed)
        km = state.density_factor * self.drag_by_mach(relative_speed / state.mach)
        state.drag = km * relative_speed

        # region RK4 integration
        def f(v):  # dv/dt
            # Bullet velocity changes due to both drag and gravity
            return self.gravity_vector - km * v * v.magnitude()

        v1 = delta_time * f(relative_velocity)
        v2 = delta_time * f(relative_velocity + 0.5 * v1)
        v3 = delta_time * f(relative_velocity + 0.5 * v2)
        v4 = delta_time * f(relative_velocity + v3)
        p1 = delta_time * state.velocity_vector
        p2 = delta_time * (state.velocity_vector + 0.5 * p1)
        p3 = delta_time * (state.velocity_vector + 0.5 * p2)
        p4 = delta_time * (state.velocity_vector + p3)
        state.velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)
        state.range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)
        # endregion RK4 integration

        # region for Reference: Euler integration
        # velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time
        # delta_range_vector = velocity_vector * delta_time
        # range_vector += delta_range_vector
        # endregion Euler integration

        state.velocity = state.velocity_vector.magnitude()  # Velocity relative to ground
        state.time += delta_time

        # Update wind reading at current point in trajectory
        if state.range_vector.x >= state.wind_sock.next_range:  # require check before call to improve performance
            state.wind_vector = state.wind_sock.vector_for_range(state.range_vector.x)

        # Update air density at current point in trajectory
        state.density_factor, state.mach = state.shot_info.atmo.get_density_factor_and_mach_for_altitude(
            self.alt0 + state.range_vector.y
        )
