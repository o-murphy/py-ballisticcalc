
#include "error_stack.h"

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

    C_LOG(LOG_LEVEL_ERROR, "%s:%d (%s): %s", file, line, func, f->msg);
}

void pop_err(ErrorStack *stack)
{
    if (stack && stack->top > 0)
    {
        // stack->top--;
        // memset(&stack->frames[stack->top], 0, sizeof(ErrorFrame));
        ErrorFrame *f = &stack->frames[--stack->top];
        C_LOG(LOG_LEVEL_DEBUG, "Popped error frame [%d/%d]: %s:%d (%s): [%d/%d] %s",
              stack->top, MAX_ERROR_STACK,
              f->file, f->line, f->func, f->src, f->code, f->msg);
        memset(&stack->frames[stack->top], 0, sizeof(ErrorFrame));
    }
}

void clear_err(ErrorStack *stack)
{
    if (!stack)
        return;
    memset(stack->frames, 0, sizeof(stack->frames));
    stack->top = 0;

    C_LOG(LOG_LEVEL_DEBUG, "Error stack cleared");
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

static const char* error_type_to_string(ErrorType code)
{
    switch (code)
    {
        case T_NO_ERROR: return "T_NO_ERROR";
        case T_ZERO_DIVISION_ERROR: return "T_ZERO_DIVISION_ERROR";
        case T_VALUE_ERROR: return "T_VALUE_ERROR";
        case T_KEY_ERROR: return "T_KEY_ERROR";
        case T_INDEX_ERROR: return "T_INDEX_ERROR";
        case T_MEMORY_ERROR: return "T_MEMORY_ERROR";
        case T_ARITHMETIC_ERROR: return "T_ARITHMETIC_ERROR";
        case T_INPUT_ERROR: return "T_INPUT_ERROR";
        case T_RUNTIME_ERROR: return "T_RUNTIME_ERROR";
        case T_ZERO_FINDING_ERROR: return "T_ZERO_FINDING_ERROR";
        case T_OUT_OF_RANGE_ERROR: return "T_OUT_OF_RANGE_ERROR";
        default: return "UNKNOWN_ERROR";
    }
}

static const char* error_source_to_string(ErrorSource src)
{
    switch (src)
    {
        case SRC_INTEGRATE: return "SRC_INTEGRATE";
        case SRC_FIND_APEX: return "SRC_FIND_APEX";
        case SRC_ZERO_ANGLE: return "SRC_ZERO_ANGLE";
        case SRC_FIND_ZERO_ANGLE: return "SRC_FIND_ZERO_ANGLE";
        case SRC_ERROR_AT_DISTANCE: return "SRC_ERROR_AT_DISTANCE";
        case SRC_FIND_MAX_RANGE: return "SRC_FIND_MAX_RANGE";
        case SRC_RANGE_FOR_ANGLE: return "SRC_RANGE_FOR_ANGLE";
        case SRC_INIT_ZERO: return "SRC_INIT_ZERO";
        default: return "UNKNOWN_SOURCE";
    }
}

void error_stack_to_string(const ErrorStack *stack, char *out, size_t out_size)
{
    if (!stack || !out || out_size == 0)
        return;

    out[0] = '\0';
    for (int i = 0; i < stack->top; i++)
    {
        const ErrorFrame *f = &stack->frames[i];
        char line[256];
        snprintf(line, sizeof(line),
                 "[%d] %s:%d (%s): [src=%d (%s), code=%d (%s)] %s\n",
                 i,
                 f->file,
                 f->line,
                 f->func,
                 f->src,
                 error_source_to_string(f->src),
                 f->code,
                 error_type_to_string(f->code),
                 f->msg);
        strncat(out, line, out_size - strlen(out) - 1);
    }
}
