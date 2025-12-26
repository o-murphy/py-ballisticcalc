# cython: freethreading_compatible=True
from libcpp.cmath cimport sin, cos
from libcpp.vector cimport vector
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
    BCLIBC_TrajFlag,
)
from py_ballisticcalc.unit import (
    Angular,
    Distance,
    Unit,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTrajData_InterpKey

from py_ballisticcalc.vector import Vector
from py_ballisticcalc.conditions import Coriolis


@final
cdef BCLIBC_Config BCLIBC_Config_from_pyobject(object config):
    cdef BCLIBC_Config result = BCLIBC_Config_fromPyObject(<PyObject *>config)
    return result


@final
cdef BCLIBC_Atmosphere BCLIBC_Atmosphere_from_pyobject(object atmo):
    cdef BCLIBC_Atmosphere result = BCLIBC_Atmosphere_fromPyObject(<PyObject *>atmo)
    return result


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
    # WARNING: Avoid calling Python attributes in a chain!
    # Cython may forget to add DECREF, so memory leaks are possible
    cdef object velocity_obj = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp)
    cdef double muzzle_velocity_fps = velocity_obj._fps

    # Create coriolis object from shot parameters
    cdef object coriolis_obj = Coriolis.create(
        shot_info.latitude,
        shot_info.azimuth,
        muzzle_velocity_fps
    )

    cdef list[object] table_data = shot_info.ammo.dm.drag_table

    return BCLIBC_ShotProps(
        shot_info.ammo.dm.BC,
        shot_info.look_angle._rad,
        shot_info.weapon.twist._inch,
        shot_info.ammo.dm.length._inch,
        shot_info.ammo.dm.diameter._inch,
        shot_info.ammo.dm.weight._grain,
        shot_info.barrel_elevation._rad,
        shot_info.barrel_azimuth._rad,
        shot_info.weapon.sight_height._feet,
        cos(<double>shot_info.cant_angle._rad),
        sin(<double>shot_info.cant_angle._rad),
        shot_info.atmo.altitude._feet,
        calc_step,
        muzzle_velocity_fps,
        0.0,
        BCLIBC_Curve_from_pylist(table_data),
        BCLIBC_MachList_from_pylist(table_data),
        BCLIBC_Atmosphere_from_pyobject(shot_info.atmo),
        BCLIBC_Coriolis_from_pyobject(coriolis_obj),
        BCLIBC_WindSock_from_pytuple(shot_info.winds),
        <BCLIBC_TrajFlag>BCLIBC_TrajFlag.BCLIBC_TRAJ_FLAG_NONE,
    )


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
