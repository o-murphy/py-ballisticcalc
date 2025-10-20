# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    MachList_t,
    Curve_t,
    Config_t,
    Wind_t,
    Coriolis_t,
    WindSock_t,
)

cdef extern from "include/bind.h" nogil:
    MachList_t MachList_t_fromPylist(const PyObject *pylist) noexcept nogil
    Curve_t Curve_t_fromPylist(const PyObject *data_points) noexcept nogil
    Config_t Config_t_fromPyObject(const PyObject * config) noexcept nogil
    Wind_t Wind_t_fromPyObject(const PyObject *w) noexcept nogil


# python to C objects conversion
cdef Config_t Config_t_from_pyobject(object config)
cdef MachList_t MachList_t_from_pylist(list[object] data)
cdef Curve_t Curve_t_from_pylist(list[object] data_points)
cdef Wind_t Wind_t_from_py(object w)
cdef Coriolis_t Coriolis_t_from_pyobject(object coriolis_obj)
# Function to create and initialize a WindSock_t
cdef WindSock_t WindSock_t_from_pylist(object winds_py_list)

# Helper functions to create unit objects
cdef object _new_feet(double val)
cdef object _new_rad(double val)
