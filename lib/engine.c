#include <math.h>
#include "v3d.h"
#include "bindings.h"
#include "trajectoryData.h"
#include "engine.h"

TrajectoryDataFilter createTrajectoryDataFilter(
    int filterFlags, double rangeStep,
    V3d initialPosition, V3d initialVelocity,
    double timeStep // Default value of 0.0 handled by caller or specific logic
) {
    // Initialize the struct using designated initializers
    // and your TrajFlag enum where appropriate.
    TrajectoryDataFilter tdf = {
        .filter = filterFlags,
        .currentFlag = TRAJ_NONE,    // Using the enum member explicitly
        .seenZero = TRAJ_NONE,       // Using the enum member explicitly
        .timeStep = timeStep,
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

    return tdf;
}

void setupSeenZero(TrajectoryDataFilter *tdf, double height, double barrelElevation, double lookAngle) {
    if (height >= 0) {
        tdf->seenZero |= TRAJ_ZERO_UP; // Use TRAJ_ZERO_UP from your C enum
    } else if (height < 0 && barrelElevation < lookAngle) {
        tdf->seenZero |= TRAJ_ZERO_DOWN; // Use TRAJ_ZERO_DOWN from your C enum
    }
    tdf->lookAngle = lookAngle; // Access struct members using '->' for a pointer
}

// Helper to check and set the RANGE flag based on time step
static void checkNextTime(TrajectoryDataFilter *tdf, double time) {
    if (time > tdf->timeOfLastRecord + tdf->timeStep) {
        tdf->currentFlag |= TRAJ_RANGE; // Use C enum
        tdf->timeOfLastRecord = time;
    }
}

// Helper to check and set the MACH flag based on Mach crossing
static void checkMachCrossing(TrajectoryDataFilter *tdf, double velocity, double mach) {
    double currentVMach = velocity / mach; // No need for 'cdef' in C
    if (tdf->previousVMach > 1 && 1 >= currentVMach) {
        tdf->currentFlag |= TRAJ_MACH; // Use C enum
    }
    tdf->previousVMach = currentVMach;
}

// Helper to check and set ZERO_UP/ZERO_DOWN flags based on zero crossing
static void checkZeroCrossing(TrajectoryDataFilter *tdf, V3d rangeVector) {
    if (rangeVector.x > 0) {
        double referenceHeight = rangeVector.x * tan(tdf->lookAngle); // tan() from <math.h>

        if (!(tdf->seenZero & TRAJ_ZERO_UP)) {
            if (rangeVector.y >= referenceHeight) {
                tdf->currentFlag |= TRAJ_ZERO_UP;
                tdf->seenZero |= TRAJ_ZERO_UP;
            }
        }

        else if (!(tdf->seenZero & TRAJ_ZERO_DOWN)) {
            if (rangeVector.y < referenceHeight) {
                tdf->currentFlag |= TRAJ_ZERO_DOWN;
                tdf->seenZero |= TRAJ_ZERO_DOWN;
            }
        }
    }
}

BaseTrajDataT* shouldRecord(TrajectoryDataFilter *tdf, V3d position, V3d velocity, double mach, double time) {
    // Initialize data pointer to NULL. This will be returned if no record is generated.
    BaseTrajDataT *data = NULL;
    double ratio;

    tdf->currentFlag = TRAJ_NONE; // Reset current flags

    // Check for range-based recording
    if ((tdf->rangeStep > 0) && (position.x >= tdf->nextRecordDistance)) {
        while (tdf->nextRecordDistance + tdf->rangeStep < position.x) {
            // Handle case where we've stepped past more than one record distance
            tdf->nextRecordDistance += tdf->rangeStep;
        }

        if (position.x > tdf->previousPosition.x) {
            // Interpolate to get BaseTrajDataT at the record distance
            ratio = (tdf->nextRecordDistance - tdf->previousPosition.x) / (position.x - tdf->previousPosition.x);

            // V3d operations - assuming functions like sub, mulS, add exist
            V3d tempSubPosition = sub(&position, &tdf->previousPosition);
            V3d tempMulPosition = mulS(&tempSubPosition, ratio);
            V3d tempPosition = add(&tdf->previousPosition, &tempMulPosition);

            V3d tempSubVelocity = sub(&velocity, &tdf->previousVelocity);
            V3d tempMulVelocity = mulS(&tempSubVelocity, ratio);
            V3d tempVelocity = add(&tdf->previousVelocity, &tempMulVelocity);

            // Allocate memory for the new BaseTrajDataT struct
            data = (BaseTrajDataT*)malloc(sizeof(BaseTrajDataT));
            if (data == NULL) {
                // Handle allocation error: possibly log, or return NULL immediately
                fprintf(stderr, "Error: Failed to allocate memory for BaseTrajDataT in shouldRecord.\n");
                // The function will return NULL, indicating no data.
            } else {
                // Initialize the allocated struct with interpolated values
                *data = (BaseTrajDataT){
                    .time = tdf->previousTime + (time - tdf->previousTime) * ratio,
                    .position = tempPosition,
                    .velocity = tempVelocity,
                    .mach = tdf->previousMach + (mach - tdf->previousMach) * ratio
                };
            }
        }
        tdf->currentFlag |= TRAJ_RANGE; // Set the RANGE flag
        tdf->nextRecordDistance += tdf->rangeStep;
        tdf->timeOfLastRecord = time;
    } else if (tdf->timeStep > 0) {
        checkNextTime(tdf, time); // Call the internal helper function
    }

    checkZeroCrossing(tdf, position);     // Call the internal helper function
    checkMachCrossing(tdf, mag(&velocity), mach); // Call the internal helper function

    // If current_flag matches filter and data was not already set (i.e., data is NULL from range interpolation)
    if ((tdf->currentFlag & tdf->filter) != 0 && data == NULL) {
        // Allocate memory for the new BaseTrajDataT struct
        data = (BaseTrajDataT*)malloc(sizeof(BaseTrajDataT));
        if (data == NULL) {
            // Handle allocation error
            fprintf(stderr, "Error: Failed to allocate memory for BaseTrajDataT (filter match) in shouldRecord.\n");
            // The function will return NULL
        } else {
            // Initialize the allocated struct with current values
            *data = (BaseTrajDataT){
                .time = time,
                .position = position,
                .velocity = velocity,
                .mach = mach
            };
        }
    }

    // Update previous values for the next iteration
    tdf->previousTime = time;
    tdf->previousPosition = position;
    tdf->previousVelocity = velocity;
    tdf->previousMach = mach;

    return data; // Returns NULL if no record was generated, or a pointer to new data
}


EngineT createEngine(ConfigT *config) {
    // Check for NULL config pointer
    if (config == NULL) {
        fprintf(stderr, "Error: createEngine called with NULL config pointer.\n");
        // Return a zero-initialized EngineT as an error state
        return (EngineT){0}; // This initializes all members to 0/NULL/false
    }

    // Correct use of compound literal with designated initializers for EngineT
    EngineT engine = {
        .config = *config, // Correct: Dereference config pointer to copy the struct
        .gravityVector = set(0.0, config->cGravityConstant, 0.0), // Use your set function for V3d
        // Or if you prefer a V3d compound literal directly:
        // .gravityVector = (V3d){0.0, config->cGravityConstant, 0.0},
        .tableData = (DragTableT){0}, // Example: Zero-initialize if it's a struct by value
        .ws = (WindSockT){0},         // Example: Zero-initialize if it's a struct by value
        .sd = (ShotDataT){0}          // Example: Zero-initialize if it's a struct by value
    };

    // If any member (like ws.winds) is a pointer that needs dynamic allocation,
    // you would do that *after* this initialization. E.g.:
    // engine.ws.winds = (WindT*)malloc(INITIAL_WIND_ARRAY_SIZE * sizeof(WindT));
    // if (engine.ws.winds == NULL) { /* handle error, free other stuff */ }
    // engine.ws.length = INITIAL_WIND_ARRAY_SIZE;
    // engine.ws.current = 0;

    return engine;
}