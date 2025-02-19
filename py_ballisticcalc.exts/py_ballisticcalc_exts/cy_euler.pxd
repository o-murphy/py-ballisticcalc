from py_ballisticcalc_exts.vector cimport CVector

cdef struct Config_t:
    double max_calc_step_size_feet
    double chart_resolution
    double cZeroFindingAccuracy
    double cMinimumVelocity
    double cMaximumDrop
    int cMaxIterations
    double cGravityConstant
    double cMinimumAltitude

cdef Config_t config_bind(object config)

cdef struct CurvePoint_t:
    double a, b, c

cdef struct Curve_t:
    CurvePoint_t * points
    double length

cdef struct MachList_t:
    double * array
    double length

cdef struct Atmosphere_t:
    double _t0
    double _a0
    double _p0
    double _mach
    double density_ratio
    double cLowestTempC

cdef void update_density_factor_and_mach_for_altitude(
        Atmosphere_t * atmo, double altitude, double * density_ratio, double * mach
)

cdef struct ShotData_t:
    double bc
    Curve_t curve
    MachList_t mach_list
    double look_angle
    double twist
    double length
    double diameter
    double weight
    double barrel_elevation
    double barrel_azimuth
    double sight_height
    double cant_cosine
    double cant_sine
    double alt0
    double calc_step
    double muzzle_velocity
    double stability_coefficient
    Atmosphere_t atmo

cdef double cy_get_calc_step(Config_t * config, double step = ?)
cdef MachList_t cy_table_to_mach(list[object] data)
cdef Curve_t cy_calculate_curve(list[object] data_points)
cdef double cy_calculate_by_curve_and_mach_list(MachList_t *mach_list, Curve_t *curve, double mach)
cdef double cy_spin_drift(ShotData_t * t, double time)
cdef double cy_drag_by_mach(ShotData_t * t, double mach)
cdef void cy_update_stability_coefficient(ShotData_t * t)

cdef double cy_get_correction(double distance, double offset)
cdef double cy_calculate_energy(double bullet_weight, double velocity)
cdef double cy_calculate_ogw(double bullet_weight, double velocity)

cdef void free_curve(Curve_t *curve)
cdef void free_mach_list(MachList_t *mach_list)
cdef void free_trajectory(ShotData_t *t)

cdef double cDegreesFtoR
cdef double cSpeedOfSoundImperial
cdef double cLapseRateImperial

cdef struct Wind_t:
    double velocity
    double direction_from
    double until_distance
    double MAX_DISTANCE_FEET

cdef CVector wind_to_c_vector(Wind_t * w)