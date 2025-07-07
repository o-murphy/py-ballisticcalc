# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT
)

cdef extern from "include/tdata.h":
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
        ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX

    ctypedef struct BaseTrajData_t:
        double time
        V3dT position
        V3dT velocity
        double mach

# aliases
ctypedef TrajFlag_t CTrajFlag
# ctypedef BaseTrajDataT BaseTrajData # temporary undeclared

cdef class BaseTrajData:
    cdef:
        readonly double time
        readonly V3dT position
        readonly V3dT velocity
        readonly double mach


cdef class TrajectoryData:
    cdef:
        readonly double time
        readonly object distance
        readonly object velocity
        readonly double mach
        readonly object height
        readonly object target_drop
        readonly object drop_adj
        readonly object windage
        readonly object windage_adj
        readonly object look_distance
        readonly object angle
        readonly double density_factor
        readonly double drag
        readonly object energy
        readonly object ogw
        readonly int flag
