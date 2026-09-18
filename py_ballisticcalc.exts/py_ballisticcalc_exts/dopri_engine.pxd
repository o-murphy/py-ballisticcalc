from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps, BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface
)

cdef extern from "include/bclibc/dormand_prince.hpp" namespace "bclibc" nogil:
    void BCLIBC_integrateDormandPrince(
        BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) except +
    void BCLIBC_dormandPrinceGetStats(int &, int &)
    void BCLIBC_dormandPrinceSetRelativeTolerance(double) except +
    void BCLIBC_dormandPrinceSetAbsoluteTolerance(double) except +

cdef class CythonizedDormandPrinceIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    cdef int _last_accepted
    cdef int _last_rejected
