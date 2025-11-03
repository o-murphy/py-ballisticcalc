#include "bclibc_log.h"
#include <stdlib.h>

/**
 * @brief Global log level control.
 *
 * Defaults to BCLIBC_LOG_LEVEL_CRITICAL (disabled by default).
 */
BCLIBC_LogLevel BCLIBC_global_log_level = BCLIBC_LOG_LEVEL_CRITICAL; // DIsabled by default

/**
 * @brief Initializes the global log level, potentially from an environment variable.
 *
 * Checks the environment variable BCLIBC_LOG_LEVEL. If it's set and contains a
 * non-negative integer, the log level is set to that value. Otherwise, it defaults
 * to the value of BCLIBC_global_log_level (which is BCLIBC_LOG_LEVEL_CRITICAL initially).
 */
void BCLIBC_LogLevel_init()
{
    const char *env_level_str = getenv("BCLIBC_LOG_LEVEL");

    if (env_level_str != NULL)
    {
        int env_level = atoi(env_level_str);

        if (env_level >= 0)
        {
            if ((int)BCLIBC_global_log_level != env_level)
            {
                BCLIBC_global_log_level = env_level;
                BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Log level set from environment variable BCLIBC_LOG_LEVEL to %d\n", BCLIBC_global_log_level);
            }
            return;
        }
    }

    BCLIBC_LOG(BCLIBC_LOG_LEVEL_DEBUG, "Log level defaulted to %d\n", BCLIBC_global_log_level);
}
