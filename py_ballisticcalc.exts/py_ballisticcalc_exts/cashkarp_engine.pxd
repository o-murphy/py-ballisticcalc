# pxd for cashkarp_engine to expose CythonizedCashKarpIntegrationEngine
from py_ballisticcalc_exts.base_types cimport BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface,
)


cdef extern from "include/bclibc/cash_karp.hpp" namespace "bclibc" nogil:

    void BCLIBC_integrateCashKarp(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) except +

    void BCLIBC_cashKarpGetStats(int &out_accepted, int &out_rejected)

cdef class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine):
    pass
