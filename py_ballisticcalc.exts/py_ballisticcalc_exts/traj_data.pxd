"""
Header file for traj_data.pyx - C Buffer Trajectory Sequence
"""

from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_ShotProps,
    BCLIBC_ErrorType,
    BCLIBC_TrajFlag
)
from py_ballisticcalc_exts.interp cimport BCLIBC_InterpMethod


cdef extern from "include/bclibc/traj_data.hpp" namespace "bclibc" nogil:

    cdef enum class BCLIBC_BaseTraj_InterpKey:
        TIME
        MACH
        POS_X
        POS_Y
        POS_Z
        VEL_X
        VEL_Y
        VEL_Z

    # Forward ref
    cdef cppclass BCLIBC_BaseTraj

    cdef cppclass BCLIBC_BaseTrajData:
        double time
        BCLIBC_V3dT position
        BCLIBC_V3dT velocity
        double mach

        BCLIBC_BaseTrajData() except+
        BCLIBC_BaseTrajData(
            double time,
            BCLIBC_V3dT position,
            BCLIBC_V3dT velocity,
            double mach
        ) except+

        BCLIBC_BaseTraj as_BaseTraj() const
        double get_key_value(BCLIBC_BaseTraj_InterpKey key_kind) const

        @staticmethod
        BCLIBC_ErrorType interpolate(
            BCLIBC_BaseTraj_InterpKey key_kind,
            double key_value,
            const BCLIBC_BaseTrajData &p0,
            const BCLIBC_BaseTrajData &p1,
            const BCLIBC_BaseTrajData &p2,
            BCLIBC_BaseTrajData *out
        )

    cdef cppclass BCLIBC_BaseTraj:
        double time
        double px
        double py
        double pz
        double vx
        double vy
        double vz
        double mach

        BCLIBC_BaseTraj() except+
        BCLIBC_BaseTraj(
            double time,
            double px,
            double py,
            double pz,
            double vx,
            double vy,
            double vz,
            double mach
        ) except+

        BCLIBC_BaseTrajData as_BaseTrajData() const

    cdef cppclass BCLIBC_BaseTrajHandlerInterface:
        BCLIBC_ErrorType handle(
            const BCLIBC_BaseTraj &data
        ) noexcept nogil

    cdef cppclass BCLIBC_BaseTrajSeq(BCLIBC_BaseTrajHandlerInterface):

        BCLIBC_BaseTrajSeq() except +

        BCLIBC_ErrorType append(
            const BCLIBC_BaseTraj &data
        ) noexcept nogil
        Py_ssize_t get_length() const
        Py_ssize_t get_capacity() const
        BCLIBC_ErrorType interpolate_at(
            Py_ssize_t idx,
            BCLIBC_BaseTraj_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData *out
        ) noexcept nogil
        BCLIBC_BaseTraj *get_raw_item(Py_ssize_t idx) const
        BCLIBC_ErrorType get_at_slant_height(
            double look_angle_rad,
            double value,
            BCLIBC_BaseTrajData *out
        ) const
        BCLIBC_ErrorType get_item(
            Py_ssize_t idx,
            BCLIBC_BaseTrajData *out
        ) const
        BCLIBC_ErrorType get_at(
            BCLIBC_BaseTraj_InterpKey key_kind,
            double key_value,
            double start_from_time,
            BCLIBC_BaseTrajData *out
        ) const

    cdef enum class BCLIBC_TrajectoryData_InterpKey:
        pass

    # --- C++ Class BCLIBC_TrajectoryData ---
    cdef cppclass BCLIBC_TrajectoryData:
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


cdef class BaseTrajSeqT:
    cdef BCLIBC_BaseTrajSeq _this


cdef class BaseTrajDataT:
    cdef BCLIBC_BaseTrajData _this
