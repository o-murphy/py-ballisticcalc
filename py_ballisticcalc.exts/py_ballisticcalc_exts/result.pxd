# Cython view of bclibc's noexcept error path (include/bclibc/result.hpp, exceptions.hpp).
#
# bclibc never throws: a fallible function returns BCLIBC_Result[T], checked with has_value().
# BCLIBC_Error is one tagged sum of the payload structs; Cython only needs its kind(), what()
# and the payload[P]() accessor (a pointer, nullptr for any other alternative), so the
# std::variant inside it never shows up here. The payload structs are declared in exceptions.pxd
# (they carry trajectory types), the Python exceptions raised from them in raise_engine_error().

cdef extern from "<variant>" namespace "std" nogil:
    cdef cppclass monostate:
        pass


cdef extern from "bclibc/exceptions.hpp" namespace "bclibc" nogil:
    cdef enum class BCLIBC_ErrorKind "bclibc::BCLIBC_Error::Kind":
        Logic
        Domain
        Runtime
        OutOfRange
        InvalidArgument
        SolverZeroFinding
        SolverOutOfRange
        SolverInterception
        SolverRuntime

    cdef cppclass BCLIBC_Error:
        BCLIBC_ErrorKind kind() noexcept const
        const char *what() noexcept const
        const P *payload[P]() noexcept const

    # The C++ template has a second parameter, the error type, that defaults to BCLIBC_Error.
    cdef cppclass BCLIBC_Result[T]:
        BCLIBC_Result() noexcept
        bint has_value() noexcept const
        T &value() noexcept
        const BCLIBC_Error &error() noexcept const


cdef inline void raise_std_error(const BCLIBC_Error &err):
    """Raises what Cython's default `except +` made of the std exception this error replaces.

    domain_error/invalid_argument -> ValueError, out_of_range -> IndexError, anything else ->
    RuntimeError, so a call that used to be declared plain `except +` keeps its Python type.
    """
    cdef BCLIBC_ErrorKind kind = err.kind()
    cdef str message = err.what().decode("utf-8")
    if kind == BCLIBC_ErrorKind.Domain or kind == BCLIBC_ErrorKind.InvalidArgument:
        raise ValueError(message)
    if kind == BCLIBC_ErrorKind.OutOfRange:
        raise IndexError(message)
    raise RuntimeError(message)
