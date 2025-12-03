# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
from py_ballisticcalc_exts.base_types cimport BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_Engine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface,
)


cdef extern from "include/bclibc/rk45.hpp" namespace "bclibc" nogil:

    void BCLIBC_integrateRK45(
        BCLIBC_Engine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) except +

cdef class CythonizedRK45IntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double get_calc_step(CythonizedRK45IntegrationEngine self)
