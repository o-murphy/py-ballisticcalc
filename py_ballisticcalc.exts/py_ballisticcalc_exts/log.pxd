# cython: freethreading_compatible=True

cdef extern from "include/bclibc_log.h" nogil:
    ctypedef enum BCLIBC_LogLevel:
        BCLIBC_LOG_LEVEL_CRITICAL = 50
        BCLIBC_LOG_LEVEL_ERROR = 40
        BCLIBC_LOG_LEVEL_WARNING = 30  # Default for fprintf warnings
        BCLIBC_LOG_LEVEL_INFO = 20
        BCLIBC_LOG_LEVEL_DEBUG = 10
        BCLIBC_LOG_LEVEL_NOTSET = 0

    void BCLIBC_LogLevel_init() noexcept nogil
