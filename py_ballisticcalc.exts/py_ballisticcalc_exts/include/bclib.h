#ifndef BCLIB_TYPES_H
#define BCLIB_TYPES_H

#include "v3d.h"
#include "log.h"
#include <stddef.h>

extern const double cDegreesFtoR;
extern const double cDegreesCtoK;
extern const double cSpeedOfSoundImperial;
extern const double cSpeedOfSoundMetric;
extern const double cLapseRateKperFoot;
extern const double cLapseRateImperial;
extern const double cPressureExponent;
extern const double cLowestTempF;
extern const double mToFeet;

extern const double cMaxWindDistanceFeet;
extern const double cEarthAngularVelocityRadS;

typedef enum
{
    // General error flags (bitmask)
    NO_ERROR = 0x0000,            // (0)
    ZERO_DIVISION_ERROR = 0x0001, // (1 << 0)
    VALUE_ERROR = 0x0002,         // (1 << 1)
    KEY_ERROR = 0x0004,           // (1 << 2)
    INDEX_ERROR = 0x0008,         // (1 << 3)
    MEMORY_ERROR = 0x0010,        // (1 << 4)
    ARITHMETIC_ERROR = 0x0020,    // (1 << 5)
    INPUT_ERROR = 0x0040,         // (1 << 6)
    RUNTIME_ERROR = 0x0080,       // (1 << 7)

    // Sequence (BaseTrajSeq_t) specific flags
    SEQUENCE_ERROR = 0x0100,                                     // (1 << 8)
    SEQUENCE_INPUT_ERROR = SEQUENCE_ERROR | INPUT_ERROR,           // 0x0100 | 0x0040 = 0x0140  -> (1 << 8) | (1 << 6)
    SEQUENCE_VALUE_ERROR = SEQUENCE_ERROR | VALUE_ERROR,           // 0x0100 | 0x0002 = 0x0102  -> (1 << 8) | (1 << 1)
    SEQUENCE_KEY_ERROR = SEQUENCE_ERROR | KEY_ERROR,               // 0x0100 | 0x0004 = 0x0104  -> (1 << 8) | (1 << 2)
    SEQUENCE_MEMORY_ERROR = SEQUENCE_ERROR | MEMORY_ERROR,         // 0x0100 | 0x0010 = 0x0110  -> (1 << 8) | (1 << 4)
    SEQUENCE_INDEX_ERROR = SEQUENCE_ERROR | INDEX_ERROR,           // 0x0100 | 0x0008 = 0x0108  -> (1 << 8) | (1 << 3)
    SEQUENCE_ARITHMETIC_ERROR = SEQUENCE_ERROR | ARITHMETIC_ERROR, // 0x0100 | 0x0020 = 0x0120  -> (1 << 8) | (1 << 5)

    // Interpolation specific flag
    INTERPOLATION_ERROR = 0x0200, // (1 << 9)

    // Solver specific flags (always include RANGE_ERROR)
    RANGE_ERROR = 0x0400,                             // 0x0400 -> (1 << 10)
    RANGE_ERROR_MINIMUM_VELOCITY_REACHED = RANGE_ERROR | 0x0800, // 0x0400 | 0x0800 = 0x0C00 -> (1 << 10) | (1 << 11)
    RANGE_ERROR_MAXIMUM_DROP_REACHED = RANGE_ERROR | 0x1000,     // 0x0400 | 0x1000 = 0x1400 -> (1 << 10) | (1 << 12)
    RANGE_ERROR_MINIMUM_ALTITUDE_REACHED = RANGE_ERROR | 0x2000, // 0x0400 | 0x2000 = 0x2400 -> (1 << 10) | (1 << 13)

    // Zero init specific flags
    OUT_OF_RANGE_ERROR = 0x4000,            // (1 << 14)
    ZERO_INIT_CONTINUE = NO_ERROR | 0x8000, // 0x8000 -> (1 << 15)
    ZERO_INIT_DONE = NO_ERROR | 0x10000,    // 0x10000 -> (1 << 16)

    // Zero finding error flag
    ZERO_FINDING_ERROR = 0x20000, // (1 << 17)

    // Undefined
    UNDEFINED_ERROR = 0x40000 // (1 << 18)
} ErrorCode;

typedef struct
{
    double cStepMultiplier;
    double cZeroFindingAccuracy;
    double cMinimumVelocity;
    double cMaximumDrop;
    int cMaxIterations;
    double cGravityConstant;
    double cMinimumAltitude;
} Config_t;

typedef struct
{
    double a;
    double b;
    double c;
    double d; // PCHIP cubic constant term for segment (y at left knot)
} CurvePoint_t;

typedef struct
{
    CurvePoint_t *points;
    size_t length;
} Curve_t;

typedef struct
{
    double *array;
    size_t length;
} MachList_t;

typedef struct
{
    double _t0;
    double _a0;
    double _p0;
    double _mach;
    double density_ratio;
    double cLowestTempC;
} Atmosphere_t;

typedef struct
{
    double sin_lat;
    double cos_lat;
    double sin_az;
    double cos_az;
    double range_east;
    double range_north;
    double cross_east;
    double cross_north;
    int flat_fire_only;
    double muzzle_velocity_fps;
} Coriolis_t;

typedef struct
{
    double velocity;
    double direction_from;
    double until_distance;
    double MAX_DISTANCE_FEET;
} Wind_t;

typedef enum
{
    TFLAG_NONE = 0,
    TFLAG_ZERO_UP = 1,
    TFLAG_ZERO_DOWN = 2,
    TFLAG_ZERO = TFLAG_ZERO_UP | TFLAG_ZERO_DOWN,
    TFLAG_MACH = 4,
    TFLAG_RANGE = 8,
    TFLAG_APEX = 16,
    TFLAG_ALL = TFLAG_RANGE | TFLAG_ZERO_UP | TFLAG_ZERO_DOWN | TFLAG_MACH | TFLAG_APEX,
    TFLAG_MRT = 32
} TrajFlag_t;

typedef struct
{
    double time;
    V3dT position;
    V3dT velocity;
    double mach;
} BaseTrajData_t;

typedef struct
{
    Wind_t *winds;
    int current;
    int length;
    double next_range;
    V3dT last_vector_cache;
} WindSock_t;

typedef struct
{
    double bc;
    double look_angle;
    double twist;
    double length;
    double diameter;
    double weight;
    double barrel_elevation;
    double barrel_azimuth;
    double sight_height;
    double cant_cosine;
    double cant_sine;
    double alt0;
    double calc_step;
    double muzzle_velocity;
    double stability_coefficient;
    Curve_t curve;
    MachList_t mach_list;
    Atmosphere_t atmo;
    Coriolis_t coriolis;
    WindSock_t wind_sock;
    TrajFlag_t filter_flags;
} ShotProps_t;

/**
 * Keys used to look up specific values within a BaseTraj_t struct.
 */
typedef enum
{
    KEY_TIME,
    KEY_MACH,
    KEY_POS_X,
    KEY_POS_Y,
    KEY_POS_Z,
    KEY_VEL_X,
    KEY_VEL_Y,
    KEY_VEL_Z
} InterpKey;

#ifdef __cplusplus
extern "C"
{
#endif
    void setLogLevel(LogLevel level);
    void initLogLevel();

    void Curve_t_release(Curve_t *curve_ptr);

    // MachList_t MachList_fromArray(const double *values, size_t length);
    void MachList_t_release(MachList_t *mach_list_ptr);

    void Atmosphere_t_updateDensityFactorAndMachForAltitude(
        const Atmosphere_t *atmo_ptr,
        double altitude,
        double *density_ratio_ptr,
        double *mach_ptr);

    void ShotProps_t_release(ShotProps_t *shot_props_ptr);
    double ShotProps_t_spinDrift(const ShotProps_t *shot_props_ptr, double time);
    ErrorCode ShotProps_t_updateStabilityCoefficient(ShotProps_t *shot_props_ptr);
    double ShotProps_t_dragByMach(const ShotProps_t *shot_props_ptr, double mach);

    double calculateByCurveAndMachList(const MachList_t *mach_list_ptr,
                                       const Curve_t *curve_ptr,
                                       double mach);

    V3dT Wind_t_to_V3dT(const Wind_t *wind_ptr);

    ErrorCode WindSock_t_init(WindSock_t *ws, size_t length, Wind_t *winds);
    void WindSock_t_release(WindSock_t *ws);
    V3dT WindSock_t_currentVector(const WindSock_t *wind_sock);
    ErrorCode WindSock_t_updateCache(WindSock_t *ws);
    V3dT WindSock_t_vectorForRange(WindSock_t *ws, double next_range_param);

    // helpers
    double getCorrection(double distance, double offset);
    double calculateEnergy(double bulletWeight, double velocity);
    double calculateOgw(double bulletWeight, double velocity);

    void Coriolis_t_coriolis_acceleration_local(
        const Coriolis_t *coriolis_ptr,
        const V3dT *velocity_ptr,
        V3dT *accel_ptr);

    ErrorCode BaseTrajData_t_interpolate(
        InterpKey key_kind,
        double key_value,
        const BaseTrajData_t *p0,
        const BaseTrajData_t *p1,
        const BaseTrajData_t *p2,
        BaseTrajData_t *out);

#ifdef __cplusplus
}
#endif

#endif // BCLIB_TYPES_H
