#include <stdio.h>
#include <stdlib.h> // For malloc, free
#include <stdbool.h> // For bool type
#include <math.h>   // For M_PI (or define PI), fabs, cos, sin, tan, pow, fmin, atan2

// Include all necessary header files for your project
#include "bc.h"
#include "config.h"
#include "atmo.h"
#include "drag.h"
#include "wind.h"
#include "tData.h" // For TrajectoryTableT, TrajectoryDataT
#include "tDataFilter.h" // If you have separate filter functions
#include "v3d.h" // For V3dT and vector operations
#include "consts.h" // For SUCCESS, ERROR_*, M_PI etc. if defined there.

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Function to print TrajectoryDataT (for debugging/output)
void printTrajectoryDataT(const TrajectoryDataT* data) {
    if (data == NULL) {
        printf("  (NULL TrajectoryDataT)\n");
        return;
    }
    printf("  Time: %.4f s, Distance: %.2f ft, Velocity: %.2f ft/s, Mach: %.2f, Height: %.2f ft\n",
           data->time, data->distance, data->velocity, data->mach, data->height);
    printf("  TargetDrop: %.2f ft, DropAdj: %.4f rad, Windage: %.2f ft, WindageAdj: %.4f rad\n",
           data->targetDrop, data->dropAdj, data->windage, data->windageAdj);
    printf("  LookDistance: %.2f ft, Angle: %.4f rad, DensityFactor: %.4f, Drag: %.4f\n",
           data->lookDistance, data->angle, data->densityFactor, data->drag);
    printf("  Energy: %.2f ft-lbs, OGW: %.2e, Flag: %d\n",
           data->energy, data->ogw, data->flag);
}


int main() {
    printf("Starting C main program...\n");
    int status;

    // --- 1. Create a ConfigT instance ---
    ConfigT config = {
        .cMaxCalcStepSizeFeet = 1.0,
        .cZeroFindingAccuracy = 0.001,
        .cMinimumVelocity = 500.0,
        .cMaximumDrop = -100.0, // Use negative for drop below bore
        .cMaxIterations = 1000,
        .cGravityConstant = 32.174, // ft/s^2
        .cMinimumAltitude = 0.0
    };
    printf("ConfigT initialized.\n");

    // --- 2. Create an EngineT instance ---
    EngineT engine;
    status = initEngine(&engine, &config);
    if (status != SUCCESS) {
        fprintf(stderr, "Error: Failed to initialize C engine: %d\n", status);
        return 1;
    }
    printf("EngineT initialized.\n");

    // --- 3. Create an AtmosphereT instance ---
    AtmosphereT atmo = {
        .t0 = 293.15,   // 20 C in Kelvin
        .a0 = 1116.4,   // Speed of sound in ft/s at sea level standard
        .p0 = 1013.25,  // hPa (hectopascals)
        .mach = 1.0,    // Will be updated by C code
        .densityFactor = 1.0, // Will be updated by C code
        .cLowestTempC = -70.0
    };
    printf("AtmosphereT initialized.\n");

    // --- 4. Create a DragTableT instance (example G1 drag table data) ---
    // Allocate memory for drag points
    size_t num_drag_points = 6;
    DragTablePointT *drag_points = (DragTablePointT*)malloc(num_drag_points * sizeof(DragTablePointT));
    if (drag_points == NULL) {
        fprintf(stderr, "Error: Malloc for drag_points failed.\n");
        return 1;
    }

    drag_points[0] = (DragTablePointT){.Mach = 0.0, .CD = 0.5};
    drag_points[1] = (DragTablePointT){.Mach = 0.5, .CD = 0.4};
    drag_points[2] = (DragTablePointT){.Mach = 0.8, .CD = 0.3};
    drag_points[3] = (DragTablePointT){.Mach = 1.0, .CD = 0.6}; // Transonic spike
    drag_points[4] = (DragTablePointT){.Mach = 1.2, .CD = 0.45};
    drag_points[5] = (DragTablePointT){.Mach = 2.0, .CD = 0.3};

    DragTableT drag_table = {
        .table = drag_points,
        .length = num_drag_points
    };
    printf("DragTableT initialized.\n");

    // --- 5. Create a WindsT instance (example winds data) ---
    // Allocate memory for wind data
    size_t num_winds = 2;
    WindT *winds_data = (WindT*)malloc(num_winds * sizeof(WindT));
    if (winds_data == NULL) {
        fprintf(stderr, "Error: Malloc for winds_data failed.\n");
        // Free previously allocated memory before exiting
        free(drag_points);
        return 1;
    }

    winds_data[0] = (WindT){.velocity = 10.0, .directionFrom = 90.0 * M_PI / 180.0, .untilDistance = 500.0, .MAX_DISTANCE_FEET = 999999.0};
    winds_data[1] = (WindT){.velocity = 5.0, .directionFrom = 0.0, .untilDistance = 1000.0, .MAX_DISTANCE_FEET = 999999.0};

    WindsT winds = {
        .winds = winds_data,
        .length = num_winds
    };
    printf("WindsT initialized.\n");

    // --- 6. Create ShotDataT instance ---
    ShotDataT shot_data = {
        .bc = 0.3,
        .dragTable = &drag_table, // Point to the locally defined drag_table
        .lookAngle = 0.0,
        .twist = 1.0,
        .length = 2.0,    // inches
        .diameter = 0.308, // inches
        .weight = 175.0,  // grains
        .barrelElevation = 0.0,
        .barrelAzimuth = 0.0,
        .sightHeight = 1.5, // inches
        .cantCosine = 1.0,
        .cantSine = 0.0,
        .alt0 = 0.0,
        .calcStep = 0.01,
        .muzzleVelocity = 2600.0, // ft/s
        .stabilityCoefficient = 0.0, // Will be updated by C code
        .atmo = &atmo, // Point to the locally defined atmo
        .winds = &winds, // Point to the locally defined winds
    };
    printf("ShotDataT initialized.\n");

    // --- 6.1 Update Stability Coefficient ---
    updateStabilityCoefficient(&shot_data);
    printf("Updated stability coefficient: %.4f\n", shot_data.stabilityCoefficient);

    // --- 7. Call trajectory calculation ---
    double max_range_feet = 1000.0 * 3.0; // 1000 yards to feet
    double dist_step_feet = 10.0 * 3.0;   // 10 yards to feet
    bool extra_data = true;
    double time_step = 0.01; // seconds

    TrajectoryTableT traj_table_c; // This will hold the result from trajectory()

    printf("Calling trajectory function...\n");
    status = trajectory(&engine, &shot_data, max_range_feet, dist_step_feet, extra_data, time_step, &traj_table_c);

    if (status == SUCCESS) {
        printf("Trajectory calculated successfully. Points: %zu\n", traj_table_c.length);
        if (traj_table_c.length > 0) {
            printf("First point:\n");
            printTrajectoryDataT(&traj_table_c.ranges[0]);
            if (traj_table_c.length > 1) {
                 printf("Last point:\n");
                 printTrajectoryDataT(&traj_table_c.ranges[traj_table_c.length - 1]);
            }
        }
    } else {
        fprintf(stderr, "Error: Trajectory calculation failed with status: %d\n", status);
    }

    // --- Cleanup: Free dynamically allocated C memory ---
    printf("Cleaning up dynamically allocated memory...\n");
    free(drag_points); // Free memory allocated for drag_table.table
    free(winds_data);  // Free memory allocated for winds.winds
    freeTrajectoryTable(&traj_table_c); // Free memory allocated within traj_table_c (its ranges)

    printf("Script finished.\n");

    return 0;
}