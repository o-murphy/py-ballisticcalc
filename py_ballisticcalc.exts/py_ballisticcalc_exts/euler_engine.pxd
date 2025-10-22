# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    TrajFlag_t,
    ErrorCode,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeq_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport Engine_t


cdef extern from "include/euler.h" nogil:
    double _euler_time_step(double base_step, double velocity) noexcept nogil

    ErrorCode _integrate_euler(
        Engine_t *engine_ptr,
        double range_limit_ft, double range_step_ft,
        double time_step, TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr
    ) noexcept nogil

cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedEulerIntegrationEngine self)
    cdef tuple _integrate(CythonizedEulerIntegrationEngine self,
                          double range_limit_ft, double range_step_ft,
                          double time_step, TrajFlag_t filter_flags)
