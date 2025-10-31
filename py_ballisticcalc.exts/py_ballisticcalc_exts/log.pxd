# cython: freethreading_compatible=True

cdef extern from "include/log.h" nogil:
    ctypedef enum LogLevel:
        LOG_LEVEL_CRITICAL = 50
        LOG_LEVEL_ERROR = 40
        LOG_LEVEL_WARNING = 30  # Default for fprintf warnings
        LOG_LEVEL_INFO = 20
        LOG_LEVEL_DEBUG = 10
        LOG_LEVEL_NOTSET = 0

    void initLogLevel() noexcept nogil
