# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    ShotProps_t,
    TrajFlag_t,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BaseTrajSeq_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    Engine_t,
    StatusCode,
    TerminationReason,
)

cdef extern from "include/rk45.h" nogil:

    StatusCode _integrate_rk45(
        Engine_t *eng,
        double range_limit_ft, double range_step_ft,
        double time_step, TrajFlag_t filter_flags,
        BaseTrajSeq_t *traj_seq_ptr,
        TerminationReason *reason,
    ) noexcept nogil

cdef class CythonizedRK45IntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedRK45IntegrationEngine self)
    cdef tuple _integrate(CythonizedRK45IntegrationEngine self,
                          double range_limit_ft, double range_step_ft,
                          double time_step, TrajFlag_t filter_flags)
