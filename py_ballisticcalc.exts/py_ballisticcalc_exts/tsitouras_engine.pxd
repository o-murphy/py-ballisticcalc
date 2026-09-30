from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps, BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface
)

cdef extern from "include/bclibc/tsitouras.hpp" namespace "bclibc" nogil:
    void BCLIBC_integrateTsitouras(
        BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) except +

    # Stateful functor: owns its own tolerances/step-counts per instance,
    # replacing the old thread-local free-function API.
    cdef cppclass BCLIBC_TsitourasIntegrator:
        BCLIBC_TsitourasIntegrator() except +
        void operator()(
            BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) except +
        void get_stats(int &, int &) const
        # set_relative_tolerance/set_absolute_tolerance now return a Result instead of
        # throwing std::invalid_argument; called only through the py_tsitouras_set_*()
        # wrappers below.

# bclibc no longer throws: BCLIBC_TsitourasIntegrator's tolerance setters return a Result.
# Self-contained here: this is the only extension that compiles tsitouras.cpp
# (see setup.py's _TSITOURAS_DEPS).
cdef extern from *:
    """
    #include "bclibc/tsitouras.hpp"
    #include <Python.h>
    #include <variant>

    namespace {
        static bool py_tsitouras_set_relative_tolerance(
            bclibc::BCLIBC_TsitourasIntegrator &integrator, double tolerance)
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

        static bool py_tsitouras_set_absolute_tolerance(
            bclibc::BCLIBC_TsitourasIntegrator &integrator, double tolerance)
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
    bint py_tsitouras_set_relative_tolerance(BCLIBC_TsitourasIntegrator&, double) except 0
    bint py_tsitouras_set_absolute_tolerance(BCLIBC_TsitourasIntegrator&, double) except 0

cdef class CythonizedTsitourasIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # Points at this instance's own integrator living inside
    # self._this.integrate_func (see __cinit__).
    cdef BCLIBC_TsitourasIntegrator* _integrator
    cdef int _last_accepted
    cdef int _last_rejected
