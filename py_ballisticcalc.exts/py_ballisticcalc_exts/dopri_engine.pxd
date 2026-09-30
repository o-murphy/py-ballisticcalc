from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps, BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface
)

cdef extern from "include/bclibc/dormand_prince.hpp" namespace "bclibc" nogil:
    void BCLIBC_integrateDormandPrince(
        BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) except +

    # Stateful functor: owns its own tolerances/step-counts per instance,
    # replacing the old thread-local free-function API.
    cdef cppclass BCLIBC_DormandPrinceIntegrator:
        BCLIBC_DormandPrinceIntegrator() except +
        void operator()(
            BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) except +
        void get_stats(int &, int &) const
        # set_relative_tolerance/set_absolute_tolerance now return a Result instead of
        # throwing std::invalid_argument; called only through the py_dopri_set_*()
        # wrappers below.

# bclibc no longer throws: BCLIBC_DormandPrinceIntegrator's tolerance setters return a
# Result. Self-contained here: this is the only extension that compiles
# dormand_prince.cpp (see setup.py's _DORMAND_PRINCE_DEPS).
cdef extern from *:
    """
    #include "bclibc/dormand_prince.hpp"
    #include <Python.h>
    #include <variant>

    namespace {
        static bool py_dopri_set_relative_tolerance(
            bclibc::BCLIBC_DormandPrinceIntegrator &integrator, double tolerance)
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

        static bool py_dopri_set_absolute_tolerance(
            bclibc::BCLIBC_DormandPrinceIntegrator &integrator, double tolerance)
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
    bint py_dopri_set_relative_tolerance(BCLIBC_DormandPrinceIntegrator&, double) except 0
    bint py_dopri_set_absolute_tolerance(BCLIBC_DormandPrinceIntegrator&, double) except 0

cdef class CythonizedDormandPrinceIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # Points at this instance's own integrator living inside
    # self._this.integrate_func (see __cinit__).
    cdef BCLIBC_DormandPrinceIntegrator* _integrator
    cdef int _last_accepted
    cdef int _last_rejected
