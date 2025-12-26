from cpython.object cimport PyObject
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_MachList,
    BCLIBC_Curve,
    BCLIBC_Atmosphere,
    BCLIBC_Config,
    BCLIBC_Wind,
    BCLIBC_Coriolis,
    BCLIBC_WindSock,
    BCLIBC_ShotProps,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.traj_data cimport BCLIBC_BaseTrajData_InterpKey


cdef extern from "include/bclibc/py_bind.hpp" namespace "bclibc" nogil:
    BCLIBC_MachList BCLIBC_MachList_fromPylist(PyObject *pylist) except *
    BCLIBC_Curve BCLIBC_Curve_fromPylist(PyObject *data_points) except *
    BCLIBC_Config BCLIBC_Config_fromPyObject(PyObject * config) except *
    BCLIBC_Atmosphere BCLIBC_Atmosphere_fromPyObject(PyObject *atmo) except *

# python to C objects conversion
cdef BCLIBC_Config BCLIBC_Config_from_pyobject(object config)
cdef BCLIBC_Atmosphere BCLIBC_Atmosphere_from_pyobject(object atmo)
cdef BCLIBC_MachList BCLIBC_MachList_from_pylist(list[object] data)
cdef BCLIBC_Curve BCLIBC_Curve_from_pylist(list[object] data_points)
cdef BCLIBC_Coriolis BCLIBC_Coriolis_from_pyobject(object coriolis_obj)
# Function to create and initialize a BCLIBC_WindSock
cdef BCLIBC_WindSock BCLIBC_WindSock_from_pytuple(tuple[object] winds_py_tuple)
cdef BCLIBC_ShotProps BCLIBC_ShotProps_from_pyobject(object shot_info, double calc_step = *)

# Helper functions to create unit objects
cdef object feet_from_c(double val)
cdef object rad_from_c(double val)

cdef object v3d_to_vector(const BCLIBC_V3dT *v)

cdef BCLIBC_BaseTrajData_InterpKey _attribute_to_key(str key_attribute)
cdef str _key_to_attribute(BCLIBC_BaseTrajData_InterpKey key_kind)
