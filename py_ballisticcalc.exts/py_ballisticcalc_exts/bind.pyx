# cython: freethreading_compatible=True
# noinspection PyUnresolvedReferences
from libc.stdlib cimport calloc, free
# noinspection PyUnresolvedReferences
from libc.string cimport memset
# noinspection PyUnresolvedReferences
from cpython.exc cimport PyErr_Occurred
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_MachList,
    BCLIBC_Curve,
    BCLIBC_Config,
    BCLIBC_Wind,
    BCLIBC_WindSock,
    BCLIBC_Coriolis,
    BCLIBC_WindSock_init,
    BCLIBC_BaseTrajSeq_InterpKey,
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc.unit import (
    Angular,
    Distance,
    Unit,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT

from py_ballisticcalc.vector import Vector


@final
cdef BCLIBC_Config BCLIBC_Config_from_pyobject(object config):
    cdef BCLIBC_Config result = BCLIBC_Config_fromPyObject(<PyObject *>config)
    if PyErr_Occurred():
        raise
    return result


@final
cdef BCLIBC_MachList BCLIBC_MachList_from_pylist(list[object] data):
    cdef BCLIBC_MachList ml = BCLIBC_MachList_fromPylist(<PyObject *>data)
    if ml.array is NULL:
        if PyErr_Occurred():
            raise
        else:
            raise MemoryError("Failed to create BCLIBC_MachList from Python list")
    return ml


@final
cdef BCLIBC_Curve BCLIBC_Curve_from_pylist(list[object] data_points):
    cdef BCLIBC_Curve result = BCLIBC_Curve_fromPylist(<PyObject *>data_points)
    if PyErr_Occurred():
        raise
    return result


# We still need a way to get data from Python objects into BCLIBC_Wind structs.
# This internal helper function is used by WindSockT_create.
# It assumes 'w' is a Python object that conforms to the interface needed.
@final
cdef BCLIBC_Wind BCLIBC_Wind_from_py(object w):
    cdef BCLIBC_Wind wind = {}
    memset(&wind, 0, sizeof(wind))  # CRITICAL: use memset to ensure initialized with zeros
    wind = BCLIBC_Wind_fromPyObject(<PyObject *>w)
    if PyErr_Occurred():
        raise
    return wind


cdef BCLIBC_Coriolis BCLIBC_Coriolis_from_pyobject(object coriolis_obj):
    cdef BCLIBC_Coriolis coriolis = {}  # << CRITICAL! should be defined
    memset(&coriolis, 0, sizeof(coriolis))  # CRITICAL: use memset to ensure initialized with zeros
    
    if coriolis_obj:
        coriolis.sin_lat = coriolis_obj.sin_lat
        coriolis.cos_lat = coriolis_obj.cos_lat
        coriolis.flat_fire_only = <int>coriolis_obj.flat_fire_only
        coriolis.muzzle_velocity_fps = coriolis_obj.muzzle_velocity_fps

        coriolis.sin_az = coriolis_obj.sin_az if coriolis_obj.sin_az is not None else 0.0
        coriolis.cos_az = coriolis_obj.cos_az if coriolis_obj.cos_az is not None else 0.0
        coriolis.range_east = coriolis_obj.range_east if coriolis_obj.range_east is not None else 0.0
        coriolis.range_north = coriolis_obj.range_north if coriolis_obj.range_north is not None else 0.0
        coriolis.cross_east = coriolis_obj.cross_east if coriolis_obj.cross_east is not None else 0.0
        coriolis.cross_north = coriolis_obj.cross_north if coriolis_obj.cross_north is not None else 0.0
    return coriolis


cdef BCLIBC_WindSock BCLIBC_WindSock_from_pylist(object winds_py_list):
    """
    Creates and initializes a BCLIBC_WindSock structure.
    Processes the Python list, then delegates initialization to C.
    """
    cdef size_t length = <size_t> len(winds_py_list)
    cdef BCLIBC_WindSock ws = {}
    memset(&ws, 0, sizeof(ws))  # CRITICAL: use memset to ensure initialized with zeros
    # Memory allocation for the BCLIBC_Wind array (remains in Cython)
    cdef BCLIBC_Wind * winds_array = <BCLIBC_Wind *> calloc(<size_t> length, sizeof(BCLIBC_Wind))
    if <void *> winds_array is NULL:
        raise MemoryError("Failed to allocate internal BCLIBC_Wind array.")

    # Copying data from Python objects to C structures (must remain in Cython)
    cdef int i
    try:
        for i in range(<int>length):
            # BCLIBC_Wind_from_py interacts with a Python object, so it remains here
            winds_array[i] = BCLIBC_Wind_from_py(winds_py_list[i])
    except Exception:
        # Error handling
        free(<void *> winds_array)
        raise RuntimeError("Invalid wind entry in winds list")

    # 4. Structure initialization (calling the C function)
    BCLIBC_WindSock_init(&ws, length, winds_array)

    return ws


# Helper functions to create unit objects
cdef object feet_from_c(double val):
    return Distance(val, Unit.Foot)
cdef object rad_from_c(double val):
    return Angular(val, Unit.Radian)


cdef object v3d_to_vector(const BCLIBC_V3dT *v):
    """Convert C BCLIBC_V3dT -> Python Vector"""
    return Vector(v.x, v.y, v.z)


cdef BCLIBC_BaseTrajSeq_InterpKey _attribute_to_key(str key_attribute):
    cdef BCLIBC_BaseTrajSeq_InterpKey key_kind

    if key_attribute == 'time':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_TIME
    elif key_attribute == 'mach':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_MACH
    elif key_attribute == 'position.x':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X
    elif key_attribute == 'position.y':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Y
    elif key_attribute == 'position.z':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Z
    elif key_attribute == 'velocity.x':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_X
    elif key_attribute == 'velocity.y':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y
    elif key_attribute == 'velocity.z':
        key_kind = BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Z
    else:
        raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

    return key_kind

cdef str _key_to_attribute(BCLIBC_BaseTrajSeq_InterpKey key_kind):
    cdef str key_attribute

    if key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_TIME:
        key_attribute = 'time'
    elif key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_MACH:
        key_attribute = 'mach'
    elif key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_POS_X:
        key_attribute = 'position.x'
    elif key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Y:
        key_attribute = 'position.y'
    elif key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_POS_Z:
        key_attribute = 'position.z'
    elif key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_X:
        key_attribute = 'velocity.x'
    elif key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Y:
        key_attribute = 'velocity.y'
    elif key_kind == BCLIBC_BaseTrajSeq_InterpKey.BCLIBC_BASE_TRAJ_INTERP_KEY_VEL_Z:
        key_attribute = 'velocity.z'
    else:
        raise ValueError(f"Unknown BCLIBC_BaseTrajSeq_InterpKey value: {key_kind}")

    return key_attribute
