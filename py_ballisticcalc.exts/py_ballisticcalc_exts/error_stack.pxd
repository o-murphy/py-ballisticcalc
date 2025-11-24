cdef extern from "include/bclibc/error_stack.hpp" namespace "bclibc" nogil:
    DEF BCLIBC_MAX_ERROR_STACK = 16
    DEF BCLIBC_MAX_ERROR_MSG_LEN = 256
    DEF BCLIBC_MAX_ERROR_TRACE_LEN = 4096

    cdef enum class BCLIBC_StatusCode:
        SUCCESS
        ERROR

    cdef enum class BCLIBC_ErrorSource:
        INTEGRATE
        FIND_APEX
        INIT_ZERO
        ZERO_ANGLE
        FIND_ZERO_ANGLE
        ERROR_AT_DISTANCE
        FIND_MAX_RANGE
        RANGE_FOR_ANGLE

    cdef enum class BCLIBC_ErrorType:
        NO_ERROR
        ZERO_FINDING_ERROR
        OUT_OF_RANGE_ERROR

    ctypedef struct BCLIBC_ErrorFrame:
        BCLIBC_ErrorType code
        BCLIBC_ErrorSource src
        const char *func
        const char *file
        int line
        char msg[BCLIBC_MAX_ERROR_MSG_LEN]

    ctypedef struct BCLIBC_ErrorStack:
        BCLIBC_ErrorFrame frames[BCLIBC_MAX_ERROR_STACK]
        int top

    void BCLIBC_ErrorStack_pushErr(
        BCLIBC_ErrorStack *stack,
        BCLIBC_ErrorType code,
        BCLIBC_ErrorSource src,
        const char *func,
        const char *file,
        int line,
        const char *fmt,
        ...
    )
    void BCLIBC_ErrorStack_popErr(BCLIBC_ErrorStack *stack)
    void BCLIBC_ErrorStack_clearErr(BCLIBC_ErrorStack *stack)
    const BCLIBC_ErrorFrame *BCLIBC_ErrorStack_lastErr(const BCLIBC_ErrorStack *stack)
    void BCLIBC_ErrorStack_print(const BCLIBC_ErrorStack *stack)
    void BCLIBC_ErrorStack_toString(const BCLIBC_ErrorStack *stack, char *out, size_t out_size)
