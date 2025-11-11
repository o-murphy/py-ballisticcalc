# distutils: language = c++

from libcpp.vector cimport vector
from libc.stddef cimport ptrdiff_t
from cython.operator cimport dereference as deref, preincrement as inc

from py_ballisticcalc_exts.bclib cimport (
    BCLIBC_ShotProps,
    BCLIBC_BaseTrajData,
    BCLIBC_TrajFlag,
)
from py_ballisticcalc_exts.v3d cimport BCLIBC_V3dT

from py_ballisticcalc_exts.traj_filter cimport (
    BCLIBC_TrajectoryData,
    BCLIBC_TrajectoryDataFilter,
)

from py_ballisticcalc.trajectory_data import TrajectoryData

cdef class TrajectoryDataFilterT:

    def __cinit__(self):
        pass

    cdef init(
        self,
        BCLIBC_ShotProps *props,
        int filter_flags,
        BCLIBC_V3dT initial_position,
        BCLIBC_V3dT initial_velocity,
        double barrel_angle_rad,
        double look_angle_rad=0.0,
        double range_limit=0.0,
        double range_step=0.0,
        double time_step=0.0
    ):

        self.thisptr = new BCLIBC_TrajectoryDataFilter(
            props,
            <BCLIBC_TrajFlag>filter_flags,
            initial_position,
            initial_velocity,
            barrel_angle_rad,
            look_angle_rad,
            range_limit,
            range_step,
            time_step
        )

    def __dealloc__(self):
        if self.thisptr is not NULL:
            del self.thisptr
            self.thisptr = NULL

    cdef void record(self, BCLIBC_BaseTrajData *new_data) except +:
        if self.thisptr is NULL:
            raise MemoryError("BCLIBC_TrajectoryDataFilter allocation error")
        self.thisptr.record(new_data)

    cdef list get_records(self):
        cdef list py_list = []

        cdef const vector[BCLIBC_TrajectoryData]* cpp_records_ptr
        cpp_records_ptr = &self.thisptr.get_records()

        cdef vector[BCLIBC_TrajectoryData].const_iterator it
        cdef vector[BCLIBC_TrajectoryData].const_iterator end

        it = cpp_records_ptr.begin()
        end = cpp_records_ptr.end()

        while it != end:
            py_list.append(TrajectoryData_from_cpp(deref(it)))
            inc(it)

        return py_list

    cdef void append(self, BCLIBC_TrajectoryData *new_data) except +:
        self.thisptr.append(new_data)

    cdef void insert(self, BCLIBC_TrajectoryData *new_data, size_t index) except +:
        self.thisptr.insert(new_data, index)

    cdef BCLIBC_TrajectoryData get_record(self, Py_ssize_t index) except +:
        return self.thisptr.get_record(<ptrdiff_t>index)


cdef TrajectoryData_from_cpp(const BCLIBC_TrajectoryData& cpp_data):
    cdef object pydata = TrajectoryData(
        time=cpp_data.time,
        distance=TrajectoryData._new_feet(cpp_data.distance_ft),
        velocity=TrajectoryData._new_fps(cpp_data.velocity_fps),
        mach=cpp_data.mach,
        height=TrajectoryData._new_feet(cpp_data.height_ft),
        slant_height=TrajectoryData._new_feet(cpp_data.slant_height_ft),
        drop_angle=TrajectoryData._new_rad(cpp_data.drop_angle_rad),
        windage=TrajectoryData._new_feet(cpp_data.windage_ft),
        windage_angle=TrajectoryData._new_rad(cpp_data.windage_angle_rad),
        slant_distance=TrajectoryData._new_feet(cpp_data.slant_distance_ft),
        angle=TrajectoryData._new_rad(cpp_data.angle_rad),
        density_ratio=cpp_data.density_ratio,
        drag=cpp_data.drag,
        energy=TrajectoryData._new_ft_lb(cpp_data.energy_ft_lb),
        ogw=TrajectoryData._new_lb(cpp_data.ogw_lb),
        flag=cpp_data.flag
    )
    return pydata
