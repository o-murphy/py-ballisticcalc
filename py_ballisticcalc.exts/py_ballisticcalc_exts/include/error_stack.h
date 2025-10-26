#ifndef BCLIB_ERROR_STACK_H
#define BCLIB_ERROR_STACK_H

// without prev
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "log.h"

#define MAX_ERROR_STACK 16
#define MAX_ERROR_MSG_LEN 256

typedef enum
{
    STATUS_SUCCESS,
    STATUS_ERROR,
} StatusCode;

typedef enum
{
    SRC_INTEGRATE,
    SRC_FIND_APEX,
    SRC_ZERO_ANGLE,
    SRC_FIND_ZERO_ANGLE,
    SRC_ERROR_AT_DISTANCE,
} ErrorSource;

typedef enum
{
    T_NO_ERROR,
    T_ZERO_DIVISION_ERROR,
    T_VALUE_ERROR,
    T_KEY_ERROR,
    T_INDEX_ERROR,
    T_MEMORY_ERROR,
    T_ARITHMETIC_ERROR,
    T_INPUT_ERROR,
    T_RUNTIME_ERROR,
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

#ifdef __cplusplus
}
#endif

#define PUSH_ERR(stack, code, src, ...) \
    push_err((stack), (code), (src), __func__, __FILE__, __LINE__, __VA_ARGS__)

// Usage example
// if (angle <= 0.0)
//     RETURN_ERR(&eng->err_stack, T_VALUE_ERROR, FIND_APEX,
//                "Invalid angle %.2f — must be positive", angle);

#define PUSH_ERR_LOG(stack, code, src, ...)      \
    do                                           \
    {                                            \
        PUSH_ERR(stack, code, src, __VA_ARGS__); \
        C_LOG(T_LOG_LEVEL_ERROR, __VA_ARGS__);   \
    } while (0)

#define POP_ERR(stack) \
    pop_err((stack))

#define POP_ERR_LOG(stack)                                              \
    do                                                                  \
    {                                                                   \
        if (stack && stack->top > 0)                                    \
        {                                                               \
            ErrorFrame *f = &stack->frames[stack->top - 1];             \
            C_LOG(LOG_LEVEL_DEBUG,                                      \
                  "Popped error frame [%d/%d]: %s:%d (%s): [%d/%d] %s", \
                  stack->top - 1, MAX_ERROR_STACK,                      \
                  f->file, f->line, f->func, f->src, f->code, f->msg);  \
        }                                                               \
        POP_ERR(stack);                                                 \
    } while (0)

#define RETURN_ERR(stack, code, src, ...)              \
    do                                                 \
    {                                                  \
        PUSH_ERR((stack), (code), (src), __VA_ARGS__); \
        return ERROR;                                  \
    } while (0)

#define RETURN_ERR_LOG(stack, code, src, ...)    \
    do                                           \
    {                                            \
        PUSH_ERR(stack, code, src, __VA_ARGS__); \
        C_LOG(T_LOG_LEVEL_ERROR, __VA_ARGS__);   \
        return ERROR;                            \
    } while (0)

#define CLEAR_ERR(stack) \
    clear_err((stack))

#define CLEAR_ERR_LOG(stack)                           \
    do                                                 \
    {                                                  \
        CLEAR_ERR(stack);                              \
        C_LOG(LOG_LEVEL_DEBUG, "Error stack cleared"); \
    } while (0)

#endif // BCLIB_ERROR_STACK_H