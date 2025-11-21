# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_TrajFlag,
)
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTrajDataHandlerInterface
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_Engine,
    BCLIBC_StatusCode,
    BCLIBC_TerminationReason,
)


cdef extern from "include/bclibc/euler.hpp" namespace "bclibc" nogil:

    BCLIBC_StatusCode BCLIBC_integrateEULER(
        BCLIBC_Engine &eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) noexcept nogil

cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedEulerIntegrationEngine self)
