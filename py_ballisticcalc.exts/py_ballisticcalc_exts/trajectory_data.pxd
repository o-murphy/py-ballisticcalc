# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.bclib cimport BaseTrajData_t

cdef class BaseTrajDataT:
    cdef:
        BaseTrajData_t _c_view

    # Hot-path C accessors (must be declared in .pxd to avoid Cython errors)
    cdef V3dT c_position(self)
    cdef V3dT c_velocity(self)
