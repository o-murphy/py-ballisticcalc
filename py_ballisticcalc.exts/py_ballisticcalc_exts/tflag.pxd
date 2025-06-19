# pxd file for tdatafilter.h

# Include standard C library types
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT

# Declare the TFlag enum
cdef extern from "include/tflag.h":
    # Using 'int' as the underlying type for the enum
    # Cython can typically handle C enums directly.
    # The actual integer values are important for bitwise operations.
    enum TFlag:
        TRAJ_NONE = 0
        TRAJ_ZERO_UP = 1
        TRAJ_ZERO_DOWN = 2
        TRAJ_ZERO = TRAJ_ZERO_UP | TRAJ_ZERO_DOWN
        TRAJ_MACH = 4
        TRAJ_RANGE = 8
        TRAJ_APEX = 16
        TRAJ_ALL = TRAJ_RANGE | TRAJ_ZERO_UP | TRAJ_ZERO_DOWN | TRAJ_MACH | TRAJ_APEX
