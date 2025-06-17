#include <string.h> // <-- Add this line
#include <stdio.h>  // <-- You likely already have this for fprintf
#include <stdlib.h> // <-- You likely already have this for malloc/free
#include <stdbool.h>
#include "v3d.h"
#include "bc.h"

// --- Global Constants Definitions ---
const double C_DEGREES_F_TO_R = 459.67;
const double C_DEGREES_C_TO_K = 273.15;
const double C_SPEED_OF_SOUND_IMPERIAL = 49.0223;
const double C_SPEED_OF_SOUND_METRIC = 20.0467;
const double C_LAPSE_RATE_K_PER_FOOT = -0.0019812;
const double C_LAPSE_RATE_IMPERIAL = -3.56616e-03;
const double C_PRESSURE_EXPONENT = 5.2559;
const double C_LOWEST_TEMP_F = -130.0;
const double M_TO_FEET = 3.28084;
const double C_MAX_WIND_DISTANCE_FEET = 999999.0;

V3dT windToVector(const WindT *w) { // Added const as input 'w' isn't modified
    V3dT result;

    if (w == NULL) {
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

// initDataFilter: Initializes a TrajectoryDataFilterT struct based on input parameters.
// Parameters:
//   tdf: Pointer to the TrajectoryDataFilterT struct to be initialized.
//   filterFlags: Integer representing the desired trajectory flags (e.g., TRAJ_RANGE, TRAJ_ZERO_UP).
//   rangeStep: The step size for recording range-based data.
//   initialPosition: The starting position vector of the projectile.
//   initialVelocity: The starting velocity vector of the projectile.
//   timeStep: The time step for simulation, if applicable (default 0.0 means auto-calculated or not used for this filter).
// Returns: 0 on success, -1 on failure (e.g., NULL pointer).
int initDataFilter(TrajectoryDataFilterT *tdf, int filterFlags, double rangeStep,
                   V3dT initialPosition, V3dT initialVelocity, double timeStep) {
    if (tdf == NULL) {
        fprintf(stderr, "Error: initDataFilter received a NULL TrajectoryDataFilterT pointer.\n");
        return -1;
    }

    // Initialize the struct using designated initializers.
    // Any members not explicitly listed will be zero-initialized.
    *tdf = (TrajectoryDataFilterT){
        .filter = filterFlags,
        .currentFlag = TRAJ_NONE,            .seenZero = TRAJ_NONE,               .timeStep = timeStep,
        .rangeStep = rangeStep,
        .timeOfLastRecord = 0.0,
        .nextRecordDistance = 0.0,
        .previousMach = 0.0,
        .previousTime = 0.0,
        .previousPosition = initialPosition,
        .previousVelocity = initialVelocity,
        .previousVMach = 0.0,
        .lookAngle = 0.0
    };

    return 0; // Success
}

static void checkNextTime(TrajectoryDataFilterT *tdf, double time) {
    if (tdf == NULL) {
        fprintf(stderr, "Error: checkNextTime received a NULL TrajectoryDataFilterT pointer.\n");
        return;
    }

        if (time > tdf->timeOfLastRecord + tdf->timeStep) {
                tdf->currentFlag |= TRAJ_RANGE;
                tdf->timeOfLastRecord = time;
    }
}

static void checkMachCrossing(TrajectoryDataFilterT *tdf, double velocity, double mach) {
    if (tdf == NULL) {
        fprintf(stderr, "Error: checkMachCrossing received a NULL TrajectoryDataFilterT pointer.\n");
        return;
    }
    // Avoid division by zero if mach is very small or zero
    if (mach == 0.0) {
        // Handle this case, perhaps by logging an error or returning early.
        // Or set currentVMach to a very large number or specific error value.
        // For now, we'll assume mach is always positive when called.
        fprintf(stderr, "Warning: checkMachCrossing called with mach = 0.0\n");
        return;
    }

        double currentVMach = velocity / mach;

        // This checks if previousVMach was greater than 1 AND currentVMach is less than or equal to 1.
    if (tdf->previousVMach > 1.0 && currentVMach <= 1.0) {
                tdf->currentFlag |= TRAJ_MACH;
    }

        tdf->previousVMach = currentVMach;
}

static void checkZeroCrossing(TrajectoryDataFilterT *tdf, V3dT rangeVector) {
    if (tdf == NULL) {
        fprintf(stderr, "Error: checkZeroCrossing received a NULL TrajectoryDataFilterT pointer.\n");
        return;
    }

        if (rangeVector.x > 0.0) {
                double referenceHeight = rangeVector.x * tan(tdf->lookAngle);

                // Checks if ZERO_UP flag is NOT set in seenZero
        if (!(tdf->seenZero & TRAJ_ZERO_UP)) {
                        if (rangeVector.y >= referenceHeight) {
                                tdf->currentFlag |= TRAJ_ZERO_UP;
                                tdf->seenZero |= TRAJ_ZERO_UP;
            }
        }
                // Checks if ZERO_DOWN flag is NOT set in seenZero (and ZERO_UP was set, implicitly by the 'else if')
        else if (!(tdf->seenZero & TRAJ_ZERO_DOWN)) {
                        if (rangeVector.y < referenceHeight) {
                                tdf->currentFlag |= TRAJ_ZERO_DOWN;
                                tdf->seenZero |= TRAJ_ZERO_DOWN;
            }
        }
    }
}

void setupSeenZero(TrajectoryDataFilterT * tdf, double height, double barrelElevation, double lookAngle) {
    // Input validation: Always good practice, even for void functions,
    // to prevent dereferencing a NULL pointer.
    if (tdf == NULL) {
        fprintf(stderr, "Error: setupSeenZero received a NULL TrajectoryDataFilterT pointer.\n");
        return; // Exit if input is invalid
    }

        if (height >= 0.0) {
                tdf->seenZero |= TRAJ_ZERO_UP;
    }
        else if (height < 0.0 && barrelElevation < lookAngle) {
                tdf->seenZero |= TRAJ_ZERO_DOWN;
    }

        tdf->lookAngle = lookAngle;
}

BaseTrajDataT* shouldRecord(TrajectoryDataFilterT *tdf, V3dT position, V3dT velocity, double mach, double time) {
    // In C, we return a pointer to a dynamically allocated struct (or NULL).
    BaseTrajDataT *data = NULL;
    double ratio;

    // Local variables for V3dT operations to avoid modifying inputs
    V3dT tempPositionSub, tempPositionMul, tempPositionFinal;
    V3dT tempVelocitySub, tempVelocityMul, tempVelocityFinal;

    // Input validation
    if (tdf == NULL) {
        fprintf(stderr, "Error: shouldRecord received a NULL TrajectoryDataFilterT pointer.\n");
        return NULL;
    }

        tdf->currentFlag = TRAJ_NONE;

        if ((tdf->rangeStep > 0.0) && (position.x >= tdf->nextRecordDistance)) {
                while (tdf->nextRecordDistance + tdf->rangeStep < position.x) {
            tdf->nextRecordDistance += tdf->rangeStep;
        }

                if (position.x > tdf->previousPosition.x) {
                        // Ensure no division by zero for ratio calculation
            double deltaX = position.x - tdf->previousPosition.x;
            if (deltaX == 0.0) {
                 // This case indicates no movement in X, interpolation is not well-defined.
                 // Skip interpolation and just mark for range if filter allows.
                 // Or, you might want to handle this as an error or specific edge case.
                 // For now, we'll proceed without interpolation for this record.
                 fprintf(stderr, "Warning: Zero x-movement detected for interpolation in shouldRecord. Skipping interpolation.\n");
                 tdf->currentFlag |= TRAJ_RANGE; // Still mark if range step reached.
                 tdf->nextRecordDistance += tdf->rangeStep;
                 tdf->timeOfLastRecord = time;
                 return NULL; // Or return data without interpolation if logic allows
            }
            ratio = (tdf->nextRecordDistance - tdf->previousPosition.x) / deltaX;

            // Interpolate position
                        tempPositionSub = sub(&position, &tdf->previousPosition);
                        tempPositionMul = mulS(&tempPositionSub, ratio);
                        tempPositionFinal = add(&tdf->previousPosition, &tempPositionMul);

            // Interpolate velocity
                        tempVelocitySub = sub(&velocity, &tdf->previousVelocity);
                        tempVelocityMul = mulS(&tempVelocitySub, ratio);
                        tempVelocityFinal = add(&tdf->previousVelocity, &tempVelocityMul);

            // Allocate memory for the new BaseTrajDataT struct
            data = (BaseTrajDataT*)malloc(sizeof(BaseTrajDataT));
            if (data == NULL) {
                fprintf(stderr, "Error: Failed to allocate memory for BaseTrajDataT in shouldRecord.\n");
                return NULL; // Indicate allocation failure
            }

            // Initialize the allocated struct using designated initializers
            *data = (BaseTrajDataT){
                .time = tdf->previousTime + (time - tdf->previousTime) * ratio,
                .position = tempPositionFinal,
                .velocity = tempVelocityFinal,
                .mach = tdf->previousMach + (mach - tdf->previousMach) * ratio
            };
        }
                tdf->currentFlag |= TRAJ_RANGE;
                tdf->nextRecordDistance += tdf->rangeStep;
                tdf->timeOfLastRecord = time;
    }
        else if (tdf->timeStep > 0.0) {
                checkNextTime(tdf, time);
    }

        checkZeroCrossing(tdf, position);

        checkMachCrossing(tdf, mag(&velocity), mach);

        // In C, 'data is None' means 'data == NULL'
    if (((tdf->currentFlag & tdf->filter) != 0) && (data == NULL)) {
        // Allocate memory for the new BaseTrajDataT struct if not already allocated
        data = (BaseTrajDataT*)malloc(sizeof(BaseTrajDataT));
        if (data == NULL) {
            fprintf(stderr, "Error: Failed to allocate memory for BaseTrajDataT in shouldRecord (second allocation).\n");
            return NULL; // Indicate allocation failure
        }
                *data = (BaseTrajDataT){
            .time = time,
            .position = position,
            .velocity = velocity,
            .mach = mach
        };
    }

        tdf->previousTime = time;
    tdf->previousPosition = position;
    tdf->previousVelocity = velocity;
    tdf->previousMach = mach;

    return data; // Return the pointer to the allocated BaseTrajDataT or NULL
}

int initWindSock(WindSockT *ws, WindsT *windsData) {
    if (ws == NULL) {
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

V3dT currentWindVector(WindSockT * ws) {
    return ws->lastVectorCache;
}


void updateWindCache(WindSockT *ws) {
    if (ws == NULL) {
        fprintf(stderr, "Error: updateWindCache received a NULL WindSockT pointer.\n");
        return;
    }

    // Check if the current index is within the actual length of the winds.
    if (ws->current < ws->winds->length) {
        // Access the current wind from the array (ws->winds->winds[ws->current]).
        // Note: It's technically possible for ws->winds to be NULL here if ws->length is 0.
        // The earlier initWindSock should prevent this, but an extra check for safety:
        if (ws->winds == NULL) { // Should not happen if ws->length is correctly 0 if winds is NULL
             ws->lastVectorCache = (V3dT){0.0, 0.0, 0.0};
             ws->nextRange = C_MAX_WIND_DISTANCE_FEET;
             fprintf(stderr, "Warning: WindSockT has length > 0 but winds pointer is NULL in updateWindCache.\n");
             return;
        }

        WindT curWind = ws->winds->winds[ws->current];
        ws->lastVectorCache = windToVector(&curWind);
        ws->nextRange = curWind.untilDistance; // Now we can set this directly
    } else {
        // No more winds, or current index is out of bounds.
        ws->lastVectorCache = (V3dT){0.0, 0.0, 0.0};
        ws->nextRange = C_MAX_WIND_DISTANCE_FEET; // Set to the global max distance
    }
}

V3dT windVectorForRange(WindSockT *ws, double nextRange) {
    // Input validation: Always check for NULL pointers to prevent crashes.
    if (ws == NULL) {
        fprintf(stderr, "Error: windVectorForRange received a NULL WindSockT pointer. Returning zero vector.\n");
        return (V3dT){0.0, 0.0, 0.0}; // Return a zero vector on error.
    }

    // Using a small tolerance for floating-point comparisons is good practice.
    // This accounts for potential precision issues that might occur when `nextRange`
    // is just barely reached or slightly exceeded.
    const double EPSILON = 1e-6;

    // Check if the current trajectory position has reached or exceeded the 'untilDistance'
    // for the *current* active wind segment (stored in ws->nextRange).
    if (nextRange + EPSILON >= ws->nextRange) {
        ws->current += 1; // Advance to the next wind segment.

        // Check if we've moved past all defined wind segments.
        // We also need to check if `ws->winds` itself is not NULL, as `ws->winds->length` would be an invalid access.
        if (ws->winds == NULL || ws->current >= ws->winds->length) {
            // We've exhausted all specific wind segments.
            // The wind is now considered zero, and the effective boundary is the global max distance.
            ws->lastVectorCache = (V3dT){0.0, 0.0, 0.0};
            ws->nextRange = C_MAX_WIND_DISTANCE_FEET;
        } else {
            // There are more wind segments; update the cached wind vector
            // and the next range threshold from the newly 'current' wind segment.
            updateWindCache(ws); // Calls the function you provided above.
        }
    }

    // Return the currently cached wind vector.
    return ws->lastVectorCache;
}

int initEngine(EngineT *engine, ConfigT *config) {
    // 1. Validate incoming engine pointer
    if (engine == NULL) {
        fprintf(stderr, "Error: initEngine received a NULL engine pointer.\n");
        return -1; // Indicate failure
    }

    // 2. Validate incoming config pointer
    if (config == NULL) {
        fprintf(stderr, "Error: initEngine received a NULL config pointer.\n");
        return -1; // Indicate failure
    }

    // 3. Initialize the members of the *existing* EngineT struct
    //    by dereferencing the 'engine' pointer.
    engine->config = config;
    engine->gravityVector = set(0.0, config->cGravityConstant, 0.0);

    // Initialize tProps. Since tProps is a direct struct member (not a pointer)
    // and contains pointers itself (shotData, curve.points, etc.), it's crucial
    // to initialize it to a known, safe state (typically all zeros/NULLs).
    // This assumes initTrajectory will later fill it with meaningful data.
    // Use memset to zero-initialize the entire TrajectoryPropsT struct.
    memset(&(engine->tProps), 0, sizeof(TrajectoryPropsT));
    // For example, after memset, engine->tProps.shotData will be NULL,
    // engine->tProps.curve.points will be NULL, etc. This is good.

    return 0; // Indicate success
}


int initTrajectory(EngineT *engine, ShotDataT *initialShotData) {
    // 1. Validate incoming pointers
    if (engine == NULL) {
        fprintf(stderr, "Error: initTrajectory received a NULL engine pointer.\n");
        return -1; // Indicate failure
    }
    if (initialShotData == NULL) {
        fprintf(stderr, "Error: initTrajectory received a NULL initialShotData pointer.\n");
        return -1; // Indicate failure
    }
    // Also, check if initialShotData has its *own* critical pointers valid
    if (initialShotData->dragTable == NULL) {
        fprintf(stderr, "Error: initialShotData->dragTable is NULL. Cannot initialize trajectory without drag table.\n");
        return -1;
    }
    // You might also want to check initialShotData->atmo and initialShotData->winds if they are critical

    // --- 2. Clean up existing dynamic data within engine->tProps (if any) ---
    // If initTrajeint initTrajectory(EngineT *engine, ShotDataT *initialShotData) {
    // 1. Validate incoming pointers
    if (engine == NULL) {
        fprintf(stderr, "Error: initTrajectory received a NULL engine pointer.\n");
        return -1; // Indicate failure
    }
    if (initialShotData == NULL) {
        fprintf(stderr, "Error: initTrajectory received a NULL initialShotData pointer.\n");
        return -1; // Indicate failure
    }
    // Also, check if initialShotData has its *own* critical pointers valid
    if (initialShotData->dragTable == NULL) {
        fprintf(stderr, "Error: initialShotData->dragTable is NULL. Cannot initialize trajectory without drag table.\n");
        return -1;
    }
    // You might also want to check initialShotData->atmo and initialShotData->winds if they are critical

    // --- 2. Clean up existing dynamic data within engine->tProps (if any) ---
    // If initTrajectory can be called multiple times on the same engine object
    // to reset its state, we must free resources associated with the *old* state.

    // 2.1 Free old CurveT (points) if they exist
    if (engine->tProps.curve.points != NULL) {
        freeCurve(&engine->tProps.curve); // Use your existing helper
        engine->tProps.curve.points = NULL;
        engine->tProps.curve.length = 0;
    }

    // 2.2 Free old MachListT (values) if they exist
    if (engine->tProps.machList.values != NULL) {
        freeMachList(&engine->tProps.machList); // Use your existing helper
        engine->tProps.machList.values = NULL;
        engine->tProps.machList.length = 0;
    }

    // 2.3 IMPORTANT: For engine->tProps.shotData:
    // This function's design implies that `initialShotData` is owned externally.
    // Therefore, we *do not* free the `ShotDataT` pointed to by `engine->tProps.shotData` here.
    // The previous `engine->tProps.shotData` will just be overwritten.

    // --- 3. Assign the new ShotDataT pointer ---
    engine->tProps.shotData = initialShotData; // <-- Direct pointer assignment

    // --- 4. Derive and initialize other TrajectoryPropsT members ---

    // 4.1 CurveT and MachListT (derived from shotData's dragTable)
    // These now use the dragTable from the *newly assigned* shotData.
    engine->tProps.curve = calculateCurve(engine->tProps.shotData->dragTable);
    engine->tProps.machList = tableToMach(engine->tProps.shotData->dragTable);

    // 4.2 Initialize TrajectoryDataFilterT
    // Use the dedicated helper function with the new signature.
    // We need an initial position and velocity for the filter's 'previous' state.
    // Let's assume for simplicity that at the start, position is {0,0,0} and velocity is initial muzzle velocity.
    // The `filterFlags` and `rangeStep` parameters for initDataFilter are *not*
    // available directly from ShotDataT in your current definition.
    // You'll need to decide where these come from. For now, I'll use placeholders.
    // A common approach is to pass them into initTrajectory or make them part of ConfigT.

    // Placeholder values for filterFlags and rangeStep (adjust as needed for your application)
    int defaultFilterFlags = TRAJ_ALL; // Or specific flags you want
    double defaultRangeStep = 100.0;   // Example: record every 100 feet

    // The initial position and velocity for the filter should be the shot's muzzle conditions.
    // Assuming initialShotData doesn't hold current position/velocity,
    // we'd typically derive these for the filter's starting point.
    // A reasonable default for filter's initial position is the origin {0,0,0}
    // and for initial velocity, it's the muzzle velocity in the direction of barrel elevation.
    // However, the `initDataFilter` expects a `V3dT` for initial position/velocity.
    // For a filter tracking the trajectory from the start, {0,0,0} for position
    // and a velocity vector derived from muzzleVelocity and barrelElevation
    // would be appropriate.
    // Let's use simple zeros for now, but acknowledge this might need refinement.

    V3dT initialFilterPosition = {0.0, 0.0, 0.0}; // Assuming starting at origin
    V3dT initialFilterVelocity = {0.0, 0.0, 0.0}; // Placeholder, would derive from muzzleVelocity

    // If you always want to record the muzzle conditions as the first point:
    // This is often handled in the main integration loop, not by filter init.

    int filterStatus = initDataFilter(&engine->tProps.dataFilter,
                                       defaultFilterFlags,
                                       defaultRangeStep,
                                       initialFilterPosition,
                                       initialFilterVelocity,
                                       0.0); // timeStep (0.0 for auto/not used by filter for primary recording)

    if (filterStatus != 0) {
        fprintf(stderr, "Error: Failed to initialize TrajectoryDataFilterT.\n");
        // Clean up already allocated curve and machList if this is a critical failure.
        freeCurve(&engine->tProps.curve);
        freeMachList(&engine->tProps.machList);
        return -1;
    }

    // 4.3 Initialize WindSockT, passing the winds from initialShotData
    int windsockStatus = initWindSock(&engine->tProps.windSock, initialShotData->winds);
    if (windsockStatus != 0) {
        fprintf(stderr, "Error: Failed to initialize WindSockT.\n");
        // Clean up other allocations if this is a critical failure
        freeCurve(&engine->tProps.curve);
        freeMachList(&engine->tProps.machList);
        return -1;
    }

    return 0; // Indicate success
}

void freeTrajectory(EngineT *engine) {
    // 1. Validate incoming engine pointer.
    // While this is a 'free' function, checking for NULL is good practice
    // to prevent crashes if it's called on an uninitialized or already freed engine.
    if (engine == NULL) {
        fprintf(stderr, "Warning: freeTrajectory received a NULL engine pointer. Nothing to free.\n");
        return;
    }

    // --- 2. Free dynamic data within engine->tProps ---

    // 2.1 Free CurveT (points)
    // Check if points is not NULL before freeing to avoid double-free or freeing invalid memory.
    if (engine->tProps.curve.points != NULL) {
        freeCurve(&engine->tProps.curve); // Call your helper to free points and reset members
        engine->tProps.curve.points = NULL; // Explicitly set to NULL after freeing
        engine->tProps.curve.length = 0;    // Reset length
    }

    // 2.2 Free MachListT (values)
    // Check if values is not NULL before freeing.
    if (engine->tProps.machList.values != NULL) {
        freeMachList(&engine->tProps.machList); // Call your helper to free values and reset members
        engine->tProps.machList.values = NULL; // Explicitly set to NULL after freeing
        engine->tProps.machList.length = 0;    // Reset length
    }

    // 2.3 ShotDataT (engine->tProps.shotData):
    // As noted in initTrajectory, `initialShotData` (which becomes engine->tProps.shotData)
    // is designed to be *owned externally*.
    // Therefore, we **DO NOT** free `engine->tProps.shotData` here.
    // It is the responsibility of the caller who provided `initialShotData` to `initTrajectory`
    // to free that `ShotDataT` object when it's no longer needed.
    // We can, however, set the pointer to NULL to indicate it's no longer referencing valid data.
    engine->tProps.shotData = NULL;

    // 2.4 WindSockT (engine->tProps.windSock):
    // The `WindSockT` struct itself is a direct member of `TrajectoryPropsT`, so it's
    // not dynamically allocated.
    // Its `winds` member (`WindsT *`) is a pointer to external data, similar to `shotData`.
    // We **DO NOT** free `engine->tProps.windSock.winds` here; it's owned externally.
    // We can reset its internal state if desired, or `initWindSock` will re-initialize it.
    engine->tProps.windSock.winds = NULL; // Indicate it no longer references external winds
    engine->tProps.windSock.current = 0; // Reset index
    engine->tProps.windSock.nextRange = C_MAX_WIND_DISTANCE_FEET; // Reset range
    engine->tProps.windSock.lastVectorCache = (V3dT){0.0, 0.0, 0.0}; // Reset cache

    // 2.5 TrajectoryDataFilterT (engine->tProps.dataFilter):
    // This is also a direct struct member and does not contain any dynamically allocated memory
    // that `initDataFilter` would manage (it holds values, not pointers to owned data).
    // So, no explicit freeing is needed here, but its members will be overwritten by the next `initDataFilter`.
    // We could memset it to zeros for cleanliness, but it's not strictly necessary for memory safety.
    // memset(&(engine->tProps.dataFilter), 0, sizeof(TrajectoryDataFilterT)); // Optional: to fully zero out
}


double spinDrift(ShotDataT * t, double time) {
    double sign;

    if (t == NULL) {
        fprintf(stderr, "Error: ShotDataT is NULL in spinDrift.\n");
        return 0.0;
    }

    if (t->twist != 0.0 && t->stabilityCoefficient != 0.0) {
        sign = (t->twist > 0.0) ? 1.0 : -1.0;
        return sign * (1.25 * (t->stabilityCoefficient + 1.2) * pow(time, 1.83)) / 12.0;
    }
    return 0.0;
}


// helpers
double getCorrection(double distance, double offset) {
    if (distance != 0.0) {
        return atan2(offset, distance);
    }
    return 0.0;
}

double calculateEnergy(double bulletWeight, double velocity) {
    // Ensure 450400.0 is not zero
    if (450400.0 == 0.0) { // This is a constant, won't be zero.
        fprintf(stderr, "Error: Division by zero in energy calculation.\n");
        return 0.0;
    }
    return bulletWeight * (velocity * velocity) / 450400.0;
}

double calculateOGW(double bulletWeight, double velocity) {
    return (bulletWeight * bulletWeight) * (velocity * velocity * velocity) * 1.5e-12;
}

int zeroAngle(EngineT *engine, ShotDataT *shotData, double distance, double *zeroAngle) {
    // Input validation
    if (engine == NULL) {
        fprintf(stderr, "Error: zeroAngle received a NULL engine pointer.\n");
        return ZERO_ANGLE_ERROR_NULL_ENGINE;
    }
    if (shotData == NULL) {
        fprintf(stderr, "Error: zeroAngle received a NULL shotData pointer.\n");
        return ZERO_ANGLE_ERROR_NULL_SHOTDATA;
    }
    if (zeroAngle == NULL) {
        fprintf(stderr, "Error: zeroAngle received a NULL zeroAngle output pointer.\n");
        return ZERO_ANGLE_ERROR_NULL_ZEROANGLE_OUT;
    }
    // Also check if critical sub-structs are initialized
    if (engine->config == NULL || engine->tProps.windSock.winds == NULL || shotData->atmo == NULL) {
        fprintf(stderr, "Error: zeroAngle: Engine or ShotData properties not fully initialized.\n");
        return ZERO_ANGLE_ERROR_NULL_SHOTDATA; // Using existing error code
    }


    // "hack to reload config if it was changed explicit on existed instance"
    // In C, you'd explicitly call a function like `updateEngineConfig(engine, newConfig)`
    // if you wanted to change config runtime. Here, we assume engine->config is up-to-date.
    // The gravity vector is set during initEngine, no need to recalculate here.

    // Early bindings for config values
    double _cZeroFindingAccuracy = engine->config->cZeroFindingAccuracy;
    int _cMaxIterations = engine->config->cMaxIterations;

    double zero_distance_m; // Horizontal distance to target (barrel to target)
    double height_at_zero_m; // Vertical height of target relative to barrel
    double maximum_range;
    int iterations_count = 0;
    double zero_finding_error;

    TrajectoryTableT temp_trajectory; // Temporary trajectory for integrate results
    int integrate_status;       // Status from integrate call

    double height_at_target;
    double last_distance_foot_from_integrate; // Used if integrate returns RangeError (early termination)
    double proportion;

    // Convert from look_angle (radians) and distance (feet) to meters (if your internal calculations are in meters)
    // Assuming distance is in feet, and look_angle is in radians, match C definition
    zero_distance_m = cos(shotData->lookAngle) * distance; // Assuming 'distance' parameter is already in feet
    height_at_zero_m = sin(shotData->lookAngle) * distance;

    // Initialize trajectory related properties
    // This is equivalent to self._init_trajectory(shot_info)
    // Note: initTrajectory also sets up dataFilter and windSock.
    // It's crucial that initTrajectory is called before zeroAngle.
    // If not, you might need to manually set up shotData for this calculation.
    // Given initTrajectory takes ShotDataT*, we might need to copy/modify the existing one.
    // The Cython was modifying `self._shot_s`, which is `engine->tProps.shotData`.
    // So we modify `engine->tProps.shotData` directly.
    initTrajectory(engine, shotData); // Re-initialize or ensure engine->tProps.shotData is set up.

    engine->tProps.shotData->barrelAzimuth = 0.0; // Resetting azimuth
    engine->tProps.shotData->barrelElevation = atan2(height_at_zero_m, zero_distance_m); // Use atan2 for robustness
    engine->tProps.shotData->twist = 0; // Resetting twist

    // maximum_range -= 1.5 * self._shot_s.calc_step;
    maximum_range = zero_distance_m - (1.5 * engine->tProps.shotData->calcStep);

    // Initialize zero_finding_error to ensure the loop runs at least once
    zero_finding_error = _cZeroFindingAccuracy * 2;


    // Loop to find the zero angle
    while (zero_finding_error > _cZeroFindingAccuracy && iterations_count < _cMaxIterations) {
        // Call integrate. `temp_trajectory` will store the results.
        // It uses `TRAJ_NONE` filter_flags as in Cython.
        integrate_status = integrate(engine, maximum_range, zero_distance_m, TRAJ_NONE, 0.0, &temp_trajectory);

        if (integrate_status >= INTEGRATE_REASON_MIN_VELOCITY_REACHED) { // integrate returned an early termination reason
            // Cython's RangeError handling
            // e.g., RangeError(reason, ranges) where ranges is incomplete_trajectory
            // last_distance_foot = e.last_distance._feet -> this would be temp_trajectory.ranges[last_index].distance
            // height = (e.incomplete_trajectory[-1].height._feet) / proportion

            // Check if trajectory has at least one point, should always have one if integrate returns a reason
            if (temp_trajectory.length > 0) {
                last_distance_foot_from_integrate = temp_trajectory.ranges[temp_trajectory.length - 1].distance;
                // Avoid division by zero for proportion if zero_distance_m is very small
                if (zero_distance_m != 0.0) {
                    proportion = last_distance_foot_from_integrate / zero_distance_m;
                } else {
                    proportion = 1.0; // Avoid division by zero, though conceptually odd for zero_distance
                }

                if (proportion != 0.0) { // Avoid division by zero for height calculation
                    height_at_target = temp_trajectory.ranges[temp_trajectory.length - 1].height / proportion;
                } else {
                    height_at_target = temp_trajectory.ranges[temp_trajectory.length - 1].height; // Fallback
                }
            } else {
                // If integrate somehow returned a reason but no points, this is an error
                fprintf(stderr, "Error: integrate returned early but no trajectory data available.\n");
                height_at_target = -9999.0; // Indicate a severe issue
            }
            freeTrajectory(engine); // Free temporary trajectory data
            temp_trajectory.ranges = NULL; temp_trajectory.length = 0; // Clear for next iteration
        } else if (integrate_status != INTEGRATE_SUCCESS) { // integrate returned a critical error
            fprintf(stderr, "Error: integrate failed with status %d during zeroAngle calculation.\n", integrate_status);
            freeTrajectory(engine); // Ensure clean up
            temp_trajectory.ranges = NULL; temp_trajectory.length = 0; // Clear for next iteration
            return ZERO_ANGLE_ERROR_INTEGRATE_FAILED;
        } else { // integrate_status == INTEGRATE_SUCCESS
            // Cython: t = self._integrate(...)[0]
            // Access the relevant data point. In C, we have the full trajectory.
            // The Cython was likely getting the height at `zero_distance`.
            // The `record_step` for integrate was `zero_distance`, so the last point should be close.
            if (temp_trajectory.length > 0) {
                height_at_target = temp_trajectory.ranges[temp_trajectory.length - 1].height;
            } else {
                // This shouldn't happen if integrate was successful
                fprintf(stderr, "Warning: integrate successful but no trajectory points found.\n");
                height_at_target = -9999.0; // Indicate problem
            }
            freeTrajectory(engine); // Free temporary trajectory data
            temp_trajectory.ranges = NULL; temp_trajectory.length = 0; // Clear for next iteration
        }

        zero_finding_error = fabs(height_at_target - height_at_zero_m);

        if (zero_finding_error > _cZeroFindingAccuracy) {
            // Adjust barrel_elevation
            // Cython: self._shot_s.barrel_elevation -= (height - height_at_zero) / zero_distance
            if (zero_distance_m != 0.0) { // Protect against division by zero
                engine->tProps.shotData->barrelElevation -= (height_at_target - height_at_zero_m) / zero_distance_m;
            } else {
                // If zero_distance_m is 0, we can't adjust this way.
                // This implies shooting straight up or down for a zero-distance target,
                // which needs different logic or is an invalid input.
                fprintf(stderr, "Error: zero_distance is zero, cannot adjust barrel_elevation.\n");
                // Decide how to handle: break loop, return error, etc.
                break; // Exit loop if cannot adjust
            }
        } else {
            // last barrel_elevation hit zero!
            break;
        }
        iterations_count++;
    }

    // freeTrajectory(engine); // This was previously called inside the loop, now outside.
                              // Moved into the if/else-if branches inside the loop.
                              // If loop finishes, temp_trajectory is freed in the last iteration.

    // Check if the target accuracy was reached
    if (zero_finding_error > _cZeroFindingAccuracy) {
        fprintf(stderr, "ZeroFindingError: Accuracy not reached. Error: %f, Iterations: %d, Final Angle: %f radians.\n",
                zero_finding_error, iterations_count, engine->tProps.shotData->barrelElevation);
        *zeroAngle = engine->tProps.shotData->barrelElevation; // Still return the last calculated angle
        return ZERO_ANGLE_ERROR_MAX_ITERATIONS_REACHED; // Indicate failure to reach accuracy
    }

    *zeroAngle = engine->tProps.shotData->barrelElevation; // Return the calculated zero angle (in radians)
    return ZERO_ANGLE_SUCCESS; // Success
}

int trajectory(EngineT *engine, ShotDataT *shotData, double maxRange, double distStep,
               bool extraData, double timeStep, TrajectoryTableT *resultTrajectory) {

    // 1. Validate incoming pointers
    if (engine == NULL) {
        fprintf(stderr, "Error: trajectory received a NULL engine pointer.\n");
        return -1;
    }
    if (shotData == NULL) {
        fprintf(stderr, "Error: trajectory received a NULL shotData pointer.\n");
        return -1;
    }
    if (resultTrajectory == NULL) {
        fprintf(stderr, "Error: trajectory received a NULL resultTrajectory pointer.\n");
        return -1;
    }

    // --- Handling config reload (if necessary in C) ---
    // In pure C, `engine->config` is directly the `ConfigT*`.
    // The Cython `_config_s = config_bind(self._config)` suggests
    // `_config` might be a Python object needing conversion.
    // If your C `ConfigT` struct is directly managed, this "hack" is likely not needed.
    // `engine->gravityVector` should already be set in `initEngine` based on `engine->config`.
    // If the *contents* of `engine->config` can change *after* `initEngine` but *before* `trajectory`,
    // and you need `gravityVector` to reflect that, then you'd re-calculate it:
    // engine->gravityVector = set(0.0, engine->config->cGravityConstant, 0.0);
    // For this implementation, we assume `engine->gravityVector` is correctly set up.

    // 2. Determine filter flags based on `extraData`
    TrajFlag filterFlags = TRAJ_RANGE; // Default to TRAJ_RANGE
    if (extraData) {
        filterFlags = TRAJ_ALL; // If extra_data is true, use TRAJ_ALL
    }

    // 3. Initialize trajectory properties (analogous to self._init_trajectory)
    // This will set up engine->tProps with the new shotData, curve, machList, dataFilter, and windSock.
    int initStatus = initTrajectory(engine, shotData);
    if (initStatus != 0) {
        fprintf(stderr, "Error: Failed to initialize trajectory properties.\n");
        return -1; // Propagate error
    }

    // 4. Run the integration (analogous to self._integrate)
    // `maxRange` and `distStep` are directly used as doubles.
    // The `_integrate` function needs to fill the `resultTrajectory` struct.
    int integrateStatus = integrate(engine, maxRange, distStep, filterFlags, timeStep, resultTrajectory);
    if (integrateStatus != 0) {
        fprintf(stderr, "Error: Trajectory integration failed.\n");
        // Ensure cleanup even on integration failure
        freeTrajectory(engine);
        return -1; // Propagate error
    }

    // 5. Clean up trajectory properties (analogous to self._free_trajectory)
    // This frees memory allocated within engine->tProps (curve.points, machList.values).
    freeTrajectory(engine);

    // 6. Return success. The resultTrajectory struct has been filled.
    return 0; // Indicate success
}

TrajectoryDataT createTrajectoryData(double time, V3dT rangeVector, V3dT velocityVector,
                                     double velocity, double mach, double spinDrift, double lookAngle,
                                     double densityFactor, double drag, double weight, int flag) {

    // Declare variables for intermediate calculations
    double windage;
    double dropAdjustment;
    double windageAdjustment;
    double trajectoryAngle;
    double targetDropCalc;
    double dropAdjCalc;
    double lookDistanceCalc;
    double energyCalc;
    double ogwCalc;

    // Calculate derived values, mirroring the Cython logic
    windage = rangeVector.z + spinDrift;
    dropAdjustment = getCorrection(rangeVector.x, rangeVector.y);
    windageAdjustment = getCorrection(rangeVector.x, windage);
    trajectoryAngle = atan2(velocityVector.y, velocityVector.x);

    // Calculate target_drop, handling the potential division by zero for cos(look_angle)
    // and the conditional 'if range_vector.x' part from Cython.
    // The Cython `range_vector.x * tan(look_angle)` part implies if range_vector.x is 0, this is 0.
    // If cos(look_angle) is near zero (e.g., look_angle near PI/2 or 3*PI/2),
    // look_distance could become extremely large or +/- infinity.
    // Assuming look_angle is within practical shooting limits where cos(look_angle) is not zero.
    if (rangeVector.x == 0.0) { // If at the very beginning of the trajectory (range 0)
        targetDropCalc = 0.0;
        // Cython's `(look_angle if range_vector.x else 0)` implies if range_vector.x is 0, subtract 0
        dropAdjCalc = dropAdjustment - 0.0;
        lookDistanceCalc = 0.0;
    } else {
        targetDropCalc = (rangeVector.y - rangeVector.x * tan(lookAngle)) * cos(lookAngle);
        dropAdjCalc = dropAdjustment - lookAngle; // Since range_vector.x is not 0, always subtract look_angle
        lookDistanceCalc = rangeVector.x / cos(lookAngle);
    }


    // Calculate energy and OGW using the helper functions
    energyCalc = calculateEnergy(weight, velocity);
    ogwCalc = calculateOGW(weight, velocity);

    // Create and return the TrajectoryDataT struct using designated initializers.
    // Note: The Cython code performs unit conversions (_new_feet, _new_fps, etc.).
    // In C, we generally stick to raw double values in the struct and handle conversions
    // at the display layer if needed. So, we're assigning the calculated doubles directly.
    return (TrajectoryDataT){
        .time = time,
        .distance = rangeVector.x,
        .velocity = velocity,
        .mach = velocity / mach, // Cython has velocity / mach, assuming mach is speed of sound here.
                                  // If 'mach' parameter IS the Mach number, then this should just be `mach`.
                                  // Re-checking Cython: `mach=velocity / mach` is unusual. Typically mach is a ratio.
                                  // Assuming 'mach' parameter is `speed_of_sound_at_current_altitude`.
                                  // If `mach` parameter is already THE mach number, then this calculation is wrong.
                                  // I'll stick to your Cython literally: `velocity / mach`.
                                  // If `mach` input parameter is already the Mach number, change this to `.mach = mach,`
        .height = rangeVector.y,
        .targetDrop = targetDropCalc,
        .dropAdj = dropAdjCalc,
        .windage = windage,
        .windageAdj = windageAdjustment,
        .lookDistance = lookDistanceCalc,
        .angle = trajectoryAngle,
        .densityFactor = densityFactor - 1.0, // Cython has `density_factor - 1`
        .drag = drag,
        .energy = energyCalc,
        .ogw = ogwCalc,
        .flag = flag
    };
}


// Helper to add a TrajectoryDataT to a dynamically growing array
// Returns 0 on success, -1 on reallocation failure
int addTrajectoryDataPoint(TrajectoryTableT *TrajectoryTableTable, TrajectoryDataT newData) {
    // Increase capacity if needed
    size_t newCapacity = TrajectoryTableTable->length + 1;
    TrajectoryDataT *temp = (TrajectoryDataT*)realloc(TrajectoryTableTable->ranges, newCapacity * sizeof(TrajectoryDataT));
    if (temp == NULL) {
        fprintf(stderr, "Error: Failed to reallocate memory for trajectory data points.\n");
        return -1; // Reallocation failed
    }
    TrajectoryTableTable->ranges = temp;
    TrajectoryTableTable->ranges[TrajectoryTableTable->length] = newData;
    TrajectoryTableTable->length++;
    return 0; // Success
}


// Re-implementation of Cython's _integrate function in C
// CORRECTED: Added TrajectoryTableT *trajectory parameter
int integrate(EngineT *engine, double maximumRange, double recordStep, TrajFlag filterFlags, double timeStep, TrajectoryTableT *trajectory) {
    // Input validation
    if (engine == NULL) {
        fprintf(stderr, "Error: integrate received a NULL engine pointer.\n");
        return INTEGRATE_ERROR_NULL_ENGINE;
    }
    // Also check if critical sub-structs are initialized
    if (engine->config == NULL || engine->tProps.shotData == NULL ||
        engine->tProps.windSock.winds == NULL || engine->tProps.shotData->atmo == NULL) {
        fprintf(stderr, "Error: integrate: Engine or ShotData properties not fully initialized.\n");
        return INTEGRATE_ERROR_BAD_INPUT_SHOTDATA;
    }

    double velocity;
    double delta_time;
    double density_factor = 0.0;
    double mach = 0.0;

    double time = 0.0;
    double drag_val = 0.0; // Renamed to drag_val to avoid conflict with `drag` field in TrajectoryDataT

    V3dT range_vector;
    V3dT velocity_vector;
    V3dT delta_range_vector;
    V3dT velocity_adjusted;

    double min_step;
    double calc_step = engine->tProps.shotData->calcStep;

    // Initialize wind-related variables to first wind reading (if any)
    V3dT wind_vector = currentWindVector(&(engine->tProps.windSock)); // Use the helper directly

    BaseTrajDataT *data_to_record = NULL; // Pointer to BaseTrajDataT from shouldRecord

    // Early bindings for config values
    double _cMinimumVelocity = engine->config->cMinimumVelocity;
    double _cMaximumDrop = engine->config->cMaximumDrop;
    double _cMinimumAltitude = engine->config->cMinimumAltitude;

    // Temp vector for calculations
    V3dT _tv;

    double lastRecordedRange = 0.0;

    // Initialize velocity and position of projectile
    velocity = engine->tProps.shotData->muzzleVelocity;
    range_vector = set(0.0,
                       -engine->tProps.shotData->cantCosine * engine->tProps.shotData->sightHeight,
                       -engine->tProps.shotData->cantSine * engine->tProps.shotData->sightHeight);

    _tv = set(cos(engine->tProps.shotData->barrelElevation) * cos(engine->tProps.shotData->barrelAzimuth),
              sin(engine->tProps.shotData->barrelElevation),
              cos(engine->tProps.shotData->barrelElevation) * sin(engine->tProps.shotData->barrelAzimuth));
    velocity_vector = mulS(&_tv, velocity);

    min_step = fmin(calc_step, recordStep);

    setupSeenZero(&(engine->tProps.dataFilter), range_vector.y,
                  engine->tProps.shotData->barrelElevation, engine->tProps.shotData->lookAngle);


    // Initialize the output trajectory array
    trajectory->ranges = NULL; // Initialize pointer
    trajectory->length = 0;    // Initialize length


    lastRecordedRange = 0.0;

    while ( (range_vector.x <= maximumRange + min_step) ||
            ((filterFlags != TRAJ_NONE) && (lastRecordedRange <= maximumRange - 1e-6)) )
    {
        if (range_vector.x >= engine->tProps.windSock.nextRange) {
            wind_vector = windVectorForRange(&(engine->tProps.windSock), range_vector.x);
        }

        updateDensityFactorAndMatchForAltitude(engine->tProps.shotData->atmo,
                                               engine->tProps.shotData->alt0 + range_vector.y,
                                               &density_factor, &mach);

        if (filterFlags != TRAJ_NONE) {
            data_to_record = shouldRecord(&(engine->tProps.dataFilter), range_vector, velocity_vector, mach, time);
            if (data_to_record != NULL) {
                TrajectoryDataT currentRow = createTrajectoryData(
                    data_to_record->time, data_to_record->position, data_to_record->velocity,
                    mag(&data_to_record->velocity), data_to_record->mach,
                    spinDrift(engine->tProps.shotData, time), engine->tProps.shotData->lookAngle,
                    density_factor, drag_val, engine->tProps.shotData->weight,
                    engine->tProps.dataFilter.currentFlag
                );
                // CORRECTED: Pass 'trajectory' to addTrajectoryDataPoint
                if (addTrajectoryDataPoint(trajectory, currentRow) != 0) {
                    free(data_to_record);
                    if (trajectory->ranges != NULL) {
                        free(trajectory->ranges);
                        trajectory->ranges = NULL;
                        trajectory->length = 0;
                    }
                    return INTEGRATE_ERROR_REALLOC_FAILED;
                }
                lastRecordedRange = data_to_record->position.x;
                free(data_to_record);
                data_to_record = NULL;
            }
        }

        velocity_adjusted = sub(&velocity_vector, &wind_vector);
        velocity = mag(&velocity_adjusted);
        
        delta_time = calc_step / fmax(1.0, velocity);

        if (mach == 0.0) {
             fprintf(stderr, "Warning: Mach is zero during integration, setting drag to 0.\n");
             drag_val = 0.0;
        } else {
             drag_val = density_factor * velocity * dragByMach(engine->tProps.shotData, velocity / mach);
        }

        _tv = mulS(&velocity_adjusted, drag_val);
        _tv = sub(&_tv, &engine->gravityVector);
        _tv = mulS(&_tv, delta_time);
        velocity_vector = sub(&velocity_vector, &_tv);

        delta_range_vector = mulS(&velocity_vector, delta_time);
        range_vector = add(&range_vector, &delta_range_vector);

        velocity = mag(&velocity_vector);
        time += delta_time;

        if (velocity < _cMinimumVelocity ||
            range_vector.y < _cMaximumDrop ||
            (engine->tProps.shotData->alt0 + range_vector.y) < _cMinimumAltitude) {

            TrajectoryDataT currentRow = createTrajectoryData(
                time, range_vector, velocity_vector,
                velocity, mach,
                spinDrift(engine->tProps.shotData, time), engine->tProps.shotData->lookAngle,
                density_factor, drag_val, engine->tProps.shotData->weight,
                engine->tProps.dataFilter.currentFlag
            );
            // CORRECTED: Pass 'trajectory' to addTrajectoryDataPoint
            if (addTrajectoryDataPoint(trajectory, currentRow) != 0) {
                 return INTEGRATE_ERROR_REALLOC_FAILED;
            }

            if (velocity < _cMinimumVelocity) {
                return INTEGRATE_REASON_MIN_VELOCITY_REACHED;
            } else if (range_vector.y < _cMaximumDrop) {
                return INTEGRATE_REASON_MAX_DROP_REACHED;
            } else {
                return INTEGRATE_REASON_MIN_ALTITUDE_REACHED;
            }
        }
    }

    // CORRECTED: Use trajectory->length for the final check
    if (trajectory->length < 2) {
        TrajectoryDataT currentRow = createTrajectoryData(
            time, range_vector, velocity_vector,
            velocity, mach,
            spinDrift(engine->tProps.shotData, time), engine->tProps.shotData->lookAngle,
            density_factor, drag_val, engine->tProps.shotData->weight,
            TRAJ_NONE
        );
        // CORRECTED: Pass 'trajectory' to addTrajectoryDataPoint
        if (addTrajectoryDataPoint(trajectory, currentRow) != 0) {
            return INTEGRATE_ERROR_REALLOC_FAILED;
        }
    }

    return INTEGRATE_SUCCESS;
}


MachListT tableToMach(DragTableT *table) {
    MachListT machList;
    machList.values = NULL;
    machList.length = 0;

    if (table == NULL || table->table == NULL || table->length == 0) {
        fprintf(stderr, "Warning: tableToMach received a NULL, empty, or invalid DragTableT.\n");
        // Return an empty MachListT
        return machList;
    }

    // Each point in DragTableT consists of 2 doubles (Mach, CD).
    // So, the 'values' array in MachListT needs to be twice the length of DragTableT.
    size_t num_doubles = table->length * 2;

    // Allocate memory for the interleaved Mach and CD values
    machList.values = (double*)malloc(num_doubles * sizeof(double));
    if (machList.values == NULL) {
        fprintf(stderr, "Error: Failed to allocate memory for MachListT.values.\n");
        return machList; // Return empty on allocation failure
    }

    machList.length = num_doubles; // Set the length to the total number of doubles

    // Copy data from DragTableT to MachListT in an interleaved manner
    for (size_t i = 0; i < table->length; ++i) {
        // Mach value at even index
        machList.values[2 * i] = table->table[i].Mach;
        // CD value at odd index
        machList.values[2 * i + 1] = table->table[i].CD;
    }

    return machList;
}

// Helper function to free a MachListT
// This function frees the single 'values' array.
void freeMachList(MachListT *machList) {
    if (machList == NULL) {
        return;
    }
    if (machList->values != NULL) {
        free(machList->values);
        machList->values = NULL;
    }
    machList->length = 0;
}