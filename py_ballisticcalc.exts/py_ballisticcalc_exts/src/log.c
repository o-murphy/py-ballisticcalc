#include "log.h"
#include <stdlib.h>

/**
 * @brief Global log level control.
 *
 * Defaults to LOG_LEVEL_CRITICAL (disabled by default).
 */
LogLevel global_log_level = LOG_LEVEL_CRITICAL; // DIsabled by default

/**
 * @brief Initializes the global log level, potentially from an environment variable.
 *
 * Checks the environment variable BCLIBC_LOG_LEVEL. If it's set and contains a
 * non-negative integer, the log level is set to that value. Otherwise, it defaults
 * to the value of global_log_level (which is LOG_LEVEL_CRITICAL initially).
 */
void initLogLevel()
{
    const char *env_level_str = getenv("BCLIBC_LOG_LEVEL");

    if (env_level_str != NULL)
    {
        int env_level = atoi(env_level_str);

        if (env_level >= 0)
        {
            if ((int)global_log_level != env_level)
            {
                global_log_level = env_level;
                C_LOG(LOG_LEVEL_DEBUG, "Log level set from environment variable BCLIBC_LOG_LEVEL to %d\n", global_log_level);
            }
            return;
        }
    }

    C_LOG(LOG_LEVEL_DEBUG, "Log level defaulted to %d\n", global_log_level);
}


// Force log level initialisation
