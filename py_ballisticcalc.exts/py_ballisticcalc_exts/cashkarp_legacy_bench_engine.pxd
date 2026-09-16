# TEMPORARY benchmark-only pxd. Delete alongside the .pyx/.hpp/.cpp counterparts.
from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps, BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface,
)

cdef extern from "include/bclibc/cash_karp_legacy_bench.hpp" namespace "bclibc" nogil:
    void BCLIBC_integrateCashKarpLegacy(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) except +
    void BCLIBC_cashKarpLegacyGetStats(int &out_accepted, int &out_rejected)
    void BCLIBC_cashKarpLegacySetRelativeTolerance(double tolerance) except +

cdef class CythonizedCashKarpLegacyIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef int _last_accepted
    cdef int _last_rejected

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedCashKarpLegacyIntegrationEngine self,
        object shot_info,
    )
    cdef void _snapshot_step_stats(CythonizedCashKarpLegacyIntegrationEngine self)
