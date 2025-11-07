# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_MachList,
    BCLIBC_Curve,
    BCLIBC_Config,
    BCLIBC_Wind,
    BCLIBC_Coriolis,
    BCLIBC_WindSock,
    BCLIBC_BaseTrajSeq_InterpKey,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT


cdef extern from "include/bclibc_py_bind.h" nogil:
    BCLIBC_MachList BCLIBC_MachList_fromPylist(PyObject *pylist) noexcept nogil
    BCLIBC_Curve BCLIBC_Curve_fromPylist(PyObject *data_points) noexcept nogil
    BCLIBC_Config BCLIBC_Config_fromPyObject(PyObject * config) noexcept nogil
    BCLIBC_Wind BCLIBC_Wind_fromPyObject(PyObject *w) noexcept nogil


# python to C objects conversion
cdef BCLIBC_Config BCLIBC_Config_from_pyobject(object config)
cdef BCLIBC_MachList BCLIBC_MachList_from_pylist(list[object] data)
cdef BCLIBC_Curve BCLIBC_Curve_from_pylist(list[object] data_points)
cdef BCLIBC_Wind BCLIBC_Wind_from_py(object w)
cdef BCLIBC_Coriolis BCLIBC_Coriolis_from_pyobject(object coriolis_obj)
# Function to create and initialize a BCLIBC_WindSock
cdef BCLIBC_WindSock BCLIBC_WindSock_from_pylist(object winds_py_list)

# Helper functions to create unit objects
cdef object feet_from_c(double val)
cdef object rad_from_c(double val)

cdef object v3d_to_vector(const BCLIBC_V3dT *v)

cdef BCLIBC_BaseTrajSeq_InterpKey _attribute_to_key(str key_attribute)
cdef str _key_to_attribute(BCLIBC_BaseTrajSeq_InterpKey key_kind)
