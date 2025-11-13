"""
Header file for base_traj_seq.pyx - C Buffer Trajectory Sequence
"""

from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.bclib cimport BCLIBC_ErrorType

cdef extern from "include/bclibc_seq.hpp" namespace "bclibc" nogil:

    cdef enum class BCLIBC_BaseTraj_InterpKey:
        TIME
        MACH
        POS_X
        POS_Y
        POS_Z
        VEL_X
        VEL_Y
        VEL_Z

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

        @staticmethod
        BCLIBC_ErrorType interpolate(
            BCLIBC_BaseTraj_InterpKey key_kind,
            double key_value,
            const BCLIBC_BaseTrajData *p0,
            const BCLIBC_BaseTrajData *p1,
            const BCLIBC_BaseTrajData *p2,
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

    # Forward ref
    cdef cppclass BCLIBC_BaseTrajSeq:

        BCLIBC_BaseTrajSeq() except +

        BCLIBC_ErrorType append(
            double time,
            double px, double py, double pz,
            double vx, double vy, double vz,
            double mach
        ) noexcept nogil
        BCLIBC_ErrorType ensure_capacity(size_t min_capacity) noexcept nogil
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


cdef class BaseTrajSeqT:
    cdef BCLIBC_BaseTrajSeq _this

cdef class BaseTrajDataT:
    cdef BCLIBC_BaseTrajData _this
