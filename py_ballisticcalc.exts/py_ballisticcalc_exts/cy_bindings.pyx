# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from libc.stdlib cimport malloc, free
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, pow, atan2, exp, sqrt, sin, cos, fmin
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT

@final
cdef Config_t Config_t_from_pyobject(object config):
    return Config_t_fromPyObject(<PyObject *>config)

cdef MachList_t MachList_t_from_pylist(list[object] data):
    cdef MachList_t ml = MachList_t_fromPylist(<PyObject *>data)
    if ml.array == NULL:
        raise MemoryError("Failed to create MachList_t from Python list")
    return ml

cdef Curve_t Curve_t_from_pylist(list[object] data_points):
    return Curve_t_fromPylist(<PyObject *>data_points)


# We still need a way to get data from Python objects into Wind_t structs.
# This internal helper function is used by WindSockT_create.
# It assumes 'w' is a Python object that conforms to the interface needed.
cdef Wind_t Wind_t_from_python(object w):
    return Wind_t(
        w.velocity._fps,
        w.direction_from._rad,
        w.until_distance._feet,
        w.MAX_DISTANCE_FEET
    )
