from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps, BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface
)
from py_ballisticcalc_exts.result cimport BCLIBC_Result, monostate

cdef extern from "include/bclibc/dormand_prince.hpp" namespace "bclibc" nogil:
    BCLIBC_Result[monostate] BCLIBC_integrateDormandPrince(
        BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) noexcept

    # Stateful functor: owns its own tolerances/step-counts per instance,
    # replacing the old thread-local free-function API.
    cdef cppclass BCLIBC_DormandPrinceIntegrator:
        BCLIBC_DormandPrinceIntegrator() except +
        BCLIBC_Result[monostate] operator()(
            BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) noexcept
        void get_stats(int &, int &) const
        BCLIBC_Result[monostate] set_relative_tolerance(double tolerance) noexcept
        BCLIBC_Result[monostate] set_absolute_tolerance(double tolerance) noexcept


cdef class CythonizedDormandPrinceIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # Points at this instance's own integrator living inside
    # self._this.integrate_func (see __cinit__).
    cdef BCLIBC_DormandPrinceIntegrator* _integrator
    cdef int _last_accepted
    cdef int _last_rejected
