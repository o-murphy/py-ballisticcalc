# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
from py_ballisticcalc_exts.base_types cimport BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface,
)


cdef extern from "include/bclibc/euler.hpp" namespace "bclibc" nogil:

    void BCLIBC_integrateEULER(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) except +

cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    pass
