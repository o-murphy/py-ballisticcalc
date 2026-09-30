# pxd for rk4_engine to expose CythonizedRK4IntegrationEngine
from py_ballisticcalc_exts.base_types cimport BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface,
)
from py_ballisticcalc_exts.result cimport BCLIBC_Result, monostate


cdef extern from "include/bclibc/rk4.hpp" namespace "bclibc" nogil:

    BCLIBC_Result[monostate] BCLIBC_integrateRK4(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) noexcept

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    pass
