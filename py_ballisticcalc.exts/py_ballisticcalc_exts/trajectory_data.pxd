# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.tflag cimport TFlag


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
        readonly TFlag flag
