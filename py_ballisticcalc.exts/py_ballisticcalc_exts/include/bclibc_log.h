#ifndef BCLIBC_LOG_H
#define BCLIBC_LOG_H

#include <stdio.h> // For fprintf

#define BCLIBC_ANSI_COLOR_RED "\x1b[31m"
#define BCLIBC_ANSI_COLOR_YELLOW "\x1b[33m"
#define BCLIBC_ANSI_COLOR_BLUE "\x1b[34m"
#define BCLIBC_ANSI_COLOR_MAGENTA "\x1b[35m"
#define BCLIBC_ANSI_COLOR_CYAN "\x1b[36m"
#define BCLIBC_ANSI_COLOR_RESET "\x1b[0m"

#define BCLIBC_ANSI_BOLD_RED "\x1b[1;31m"
#define BCLIBC_ANSI_BOLD_MAGENTA "\x1b[1;35m"

// Define Log Levels (matching Python's logging module for consistency)
typedef enum
{
    BCLIBC_LOG_LEVEL_CRITICAL = 50,
    BCLIBC_LOG_LEVEL_ERROR = 40,
    BCLIBC_LOG_LEVEL_WARNING = 30, // Default for fprintf warnings
    BCLIBC_LOG_LEVEL_INFO = 20,
    BCLIBC_LOG_LEVEL_DEBUG = 10,
    BCLIBC_LOG_LEVEL_NOTSET = 0
} BCLIBC_LogLevel;

/*
 * Example output:
 * [ERROR] bclib.c:123 in BCLIBC_ShotProps_updateStabilityCoefficient: Division by zero in ftp calculation.
 * [DEBUG] bclibc_engine.h:45 in BCLIBC_EngineT_integrate: Using integration function pointer 0x12345678.
 * [WARNING] bclib.c:234 in BCLIBC_Atmosphere_updateDensityFactorAndMachForAltitude: Density request for altitude above troposphere.
 */

// Alternative: Shorter format (just filename without path)
#if defined(_MSC_VER)
#define __FILENAME__ (strrchr(__FILE__, '\\') ? strrchr(__FILE__, '\\') + 1 : __FILE__)
#else
#define __FILENAME__ (strrchr(__FILE__, '/') ? strrchr(__FILE__, '/') + 1 : __FILE__)
#endif

#ifdef __cplusplus
extern "C"
{
#endif
    // Global variable to hold the currently configured minimum level
    extern BCLIBC_LogLevel BCLIBC_global_log_level;

    void BCLIBC_LogLevel_init();

#ifdef __cplusplus
}
#endif

// Colored log macro
#define BCLIBC_LOG(level, format, ...)                                             \
    do                                                                             \
    {                                                                              \
        if ((level) >= BCLIBC_global_log_level)                                    \
        {                                                                          \
            const char *color_code =                                               \
                ((level) >= BCLIBC_LOG_LEVEL_CRITICAL)  ? BCLIBC_ANSI_BOLD_RED     \
                : ((level) >= BCLIBC_LOG_LEVEL_ERROR)   ? BCLIBC_ANSI_COLOR_RED    \
                : ((level) >= BCLIBC_LOG_LEVEL_WARNING) ? BCLIBC_ANSI_COLOR_YELLOW \
                : ((level) >= BCLIBC_LOG_LEVEL_INFO)    ? BCLIBC_ANSI_COLOR_CYAN   \
                : ((level) >= BCLIBC_LOG_LEVEL_DEBUG)   ? BCLIBC_ANSI_COLOR_BLUE   \
                                                        : BCLIBC_ANSI_COLOR_RESET;   \
                                                                                   \
            fprintf(stderr, "%s%s%s: %s:%d in %s: " format "\n",                   \
                    color_code,                                                    \
                    ((level) >= BCLIBC_LOG_LEVEL_CRITICAL)  ? "CRITICAL"           \
                    : ((level) >= BCLIBC_LOG_LEVEL_ERROR)   ? "ERROR"              \
                    : ((level) >= BCLIBC_LOG_LEVEL_WARNING) ? "WARNING"            \
                    : ((level) >= BCLIBC_LOG_LEVEL_INFO)    ? "INFO"               \
                    : ((level) >= BCLIBC_LOG_LEVEL_DEBUG)   ? "DEBUG"              \
                                                            : "NOTSET",              \
                    BCLIBC_ANSI_COLOR_RESET,                                       \
                    __FILE__, __LINE__, __func__,                                  \
                    ##__VA_ARGS__);                                                \
        }                                                                          \
    } while (0)

// #define BCLIBC_LOG(level, format, ...)                                 \
//     do                                                            \
//     {                                                             \
//         if ((level) >= BCLIBC_global_log_level)                          \
//         {                                                         \
//             fprintf(stderr, "[%s] %s:%d in %s: " format "\n",     \
//                     ((level) >= BCLIBC_LOG_LEVEL_CRITICAL)  ? "CRITICAL" \
//                     : ((level) >= BCLIBC_LOG_LEVEL_ERROR)   ? "ERROR"    \
//                     : ((level) >= BCLIBC_LOG_LEVEL_WARNING) ? "WARNING"  \
//                     : ((level) >= BCLIBC_LOG_LEVEL_INFO)    ? "INFO"     \
//                     : ((level) >= BCLIBC_LOG_LEVEL_DEBUG)   ? "DEBUG"    \
//                                                      : "NOTSET",    \
//                     __FILE__, __LINE__, __func__,                 \
//                     ##__VA_ARGS__);                               \
//         }                                                         \
//     } while (0)

// /*
//  * Example output (shorter):
//  * [ERROR] bclib.c:123 BCLIBC_ShotProps_updateStabilityCoefficient() Division by zero in ftp calculation.
//  */

// #define C_LOG_SHORT(level, format, ...)                           \
//     do                                                            \
//     {                                                             \
//         if ((level) >= BCLIBC_global_log_level)                          \
//         {                                                         \
//             fprintf(stderr, "[%s] %s:%d %s() " format "\n",       \
//                     ((level) >= BCLIBC_LOG_LEVEL_CRITICAL)  ? "CRITICAL" \
//                     : ((level) >= BCLIBC_LOG_LEVEL_ERROR)   ? "ERROR"    \
//                     : ((level) >= BCLIBC_LOG_LEVEL_WARNING) ? "WARNING"  \
//                     : ((level) >= BCLIBC_LOG_LEVEL_INFO)    ? "INFO"     \
//                     : ((level) >= BCLIBC_LOG_LEVEL_DEBUG)   ? "DEBUG"    \
//                                                      : "NOTSET",    \
//                     __FILENAME__, __LINE__, __func__,             \
//                     ##__VA_ARGS__);                               \
//         }                                                         \
//     } while (0)

// /*
//  * Example output (smart - location only for errors):
//  * [ERROR] bclib.c:123 in BCLIBC_ShotProps_updateStabilityCoefficient: Division by zero.
//  * [INFO] Log level set to 20
//  * [DEBUG] Altitude: 1000.00, Density ratio: 0.950000
//  */
// #define C_LOG_SMART(level, format, ...)                                         \
//     do                                                                          \
//     {                                                                           \
//         if ((level) >= BCLIBC_global_log_level)                                        \
//         {                                                                       \
//             if ((level) >= BCLIBC_LOG_LEVEL_ERROR)                                     \
//             {                                                                   \
//                 fprintf(stderr, "[%s] %s:%d in %s: " format "\n",               \
//                         ((level) >= BCLIBC_LOG_LEVEL_CRITICAL) ? "CRITICAL" : "ERROR", \
//                         __FILE__, __LINE__, __func__,                           \
//                         ##__VA_ARGS__);                                         \
//             }                                                                   \
//             else                                                                \
//             {                                                                   \
//                 fprintf(stderr, "[%s] " format "\n",                            \
//                         ((level) >= BCLIBC_LOG_LEVEL_WARNING) ? "WARNING"              \
//                         : ((level) >= BCLIBC_LOG_LEVEL_INFO)  ? "INFO"                 \
//                         : ((level) >= BCLIBC_LOG_LEVEL_DEBUG) ? "DEBUG"                \
//                                                        : "NOTSET",              \
//                         ##__VA_ARGS__);                                         \
//             }                                                                   \
//         }                                                                       \
//     } while (0)

#endif // BCLIBC_LOG_H
