# cython: freethreading_compatible=True
from libcpp.vector cimport vector
from libc.math cimport NAN
from cython cimport final
from cpython.object cimport PyObject
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_MachList,
    BCLIBC_Curve,
    BCLIBC_Config,
    BCLIBC_Atmosphere,
    BCLIBC_Wind,
    BCLIBC_WindSock,
    BCLIBC_Coriolis,
    BCLIBC_ShotProps,
    BCLIBC_Shot,
)
from py_ballisticcalc.unit import (
    Angular,
    Distance,
    Unit,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTrajData_InterpKey

from py_ballisticcalc.vector import Vector


# @final on cdef functions: unrelated to abi3/Py_TPFLAGS_BASETYPE — marks the function
# as non-overridable in subclasses and allows the compiler to inline the call.
@final
cdef BCLIBC_Config BCLIBC_Config_from_pyobject(object config):
    cdef BCLIBC_Config result = BCLIBC_Config_fromPyObject(<PyObject *>config)
    return result


@final
cdef BCLIBC_Atmosphere BCLIBC_Atmosphere_from_pyobject(object atmo):
    """Build BCLIBC_Atmosphere from a pre-computed Python Atmo object.

    Kept for callers that already hold a Python Atmo instance with pre-computed
    density_ratio and _mach. Prefer BCLIBC_Atmosphere_from_conditions() when
    only raw temperature/pressure/humidity are available.
    """
    cdef BCLIBC_Atmosphere result = BCLIBC_Atmosphere_fromPyObject(<PyObject *>atmo)
    return result


@final
cdef BCLIBC_Atmosphere BCLIBC_Atmosphere_from_conditions(object atmo):
    """Build BCLIBC_Atmosphere from user-facing conditions via bclibc CIPM-2007 factory.

    Delegates density and Mach computation to BCLIBC_Atmosphere::from_conditions(),
    eliminating the round-trip through pre-computed Python Atmo fields.

    Vacuum guard: Atmo.__init__ stores `_p0` via `pressure or cStandardPressure`, so
    Vacuum()._p0 is 1013.25 hPa (not 0) even though density_ratio is correctly 0.
    Passing p_hpa=0 when density_ratio==0 ensures from_conditions() hits its own
    vacuum early-return and returns zero density instead of computing CIPM-2007.
    """
    cdef double p_hpa = 0.0 if atmo.density_ratio == 0.0 else atmo._p0
    return BCLIBC_Atmosphere.from_conditions(
        atmo._t0,
        p_hpa,
        atmo._a0,
        atmo.humidity,
    )


@final
cdef BCLIBC_MachList BCLIBC_MachList_from_pylist(list[object] data):
    cdef BCLIBC_MachList ml = BCLIBC_MachList_fromPylist(<PyObject *>data)
    return ml


@final
cdef BCLIBC_Curve BCLIBC_Curve_from_pylist(list[object] data_points):
    # Call the C++ function. 'except *' handles Python exceptions
    # and 'except +' (assumed in .pxd) handles C++ exceptions (like std::bad_alloc).
    cdef BCLIBC_Curve result = BCLIBC_Curve_fromPylist(<PyObject *>data_points)
    return result


@final
cdef BCLIBC_Coriolis BCLIBC_Coriolis_from_pyobject(object coriolis_obj):
    """Build BCLIBC_Coriolis from a pre-computed Python Coriolis object.

    Kept for callers that already hold a Python Coriolis instance.
    Prefer BCLIBC_Coriolis_from_lat_az() when only raw lat/az are available.
    """
    if coriolis_obj:
        return BCLIBC_Coriolis(
            coriolis_obj.sin_lat,
            coriolis_obj.cos_lat,
            coriolis_obj.sin_az if coriolis_obj.sin_az is not None else 0.0,
            coriolis_obj.cos_az if coriolis_obj.cos_az is not None else 0.0,
            coriolis_obj.range_east if coriolis_obj.range_east is not None else 0.0,
            coriolis_obj.range_north if coriolis_obj.range_north is not None else 0.0,
            coriolis_obj.cross_east if coriolis_obj.cross_east is not None else 0.0,
            coriolis_obj.cross_north if coriolis_obj.cross_north is not None else 0.0,
            coriolis_obj.flat_fire_only,
            coriolis_obj.muzzle_velocity_fps,
        )
    return BCLIBC_Coriolis()


@final
cdef BCLIBC_Coriolis BCLIBC_Coriolis_from_lat_az(
    object latitude, object azimuth, double muzzle_velocity_fps
):
    """Build BCLIBC_Coriolis directly from geographic inputs via bclibc factory.

    Delegates all trig pre-computation to BCLIBC_Coriolis::from_lat_az(),
    eliminating the round-trip through the Python Coriolis domain object.

    None latitude  → no Coriolis effect (all-zero struct, flat_fire_only=1).
    None azimuth   → flat-fire drift only (sin/cos lat computed, azimuth zeroed).
    Both provided  → full 3D Coriolis.
    """
    return BCLIBC_Coriolis.from_lat_az(
        NAN if latitude is None else <double>latitude,
        muzzle_velocity_fps,
        NAN if azimuth is None else <double>azimuth,
    )


# We still need a way to get data from Python objects into BCLIBC_Wind structs.
# This internal helper function is used by WindSockT_create.
# It assumes 'w' is a Python object that conforms to the interface needed.
cdef BCLIBC_WindSock BCLIBC_WindSock_from_pytuple(tuple[object] winds_py_tuple):
    """
    Creates and initializes a BCLIBC_WindSock structure
    by iterating over the Python list and calling push() for each element.

    This function uses the BCLIBC_WindSock constructor and the push() method to add
    elements to the internal std::vector, consistent with the C++ design.
    """
    cdef size_t n = len(winds_py_tuple)
    if n <= 0:
        return BCLIBC_WindSock()

    cdef vector[BCLIBC_Wind] winds_vec
    winds_vec.reserve(n)

    for w in winds_py_tuple:
        winds_vec.emplace_back(
            <double>w.velocity._fps,
            <double>w.direction_from._rad,
            <double>w.until_distance._feet,
            <double>w.MAX_DISTANCE_FEET
        )

    return BCLIBC_WindSock(winds_vec)


cdef BCLIBC_ShotProps BCLIBC_ShotProps_from_pyobject(object shot_info, double calc_step = 1.0):
    """Thin field mapper: copies Python Shot fields into BCLIBC_Shot, then delegates
    all physics/unit conversions to BCLIBC_Shot.to_shot_props() in C++.

    Vectors for drag table and winds are stack-allocated here and stay alive until
    to_shot_props() returns — BCLIBC_Shot holds non-owning pointers to them.
    """
    # Cache Python object intermediates — Cython may omit DECREF for temporaries in
    # chained attribute expressions (e.g. shot_info.ammo.dm.BC), leaking the
    # intermediate objects on exception paths.
    cdef object ammo   = shot_info.ammo
    cdef object dm     = ammo.dm
    cdef object atmo   = shot_info.atmo
    cdef object weapon = shot_info.weapon
    # Shot.winds returns tuple(self._winds) — a new tuple on every access.
    # Cache once so len() and the loop see the same snapshot, and to avoid
    # allocating two tuples per call (important under freethreading where a
    # concurrent _winds mutation between two accesses would make wind_count
    # disagree with winds_vec.size(), causing an OOB read in to_shot_props()).
    cdef object winds_py = shot_info.winds

    cdef object velocity_obj = ammo.get_velocity_for_temp(atmo.powder_temp)
    cdef double muzzle_velocity_fps = velocity_obj._fps

    # Extract drag table into C++ vectors (non-owning pointers passed to BCLIBC_Shot)
    cdef list[object] table_data = dm.drag_table
    cdef size_t n_drag = len(table_data)
    cdef vector[double] mach_vec
    cdef vector[double] cd_vec
    mach_vec.resize(n_drag)
    cd_vec.resize(n_drag)
    cdef size_t i
    for i in range(n_drag):
        mach_vec[i] = table_data[i].Mach
        cd_vec[i] = table_data[i].CD

    # Extract winds into BCLIBC_Wind vector (non-owning pointer passed to BCLIBC_Shot)
    cdef size_t n_winds = len(winds_py)
    cdef vector[BCLIBC_Wind] winds_vec
    winds_vec.reserve(n_winds)
    for w in winds_py:
        winds_vec.emplace_back(
            <double>w.velocity._fps,
            <double>w.direction_from._rad,
            <double>w.until_distance._feet,
            <double>w.MAX_DISTANCE_FEET,
        )

    # Fill BCLIBC_Shot — pure field mapping, no conversion logic here
    cdef BCLIBC_Shot shot
    shot.bc = dm.BC
    shot.weight_grain = dm.weight._grain
    shot.diameter_inch = dm.diameter._inch
    shot.length_inch = dm.length._inch
    shot.muzzle_velocity_fps = muzzle_velocity_fps
    shot.stability_coefficient = 0.0
    shot.mach_data = mach_vec.data()
    shot.cd_data = cd_vec.data()
    shot.drag_table_size = <int>n_drag
    shot.sight_height_ft = weapon.sight_height._feet
    shot.twist_inch = weapon.twist._inch
    shot.temp_c = atmo._t0
    shot.pressure_hpa = atmo._p0
    shot.altitude_ft = atmo._a0
    shot.humidity = atmo.humidity
    shot.winds = winds_vec.data() if n_winds > 0 else <BCLIBC_Wind*>0
    shot.wind_count = <int>n_winds
    shot.look_angle_rad = shot_info.look_angle._rad
    shot.barrel_elevation_rad = shot_info.barrel_elevation._rad
    shot.barrel_azimuth_rad = shot_info.barrel_azimuth._rad
    shot.cant_angle_rad = shot_info.cant_angle._rad
    shot.latitude_deg = NAN if shot_info.latitude is None else <double>shot_info.latitude
    shot.azimuth_deg = NAN if shot_info.azimuth is None else <double>shot_info.azimuth
    shot.calc_step = calc_step

    # All physics conversion happens inside C++
    return shot.to_shot_props()


# Helper functions to create unit objects
cdef object feet_from_c(double val):
    return Distance(val, Unit.Foot)
cdef object rad_from_c(double val):
    return Angular(val, Unit.Radian)


cdef object v3d_to_vector(const BCLIBC_V3dT *v):
    """Convert C BCLIBC_V3dT -> Python Vector"""
    return Vector(v.x, v.y, v.z)


cdef BCLIBC_BaseTrajData_InterpKey _attribute_to_key(str key_attribute):
    cdef BCLIBC_BaseTrajData_InterpKey key_kind

    if key_attribute == 'time':
        key_kind = BCLIBC_BaseTrajData_InterpKey.TIME
    elif key_attribute == 'mach':
        key_kind = BCLIBC_BaseTrajData_InterpKey.MACH
    elif key_attribute == 'position.x':
        key_kind = BCLIBC_BaseTrajData_InterpKey.POS_X
    elif key_attribute == 'position.y':
        key_kind = BCLIBC_BaseTrajData_InterpKey.POS_Y
    elif key_attribute == 'position.z':
        key_kind = BCLIBC_BaseTrajData_InterpKey.POS_Z
    elif key_attribute == 'velocity.x':
        key_kind = BCLIBC_BaseTrajData_InterpKey.VEL_X
    elif key_attribute == 'velocity.y':
        key_kind = BCLIBC_BaseTrajData_InterpKey.VEL_Y
    elif key_attribute == 'velocity.z':
        key_kind = BCLIBC_BaseTrajData_InterpKey.VEL_Z
    else:
        raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

    return key_kind

cdef str _key_to_attribute(BCLIBC_BaseTrajData_InterpKey key_kind):
    cdef str key_attribute

    if key_kind == BCLIBC_BaseTrajData_InterpKey.TIME:
        key_attribute = 'time'
    elif key_kind == BCLIBC_BaseTrajData_InterpKey.MACH:
        key_attribute = 'mach'
    elif key_kind == BCLIBC_BaseTrajData_InterpKey.POS_X:
        key_attribute = 'position.x'
    elif key_kind == BCLIBC_BaseTrajData_InterpKey.POS_Y:
        key_attribute = 'position.y'
    elif key_kind == BCLIBC_BaseTrajData_InterpKey.POS_Z:
        key_attribute = 'position.z'
    elif key_kind == BCLIBC_BaseTrajData_InterpKey.VEL_X:
        key_attribute = 'velocity.x'
    elif key_kind == BCLIBC_BaseTrajData_InterpKey.VEL_Y:
        key_attribute = 'velocity.y'
    elif key_kind == BCLIBC_BaseTrajData_InterpKey.VEL_Z:
        key_attribute = 'velocity.z'
    else:
        raise ValueError(f"Unknown BCLIBC_BaseTrajData_InterpKey value: {key_kind}")

    return key_attribute
