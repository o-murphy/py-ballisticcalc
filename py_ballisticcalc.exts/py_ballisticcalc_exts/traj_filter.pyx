# cython: freethreading_compatible=True

from libcpp.vector cimport vector
from cython.operator cimport dereference as deref, preincrement as inc
from py_ballisticcalc_exts.traj_filter cimport BCLIBC_TrajectoryData
from py_ballisticcalc.trajectory_data import TrajectoryData


cdef list get_records(const vector[BCLIBC_TrajectoryData] *records):
    cdef list py_list = []
    cdef vector[BCLIBC_TrajectoryData].const_iterator it = records.begin()
    cdef vector[BCLIBC_TrajectoryData].const_iterator end = records.end()

    while it != end:
        py_list.append(TrajectoryData_from_cpp(deref(it)))
        inc(it)

    return py_list


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
