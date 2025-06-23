# Total Score: 2394, Possible Score: 45200
# Total Non-Empty Lines: 452
# Python Overhead Lines: 152
# Cythonization Percentage: 94.70%
# Python Overhead Lines Percentage: 33.63%


# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2, fmin, fmax, pow
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport CTrajFlag, BaseTrajData, TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    update_density_factor_and_mach_for_altitude,
    cy_drag_by_mach,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
    CythonizedBaseIntegrationState,
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT, add, sub, mag, mulS
)


__all__ = (
    'CythonizedRK4IntegrationEngine'
)


cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):

    cdef double get_calc_step(CythonizedRK4IntegrationEngine self, double step = 0.0):
        step = CythonizedBaseIntegrationEngine.get_calc_step(self, step)  # likely a super().get_calc_step(step)
        # adjust Euler default step to RK4 algorythm
        # NOTE: pow(step, 0.5) recommended by https://github.com/serhiy-yevtushenko
        return pow(step, 0.5)

    cdef void _generate_next_state(CythonizedRK4IntegrationEngine self,
                                   CythonizedBaseIntegrationState *state):
        # temp variables
        cdef:
            double relative_speed
            V3dT relative_velocity
            V3dT _temp_add_operand, _temp_v_result, _temp_p_result
            V3dT _v_sum_intermediate, _p_sum_intermediate
            V3dT v1, v2, v3, v4, p1, p2, p3, p4

            double delta_time, km

        # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
        relative_velocity = sub(&state.velocity_vector, &state.wind_vector)
        relative_speed = mag(&relative_velocity)

        # Time step is normalized by velocity so that we take smaller steps when moving faster
        delta_time = self._shot_s.calc_step / fmax(1.0, relative_speed)
        km = state.density_factor * cy_drag_by_mach(&self._shot_s, relative_speed / state.mach)
        state.drag = km * relative_speed

        # # region RK4 integration

        # region for Reference:
        # cdef V3dT f(V3dT v):  # dv/dt
        #     # Bullet velocity changes due to both drag and gravity
        #     return self.gravity_vector - km * v * v.magnitude()
        #
        # v1 = delta_time * f(relative_velocity)
        # v2 = delta_time * f(relative_velocity + 0.5 * v1)
        # v3 = delta_time * f(relative_velocity + 0.5 * v2)
        # v4 = delta_time * f(relative_velocity + v3)
        # p1 = delta_time * velocity_vector
        # p2 = delta_time * (velocity_vector + 0.5 * p1)
        # p3 = delta_time * (velocity_vector + 0.5 * p2)
        # p4 = delta_time * (velocity_vector + p3)
        # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)
        # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)
        # # endregion RK4 integration

        # v1 = delta_time * f(relative_velocity)
        _temp_v_result = _f_dvdt(&relative_velocity, &self.gravity_vector, km)
        v1 = mulS(&_temp_v_result, delta_time)

        # v2 = delta_time * f(relative_velocity + 0.5 * v1)
        _temp_add_operand = mulS(&v1, 0.5)  # Store temporary result
        _temp_v_result = add(&relative_velocity, &_temp_add_operand)
        _temp_v_result = _f_dvdt(&_temp_v_result, &self.gravity_vector, km)
        v2 = mulS(&_temp_v_result, delta_time)

        # v3 = delta_time * f(relative_velocity + 0.5 * v2)
        _temp_add_operand = mulS(&v2, 0.5)  # Store temporary result
        _temp_v_result = add(&relative_velocity, &_temp_add_operand)
        _temp_v_result = _f_dvdt(&_temp_v_result, &self.gravity_vector, km)
        v3 = mulS(&_temp_v_result, delta_time)

        # v4 = delta_time * f(relative_velocity + v3)
        _temp_v_result = add(&relative_velocity, &v3)
        _temp_v_result = _f_dvdt(&_temp_v_result, &self.gravity_vector, km)
        v4 = mulS(&_temp_v_result, delta_time)

        # p1 = delta_time * velocity_vector
        p1 = mulS(&state.velocity_vector, delta_time)

        # p2 = delta_time * (velocity_vector + 0.5 * p1)
        _temp_add_operand = mulS(&p1, 0.5)  # Store temporary result
        _temp_p_result = add(&state.velocity_vector, &_temp_add_operand)
        p2 = mulS(&_temp_p_result, delta_time)

        # p3 = delta_time * (velocity_vector + 0.5 * p2)
        _temp_add_operand = mulS(&p2, 0.5)  # Store temporary result
        _temp_p_result = add(&state.velocity_vector, &_temp_add_operand)
        p3 = mulS(&_temp_p_result, delta_time)

        # p4 = delta_time * (velocity_vector + p3)
        _temp_p_result = add(&state.velocity_vector, &p3)
        p4 = mulS(&_temp_p_result, delta_time)

        # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)
        # Break down the sum and scalar multiplication to avoid "non-lvalue" errors
        _temp_add_operand = mulS(&v2, 2.0)
        _v_sum_intermediate = add(&v1, &_temp_add_operand)

        _temp_add_operand = mulS(&v3, 2.0)
        _v_sum_intermediate = add(&_v_sum_intermediate, &_temp_add_operand)

        _v_sum_intermediate = add(&_v_sum_intermediate, &v4)
        _v_sum_intermediate = mulS(&_v_sum_intermediate, (1.0 / 6.0))
        state.velocity_vector = add(&state.velocity_vector, &_v_sum_intermediate)

        # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)
        # Break down the sum and scalar multiplication
        _temp_add_operand = mulS(&p2, 2.0)
        _p_sum_intermediate = add(&p1, &_temp_add_operand)

        _temp_add_operand = mulS(&p3, 2.0)
        _p_sum_intermediate = add(&_p_sum_intermediate, &_temp_add_operand)

        _p_sum_intermediate = add(&_p_sum_intermediate, &p4)
        _p_sum_intermediate = mulS(&_p_sum_intermediate, (1.0 / 6.0))
        state.range_vector = add(&state.range_vector, &_p_sum_intermediate)

        # region for Reference: Euler integration
        # velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time
        # delta_range_vector = velocity_vector * delta_time
        # range_vector += delta_range_vector
        # endregion Euler integration

        state.velocity = mag(&state.velocity_vector)
        state.time += delta_time


# This function calculates dv/dt for velocity (v) affected by gravity and drag.
# It now takes gravity_vector and km as explicit arguments.
cdef V3dT _f_dvdt(V3dT *v_ptr, V3dT *gravity_vector_ptr, double km_coeff):
    cdef V3dT drag_force_component
    # Bullet velocity changes due to both drag and gravity
    # Original: return self.gravity_vector - km * v * v.magnitude()
    drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr))
    return sub(gravity_vector_ptr, &drag_force_component)