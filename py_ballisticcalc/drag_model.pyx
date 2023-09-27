from libc.math cimport floor, pow
from libc.stdlib cimport malloc, free

from .settings import Settings as Set
from .unit import *
from .drag_tables import DragTablesSet


__all__ = (
    'DragModel',
    'make_data_points'
)


cdef class DragDataPoint:
    cdef readonly double CD  # BC or CD
    cdef readonly Mach  # muzzle velocity or Mach

    def __cinit__(self, cd: float, mach: float):
        self.CD = cd
        self.Mach = mach

    def __iter__(self):
        yield self.CD
        yield self.Mach

    def __repr__(self):
        return f"DragDataPoint(CD={self.CD}, Mach={self.Mach})"


cdef struct CurvePoint:
    double a, b, c


cdef struct DragTableRow:
    double CD
    double Mach


cdef class DragModel:
    cdef:
        readonly object weight, diameter
        list _table_data, _curve_data
        double value
        double form_factor, sectional_density

    def __init__(self, double value,
                 drag_table: list,
                 weight: [float, Weight],
                 diameter: [float, Distance]):
        self.__post__init__(value, drag_table, weight, diameter)

    cdef __post__init__(DragModel self, double value, list drag_table, double weight, double diameter):
        cdef:
            double table_len = len(drag_table)
            str error = ''

        if table_len <= 0:
            error = 'Custom drag table must be longer than 0'
        elif value <= 0:
            error = 'Drag coefficient must be greater than zero'

        if error:
            raise ValueError(error)

        if drag_table in DragTablesSet:
            self.value = value
        elif table_len > 0:
            self.value = 1  # or 0.999
        else:
            raise ValueError('Wrong drag data')

        self.weight = weight if is_unit(weight) else Set.Units.weight(weight)
        self.diameter = Set.Units.diameter(diameter)
        self.sectional_density = self._get_sectional_density()
        self.form_factor = self._get_form_factor(self.value)
        self._table_data = make_data_points(drag_table)
        self._curve_data = calculate_curve(self._table_data)

    cpdef double drag(DragModel self, double mach):
        cdef double cd
        cd = calculate_by_curve(self._table_data, self._curve_data, mach)
        return cd * 2.08551e-04 / self.value

    cdef double _get_form_factor(self, double bc):
        return self.sectional_density / bc

    cdef double _get_sectional_density(self):
        cdef double w, d
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return sectional_density(w, d)

    cdef double _standard_cd(self, double mach):
        return calculate_by_curve(self._table_data, self._curve_data, mach)

    cdef double _calculated_cd(self, double mach):
        return self._standard_cd(mach) * self.form_factor

    cpdef list calculated_drag_function(self):
        """
        Returns custom drag function based on input bc value
        """
        cdef:
            double cd, st_mach
            DragDataPoint point
            list calculated_cd_table = []

        for point in self._table_data:
            st_mach = point.Mach
            cd = self._calculated_cd(st_mach)
            calculated_cd_table.append(DragTableRow(cd, st_mach))

        return calculated_cd_table

cpdef list make_data_points(drag_table: list):
    return [DragDataPoint(point['CD'], point['Mach']) for point in drag_table]

cdef double sectional_density(double weight, double diameter):
    return weight / pow(diameter, 2) / 7000

cdef list calculate_curve(list data_points):

    cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
    cdef curve = []
    cdef curve_point
    cdef int num_points, len_data_points, len_data_range

    rate = (data_points[1].CD - data_points[0].CD) / (data_points[1].Mach - data_points[0].Mach)
    curve = [CurvePoint(0, rate, data_points[0].CD - data_points[0].Mach * rate)]
    len_data_points = int(len(data_points))
    len_data_range = len_data_points - 1

    for i in range(1, len_data_range):
        x1 = data_points[i - 1].Mach
        x2 = data_points[i].Mach
        x3 = data_points[i + 1].Mach
        y1 = data_points[i - 1].CD
        y2 = data_points[i].CD
        y3 = data_points[i + 1].CD
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_point = CurvePoint(a, b, c)
        curve.append(curve_point)

    num_points = len_data_points
    rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
           (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
    curve_point = CurvePoint(0, rate, data_points[num_points - 1].CD - data_points[num_points - 2].Mach * rate)
    curve.append(curve_point)
    return curve


cdef double calculate_by_curve(data: list, curve: list, mach: float):
    cdef int num_points, mlo, mhi, mid
    cdef CurvePoint curve_m

    num_points = int(len(curve))
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = int(floor(mhi + mlo) / 2.0)
        if data[mid].Mach < mach:
            mlo = mid
        else:
            mhi = mid

    if data[mhi].Mach - mach > mach - data[mlo].Mach:
        m = mlo
    else:
        m = mhi
    curve_m = curve[m]
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)

# def calculate_by_curve(data, curve, mach):
#     num_points = len(curve)
#     mlo = 0
#     mhi = num_points - 2
#
#     while mhi - mlo > 1:
#         mid = (mhi + mlo) // 2
#         mid_velocity = data[mid].velocity
#
#         if mid_velocity < mach:
#             mlo = mid
#         else:
#             mhi = mid
#
#     mlo_velocity = data[mlo].velocity
#     mhi_velocity = data[mhi].velocity
#
#     if mhi_velocity - mach > mach - mlo_velocity:
#         m = mlo
#     else:
#         m = mhi
#
#     curve_m = curve[m]
#     a = curve_m.a
#     b = curve_m.b
#     c = curve_m.c
#
#     return c + mach * (b + a * mach)
