#include <stdlib.h> // <-- You likely already have this for malloc/free
#include "v3d.h"
#include "tData.h"
#include "tDataFilter.h"

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