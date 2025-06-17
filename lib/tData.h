#ifndef TDATA_H
#define TDATA_H

#include <stdlib.h>


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

typedef struct {
    TrajectoryDataT *ranges;
    size_t length;
    size_t capacity; // <-- NEW: Added capacity field
} TrajectoryTableT;

int initTrajectoryTable(TrajectoryTableT *table);
int addTrajectoryDataPoint(TrajectoryTableT *TrajectoryTableTable, TrajectoryDataT newData);
void freeTrajectoryTable(TrajectoryTableT *table);


#endif // TDATA_H