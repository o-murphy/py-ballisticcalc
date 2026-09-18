# pxd for cashkarp_engine to expose CythonizedCashKarpIntegrationEngine
from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps, BCLIBC_TerminationReason
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

    void BCLIBC_cashKarpSetRelativeTolerance(double tolerance) except +

    void BCLIBC_cashKarpSetAbsoluteTolerance(double tolerance) except +

cdef class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # Per-instance snapshot of BCLIBC_cashKarpGetStats(), taken right after this
    # engine's own integrate() call returns. BCLIBC_cashKarpGetStats() itself
    # reads thread-local counters *shared* across every CythonizedCashKarpIntegrationEngine
    # instance on the same thread -- reading it lazily from get_step_stats()
    # instead of snapshotting here would silently return whichever instance
    # integrated *last* on this thread, not necessarily self's own result.
    cdef int _last_accepted
    cdef int _last_rejected

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedCashKarpIntegrationEngine self,
        object shot_info,
    )
    cdef void _snapshot_step_stats(CythonizedCashKarpIntegrationEngine self)
