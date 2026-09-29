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
        # set_relative_tolerance/set_absolute_tolerance now return a Result instead of
        # throwing std::invalid_argument; called only through the py_cashkarp_set_*()
        # wrappers below.

# bclibc no longer throws: BCLIBC_CashKarpIntegrator's tolerance setters return a Result.
# Self-contained here (not py_bind.cpp/base_engine.pxd): this is the only extension that
# compiles cash_karp.cpp (see setup.py's _CASH_KARP_DEPS).
cdef extern from *:
    """
    #include "bclibc/cash_karp.hpp"
    #include <Python.h>
    #include <variant>

    namespace {
        static bool py_cashkarp_set_relative_tolerance(bclibc::BCLIBC_CashKarpIntegrator &integrator, double tolerance)
        {
            auto result = integrator.set_relative_tolerance(tolerance);
            if (bclibc::has_error(result))
            {
                const auto &error = std::get<bclibc::BCLIBC_BaseError>(result);
                PyErr_SetString(PyExc_ValueError, std::visit([](const auto &e) { return e.what(); }, error));
                return 0;
            }
            return 1;
        }

        static bool py_cashkarp_set_absolute_tolerance(bclibc::BCLIBC_CashKarpIntegrator &integrator, double tolerance)
        {
            auto result = integrator.set_absolute_tolerance(tolerance);
            if (bclibc::has_error(result))
            {
                const auto &error = std::get<bclibc::BCLIBC_BaseError>(result);
                PyErr_SetString(PyExc_ValueError, std::visit([](const auto &e) { return e.what(); }, error));
                return 0;
            }
            return 1;
        }
    }
    """
    bint py_cashkarp_set_relative_tolerance(BCLIBC_CashKarpIntegrator&, double) except 0
    bint py_cashkarp_set_absolute_tolerance(BCLIBC_CashKarpIntegrator&, double) except 0

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
