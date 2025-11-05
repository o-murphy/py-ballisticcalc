#ifndef BCLIBC_ERROR_STACK_H
#define BCLIBC_ERROR_STACK_H

#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "bclibc_log.h"

#define BCLIBC_MAX_ERROR_STACK 16
#define BCLIBC_MAX_ERROR_MSG_LEN 256

typedef enum
{
    BCLIBC_STATUS_SUCCESS = 0x0000,
    BCLIBC_STATUS_ERROR = 0x0001,
} BCLIBC_StatusCode;

typedef enum
{
    BCLIBC_SRC_INTEGRATE,
    BCLIBC_SRC_FIND_APEX,
    BCLIBC_SRC_INIT_ZERO,
    BCLIBC_SRC_ZERO_ANGLE,
    BCLIBC_SRC_FIND_ZERO_ANGLE,
    BCLIBC_SRC_ERROR_AT_DISTANCE,
    BCLIBC_SRC_FIND_MAX_RANGE,
    BCLIBC_SRC_RANGE_FOR_ANGLE,
} BCLIBC_ErrorSource;

typedef enum
{
    // General
    BCLIBC_E_NO_ERROR,
    BCLIBC_E_ZERO_DIVISION_ERROR,
    BCLIBC_E_VALUE_ERROR,
    BCLIBC_E_BASE_TRAJ_INTERP_KEY_ERROR,
    BCLIBC_E_INDEX_ERROR,
    BCLIBC_E_MEMORY_ERROR,
    BCLIBC_E_ARITHMETIC_ERROR,
    BCLIBC_E_INPUT_ERROR,
    BCLIBC_E_RUNTIME_ERROR,
    // Special
    BCLIBC_E_ZERO_FINDING_ERROR,
    BCLIBC_E_OUT_OF_RANGE_ERROR,
} BCLIBC_ErrorType;

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

#ifdef __cplusplus
extern "C"
{
#endif

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

#ifdef __cplusplus
}
#endif

#define BCLIBC_PUSH_ERR(stack, code, src, format, ...) \
    BCLIBC_ErrorStack_pushErr((stack), (code), (src), __func__, __FILE__, __LINE__, format, ##__VA_ARGS__)

// #define BCLIBC_RETURN_ERR(stack, code, src, format, ...)          \
//     do                                                     \
//     {                                                      \
//         BCLIBC_PUSH_ERR(stack, code, src, format, ##__VA_ARGS__); \
//         return ERROR;                                      \
//     } while (0)

#define BCLIBC_POP_ERR(stack) BCLIBC_ErrorStack_popErr(stack)
#define BCLIBC_CLEAR_ERR(stack) BCLIBC_ErrorStack_clearErr(stack)

#endif // BCLIBC_ERROR_STACK_H
