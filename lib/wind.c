#include "v3d.h"
#include "wind.h"
#include "consts.h"


V3dT windToVector(const WindT *w)
{ // Added const as input 'w' isn't modified
    V3dT result;

    if (w == NULL)
    {
        fprintf(stderr, "Error: NULL WindT pointer passed to windToVector.\n");
        result.x = 0.0;
        result.y = 0.0;
        result.z = 0.0;
        return result;
    }

    double range_component = w->velocity * cos(w->directionFrom);
    double cross_component = w->velocity * sin(w->directionFrom);

    result.x = range_component;
    result.y = 0.0; // Wind often acts horizontally, so Y (vertical) component is zero
    result.z = cross_component;

    return result;
}

int initWindSock(WindSockT *ws, WindsT *windsData)
{
    if (ws == NULL)
    {
        fprintf(stderr, "Error: initWindSock received a NULL WindSockT pointer.\n");
        return -1;
    }

    *ws = (WindSockT){
        .winds = windsData,
        .current = 0,
        .lastVectorCache = {0.0, 0.0, 0.0},
        .nextRange = C_MAX_WIND_DISTANCE_FEET, // Initialize with default max range
    };

    updateWindCache(ws);

    return 0; // Success
}

V3dT currentWindVector(WindSockT *ws)
{
    return ws->lastVectorCache;
}

void updateWindCache(WindSockT *ws)
{
    if (ws == NULL)
    {
        fprintf(stderr, "Error: updateWindCache received a NULL WindSockT pointer.\n");
        return;
    }

    // Check if the current index is within the actual length of the winds.
    if ((size_t)ws->current < ws->winds->length)
    {
        // Access the current wind from the array (ws->winds->winds[ws->current]).
        // Note: It's technically possible for ws->winds to be NULL here if ws->length is 0.
        // The earlier initWindSock should prevent this, but an extra check for safety:
        if (ws->winds == NULL)
        { // Should not happen if ws->length is correctly 0 if winds is NULL
            ws->lastVectorCache = (V3dT){0.0, 0.0, 0.0};
            ws->nextRange = C_MAX_WIND_DISTANCE_FEET;
            fprintf(stderr, "Warning: WindSockT has length > 0 but winds pointer is NULL in updateWindCache.\n");
            return;
        }

        WindT curWind = ws->winds->winds[ws->current];
        ws->lastVectorCache = windToVector(&curWind);
        ws->nextRange = curWind.untilDistance; // Now we can set this directly
    }
    else
    {
        // No more winds, or current index is out of bounds.
        ws->lastVectorCache = (V3dT){0.0, 0.0, 0.0};
        ws->nextRange = C_MAX_WIND_DISTANCE_FEET; // Set to the global max distance
    }
}

V3dT windVectorForRange(WindSockT *ws, double nextRange)
{
    // Input validation: Always check for NULL pointers to prevent crashes.
    if (ws == NULL)
    {
        fprintf(stderr, "Error: windVectorForRange received a NULL WindSockT pointer. Returning zero vector.\n");
        return (V3dT){0.0, 0.0, 0.0}; // Return a zero vector on error.
    }

    // Using a small tolerance for floating-point comparisons is good practice.
    // This accounts for potential precision issues that might occur when `nextRange`
    // is just barely reached or slightly exceeded.
    const double EPSILON = 1e-6;

    // Check if the current trajectory position has reached or exceeded the 'untilDistance'
    // for the *current* active wind segment (stored in ws->nextRange).
    if (nextRange + EPSILON >= ws->nextRange)
    {
        ws->current += 1; // Advance to the next wind segment.

        // Check if we've moved past all defined wind segments.
        // We also need to check if `ws->winds` itself is not NULL, as `ws->winds->length` would be an invalid access.
        if (ws->winds == NULL || (size_t)ws->current >= ws->winds->length)
        {
            // We've exhausted all specific wind segments.
            // The wind is now considered zero, and the effective boundary is the global max distance.
            ws->lastVectorCache = (V3dT){0.0, 0.0, 0.0};
            ws->nextRange = C_MAX_WIND_DISTANCE_FEET;
        }
        else
        {
            // There are more wind segments; update the cached wind vector
            // and the next range threshold from the newly 'current' wind segment.
            updateWindCache(ws); // Calls the function you provided above.
        }
    }

    // Return the currently cached wind vector.
    return ws->lastVectorCache;
}