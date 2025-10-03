# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT

cdef extern from "include/bclib.h":
    # Using 'int' as the underlying type for the enum
    # Cython can typically handle C enums directly.
    # The actual integer values are important for bitwise operations.
    ctypedef enum TrajFlag_t:
        NONE = 0
        ZERO_UP = 1
        ZERO_DOWN = 2
        ZERO = ZERO_UP | ZERO_DOWN
        MACH = 4
        RANGE = 8
        APEX = 16
        ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX  # 31
        MRT = 32

    ctypedef struct BaseTrajData_t:
        double time
        V3dT position
        V3dT velocity
        double mach


cdef class BaseTrajDataT:
    cdef:
        readonly double time
        readonly V3dT _position
        readonly V3dT _velocity
        readonly double mach
    # Hot-path C accessors (must be declared in .pxd to avoid Cython errors)
    cdef V3dT c_position(self)
    cdef V3dT c_velocity(self)

cdef class TrajectoryDataT:
    cdef:
        readonly double time
        readonly object distance
        readonly object velocity
        readonly double mach
        readonly object height
        readonly object slant_height
        readonly object drop_angle
        readonly object windage
        readonly object windage_angle
        readonly object slant_distance
        readonly object angle
        readonly double density_ratio
        readonly double drag
        readonly object energy
        readonly object ogw
        readonly int flag
