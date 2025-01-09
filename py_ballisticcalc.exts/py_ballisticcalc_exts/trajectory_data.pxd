from py_ballisticcalc_exts._data_repr cimport _DataRepr


cdef enum CTrajFlag:
    NONE = 0
    ZERO_UP = 1
    ZERO_DOWN = 2
    MACH = 4
    RANGE = 8
    DANGER = 16
    ZERO = ZERO_UP | ZERO_DOWN
    ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | DANGER


cdef class TrajectoryData(_DataRepr):
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
