# cython: freethreading_compatible=True

cdef extern from "include/bclibc/log.hpp" namespace "bclibc" nogil:
    cdef enum class BCLIBC_LogLevel:
        CRITICAL = 50
        ERROR = 40
        WARNING = 30
        INFO = 20
        DEBUG = 10
        NOTSET = 0

    # NOTE: The C++ function 'log' is variadic (takes '...').
    # Calling variadic functions directly from Cython is complex.
    # For production use, consider creating a C++ wrapper function
    # that accepts a simple pre-formatted message string.
    void log(BCLIBC_LogLevel level,
             const char* file,
             int line,
             const char* func,
             const char* format,
             ...) noexcept nogil

    # Expose helper function to get string representation (optional, but useful)
    const char* level_to_string(BCLIBC_LogLevel level) noexcept nogil

    # The old C function BCLIBC_LogLevel_init() has been removed as
    # log level initialization is now handled automatically on first access.
