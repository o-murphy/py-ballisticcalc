# cython: freethreading_compatible=True

from libcpp.vector cimport vector
from libc.stddef cimport ptrdiff_t
from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_ShotProps,
    BCLIBC_BaseTrajData,
    BCLIBC_TrajFlag,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.interp cimport (
    BCLIBC_InterpMethod,
)

cdef extern from "include/bclibc_traj_filter.hpp" namespace "bclibc":

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

    # --- C++ Class BCLIBC_TrajectoryDataFilter ---
    cdef cppclass BCLIBC_TrajectoryDataFilter:
        BCLIBC_TrajectoryDataFilter(
            const BCLIBC_ShotProps *props,
            BCLIBC_TrajFlag filter_flags,
            BCLIBC_V3dT initial_position,
            BCLIBC_V3dT initial_velocity,
            double barrel_angle_rad,
            double look_angle_rad,
            double range_limit,
            double range_step,
            double time_step) except +

        void record(BCLIBC_BaseTrajData *new_data) except +
        const vector[BCLIBC_TrajectoryData]& get_records() const
        void append(BCLIBC_TrajectoryData *new_data) except +
        void insert(BCLIBC_TrajectoryData *new_data, size_t index) except +
        const BCLIBC_TrajectoryData& get_record(ptrdiff_t index) except +

cdef class TrajectoryDataFilterT:
    cdef BCLIBC_TrajectoryDataFilter *thisptr

    cdef init(
        self,
        BCLIBC_ShotProps *props,
        int filter_flags,
        BCLIBC_V3dT initial_position,
        BCLIBC_V3dT initial_velocity,
        double barrel_angle_rad,
        double look_angle_rad=*,
        double range_limit=*,
        double range_step=*,
        double time_step=*
    )
    cdef void record(self, BCLIBC_BaseTrajData *new_data) except +
    cdef list get_records(self)
    cdef void append(self, BCLIBC_TrajectoryData *new_data) except +
    cdef void insert(self, BCLIBC_TrajectoryData *new_data, size_t index) except +
    cdef BCLIBC_TrajectoryData get_record(self, Py_ssize_t index) except +


cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data)
