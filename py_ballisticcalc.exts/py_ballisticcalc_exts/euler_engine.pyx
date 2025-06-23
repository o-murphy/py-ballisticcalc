# Total Score: 158, Possible Score: 12400
# Total Non-Empty Lines: 124
# Python Overhead Lines: 19
# Cythonization Percentage: 98.73%
# Python Overhead Lines Percentage: 15.32%


# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2, fmin, fmax
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
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT, add, sub, mag, mulS
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.state cimport (
    CythonizedBaseIntegrationState
)



__all__ = (
    'CythonizedEulerIntegrationEngine'
)


cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):

    cdef void _generate_next_state(CythonizedEulerIntegrationEngine self,
                                   CythonizedBaseIntegrationState *state):

        cdef:
            V3dT _tv, velocity_adjusted, delta_range_vector
            double velocity, delta_time

        #region Ballistic calculation step
        # use just cdef methods to maximize speed

        velocity_adjusted = sub(&state.velocity_vector, &state.wind_vector)
        velocity = mag(&velocity_adjusted)
        delta_time = self._shot_s.calc_step / fmax(1.0, velocity)
        state.drag = state.density_factor * velocity * cy_drag_by_mach(&self._shot_s, velocity / state.mach)

        _tv = mulS(&velocity_adjusted, state.drag)
        _tv = sub(&_tv, &self.gravity_vector)
        _tv = mulS(&_tv, delta_time)

        state.velocity_vector = sub(&state.velocity_vector, &_tv)

        delta_range_vector = mulS(&state.velocity_vector, delta_time)
        state.range_vector = add(&state.range_vector, &delta_range_vector)

        state.velocity = mag(&state.velocity_vector)
        state.time += delta_time
