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

cdef MachList_t MachList_t_from_pylist(list[object] data):
    cdef MachList_t ml = MachList_t_fromPylist(<PyObject *>data)
    if ml.array == NULL:
        if PyErr_Occurred():
            raise
        else:
            raise MemoryError("Failed to create MachList_t from Python list")
    return ml

cdef Curve_t Curve_t_from_pylist(list[object] data_points):
    cdef Curve_t result = Curve_t_fromPylist(<PyObject *>data_points)
    if PyErr_Occurred():
        raise
    return Curve_t_fromPylist(<PyObject *>data_points)


# We still need a way to get data from Python objects into Wind_t structs.
# This internal helper function is used by WindSockT_create.
# It assumes 'w' is a Python object that conforms to the interface needed.
cdef Wind_t Wind_t_from_py(object w):
    cdef Wind_t result
    result = Wind_t_fromPyObject(<PyObject *>w)
    if PyErr_Occurred():
        raise
    return result
