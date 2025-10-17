# cython: freethreading_compatible=True
# noinspection PyUnresolvedReferences
from cpython.exc cimport PyErr_Occurred
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport Config_t, MachList_t, Curve_t, Wind_t

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
