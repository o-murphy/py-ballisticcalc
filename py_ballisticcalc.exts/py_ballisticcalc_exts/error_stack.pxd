cdef extern from "error_stack.h":
    DEF MAX_ERROR_STACK = 16
    DEF MAX_ERROR_MSG_LEN = 256

    ctypedef enum StatusCode:
        SUCCESS
        ERROR

    ctypedef enum ErrorSource:
        INTEGRATE
        FIND_APEX
        ZERO_ANGLE
        FIND_ZERO_ANGLE
        ERROR_AT_DISTANCE

    ctypedef enum ErrorType:
        NO_ERROR
        ZERO_DIVISION_ERROR
        VALUE_ERROR
        KEY_ERROR
        INDEX_ERROR
        MEMORY_ERROR
        ARITHMETIC_ERROR
        INPUT_ERROR
        RUNTIME_ERROR

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
