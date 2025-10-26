
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

    // C_LOG(T_LOG_LEVEL_ERROR, "%s", f->msg);
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
