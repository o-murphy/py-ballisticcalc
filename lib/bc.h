#ifndef BC_H
#define BC_H

#include <stdbool.h>
#include "v3d.h"

// --- Global Constants ---
// Declared as extern, defined in bindings.c
extern const double C_DEGREES_F_TO_R;
extern const double C_DEGREES_C_TO_K;
extern const double C_SPEED_OF_SOUND_IMPERIAL;
extern const double C_SPEED_OF_SOUND_METRIC;
extern const double C_LAPSE_RATE_K_PER_FOOT;
extern const double C_LAPSE_RATE_IMPERIAL;
extern const double C_PRESSURE_EXPONENT;
extern const double C_LOWEST_TEMP_F;
extern const double M_TO_FEET;
extern const double C_MAX_WIND_DISTANCE_FEET;

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

typedef enum {
    INTEGRATE_SUCCESS = 0,
    INTEGRATE_ERROR_NULL_ENGINE = -1,
    INTEGRATE_ERROR_MALLOC_FAILED = -2,
    INTEGRATE_ERROR_REALLOC_FAILED = -3,
    INTEGRATE_REASON_MIN_VELOCITY_REACHED = 1,
    INTEGRATE_REASON_MAX_DROP_REACHED = 2,
    INTEGRATE_REASON_MIN_ALTITUDE_REACHED = 3,
    INTEGRATE_ERROR_BAD_INPUT_SHOTDATA = -4 // Added for robustness
} IntegrateStatus;

typedef enum {
    ZERO_ANGLE_SUCCESS = 0,
    ZERO_ANGLE_ERROR_NULL_ENGINE = -1,
    ZERO_ANGLE_ERROR_NULL_SHOTDATA = -2,
    ZERO_ANGLE_ERROR_NULL_ZEROANGLE_OUT = -3,
    ZERO_ANGLE_ERROR_INTEGRATE_FAILED = -4,
    ZERO_ANGLE_ERROR_MAX_ITERATIONS_REACHED = 1 // ZeroFindingError equivalent
} ZeroAngleStatus;

// Corrected BaseTrajData struct (already good, just adding for completeness)
typedef struct {
    double time;
    V3dT position;
    V3dT velocity;
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

typedef struct {
    TrajectoryDataT *ranges;
    size_t length;
} TrajectoryTableT;

typedef struct {
    double cMaxCalcStepSizeFeet;
    double cZeroFindingAccuracy;
    double cMinimumVelocity;
    double cMaximumDrop;
    int cMaxIterations;
    double cGravityConstant;
    double cMinimumAltitude;
} ConfigT;

// double getCalcStepDefault(ConfigT * config);
// double getCalcStep(ConfigT * config, double step);

typedef struct {
    double CD;
    double Mach;
} DragTablePointT;

typedef struct {
    DragTablePointT * table;
    size_t length;
} DragTableT;

typedef struct {
    double a, b, c;
} CurvePointT;

typedef struct {
    CurvePointT * points;
    size_t length;
} CurveT;

typedef struct {
    double * values;
    size_t length;
} MachListT;

MachListT tableToMach(DragTableT * table);
CurveT calculateCurve(DragTableT * table);
double calculateByCurveAndMachList(MachListT * machList, CurveT * curve, double mach);
// Memory deallocation functions
void freeDragTable(DragTableT *table);
void freeCurve(CurveT * curve);
void freeMachList(MachListT * machList);

typedef struct {
    double t0;
    double a0;
    double p0;
    double mach;
    double densityFactor; // Renamed from density_ratio to match C convention and usage
    double cLowestTempC;
} AtmosphereT;

void updateDensityFactorAndMatchForAltitude(AtmosphereT * atmo, double altitude, double * densityRatio, double * mach);

typedef struct {
    double velocity;
    double directionFrom;
    double untilDistance;
    double MAX_DISTANCE_FEET;
} WindT;

V3dT windToVector(const WindT *w);

typedef struct {
    WindT * winds;
    size_t length;
} WindsT;

typedef struct {
    double bc;
    DragTableT * dragTable;
    double lookAngle;
    double twist;
    double length;
    double diameter;
    double weight;
    double barrelElevation;
    double barrelAzimuth;
    double sightHeight;
    double cantCosine;
    double cantSine;
    double alt0;
    double calcStep;
    double muzzleVelocity;
    double stabilityCoefficient;
    AtmosphereT * atmo;
    WindsT * winds;
} ShotDataT;

double spinDrift(ShotDataT * shotData, double time);
double dragByMach(ShotDataT * shotData, double mach);
void updateStabilityCoefficient(ShotDataT * shotData);

typedef struct {
    int filter, currentFlag, seenZero;
    double timeStep, rangeStep;
    double timeOfLastRecord, nextRecordDistance;
    double previousMach, previousTime;
    V3dT previousPosition, previousVelocity;
    double previousVMach;
    double lookAngle;
} TrajectoryDataFilterT;

int initDataFilter(TrajectoryDataFilterT *tdf, int filterFlags, double rangeStep,
                   V3dT initialPosition, V3dT initialVelocity, double timeStep);
void setupSeenZero(TrajectoryDataFilterT * tdf, double height, double barrelElevation, double lookAngle);
static void checkNextTime(TrajectoryDataFilterT *tdf, double time);
static void checkMachCrossing(TrajectoryDataFilterT *tdf, double velocity, double mach);
static void checkZeroCrossing(TrajectoryDataFilterT *tdf, V3dT rangeVector);
BaseTrajDataT* shouldRecord(TrajectoryDataFilterT *tdf, V3dT position, V3dT velocity, double mach, double time);

typedef struct {
    WindsT * winds;
    int current;
    double nextRange;
    V3dT lastVectorCache;
} WindSockT;

int initWindSock(WindSockT * ws, WindsT * winds);
V3dT currentWindVector(WindSockT * ws);
void updateWindCache(WindSockT * ws);
V3dT windVectorForRange(WindSockT * ws, double nextRange);

typedef struct {
    ShotDataT * shotData;
    CurveT curve;
    MachListT machList;  
    TrajectoryDataFilterT dataFilter;
    WindSockT windSock;  
} TrajectoryPropsT;

typedef struct {
    ConfigT * config;
    V3dT gravityVector;
    TrajectoryPropsT tProps;
} EngineT;

int initEngine(EngineT *engine, ConfigT *config);
int initTrajectory(EngineT *engine, ShotDataT *initialShotData);
void freeTrajectory(EngineT *engine);
int zeroAngle(EngineT *engine, ShotDataT *shotData, double distance, double * zeroAngle);
int trajectory(EngineT *engine, ShotDataT *ShotData, double maxRange, double distStep, bool extraData, double timeStep, TrajectoryTableT * trajectory);
int integrate(EngineT *engine, double maximumRange, double recordStep, TrajFlag filterFlags, double timeStep, TrajectoryTableT * trajectory);

// helpers
double getCorrection(double distance, double offset);
double calculateEnergy(double bulletWeight, double velocity);
double calculateOGW(double bulletWeight, double velocity);

int addTrajectoryDataPoint(TrajectoryTableT *TrajectoryTableTable, TrajectoryDataT newData);

TrajectoryDataT createTrajectoryData(double time, V3dT rangeVector, V3dT velocityVector,
                                     double velocity, double mach, double spinDrift, double lookAngle,
                                     double densityFactor, double drag, double weight, int flag);



#endif // BC_H