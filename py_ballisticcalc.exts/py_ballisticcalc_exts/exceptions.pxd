# bclibc never throws: BCLIBC_BaseEngine's methods return a Result, unwrapped in Cython
# via the py_engine_*() wrappers in base_engine.pxd, which fill a PyEngineError on failure.
# This module turns that plain struct into the same rich py_ballisticcalc.exceptions type the
# old dynamic_cast-based exception_dispatch used to raise from a caught C++ exception.

from py_ballisticcalc_exts.base_engine cimport PyEngineError
from py_ballisticcalc_exts.traj_data cimport (
    CythonizedBaseTrajData,
    TrajectoryData_from_cpp,
)
from py_ballisticcalc_exts.bind cimport (
    feet_from_c,
    rad_from_c,
)


cdef inline void raise_engine_error(const PyEngineError &err):
    """Raises the py_ballisticcalc exception matching a failed py_engine_*() call.

    err.kind:
        1 - BCLIBC_SolverOutOfRangeError  -> OutOfRangeError
        2 - BCLIBC_SolverZeroFindingError -> ZeroFindingError
        3 - BCLIBC_SolverInterceptionError -> InterceptionError
        0 - anything else (BCLIBC_LogicError/DomainError/RuntimeError/OutOfRangeError/
            InvalidArgumentError) -> SolverRuntimeError, the same catch-all bucket the old
            dynamic_cast dispatch used for every solver error without a specific handler.
    """
    from py_ballisticcalc.exceptions import (
        OutOfRangeError, ZeroFindingError, InterceptionError, SolverRuntimeError,
    )
    cdef str message = err.message.decode("utf-8")
    cdef CythonizedBaseTrajData raw_data
    cdef object py_full_data

    if err.kind == 1:
        raise OutOfRangeError(
            feet_from_c(err.f0), feet_from_c(err.f1), rad_from_c(err.f2), message
        )
    elif err.kind == 2:
        raise ZeroFindingError(
            err.f0, err.i0, rad_from_c(err.f1), message
        )
    elif err.kind == 3:
        raw_data = CythonizedBaseTrajData()
        raw_data._this = err.raw_data
        py_full_data = TrajectoryData_from_cpp(err.full_data)
        raise InterceptionError(message, (raw_data, py_full_data))
    else:
        raise SolverRuntimeError(message)
