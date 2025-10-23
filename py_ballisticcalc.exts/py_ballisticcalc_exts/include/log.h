#ifndef BCLIB_LOG_H
#define BCLIB_LOG_H

#include <stdio.h> // For fprintf

// Define Log Levels (matching Python's logging module for consistency)
typedef enum
{
    LOG_LEVEL_CRITICAL = 50,
    LOG_LEVEL_ERROR = 40,
    LOG_LEVEL_WARNING = 30, // Default for fprintf warnings
    LOG_LEVEL_INFO = 20,
    LOG_LEVEL_DEBUG = 10,
    LOG_LEVEL_NOTSET = 0
} LogLevel;

// Global variable to hold the currently configured minimum level
extern LogLevel global_log_level;

#define C_LOG(level, format, ...)                                 \
    do                                                            \
    {                                                             \
        if ((level) >= global_log_level)                          \
        {                                                         \
            fprintf(stderr, "[%s] %s:%d in %s: " format "\n",     \
                    ((level) >= LOG_LEVEL_CRITICAL)  ? "CRITICAL" \
                    : ((level) >= LOG_LEVEL_ERROR)   ? "ERROR"    \
                    : ((level) >= LOG_LEVEL_WARNING) ? "WARNING"  \
                    : ((level) >= LOG_LEVEL_INFO)    ? "INFO"     \
                    : ((level) >= LOG_LEVEL_DEBUG)   ? "DEBUG"    \
                                                     : "NOTSET",    \
                    __FILE__, __LINE__, __func__,                 \
                    ##__VA_ARGS__);                               \
        }                                                         \
    } while (0)

/*
 * Example output:
 * [ERROR] bclib.c:123 in ShotProps_t_updateStabilityCoefficient: Division by zero in ftp calculation.
 * [DEBUG] engine.c:45 in Engine_t_integrate: Using integration function pointer 0x12345678.
 * [WARNING] bclib.c:234 in Atmosphere_t_updateDensityFactorAndMachForAltitude: Density request for altitude above troposphere.
 */

// Alternative: Shorter format (just filename without path)
#ifdef _WIN32
#define __FILENAME__ (strrchr(__FILE__, '\\') ? strrchr(__FILE__, '\\') + 1 : __FILE__)
#else
#define __FILENAME__ (strrchr(__FILE__, '/') ? strrchr(__FILE__, '/') + 1 : __FILE__)
#endif

#define C_LOG_SHORT(level, format, ...)                           \
    do                                                            \
    {                                                             \
        if ((level) >= global_log_level)                          \
        {                                                         \
            fprintf(stderr, "[%s] %s:%d %s() " format "\n",       \
                    ((level) >= LOG_LEVEL_CRITICAL)  ? "CRITICAL" \
                    : ((level) >= LOG_LEVEL_ERROR)   ? "ERROR"    \
                    : ((level) >= LOG_LEVEL_WARNING) ? "WARNING"  \
                    : ((level) >= LOG_LEVEL_INFO)    ? "INFO"     \
                    : ((level) >= LOG_LEVEL_DEBUG)   ? "DEBUG"    \
                                                     : "NOTSET",    \
                    __FILENAME__, __LINE__, __func__,             \
                    ##__VA_ARGS__);                               \
        }                                                         \
    } while (0)

/*
 * Example output (shorter):
 * [ERROR] bclib.c:123 ShotProps_t_updateStabilityCoefficient() Division by zero in ftp calculation.
 */

// Optional: Conditional location info (only for ERROR and above)
#define C_LOG_SMART(level, format, ...)                                         \
    do                                                                          \
    {                                                                           \
        if ((level) >= global_log_level)                                        \
        {                                                                       \
            if ((level) >= LOG_LEVEL_ERROR)                                     \
            {                                                                   \
                fprintf(stderr, "[%s] %s:%d in %s: " format "\n",               \
                        ((level) >= LOG_LEVEL_CRITICAL) ? "CRITICAL" : "ERROR", \
                        __FILE__, __LINE__, __func__,                           \
                        ##__VA_ARGS__);                                         \
            }                                                                   \
            else                                                                \
            {                                                                   \
                fprintf(stderr, "[%s] " format "\n",                            \
                        ((level) >= LOG_LEVEL_WARNING) ? "WARNING"              \
                        : ((level) >= LOG_LEVEL_INFO)  ? "INFO"                 \
                        : ((level) >= LOG_LEVEL_DEBUG) ? "DEBUG"                \
                                                       : "NOTSET",              \
                        ##__VA_ARGS__);                                         \
            }                                                                   \
        }                                                                       \
    } while (0)

/*
 * Example output (smart - location only for errors):
 * [ERROR] bclib.c:123 in ShotProps_t_updateStabilityCoefficient: Division by zero.
 * [INFO] Log level set to 20
 * [DEBUG] Altitude: 1000.00, Density ratio: 0.950000
 */

#endif // BCLIB_LOG_H