# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT

cdef extern from "include/bclib.h" nogil:
    # Using 'int' as the underlying type for the enum
    # Cython can typically handle C enums directly.
    # The actual integer values are important for bitwise operations.

    ctypedef enum TrajFlag_t:
        TFLAG_NONE = 0,
        TFLAG_ZERO_UP = 1,
        TFLAG_ZERO_DOWN = 2,
        TFLAG_ZERO = TFLAG_ZERO_UP | TFLAG_ZERO_DOWN,
        TFLAG_MACH = 4,
        TFLAG_RANGE = 8,
        TFLAG_APEX = 16,
        TFLAG_ALL = TFLAG_RANGE | TFLAG_ZERO_UP | TFLAG_ZERO_DOWN | TFLAG_MACH | TFLAG_APEX
        TFLAG_MRT = 32

    ctypedef struct BaseTrajData_t:
        double time
        V3dT position
        V3dT velocity
        double mach

    BaseTrajData_t* BaseTrajData_t_create(double time, V3dT position, V3dT velocity, double mach) noexcept nogil
    void BaseTrajData_t_destroy(BaseTrajData_t *ptr) noexcept nogil


cdef class BaseTrajDataT:
    cdef:
        BaseTrajData_t *_c_view

    # Hot-path C accessors (must be declared in .pxd to avoid Cython errors)
    cdef V3dT c_position(self)
    cdef V3dT c_velocity(self)
