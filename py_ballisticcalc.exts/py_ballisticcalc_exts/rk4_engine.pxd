# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_ShotProps,
    BCLIBC_TrajFlag,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_traj_seq cimport BCLIBC_BaseTrajSeq
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_EngineT,
    BCLIBC_StatusCode,
    BCLIBC_TerminationReason,
)

cdef extern from "include/bclibc_rk4.h" nogil:

    BCLIBC_StatusCode BCLIBC_integrateRK4(
        BCLIBC_EngineT *eng,
        double range_limit_ft, double range_step_ft,
        double time_step, BCLIBC_TrajFlag filter_flags,
        BCLIBC_BaseTrajSeq *traj_seq_ptr,
        BCLIBC_TerminationReason *reason,
    ) noexcept nogil

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedRK4IntegrationEngine self)
    cdef tuple _integrate(CythonizedRK4IntegrationEngine self,
                          double range_limit_ft, double range_step_ft,
                          double time_step, BCLIBC_TrajFlag filter_flags)
