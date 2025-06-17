#ifndef TRAJECTORY_DATA_H
#define TRAJECTORY_DATA_H

#include "v3d.h" // Assuming v3d.h defines V3d struct

// Trajectory Flag Enum
// This enum defines bit flags for various trajectory characteristics.
typedef enum {
    TRAJ_NONE = 0,         // No flags set
    TRAJ_ZERO_UP = 1,      // Trajectory is zeroed on the "up" part of the curve
    TRAJ_ZERO_DOWN = 2,    // Trajectory is zeroed on the "down" part of the curve
    TRAJ_ZERO = TRAJ_ZERO_UP | TRAJ_ZERO_DOWN, // Both zero flags
    TRAJ_MACH = 4,         // Mach data is available/relevant
    TRAJ_RANGE = 8,        // Range data is available/relevant
    TRAJ_APEX = 16,        // Apex (highest point) data is available/relevant
    TRAJ_ALL = TRAJ_RANGE | TRAJ_ZERO_UP | TRAJ_ZERO_DOWN | TRAJ_MACH | TRAJ_APEX // All flags
} TrajFlag;

// Base Trajectory Data Structure
// Represents fundamental ballistic data points.
typedef struct {
    double time;       // Time elapsed
    V3d position;      // Position vector (x, y, z)
    V3d velocity;      // Velocity vector (vx, vy, vz)
    double mach;       // Mach number
} BaseTrajData; // Renamed from BaseTrajDataT, as 'T' suffix is typically for typedef names of structs.
                // Keeping it as BaseTrajData for direct use.

// Trajectory Data Structure
// Represents a comprehensive set of calculated trajectory parameters at a given point.
typedef struct {
    double time;            // Time elapsed
    double distance;        // Distance traveled (downrange)
    double velocity;        // Magnitude of velocity
    double mach;            // Mach number
    double height;          // Vertical drop/rise from line of sight
    double targetDrop;      // Predicted drop at target distance
    double dropAdj;         // Drop adjustment required
    double windage;         // Horizontal wind drift
    double windageAdj;      // Windage adjustment required
    double lookDistance;    // Distance for current sight picture
    double angle;           // Angle of impact/flight
    double densityFactor;   // Air density factor
    double drag;            // Drag coefficient
    double energy;          // Kinetic energy of the projectile
    double ogw;             // Optimal Game Weight (OGW) or similar metric
    int flag;               // Bit flags from TrajFlag enum
} TrajectoryData; // Renamed from TrajectoryDataT for direct use.

#endif // TRAJECTORY_DATA_H