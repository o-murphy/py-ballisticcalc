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

    # Stateful functor: owns its own tolerances/step-counts per instance
    # (each field a std::atomic on the C++ side), replacing the old
    # thread-local free-function API (BCLIBC_cashKarpGetStats/Set*Tolerance).
    cdef cppclass BCLIBC_CashKarpIntegrator:
        BCLIBC_CashKarpIntegrator() except +
        void operator()(
            BCLIBC_BaseEngine &eng,
            BCLIBC_BaseTrajDataHandlerInterface &handler,
            BCLIBC_TerminationReason &reason,
        ) except +
        void get_stats(int &out_accepted, int &out_rejected) const
        void set_relative_tolerance(double tolerance) except +
        void set_absolute_tolerance(double tolerance) except +

cdef class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # Points at this instance's own integrator living *inside*
    # self._this.integrate_func (set via std::function::target() in
    # __cinit__, once integrate_func has been assigned a BCLIBC_CashKarpIntegrator
    # by value) -- so its tolerances/stats are exclusively this engine's, no
    # longer shared thread-local state.
    cdef BCLIBC_CashKarpIntegrator* _integrator
    # Snapshot of self._integrator.get_stats(), taken right after this
    # engine's own integrate() call returns.
    cdef int _last_accepted
    cdef int _last_rejected

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedCashKarpIntegrationEngine self,
        object shot_info,
    )
    cdef void _snapshot_step_stats(CythonizedCashKarpIntegrationEngine self)
