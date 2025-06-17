#ifndef TRAJECTORY_DATA_H
#define TRAJECTORY_DATA_H

#include "v3d.h"

// Corrected TrajFlag enum
typedef enum { // Using typedef enum for convenience
    NONE = 0,
    ZERO_UP = 1,
    ZERO_DOWN = 2,
    ZERO = ZERO_UP | ZERO_DOWN,
    MACH = 4,
    RANGE = 8,
    APEX = 16,
    ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX
} TrajFlag; // Semicolon after the closing brace is crucial

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