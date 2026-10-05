# pxd for the engines module: every compiled integration engine (RK4, Euler, Velocity Verlet, Cash-Karp,
# Dormand-Prince, Tsitouras) lives in one extension module so the bclibc integrator sources are linked once.
from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps, BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface,
)
from py_ballisticcalc_exts.result cimport BCLIBC_Result, monostate


cdef extern from "include/bclibc/rk4.hpp" namespace "bclibc" nogil:

    BCLIBC_Result[monostate] BCLIBC_integrateRK4(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) noexcept

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    pass


cdef extern from "include/bclibc/euler.hpp" namespace "bclibc" nogil:

    BCLIBC_Result[monostate] BCLIBC_integrateEULER(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) noexcept

cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    pass


cdef extern from "include/bclibc/velocity_verlet.hpp" namespace "bclibc" nogil:

    BCLIBC_Result[monostate] BCLIBC_integrateVELOCITY_VERLET(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) noexcept

cdef class CythonizedVelocityVerletIntegrationEngine(CythonizedBaseIntegrationEngine):
    pass


cdef extern from "include/bclibc/cash_karp.hpp" namespace "bclibc" nogil:

    BCLIBC_Result[monostate] BCLIBC_integrateCashKarp(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) noexcept

    # Stateful functor: owns its own tolerances/step-counts per instance
    # (each field a std::atomic on the C++ side), replacing the old
    # thread-local free-function API (BCLIBC_cashKarpGetStats/Set*Tolerance).
    cdef cppclass BCLIBC_CashKarpIntegrator:
        BCLIBC_CashKarpIntegrator() noexcept
        BCLIBC_Result[monostate] operator()(
            BCLIBC_BaseEngine &eng,
            BCLIBC_BaseTrajDataHandlerInterface &handler,
            BCLIBC_TerminationReason &reason,
        ) noexcept
        void get_stats(int &out_accepted, int &out_rejected) const
        BCLIBC_Result[monostate] set_relative_tolerance(double tolerance) noexcept
        BCLIBC_Result[monostate] set_absolute_tolerance(double tolerance) noexcept


cdef class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # This instance's own integrator, held by value (its tolerances/stats are exclusively this engine's).
    # self._this.integrate_func stores a std::reference_wrapper to it (see __cinit__), so it must stay
    # in place for the engine's life -- true for a cdef-class attribute.
    cdef BCLIBC_CashKarpIntegrator _integrator
    # Snapshot of self._integrator.get_stats(), taken right after this
    # engine's own integrate() call returns.
    cdef int _last_accepted
    cdef int _last_rejected

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedCashKarpIntegrationEngine self,
        object shot_info,
    )
    cdef void _snapshot_step_stats(CythonizedCashKarpIntegrationEngine self)


cdef extern from "include/bclibc/dormand_prince.hpp" namespace "bclibc" nogil:
    BCLIBC_Result[monostate] BCLIBC_integrateDormandPrince(
        BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) noexcept

    # Stateful functor: owns its own tolerances/step-counts per instance,
    # replacing the old thread-local free-function API.
    cdef cppclass BCLIBC_DormandPrinceIntegrator:
        BCLIBC_DormandPrinceIntegrator() noexcept
        BCLIBC_Result[monostate] operator()(
            BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) noexcept
        void get_stats(int &, int &) const
        BCLIBC_Result[monostate] set_relative_tolerance(double tolerance) noexcept
        BCLIBC_Result[monostate] set_absolute_tolerance(double tolerance) noexcept


cdef class CythonizedDormandPrinceIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # This instance's own integrator, held by value (its tolerances/stats are exclusively this engine's).
    # self._this.integrate_func stores a std::reference_wrapper to it (see __cinit__), so it must stay
    # in place for the engine's life -- true for a cdef-class attribute.
    cdef BCLIBC_DormandPrinceIntegrator _integrator
    cdef int _last_accepted
    cdef int _last_rejected


cdef extern from "include/bclibc/tsitouras.hpp" namespace "bclibc" nogil:
    BCLIBC_Result[monostate] BCLIBC_integrateTsitouras(
        BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) noexcept

    # Stateful functor: owns its own tolerances/step-counts per instance,
    # replacing the old thread-local free-function API.
    cdef cppclass BCLIBC_TsitourasIntegrator:
        BCLIBC_TsitourasIntegrator() noexcept
        BCLIBC_Result[monostate] operator()(
            BCLIBC_BaseEngine &, BCLIBC_BaseTrajDataHandlerInterface &, BCLIBC_TerminationReason &) noexcept
        void get_stats(int &, int &) const
        BCLIBC_Result[monostate] set_relative_tolerance(double tolerance) noexcept
        BCLIBC_Result[monostate] set_absolute_tolerance(double tolerance) noexcept


cdef class CythonizedTsitourasIntegrationEngine(CythonizedBaseIntegrationEngine):
    cdef double _relative_tolerance
    cdef double _absolute_tolerance
    # This instance's own integrator, held by value (its tolerances/stats are exclusively this engine's).
    # self._this.integrate_func stores a std::reference_wrapper to it (see __cinit__), so it must stay
    # in place for the engine's life -- true for a cdef-class attribute.
    cdef BCLIBC_TsitourasIntegrator _integrator
    cdef int _last_accepted
    cdef int _last_rejected
