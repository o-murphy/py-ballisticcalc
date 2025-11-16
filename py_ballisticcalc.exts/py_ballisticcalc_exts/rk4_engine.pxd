# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_TrajFlag,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTrajSeq
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_Engine,
    BCLIBC_StatusCode,
    BCLIBC_TerminationReason,
)

cdef extern from "include/bclibc/rk4.hpp" namespace "bclibc" nogil:

    BCLIBC_StatusCode BCLIBC_integrateRK4(
        BCLIBC_Engine *eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_BaseTrajSeq *trajectory,
        BCLIBC_TerminationReason *reason,
    ) noexcept nogil

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedRK4IntegrationEngine self)
