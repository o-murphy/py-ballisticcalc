# v3d.pxd

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT

# Declare the C header file
cdef extern from "include/state.h" nogil:
    # Declare the V3dT structure
    ctypedef struct BaseIntegrationStateT:
        double time
        V3dT wind_vector
        V3dT range_vector
        V3dT velocity_vector
        double velocity
        double mach
        double density_factor
        double drag

# internal alias
ctypedef BaseIntegrationStateT CythonizedBaseIntegrationState
