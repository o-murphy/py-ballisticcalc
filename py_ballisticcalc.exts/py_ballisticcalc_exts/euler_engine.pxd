# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_TrajFlag,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BCLIBC_BaseTrajSeq
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_EngineT,
    BCLIBC_StatusCode,
    BCLIBC_TerminationReason,
)


cdef extern from "include/bclibc_euler.h" nogil:

    BCLIBC_StatusCode BCLIBC_integrateEULER(
        BCLIBC_EngineT *eng,
        double range_limit_ft, double range_step_ft,
        double time_step, BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        BCLIBC_TerminationReason *reason,
    ) noexcept nogil

cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedEulerIntegrationEngine self)
    cdef tuple _integrate(CythonizedEulerIntegrationEngine self,
                          double range_limit_ft, double range_step_ft,
                          double time_step, BCLIBC_TrajFlag filter_flags)
