# cython: freethreading_compatible=True
from libc.stdlib cimport calloc, free
from libc.string cimport memset
from cpython.exc cimport PyErr_Occurred
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
    BCLIBC_ErrorType,
)
from py_ballisticcalc.unit import (
    Angular,
    Distance,
    Unit,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTraj_InterpKey

from py_ballisticcalc.vector import Vector


@final
cdef BCLIBC_Config BCLIBC_Config_from_pyobject(object config):
    cdef BCLIBC_Config result = BCLIBC_Config_fromPyObject(<PyObject *>config)
    if PyErr_Occurred():
        raise
    return result


@final
cdef BCLIBC_Atmosphere BCLIBC_Atmosphere_from_pyobject(object atmo):
    cdef BCLIBC_Atmosphere result = BCLIBC_Atmosphere_fromPyObject(<PyObject *>atmo)
    if PyErr_Occurred():
        raise
    return result


@final
cdef BCLIBC_MachList BCLIBC_MachList_from_pylist(list[object] data) except+:
    cdef BCLIBC_MachList ml = BCLIBC_MachList_fromPylist(<PyObject *>data)
    if ml.empty():
        if PyErr_Occurred():
            raise
        else:
            pass
    return ml


@final
cdef BCLIBC_Curve BCLIBC_Curve_from_pylist(list[object] data_points) except+:
    # Call the C++ function. 'except *' handles Python exceptions 
    # and 'except +' (assumed in .pxd) handles C++ exceptions (like std::bad_alloc).
    cdef BCLIBC_Curve result = BCLIBC_Curve_fromPylist(<PyObject *>data_points)
    
    # Check if a Python exception was set during processing
    if PyErr_Occurred():
        # If an error was set (e.g., AttributeError, ValueError, IndexError), propagate it
        raise
        
    # Check for empty result after successful execution (e.g., input list size < 2)
    # The C++ function now sets a ValueError if n < 2, so this check is mostly for 
    # completeness or if the user passed an empty list.
    if result.empty():
        pass # If PyErr_Occurred() was false, and it's empty, it means the input was handled gracefully.
        
    return result


# We still need a way to get data from Python objects into BCLIBC_Wind structs.
# This internal helper function is used by WindSockT_create.
# It assumes 'w' is a Python object that conforms to the interface needed.
@final
cdef BCLIBC_Wind BCLIBC_Wind_from_pyobject(object w):
    cdef BCLIBC_Wind wind = BCLIBC_Wind_fromPyObject(<PyObject *>w)
    if PyErr_Occurred():
        raise
    return wind


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


cdef BCLIBC_WindSock BCLIBC_WindSock_from_pylist(object winds_py_list) except+:
    """
    Creates and initializes a BCLIBC_WindSock structure 
    by iterating over the Python list and calling push() for each element.
    
    This function uses the BCLIBC_WindSock constructor and the push() method to add 
    elements to the internal std::vector, consistent with the C++ design.
    """
    cdef size_t length = <size_t> len(winds_py_list)
    
    # 1. Creating the C++ BCLIBC_WindSock object (constructor is called, handled by except+)
    cdef BCLIBC_WindSock ws = BCLIBC_WindSock()
    
    # 2. Copying data from Python objects
    cdef size_t i 
    cdef BCLIBC_Wind c_wind_segment # Temporary variable for storing the converted object
    
    try:
        for i in range(length): 
            # BCLIBC_Wind_from_pyobject converts the Python object to a C structure
            # This call can raise Python exceptions
            c_wind_segment = BCLIBC_Wind_from_pyobject(winds_py_list[i])
            
            # Add the segment to the internal C++ vector via the push method (handled by outer except+)
            ws.push(c_wind_segment) 
            
    except Exception:
        # Error handling for Python-level errors (like attribute/type conversion failure)
        raise RuntimeError("Invalid wind entry in winds list during conversion")

    # 3. Update the cache for the first (zero) wind element after filling the vector
    cdef BCLIBC_ErrorType error_code = ws.update_cache()
    if error_code != BCLIBC_ErrorType.BCLIBC_E_NO_ERROR:
        # This is a BCLIBC error, not a C++ exception, so no except+ is needed here.
        raise RuntimeError("BCLIBC_WindSock initialization error during final cache update.")

    return ws


# Helper functions to create unit objects
cdef object feet_from_c(double val):
    return Distance(val, Unit.Foot)
cdef object rad_from_c(double val):
    return Angular(val, Unit.Radian)


cdef object v3d_to_vector(const BCLIBC_V3dT *v):
    """Convert C BCLIBC_V3dT -> Python Vector"""
    return Vector(v.x, v.y, v.z)


cdef BCLIBC_BaseTraj_InterpKey _attribute_to_key(str key_attribute):
    cdef BCLIBC_BaseTraj_InterpKey key_kind

    if key_attribute == 'time':
        key_kind = BCLIBC_BaseTraj_InterpKey.TIME
    elif key_attribute == 'mach':
        key_kind = BCLIBC_BaseTraj_InterpKey.MACH
    elif key_attribute == 'position.x':
        key_kind = BCLIBC_BaseTraj_InterpKey.POS_X
    elif key_attribute == 'position.y':
        key_kind = BCLIBC_BaseTraj_InterpKey.POS_Y
    elif key_attribute == 'position.z':
        key_kind = BCLIBC_BaseTraj_InterpKey.POS_Z
    elif key_attribute == 'velocity.x':
        key_kind = BCLIBC_BaseTraj_InterpKey.VEL_X
    elif key_attribute == 'velocity.y':
        key_kind = BCLIBC_BaseTraj_InterpKey.VEL_Y
    elif key_attribute == 'velocity.z':
        key_kind = BCLIBC_BaseTraj_InterpKey.VEL_Z
    else:
        raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

    return key_kind

cdef str _key_to_attribute(BCLIBC_BaseTraj_InterpKey key_kind):
    cdef str key_attribute

    if key_kind == BCLIBC_BaseTraj_InterpKey.TIME:
        key_attribute = 'time'
    elif key_kind == BCLIBC_BaseTraj_InterpKey.MACH:
        key_attribute = 'mach'
    elif key_kind == BCLIBC_BaseTraj_InterpKey.POS_X:
        key_attribute = 'position.x'
    elif key_kind == BCLIBC_BaseTraj_InterpKey.POS_Y:
        key_attribute = 'position.y'
    elif key_kind == BCLIBC_BaseTraj_InterpKey.POS_Z:
        key_attribute = 'position.z'
    elif key_kind == BCLIBC_BaseTraj_InterpKey.VEL_X:
        key_attribute = 'velocity.x'
    elif key_kind == BCLIBC_BaseTraj_InterpKey.VEL_Y:
        key_attribute = 'velocity.y'
    elif key_kind == BCLIBC_BaseTraj_InterpKey.VEL_Z:
        key_attribute = 'velocity.z'
    else:
        raise ValueError(f"Unknown BCLIBC_BaseTraj_InterpKey value: {key_kind}")

    return key_attribute
