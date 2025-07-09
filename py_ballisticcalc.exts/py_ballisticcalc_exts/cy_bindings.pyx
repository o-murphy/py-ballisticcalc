# Total Score: 158, Possible Score: 21000
# Total Non-Empty Lines: 210
# Python Overhead Lines: 19
# Cythonization Percentage: 99.25%
# Python Overhead Lines Percentage: 9.05%

# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from cpython.object cimport PyObject
# noinspection PyUnresolvedReferences
from libc.stdlib cimport malloc, free
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, pow, atan2, exp, sqrt, sin, cos, fmin
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT
)

@final
cdef Config_t config_bind(object config):
    return Config_t(
        config.cMaxCalcStepSizeFeet,
        config.cZeroFindingAccuracy,
        config.cMinimumVelocity,
        config.cMaximumDrop,
        config.cMaxIterations,
        config.cGravityConstant,
        config.cMinimumAltitude,
    )

cdef MachList_t cy_table_to_mach(list[object] data):
    cdef MachList_t ml = MachList_t_fromPylist(<PyObject *>data)
    if ml.array == NULL:
        raise MemoryError("Failed to create MachList_t from Python list")
    return ml

cdef Curve_t cy_calculate_curve(list[object] data_points):
    return Curve_t_fromPylist(<PyObject *>data_points)


# We still need a way to get data from Python objects into Wind_t structs.
# This internal helper function is used by WindSockT_create.
# It assumes 'w' is a Python object that conforms to the interface needed.
cdef Wind_t Wind_t_from_python(object w):
    return Wind_t(
        w.velocity._fps,
        w.direction_from._rad,
        w.until_distance._feet,
        w.MAX_DISTANCE_FEET
    )
