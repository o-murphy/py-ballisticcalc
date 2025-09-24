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

# Expose new interpolation helpers for tests and reuse across modules
cpdef double interpolate_3_pt(double x, double x0, double y0, double x1, double y1, double x2, double y2)
cpdef double interpolate_2_pt(double x, double x0, double y0, double x1, double y1)

# Internal nogil helpers for PCHIP used by base_traj_seq
cdef void _sort3(double* xs, double* ys) noexcept nogil
cdef void _pchip_slopes3(double x0, double y0, double x1, double y1, double x2, double y2,
                         double* m0, double* m1, double* m2) noexcept nogil
cdef double _hermite(double x, double xk, double xk1, double yk, double yk1, double mk, double mk1) noexcept nogil

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

    # @staticmethod
    # cdef from_BaseTrajDataT(BaseTrajDataT base_data)

# Factory helper exposed for use from other Cython modules
cdef BaseTrajDataT BaseTrajDataT_create(double time, V3dT position, V3dT velocity, double mach)
