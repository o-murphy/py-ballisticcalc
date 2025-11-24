#include <cstdlib>
#include "bclibc/error_stack.hpp"

namespace bclibc
{
    void BCLIBC_ErrorStack_pushErr(
        BCLIBC_ErrorStack *stack,
        BCLIBC_ErrorType code,
        BCLIBC_ErrorSource src,
        const char *func,
        const char *file,
        int line,
        const char *fmt,
        ...)
    {
        if (!stack || stack->top >= BCLIBC_MAX_ERROR_STACK)
            return;

        BCLIBC_ErrorFrame *f = &stack->frames[stack->top++];

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

        BCLIBC_ERROR("%s:%d (%s): %s", file, line, func, f->msg);
    };

    void BCLIBC_ErrorStack_popErr(BCLIBC_ErrorStack *stack)
    {
        if (stack && stack->top > 0)
        {
            // stack->top--;
            // memset(&stack->frames[stack->top], 0, sizeof(BCLIBC_ErrorFrame));
            BCLIBC_ErrorFrame *f = &stack->frames[--stack->top];
            BCLIBC_DEBUG("Popped error frame [%d/%d]: %s:%d (%s): [%d/%d] %s",
                         stack->top, BCLIBC_MAX_ERROR_STACK,
                         f->file, f->line, f->func, f->src, f->code, f->msg);
            memset(&stack->frames[stack->top], 0, sizeof(BCLIBC_ErrorFrame));
        }
    };

    void BCLIBC_ErrorStack_clearErr(BCLIBC_ErrorStack *stack)
    {
        if (!stack)
            return;
        memset(stack->frames, 0, sizeof(stack->frames));
        stack->top = 0;

        BCLIBC_DEBUG("Error stack cleared");
    };

    const BCLIBC_ErrorFrame *BCLIBC_ErrorStack_lastErr(const BCLIBC_ErrorStack *stack)
    {
        if (!stack || stack->top <= 0)
            return nullptr;
        return &stack->frames[stack->top - 1];
    };

    void BCLIBC_ErrorStack_print(const BCLIBC_ErrorStack *stack)
    {
        if (!stack)
            return;
        for (int i = stack->top - 1; i >= 0; i--)
        {
            const BCLIBC_ErrorFrame *f = &stack->frames[i];
            fprintf(stderr, "[%d] %s:%d (%s): [%d/%d] %s\n",
                    i, f->file, f->line, f->func, f->src, f->code, f->msg);
        }
    };

    static const char *BCLIBC_ErrorType_toString(BCLIBC_ErrorType code)
    {
        switch (code)
        {
        case BCLIBC_ErrorType::ZERO_FINDING_ERROR:
            return "BCLIBC_ErrorType::ZERO_FINDING_ERROR";
        case BCLIBC_ErrorType::OUT_OF_RANGE_ERROR:
            return "BCLIBC_ErrorType::OUT_OF_RANGE_ERROR";
        default:
            return "UNKNOWN_ERROR";
        }
    };

    static const char *BCLIBC_ErrorSource_toString(BCLIBC_ErrorSource src)
    {
        switch (src)
        {
        case BCLIBC_ErrorSource::INTEGRATE:
            return "BCLIBC_ErrorType::INTEGRATE";
        case BCLIBC_ErrorSource::FIND_APEX:
            return "BCLIBC_ErrorType::FIND_APEX";
        case BCLIBC_ErrorSource::ZERO_ANGLE:
            return "BCLIBC_ErrorType::ZERO_ANGLE";
        case BCLIBC_ErrorSource::FIND_ZERO_ANGLE:
            return "BCLIBC_ErrorType::FIND_ZERO_ANGLE";
        case BCLIBC_ErrorSource::ERROR_AT_DISTANCE:
            return "BCLIBC_ErrorType::ERROR_AT_DISTANCE";
        case BCLIBC_ErrorSource::FIND_MAX_RANGE:
            return "BCLIBC_ErrorType::FIND_MAX_RANGE";
        case BCLIBC_ErrorSource::RANGE_FOR_ANGLE:
            return "BCLIBC_ErrorType::RANGE_FOR_ANGLE";
        case BCLIBC_ErrorSource::INIT_ZERO:
            return "BCLIBC_ErrorType::INIT_ZERO";
        default:
            return "UNKNOWN_SOURCE";
        }
    };

    void BCLIBC_ErrorStack_toString(const BCLIBC_ErrorStack *stack, char *out, size_t out_size)
    {
        if (!stack || !out || out_size == 0)
            return;

        out[0] = '\0';
        for (int i = 0; i < stack->top; i++)
        {
            const BCLIBC_ErrorFrame *f = &stack->frames[i];
            char line[BCLIBC_MAX_ERROR_TRACE_LEN];

            const int FILE_WIDTH = 50;
            const int FUNC_WIDTH = 25;

            snprintf(line, sizeof(line),
                     "[%d] %-*s :%-4d (%s) : [src=%-2d (%s), code=%-2d (%s)] %s\n",
                     i,
                     FILE_WIDTH, f->file,
                     f->line,
                     f->func,
                     f->src,
                     BCLIBC_ErrorSource_toString(f->src),
                     f->code,
                     BCLIBC_ErrorType_toString(f->code),
                     f->msg);

            strncat(out, line, out_size - strlen(out) - 1);
        }
    };

    void BCLIBC_requireNonNullFatal(const void *ptr, const char *file, int line, const char *func)
    {
        if (!ptr)
        {
            BCLIBC_CRITICAL("FATAL: NULL pointer at %s:%d in %s\n", file, line, func);
            fflush(stderr);
            abort();
        }
    };
};
