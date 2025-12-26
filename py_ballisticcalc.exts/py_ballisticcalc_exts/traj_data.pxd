"""
Header file for traj_data.pyx - C Buffer Trajectory Sequence
"""

from libcpp.vector cimport vector
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT
from py_ballisticcalc_exts.base_types cimport (
    BCLIBC_ShotProps,
    BCLIBC_TrajFlag
)
from py_ballisticcalc_exts.interp cimport BCLIBC_InterpMethod


cdef extern from "include/bclibc/traj_data.hpp" namespace "bclibc" nogil:

    cdef enum class BCLIBC_BaseTrajData_InterpKey:
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
        double px
        double py
        double pz
        double vx
        double vy
        double vz
        double mach

        BCLIBC_BaseTrajData() except +
        BCLIBC_BaseTrajData(
            double time,
            double px,
            double py,
            double pz,
            double vx,
            double vy,
            double vz,
            double mach
        ) except +

        BCLIBC_BaseTrajData(
            double time,
            const BCLIBC_V3dT &position,
            const BCLIBC_V3dT &velocity,
            double mach
        ) except +

        BCLIBC_V3dT position() const
        BCLIBC_V3dT velocity() const

        double operator[](BCLIBC_BaseTrajData_InterpKey key_kind) const
        double slant_val_buf(double ca, double sa) const

        @staticmethod
        void interpolate(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            const BCLIBC_BaseTrajData &p0,
            const BCLIBC_BaseTrajData &p1,
            const BCLIBC_BaseTrajData &p2,
            BCLIBC_BaseTrajData &out
        ) except +ZeroDivisionError

    cdef cppclass BCLIBC_BaseTrajDataHandlerInterface:
        void handle(const BCLIBC_BaseTrajData &data) except +
        void insert_handler(vector[BCLIBC_BaseTrajDataHandlerInterface*].iterator position,
                            BCLIBC_BaseTrajDataHandlerInterface *handler) except +
        vector[BCLIBC_BaseTrajDataHandlerInterface*].iterator begin()
        vector[BCLIBC_BaseTrajDataHandlerInterface*].iterator end()

    cdef cppclass BCLIBC_BaseTrajDataHandlerCompositor(BCLIBC_BaseTrajDataHandlerInterface):
        BCLIBC_BaseTrajDataHandlerCompositor() except +
        void handle(const BCLIBC_BaseTrajData& data) except +
        void add_handler(BCLIBC_BaseTrajDataHandlerInterface* handler) except +

    cdef cppclass BCLIBC_BaseTrajSeq(BCLIBC_BaseTrajDataHandlerInterface):

        BCLIBC_BaseTrajSeq() except +

        void handle(const BCLIBC_BaseTrajData& data) except +
        void append(
            const BCLIBC_BaseTrajData &data
        ) except +
        Py_ssize_t get_length() const
        Py_ssize_t get_capacity() const
        void interpolate_at(
            Py_ssize_t idx,
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            BCLIBC_BaseTrajData &out
        ) except +
        void get_at_slant_height(
            double look_angle_rad,
            double value,
            BCLIBC_BaseTrajData &out
        ) except +
        BCLIBC_BaseTrajData &operator[](
            Py_ssize_t idx
        ) except +IndexError
        void get_at(
            BCLIBC_BaseTrajData_InterpKey key_kind,
            double key_value,
            double start_from_time,
            BCLIBC_BaseTrajData &out
        ) except +

    cdef enum class BCLIBC_TrajectoryData_InterpKey:
        pass

    cdef cppclass BCLIBC_FlaggedData:
        BCLIBC_BaseTrajData data
        BCLIBC_TrajFlag flag

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

        BCLIBC_TrajectoryData() except +

        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            double time,
            const BCLIBC_V3dT &range_vector,
            const BCLIBC_V3dT &velocity_vector,
            double mach,
            BCLIBC_TrajFlag flag
        ) except +

        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            const BCLIBC_BaseTrajData &data,
            BCLIBC_TrajFlag flag
        ) except +

        BCLIBC_TrajectoryData(
            const BCLIBC_ShotProps &props,
            const BCLIBC_FlaggedData &data
        ) except +

        @staticmethod
        BCLIBC_TrajectoryData interpolate(
            BCLIBC_TrajectoryData_InterpKey key,
            double value,
            const BCLIBC_TrajectoryData &t0,
            const BCLIBC_TrajectoryData &t1,
            const BCLIBC_TrajectoryData &t2,
            BCLIBC_TrajFlag flag,
            BCLIBC_InterpMethod method
        ) except +


cdef class CythonizedBaseTrajSeq:
    cdef BCLIBC_BaseTrajSeq _this


cdef class CythonizedBaseTrajData:
    cdef BCLIBC_BaseTrajData _this


cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data)
cdef list TrajectoryData_list_from_cpp(const vector[BCLIBC_TrajectoryData] &records)
