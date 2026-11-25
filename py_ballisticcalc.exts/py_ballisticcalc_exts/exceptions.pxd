# bclibc never throws: its methods return a BCLIBC_Result (see result.pxd). This module turns
# the solver payloads of a BCLIBC_Error into the rich py_ballisticcalc.exceptions types the old
# dynamic_cast-based exception_dispatch raised from a caught C++ exception; every other error
# falls through to raise_std_error(), i.e. Cython's own default `except +` mapping.

from py_ballisticcalc_exts.result cimport (
    BCLIBC_Error,
    BCLIBC_ErrorKind,
)
from py_ballisticcalc_exts.traj_data cimport (
    BCLIBC_BaseTrajData,
    BCLIBC_TrajectoryData,
    CythonizedBaseTrajData,
    TrajectoryData_from_cpp,
)
from py_ballisticcalc_exts.bind cimport (
    feet_from_c,
    rad_from_c,
)


cdef extern from "bclibc/exceptions.hpp" namespace "bclibc" nogil:
    cdef cppclass BCLIBC_SolverOutOfRangeError:
        double requested_distance_ft
        double max_range_ft
        double look_angle_rad

    cdef cppclass BCLIBC_SolverZeroFindingError:
        double zero_finding_error
        int iterations_count
        double last_barrel_elevation_rad

    cdef cppclass BCLIBC_SolverInterceptionError:
        BCLIBC_BaseTrajData raw_data
        BCLIBC_TrajectoryData full_data


cdef inline str strip_core_decoration(str message):
    """Drops the kind prefix the C++ core puts on some messages, to match the pure-Python engines' text.

    "Value error (X)." -> "X." and "Runtime error (X)" -> "X": the exact prefix, and the ')' that closes it
    (the text after it, such as the final period, is kept). Anything else, including the complete messages of
    the zero-finding errors, passes through unchanged.

    OutOfRangeError is deliberately NOT normalised: the Python engines report the caller's unit, the C++ core
    feet plus ". Out of range". That difference is intentional and documented.
    """
    cdef str prefix
    cdef Py_ssize_t close
    for prefix in ("Value error (", "Runtime error ("):
        if message.startswith(prefix):
            close = message.rfind(")")
            if close > len(prefix):
                return message[len(prefix):close] + message[close + 1:]
    return message


cdef inline void raise_engine_error(const BCLIBC_Error &err):
    """Raises the py_ballisticcalc exception matching a failed BCLIBC_BaseEngine call.

    BCLIBC_Solver{OutOfRange,ZeroFinding,Interception,Runtime}Error -> OutOfRangeError,
    ZeroFindingError, InterceptionError, SolverRuntimeError; the std kinds ->
    ValueError/IndexError/RuntimeError as raise_std_error() maps them.
    Every message goes through strip_core_decoration().
    """
    from py_ballisticcalc.exceptions import (
        OutOfRangeError, ZeroFindingError, InterceptionError, SolverRuntimeError,
    )
    cdef BCLIBC_ErrorKind kind = err.kind()
    cdef str message = strip_core_decoration(err.what().decode("utf-8"))
    cdef const BCLIBC_SolverOutOfRangeError *out_of_range
    cdef const BCLIBC_SolverZeroFindingError *zero_finding
    cdef const BCLIBC_SolverInterceptionError *interception
    cdef CythonizedBaseTrajData raw_data
    cdef object py_full_data

    if kind == BCLIBC_ErrorKind.SolverOutOfRange:
        out_of_range = err.payload[BCLIBC_SolverOutOfRangeError]()
        raise OutOfRangeError(
            feet_from_c(out_of_range.requested_distance_ft),
            feet_from_c(out_of_range.max_range_ft),
            rad_from_c(out_of_range.look_angle_rad),
            message,
        )
    elif kind == BCLIBC_ErrorKind.SolverZeroFinding:
        zero_finding = err.payload[BCLIBC_SolverZeroFindingError]()
        raise ZeroFindingError(
            zero_finding.zero_finding_error,
            zero_finding.iterations_count,
            rad_from_c(zero_finding.last_barrel_elevation_rad),
            message,
        )
    elif kind == BCLIBC_ErrorKind.SolverInterception:
        interception = err.payload[BCLIBC_SolverInterceptionError]()
        raw_data = CythonizedBaseTrajData()
        raw_data._this = interception.raw_data
        py_full_data = TrajectoryData_from_cpp(interception.full_data)
        raise InterceptionError(message, (raw_data, py_full_data))
    elif kind == BCLIBC_ErrorKind.SolverRuntime:
        raise SolverRuntimeError(message)
    elif kind == BCLIBC_ErrorKind.Domain or kind == BCLIBC_ErrorKind.InvalidArgument:
        raise ValueError(message)  # the mapping of raise_std_error(), with the undecorated text
    elif kind == BCLIBC_ErrorKind.OutOfRange:
        raise IndexError(message)
    else:
        raise RuntimeError(message)
