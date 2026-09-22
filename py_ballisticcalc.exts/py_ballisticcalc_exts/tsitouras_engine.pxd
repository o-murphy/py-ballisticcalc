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
        void set_relative_tolerance(double) except +
        void set_absolute_tolerance(double) except +

cdef class CythonizedTsitourasIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # Points at this instance's own integrator living inside
    # self._this.integrate_func (see __cinit__).
    cdef BCLIBC_TsitourasIntegrator* _integrator
    cdef int _last_accepted
    cdef int _last_rejected
