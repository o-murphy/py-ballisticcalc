# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    ShotProps_t,
    TrajFlag_t,
    ErrorCode,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeq_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport Engine_t


cdef extern from "include/rk4.h" nogil:

    # This function calculates dv/dt for velocity (v)
    # affected by gravity, drag, and Coriolis forces.
    # """Calculate the derivative of velocity with respect to time.

    # Args:
    #     v_ptr: Pointer to the relative velocity vector (velocity - wind)
    #     gravity_vector_ptr: Pointer to the gravity vector
    #     km_coeff: Drag coefficient
    #     shot_props_ptr: Pointer to shot properties (for Coriolis data)
    #     ground_velocity_ptr: Pointer to ground velocity vector (for Coriolis calculation)

    # Returns:
    #     The acceleration vector (dv/dt)
    # """

    V3dT _calculate_dvdt(
        const V3dT *v_ptr,
        const V3dT *gravity_vector_ptr,
        double km_coeff,
        const ShotProps_t *shot_props_ptr,
        const V3dT *ground_velocity_ptr
    ) noexcept nogil

    ErrorCode _integrate_rk4(
        Engine_t *engine_ptr,
        double range_limit_ft, double range_step_ft,
        double time_step, TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr
    ) noexcept nogil

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedRK4IntegrationEngine self)
    cdef tuple _integrate(CythonizedRK4IntegrationEngine self,
                          double range_limit_ft, double range_step_ft,
                          double time_step, TrajFlag_t filter_flags)
