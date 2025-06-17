#ifndef TRAJECTORY_DATA_H
#define TRAJECTORY_DATA_H

#include "v3d.h"

typedef enum {
    TRAJ_NONE = 0,
    TRAJ_ZERO_UP = 1,
    TRAJ_ZERO_DOWN = 2,
    TRAJ_ZERO = TRAJ_ZERO_UP | TRAJ_ZERO_DOWN, // This is a bitwise OR operation
    TRAJ_MACH = 4,
    TRAJ_RANGE = 8,
    TRAJ_APEX = 16,
    TRAJ_ALL = TRAJ_RANGE | TRAJ_ZERO_UP | TRAJ_ZERO_DOWN | TRAJ_MACH | TRAJ_APEX
} TrajFlag;

// Corrected BaseTrajData struct (already good, just adding for completeness)
typedef struct {
    double time;
    V3d position;
    V3d velocity;
    double mach;
} BaseTrajDataT;

// Corrected TrajectoryData struct
typedef struct {
    double time;
    double distance; // Changed from object to double
    double velocity; // Changed from object to double
    double mach;
    double height; // Changed from object to double
    double targetDrop; // Changed from object to double, good C-style name
    double dropAdj; // Changed from object to double, good C-style name
    double windage; // Changed from object to double
    double windageAdj; // Changed from object to double, good C-style name
    double lookDistance; // Changed from object to double, good C-style name
    double angle; // Changed from object to double
    double densityFactor; // Already double, good.
    double drag; // Already double, good.
    double energy; // Changed from object to double
    double ogw; // Changed from object to double
    int flag; // int is correct
} TrajectoryDataT; // Added 'T' suffix for consistency

#endif // TRAJECTORY_DATA_H