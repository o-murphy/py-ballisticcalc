from libc.stdlib cimport malloc, free
from libc.math cimport tan
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_TrajFlag,
    ShotProps_t,
    BCLIBC_BaseTrajData,
    Atmosphere_t_updateDensityFactorAndMachForAltitude
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT, mag
from py_ballisticcalc_exts.bisect_left cimport bisect_left_generic

DEF EPSILON = 1e6


cdef struct TDF:
    # TDF struct definition ...
    ShotProps_t props
    BCLIBC_TrajFlag filter_flags
    BCLIBC_TrajFlag current_flag
    BCLIBC_TrajFlag seen_zero
    double time_of_last_record
    double time_step
    double range_step
    double range_limit
    BCLIBC_BaseTrajData data[2]
    double next_record_distance
    double look_angle_rad
    double look_angle_tangent


cdef TDF *TDF_create():
    # 1. Re-introduce malloc to allocate memory and get a pointer f
    cdef TDF *f = <TDF*>malloc(sizeof(TDF))
    return f


cdef TDF *TDF_init( # Function returns a pointer (TDF*)
    TDF *f,
    ShotProps_t props,
    BCLIBC_TrajFlag filter_flags,
    BCLIBC_V3dT initial_position,
    BCLIBC_V3dT initial_velocity,
    double barrel_angle_rad,
    double look_angle_rad = 0.0,
    double range_limit = 0.0,
    double range_step = 0.0,
    double time_step = 0.0,
):
    if f is NULL:
        f = TDF_create()

    # 2. Assign to the dereferenced pointer f
    f.props = props
    f.filter_flags = filter_flags
    f.seen_zero = BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_NONE
    f.time_step = time_step
    f.range_step = range_step
    f.range_limit = range_limit
    f.time_of_last_record = 0.0
    f.next_record_distance = 0.0
    f.look_angle_rad = look_angle_rad
    f.look_angle_tangent = tan(look_angle_rad)

    cdef double mach = 0.0
    cdef double density_ratio = 0.0

    if f.filter_flags & BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_MACH:
        Atmosphere_t_updateDensityFactorAndMachForAltitude(
            &f.props.atmo,
            initial_position.y,
            &density_ratio,
            &mach,
        )
        if BCLIBC_V3dBCLIBC_E_mag(&initial_velocity) < mach:
            # Cast still required: f.filter_flags &= <BCLIBC_TrajFlag>(~BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_MACH)
            f.filter_flags = <BCLIBC_TrajFlag>(f.filter_flags & ~BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_MACH)

    if f.filter_flags & BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_ZERO:
        if initial_position.y >= 0:
            # Cast still required
            f.filter_flags = <BCLIBC_TrajFlag>(f.filter_flags & ~BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_ZERO_UP)
        elif initial_position.y < 0 and barrel_angle_rad <= f.look_angle_rad:
            # Cast still required
            f.filter_flags = <BCLIBC_TrajFlag>(f.filter_flags & ~(BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_ZERO | BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_MRT))

    # 3. Return the pointer
    return f


cdef void TDF_free(TDF *f):
    if f is not NULL:
        free(f)
        f = NULL


cdef struct BaseTrajRow_t:
    BCLIBC_BaseTrajData data
    BCLIBC_TrajFlag flag

cdef int compare_records(const void *target, const void *element) noexcept nogil:
    cdef double target_val = (<const double *>target)[0]
    cdef double el_val = (<const BaseTrajRow_t*>element).data.time

    if el_val < target_val:
        return 1
    return 0

cdef size_t bisect_left_records_by_time(const BaseTrajRow_t *records, size_t num_records, const double *time) noexcept nogil:
    return bisect_left_generic(
        records,
        time,
        sizeof(BaseTrajRow_t),
        0,
        num_records,
        &compare_records
    )

cdef class TDFWrapper:
    cdef:
        TDF *_f
        list[object] records

    def __cinit__(self):
        self._f = TDF_create()
        if self._f is NULL:
            raise MemoryError("Can't allocate memory for TDF")

    def __dealloc__(self):
        TDF_free(self._f)

    cdef init(self,
        ShotProps_t props,
        BCLIBC_TrajFlag filter_flags,
        BCLIBC_V3dT initial_position,
        BCLIBC_V3dT initial_velocity,
        double barrel_angle_rad,
        double look_angle_rad = 0.0,
        double range_limit = 0.0,
        double range_step = 0.0,
        double time_step = 0.0,
    ):
        self._f = TDF_init(
            self._f,
            props, filter_flags,
            initial_position, initial_velocity,
            barrel_angle_rad,
            range_limit, range_step, time_step
        )
        if self._f is NULL:
            raise MemoryError("Can't allocate memory for TDF")
