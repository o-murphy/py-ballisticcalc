# cython: freethreading_compatible=True

from libcpp.vector cimport vector
from libc.stddef cimport ptrdiff_t
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_ShotProps,
    BCLIBC_TrajFlag,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.interp cimport BCLIBC_InterpMethod
from py_ballisticcalc_exts.traj_seq cimport BCLIBC_BaseTrajData

cdef extern from "include/bclibc/traj_filter.hpp" namespace "bclibc":

    ctypedef enum BCLIBC_TrajectoryData_InterpKey:
        pass

    ctypedef struct BCLIBC_FlaggedData:
        pass

    # --- C++ Class BCLIBC_TrajectoryData ---
    cdef cppclass BCLIBC_TrajectoryData:
        BCLIBC_TrajectoryData() except +
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps *props,
            double time,
            const BCLIBC_V3dT *range_vector,
            const BCLIBC_V3dT *velocity_vector,
            double mach,
            BCLIBC_TrajFlag flag
        ) except +
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps *props,
            const BCLIBC_BaseTrajData *data,
            BCLIBC_TrajFlag flag
        ) except +
        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps *props,
            const BCLIBC_FlaggedData *data
        ) except +

        double time
        double distance_ft
        double velocity_fps
        double mach
        double height_ft
        double slant_height_ft
        double drop_angle_rad
        double windage_ft
        double windage_angle_rad
        double slant_distance_ft
        double angle_rad
        double density_ratio
        double drag
        double energy_ft_lb
        double ogw_lb
        BCLIBC_TrajFlag flag

        @staticmethod
        BCLIBC_TrajectoryData interpolate(
            BCLIBC_TrajectoryData_InterpKey key,
            double value,
            const BCLIBC_TrajectoryData *t0,
            const BCLIBC_TrajectoryData *t1,
            const BCLIBC_TrajectoryData *t2,
            BCLIBC_TrajFlag flag,
            BCLIBC_InterpMethod method
        ) except +


cdef list get_records(const vector[BCLIBC_TrajectoryData] *records)

cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data)
