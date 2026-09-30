# pxd for velocity_verlet_engine to expose CythonizedVelocityVerletIntegrationEngine
from py_ballisticcalc_exts.base_types cimport BCLIBC_TerminationReason
from py_ballisticcalc_exts.base_engine cimport (
    BCLIBC_BaseEngine,
    CythonizedBaseIntegrationEngine,
    BCLIBC_BaseTrajDataHandlerInterface,
)
from py_ballisticcalc_exts.result cimport BCLIBC_Result, monostate


cdef extern from "include/bclibc/velocity_verlet.hpp" namespace "bclibc" nogil:

    BCLIBC_Result[monostate] BCLIBC_integrateVELOCITY_VERLET(
        BCLIBC_BaseEngine &eng,
        BCLIBC_BaseTrajDataHandlerInterface &handler,
        BCLIBC_TerminationReason &reason,
    ) noexcept

cdef class CythonizedVelocityVerletIntegrationEngine(CythonizedBaseIntegrationEngine):
    pass
