#include <stdlib.h>
#include "bc.h"
#include "v3d.h"


void main() {
    return;
}

// Re-implementation of Cython's _integrate function in C
// CORRECTED: Added TrajectoryTableT *trajectory parameter
int integrate_euler(EngineT *engine, double maximumRange, double recordStep, TrajFlag filterFlags, double timeStep, TrajectoryTableT *trajectory) {
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