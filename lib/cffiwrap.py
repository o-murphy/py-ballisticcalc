from cffi import FFI
import math

ffi = FFI()

ffi.cdef("""
// --- enum для статусів ---
typedef enum {
    SUCCESS = 0,
    ERROR_NULL_ENGINE = -1,
    ERROR_NULL_SHOTDATA = -2,
    ERROR_NULL_ZEROANGLE = -3,
    ERROE_NULL_TRAJECTORY = -4,
    ERROR_INVALID_SHOTDATA = -5,
    ERROR_MALLOC_FAILED = -6,
    ERROR_REALLOC_FAILED = -7,
    ERROR_INTEGRATE_FAILED = -8,
    ERROR_NULL_ZEROANGLE_OUT = -9,
    MIN_VELOCITY_REACHED = 1,
    MAX_DROP_REACHED = 2,
    MIN_ALTITUDE_REACHED = 3,
    MAX_ITERATIONS_REACHED = 4
} CalculationStatus;

// v3d.h
typedef struct {
    double x;
    double y;
    double z;
} V3dT;

// drag.h
typedef struct {
    double CD;
    double Mach;
} DragTablePointT;

typedef struct {
    DragTablePointT *table;
    size_t length;
} DragTableT;

// atmo.h
typedef struct {
    double t0;
    double a0;
    double p0;
    double mach;
    double densityFactor;
    double cLowestTempC;
} AtmosphereT;

// wind.h
typedef struct {
    double velocity;
    double directionFrom;
    double untilDistance;
    double MAX_DISTANCE_FEET;
} WindT;

typedef struct {
    WindT *winds;
    size_t length;
} WindsT;

// config.h
typedef struct {
    double cMaxCalcStepSizeFeet;
    double cZeroFindingAccuracy;
    double cMinimumVelocity;
    double cMaximumDrop;
    int cMaxIterations;
    double cGravityConstant;
    double cMinimumAltitude;
} ConfigT;

// shotdata
typedef struct {
    double bc;
    DragTableT *dragTable;
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
    AtmosphereT *atmo;
    WindsT *winds;
} ShotDataT;

// tData.h
typedef struct {
    double time;
    double distance;
    double velocity;
    double mach;
    double height;
    double targetDrop;
    double dropAdj;
    double windage;
    double windageAdj;
    double lookDistance;
    double angle;
    double densityFactor;
    double drag;
    double energy;
    double ogw;
    int flag;
} TrajectoryDataT;

typedef struct {
    TrajectoryDataT *ranges;
    size_t length;
    size_t capacity;
} TrajectoryTableT;

// EngineT and related structs simplified to pointers as opaque structs
typedef struct EngineT EngineT;

// Functions
int initEngine(EngineT **engine, ConfigT *config);
int trajectory(EngineT *engine, ShotDataT *shotData, double maxRange, double distStep,
               int extraData, double timeStep, TrajectoryTableT *resultTrajectory);
void freeTrajectoryTable(TrajectoryTableT *trajectoryTable);
void updateStabilityCoefficient(ShotDataT *shotData);
""")

lib = ffi.dlopen("./bcc.so")


def main():
    # --- 1. ConfigT ---
    config = ffi.new("ConfigT *", {
        "cMaxCalcStepSizeFeet": 1.0,
        "cZeroFindingAccuracy": 0.001,
        "cMinimumVelocity": 500.0,
        "cMaximumDrop": -100.0,
        "cMaxIterations": 1000,
        "cGravityConstant": 32.174,
        "cMinimumAltitude": 0.0,
    })

    # --- 2. EngineT ** ---
    engine_ptr = ffi.new("EngineT **")
    status = lib.initEngine(engine_ptr, config)
    if status != 0:
        raise RuntimeError(f"initEngine failed with status {status}")
    engine = engine_ptr[0]
    print("Engine initialized.")

    # --- 3. AtmosphereT ---
    atmo = ffi.new("AtmosphereT *", {
        "t0": 293.15,
        "a0": 1116.4,
        "p0": 1013.25,
        "mach": 1.0,
        "densityFactor": 1.0,
        "cLowestTempC": -70.0,
    })

    # --- 4. DragTableT ---
    drag_points = ffi.new("DragTablePointT[]", [
        {"Mach": 0.0, "CD": 0.5},
        {"Mach": 0.5, "CD": 0.4},
        {"Mach": 0.8, "CD": 0.3},
        {"Mach": 1.0, "CD": 0.6},
        {"Mach": 1.2, "CD": 0.45},
        {"Mach": 2.0, "CD": 0.3},
    ])
    drag_table = ffi.new("DragTableT *", {
        "table": drag_points,
        "length": 6,
    })

    # --- 5. WindsT ---
    winds_data = ffi.new("WindT[]", [
        {"velocity": 10.0, "directionFrom": 90.0 * math.pi / 180.0, "untilDistance": 500.0, "MAX_DISTANCE_FEET": 999999.0},
        {"velocity": 5.0, "directionFrom": 0.0, "untilDistance": 1000.0, "MAX_DISTANCE_FEET": 999999.0},
    ])
    winds = ffi.new("WindsT *", {
        "winds": winds_data,
        "length": 2,
    })

    # --- 6. ShotDataT ---
    shot_data = ffi.new("ShotDataT *", {
        "bc": 0.3,
        "dragTable": drag_table,
        "lookAngle": 0.0,
        "twist": 1.0,
        "length": 2.0,
        "diameter": 0.308,
        "weight": 175.0,
        "barrelElevation": 0.0,
        "barrelAzimuth": 0.0,
        "sightHeight": 1.5,
        "cantCosine": 1.0,
        "cantSine": 0.0,
        "alt0": 0.0,
        "calcStep": 0.01,
        "muzzleVelocity": 2600.0,
        "stabilityCoefficient": 0.0,
        "atmo": atmo,
        "winds": winds,
    })

    # --- 7. Update stability ---
    lib.updateStabilityCoefficient(shot_data)
    print(f"Stability coefficient updated: {shot_data.stabilityCoefficient}")

    # --- 8. Prepare TrajectoryTableT ---
    traj_table = ffi.new("TrajectoryTableT *")
    traj_table.ranges = ffi.NULL
    traj_table.length = 0
    traj_table.capacity = 0

    max_range_feet = 1000.0 * 3.0  # yards to feet
    dist_step_feet = 10.0 * 3.0    # yards to feet
    extra_data = 1
    time_step = 0.01

    # --- 9. Call trajectory ---
    status = lib.trajectory(engine, shot_data, max_range_feet, dist_step_feet, extra_data, time_step, traj_table)
    if status != 0:
        raise RuntimeError(f"trajectory failed with status {status}")

    print(f"Trajectory points count: {traj_table.length}")

    if traj_table.length > 0:
        first = traj_table.ranges[0]
        last = traj_table.ranges[traj_table.length - 1]
        print(f"First point time: {first.time:.4f} distance: {first.distance:.2f} velocity: {first.velocity:.2f}")
        print(f"Last point time: {last.time:.4f} distance: {last.distance:.2f} velocity: {last.velocity:.2f}")

    # --- 10. Free trajectory table ---
    lib.freeTrajectoryTable(traj_table)

if __name__ == "__main__":
    main()
