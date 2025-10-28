#ifndef BCLIB_ERROR_STACK_H
#define BCLIB_ERROR_STACK_H

#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "log.h"

#define MAX_ERROR_STACK 16
#define MAX_ERROR_MSG_LEN 256

typedef enum
{
    STATUS_SUCCESS = 0x0000,
    STATUS_ERROR = 0x0001,
} StatusCode;

typedef enum
{
    SRC_INTEGRATE,
    SRC_FIND_APEX,
    SRC_ZERO_ANGLE,
    SRC_FIND_ZERO_ANGLE,
    SRC_ERROR_AT_DISTANCE,
    SRC_FIND_MAX_RANGE,
    SRC_RANGE_FOR_ANGLE,
    SRC_INIT_ZERO,
} ErrorSource;

typedef enum
{
    // General
    T_NO_ERROR,
    T_ZERO_DIVISION_ERROR,
    T_VALUE_ERROR,
    T_KEY_ERROR,
    T_INDEX_ERROR,
    T_MEMORY_ERROR,
    T_ARITHMETIC_ERROR,
    T_INPUT_ERROR,
    T_RUNTIME_ERROR,
    // Special
    T_ZERO_FINDING_ERROR,
    T_OUT_OF_RANGE_ERROR,
} ErrorType;

typedef struct
{
    ErrorType code;
    ErrorSource src;
    const char *func;
    const char *file;
    int line;
    char msg[MAX_ERROR_MSG_LEN];
} ErrorFrame;

typedef struct
{
    ErrorFrame frames[MAX_ERROR_STACK];
    int top;
} ErrorStack;

#ifdef __cplusplus
extern "C"
{
#endif

    void push_err(
        ErrorStack *stack,
        ErrorType code,
        ErrorSource src,
        const char *func,
        const char *file,
        int line,
        const char *fmt,
        ...);
    void pop_err(ErrorStack *stack);
    void clear_err(ErrorStack *stack);
    const ErrorFrame *last_err(const ErrorStack *stack);
    void print_error_stack(const ErrorStack *stack);
    void error_stack_to_string(const ErrorStack *stack, char *out, size_t out_size);

#ifdef __cplusplus
}
#endif

#define PUSH_ERR(stack, code, src, format, ...) \
    push_err((stack), (code), (src), __func__, __FILE__, __LINE__, format, ##__VA_ARGS__)

// #define RETURN_ERR(stack, code, src, format, ...)          \
//     do                                                     \
//     {                                                      \
//         PUSH_ERR(stack, code, src, format, ##__VA_ARGS__); \
//         return ERROR;                                      \
//     } while (0)

#define POP_ERR(stack) pop_err(stack)
#define CLEAR_ERR(stack) clear_err(stack)

#endif // BCLIB_ERROR_STACK_H
