# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
)
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTrajDataHandlerInterface
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_Engine,
    BCLIBC_TerminationReason,
    BCLIBC_BaseTrajDataHandlerInterface,
)


cdef extern from "include/bclibc/rk4.hpp" namespace "bclibc" nogil:

    void BCLIBC_integrateRK4(
        BCLIBC_Engine &eng,
        double range_limit_ft,
        double range_step_ft,
        double time_step,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) except +

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedRK4IntegrationEngine self)
