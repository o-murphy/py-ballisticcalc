#ifndef BCLIBC_ERROR_STACK_HPP
#define BCLIBC_ERROR_STACK_HPP

#include <cstdarg>
#include <cstring>
#include "bclibc/log.hpp"

#define BCLIBC_MAX_ERROR_STACK 16
#define BCLIBC_MAX_ERROR_MSG_LEN 256
#define BCLIBC_MAX_ERROR_TRACE_LEN 4096

namespace bclibc
{
    enum class BCLIBC_StatusCode
    {
        SUCCESS = 0x0000,
        ERROR = 0x0001,
    };

    enum class BCLIBC_ErrorSource
    {
        INTEGRATE,
        FIND_APEX,
        INIT_ZERO,
        ZERO_ANGLE,
        FIND_ZERO_ANGLE,
        ERROR_AT_DISTANCE,
        FIND_MAX_RANGE,
        RANGE_FOR_ANGLE,
    };

    enum class BCLIBC_ErrorType
    {
        // General
        NO_ERROR,
        ZERO_DIVISION_ERROR,
        VALUE_ERROR,
        BASE_TRAJ_INTERP_KEY_ERROR,
        INDEX_ERROR,
        MEMORY_ERROR,
        ARITHMETIC_ERROR,
        INPUT_ERROR,
        RUNTIME_ERROR,
        // Special
        ZERO_FINDING_ERROR,
        OUT_OF_RANGE_ERROR,
    };

    typedef struct
    {
        BCLIBC_ErrorType code;
        BCLIBC_ErrorSource src;
        const char *func;
        const char *file;
        int line;
        char msg[BCLIBC_MAX_ERROR_MSG_LEN];
    } BCLIBC_ErrorFrame;

    typedef struct
    {
        BCLIBC_ErrorFrame frames[BCLIBC_MAX_ERROR_STACK];
        int top;
    } BCLIBC_ErrorStack;

    void BCLIBC_ErrorStack_pushErr(
        BCLIBC_ErrorStack *stack,
        BCLIBC_ErrorType code,
        BCLIBC_ErrorSource src,
        const char *func,
        const char *file,
        int line,
        const char *fmt,
        ...);
    void BCLIBC_ErrorStack_popErr(BCLIBC_ErrorStack *stack);
    void BCLIBC_ErrorStack_clearErr(BCLIBC_ErrorStack *stack);
    const BCLIBC_ErrorFrame *BCLIBC_ErrorStack_lastErr(const BCLIBC_ErrorStack *stack);
    void BCLIBC_ErrorStack_print(const BCLIBC_ErrorStack *stack);
    void BCLIBC_ErrorStack_toString(const BCLIBC_ErrorStack *stack, char *out, size_t out_size);

    void BCLIBC_requireNonNullFatal(const void *ptr, const char *file, int line, const char *func);
};

#define BCLIBC_PUSH_ERR(stack, code, src, format, ...) \
    BCLIBC_ErrorStack_pushErr((stack), (code), (src), __func__, __FILE__, __LINE__, format, ##__VA_ARGS__)

#define BCLIBC_POP_ERR(stack) BCLIBC_ErrorStack_popErr(stack)
#define BCLIBC_CLEAR_ERR(stack) BCLIBC_ErrorStack_clearErr(stack)

#define REQUIRE_NON_NULL(ptr) \
    BCLIBC_requireNonNullFatal((ptr), __FILE__, __LINE__, __func__)

#endif // BCLIBC_ERROR_STACK_HPP
