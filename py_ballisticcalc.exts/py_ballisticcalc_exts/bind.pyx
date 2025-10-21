# cython: freethreading_compatible=True
# noinspection PyUnresolvedReferences
from libc.stdlib cimport calloc, free
# noinspection PyUnresolvedReferences
from cpython.exc cimport PyErr_Occurred
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    MachList_t,
    Curve_t,
    Config_t,
    Wind_t,
    WindSock_t,
    Coriolis_t,
    WindSock_t_init,
    InterpKey,
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc.unit import (
    Angular,
    Distance,
    Unit,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT

from py_ballisticcalc.vector import Vector


@final
cdef Config_t Config_t_from_pyobject(object config):
    cdef Config_t result = Config_t_fromPyObject(<PyObject *>config)
    if PyErr_Occurred():
        raise
    return result


@final
cdef MachList_t MachList_t_from_pylist(list[object] data):
    cdef MachList_t ml = MachList_t_fromPylist(<PyObject *>data)
    if ml.array is NULL:
        if PyErr_Occurred():
            raise
        else:
            raise MemoryError("Failed to create MachList_t from Python list")
    return ml


@final
cdef Curve_t Curve_t_from_pylist(list[object] data_points):
    cdef Curve_t result = Curve_t_fromPylist(<PyObject *>data_points)
    if PyErr_Occurred():
        raise
    return result


# We still need a way to get data from Python objects into Wind_t structs.
# This internal helper function is used by WindSockT_create.
# It assumes 'w' is a Python object that conforms to the interface needed.
@final
cdef Wind_t Wind_t_from_py(object w):
    cdef Wind_t result
    result = Wind_t_fromPyObject(<PyObject *>w)
    if PyErr_Occurred():
        raise
    return result


cdef Coriolis_t Coriolis_t_from_pyobject(object coriolis_obj):
    cdef Coriolis_t coriolis

    if coriolis_obj:
        coriolis.sin_lat = coriolis_obj.sin_lat
        coriolis.cos_lat = coriolis_obj.cos_lat
        coriolis.flat_fire_only = coriolis_obj.flat_fire_only
        coriolis.muzzle_velocity_fps = coriolis_obj.muzzle_velocity_fps

        coriolis.sin_az = coriolis_obj.sin_az if coriolis_obj.sin_az is not None else 0.0
        coriolis.cos_az = coriolis_obj.cos_az if coriolis_obj.cos_az is not None else 0.0
        coriolis.range_east = coriolis_obj.range_east if coriolis_obj.range_east is not None else 0.0
        coriolis.range_north = coriolis_obj.range_north if coriolis_obj.range_north is not None else 0.0
        coriolis.cross_east = coriolis_obj.cross_east if coriolis_obj.cross_east is not None else 0.0
        coriolis.cross_north = coriolis_obj.cross_north if coriolis_obj.cross_north is not None else 0.0

    return coriolis


cdef WindSock_t WindSock_t_from_pylist(object winds_py_list):
    """
    Creates and initializes a WindSock_t structure.
    Processes the Python list, then delegates initialization to C.
    """
    cdef size_t length = <size_t> len(winds_py_list)
    cdef WindSock_t ws
    # Memory allocation for the Wind_t array (remains in Cython)
    cdef Wind_t * winds_array = <Wind_t *> calloc(<size_t> length, sizeof(Wind_t))
    if <void *> winds_array is NULL:
        raise MemoryError("Failed to allocate internal Wind_t array.")

    # Copying data from Python objects to C structures (must remain in Cython)
    cdef int i
    try:
        for i in range(<int>length):
            # Wind_t_from_py interacts with a Python object, so it remains here
            winds_array[i] = Wind_t_from_py(winds_py_list[i])
    except Exception:
        # Error handling
        free(<void *> winds_array)
        raise RuntimeError("Invalid wind entry in winds list")

    # 4. Structure initialization (calling the C function)
    WindSock_t_init(&ws, length, winds_array)

    return ws


# Helper functions to create unit objects
cdef object _new_feet(double val):
    return Distance(val, Unit.Foot)
cdef object _new_rad(double val):
    return Angular(val, Unit.Radian)


cdef object _v3d_to_vector(const V3dT *v):
    """Convert C V3dT -> Python Vector"""
    return Vector(v.x, v.y, v.z)


cdef InterpKey _attribute_to_key(str key_attribute):
    cdef InterpKey key_kind

    if key_attribute == 'time':
        key_kind = InterpKey.KEY_TIME
    elif key_attribute == 'mach':
        key_kind = InterpKey.KEY_MACH
    elif key_attribute == 'position.x':
        key_kind = InterpKey.KEY_POS_X
    elif key_attribute == 'position.y':
        key_kind = InterpKey.KEY_POS_Y
    elif key_attribute == 'position.z':
        key_kind = InterpKey.KEY_POS_Z
    elif key_attribute == 'velocity.x':
        key_kind = InterpKey.KEY_VEL_X
    elif key_attribute == 'velocity.y':
        key_kind = InterpKey.KEY_VEL_Y
    elif key_attribute == 'velocity.z':
        key_kind = InterpKey.KEY_VEL_Z
    else:
        raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

    return key_kind

cdef str _key_to_attribute(InterpKey key_kind):
    cdef str key_attribute

    if key_kind == InterpKey.KEY_TIME:
        key_attribute = 'time'
    elif key_kind == InterpKey.KEY_MACH:
        key_attribute = 'mach'
    elif key_kind == InterpKey.KEY_POS_X:
        key_attribute = 'position.x'
    elif key_kind == InterpKey.KEY_POS_Y:
        key_attribute = 'position.y'
    elif key_kind == InterpKey.KEY_POS_Z:
        key_attribute = 'position.z'
    elif key_kind == InterpKey.KEY_VEL_X:
        key_attribute = 'velocity.x'
    elif key_kind == InterpKey.KEY_VEL_Y:
        key_attribute = 'velocity.y'
    elif key_kind == InterpKey.KEY_VEL_Z:
        key_attribute = 'velocity.z'
    else:
        raise ValueError(f"Unknown InterpKey value: {key_kind}")

    return key_attribute
