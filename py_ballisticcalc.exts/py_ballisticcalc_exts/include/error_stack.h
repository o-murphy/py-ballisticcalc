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
    SUCCESS,
    ERROR,
} StatusCode;

typedef enum
{
    INTEGRATE,
    FIND_APEX,
    ZERO_ANGLE,
    FIND_ZERO_ANGLE,
    ERROR_AT_DISTANCE,
} ErrorSource;

typedef enum
{
    NO_ERROR,
    ZERO_DIVISION_ERROR,
    VALUE_ERROR,
    KEY_ERROR,
    INDEX_ERROR,
    MEMORY_ERROR,
    ARITHMETIC_ERROR,
    INPUT_ERROR,
    RUNTIME_ERROR,
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
        ...)
    {
        if (!stack || stack->top >= MAX_ERROR_STACK)
            return;

        ErrorFrame *f = &stack->frames[stack->top++];

        f->code = code;
        f->src = src;
        f->func = func;
        f->file = file;
        f->line = line;

        va_list args;
        va_start(args, fmt);
        vsnprintf(f->msg, sizeof(f->msg), fmt, args);
        va_end(args);

        f->msg[sizeof(f->msg) - 1] = '\0';

        // C_LOG(LOG_LEVEL_ERROR, "%s", f->msg);
    }

    void pop_err(ErrorStack *stack)
    {
        if (stack && stack->top > 0)
        {
            stack->top--;
            memset(&stack->frames[stack->top], 0, sizeof(ErrorFrame));
            // ErrorFrame *f = &stack->frames[--stack->top];
            // C_LOG(LOG_LEVEL_DEBUG, "Popped error frame [%d/%d]: %s:%d (%s): [%d/%d] %s",
            //  stack->top, MAX_ERROR_STACK,
            //  f->file, f->line, f->func, f->src, f->code, f->msg);
        }
    }

    void clear_err(ErrorStack *stack)
    {
        if (!stack)
            return;
        memset(stack->frames, 0, sizeof(stack->frames));
        stack->top = 0;
    }

    const ErrorFrame *last_err(const ErrorStack *stack)
    {
        if (!stack || stack->top <= 0)
            return NULL;
        return &stack->frames[stack->top - 1];
    }

    void print_error_stack(const ErrorStack *stack)
    {
        if (!stack)
            return;
        for (int i = stack->top - 1; i >= 0; i--)
        {
            const ErrorFrame *f = &stack->frames[i];
            fprintf(stderr, "[%d] %s:%d (%s): [%d/%d] %s\n",
                    i, f->file, f->line, f->func, f->src, f->code, f->msg);
        }
    }

#ifdef __cplusplus
}
#endif

#define PUSH_ERR(stack, code, src, ...) \
    push_err((stack), (code), (src), __func__, __FILE__, __LINE__, __VA_ARGS__)

// Usage example
// if (angle <= 0.0)
//     RETURN_ERR(&eng->err_stack, VALUE_ERROR, FIND_APEX,
//                "Invalid angle %.2f — must be positive", angle);

#define PUSH_ERR_LOG(stack, code, src, ...)      \
    do                                           \
    {                                            \
        PUSH_ERR(stack, code, src, __VA_ARGS__); \
        C_LOG(LOG_LEVEL_ERROR, __VA_ARGS__);     \
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
        C_LOG(LOG_LEVEL_ERROR, __VA_ARGS__);     \
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