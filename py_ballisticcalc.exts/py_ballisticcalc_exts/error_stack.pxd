cdef extern from "include/bclibc_error_stack.h":
    DEF BCLIBC_MAX_ERROR_STACK = 16
    DEF BCLIBC_MAX_ERROR_MSG_LEN = 256

    ctypedef enum BCLIBC_StatusCode:
        BCLIBC_STATUS_SUCCESS
        BCLIBC_STATUS_ERROR

    ctypedef enum BCLIBC_ErrorSource:
        BCLIBC_SRC_INTEGRATE
        BCLIBC_SRC_FIND_APEX
        BCLIBC_SRC_INIT_ZERO
        BCLIBC_SRC_ZERO_ANGLE
        BCLIBC_SRC_FIND_ZERO_ANGLE
        BCLIBC_SRC_ERROR_AT_DISTANCE
        BCLIBC_SRC_FIND_MAX_RANGE
        BCLIBC_SRC_RANGE_FOR_ANGLE

    ctypedef enum BCLIBC_ErrorType:
        BCLIBC_E_NO_ERROR
        BCLIBC_E_ZERO_DIVISION_ERROR
        BCLIBC_E_VALUE_ERROR
        BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR
        BCLIBC_E_INDEX_ERROR
        BCLIBC_E_MEMORY_ERROR
        BCLIBC_E_ARITHMETIC_ERROR
        BCLIBC_E_INPUT_ERROR
        BCLIBC_E_RUNTIME_ERROR

        BCLIBC_E_APEX_ERROR
        BCLIBC_E_ZERO_FINDING_ERROR
        BCLIBC_E_OUT_OF_RANGE_ERROR

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
