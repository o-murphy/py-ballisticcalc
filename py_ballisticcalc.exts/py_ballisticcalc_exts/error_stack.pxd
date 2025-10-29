cdef extern from "error_stack.h":
    DEF MAX_ERROR_STACK = 16
    DEF MAX_ERROR_MSG_LEN = 256

    ctypedef enum StatusCode:
        STATUS_SUCCESS
        STATUS_ERROR

    ctypedef enum ErrorSource:
        SRC_INTEGRATE
        SRC_FIND_APEX
        SRC_INIT_ZERO
        SRC_ZERO_ANGLE
        SRC_FIND_ZERO_ANGLE
        SRC_ERROR_AT_DISTANCE
        SRC_FIND_MAX_RANGE
        SRC_RANGE_FOR_ANGLE

    ctypedef enum ErrorType:
        T_NO_ERROR
        T_ZERO_DIVISION_ERROR
        T_VALUE_ERROR
        T_KEY_ERROR
        T_INDEX_ERROR
        T_MEMORY_ERROR
        T_ARITHMETIC_ERROR
        T_INPUT_ERROR
        T_RUNTIME_ERROR

        T_APEX_ERROR
        T_ZERO_FINDING_ERROR
        T_OUT_OF_RANGE_ERROR

    ctypedef struct ErrorFrame:
        ErrorType code
        ErrorSource src
        const char *func
        const char *file
        int line
        char msg[MAX_ERROR_MSG_LEN]

    ctypedef struct ErrorStack:
        ErrorFrame frames[MAX_ERROR_STACK]
        int top

    void push_err(
        ErrorStack *stack,
        ErrorType code,
        ErrorSource src,
        const char *func,
        const char *file,
        int line,
        const char *fmt,
        ...
    )
    void pop_err(ErrorStack *stack)
    void clear_err(ErrorStack *stack)
    const ErrorFrame *last_err(const ErrorStack *stack)
    void print_error_stack(const ErrorStack *stack)
    void error_stack_to_string(const ErrorStack *stack, char *out, size_t out_size)
