from libc.math cimport floor, pow

from .settings import Settings as Set
from .unit import *
from .drag_tables import DragTablesSet


__all__ = ('DragDataPoint', 'DragModel', 'make_data_points')


cdef class DragDataPoint:
    cdef readonly double coeff  # BC or CD
    cdef readonly double velocity  # muzzle velocity or Mach

    def __cinit__(self, coeff: float, velocity: float):
        self.coeff = coeff
        self.velocity = velocity

    def __iter__(self):
        yield self.coeff
        yield self.velocity

    def __repr__(self):
        return f"DragDataPoint(coeff={self.coeff}, velocity={self.velocity})"


cdef struct CurvePoint:
    double a, b, c


cdef class DragModel:
    cdef list _table_data, _curve_data
    cdef readonly list table
    cdef readonly object weight, diameter
    cdef public double value
    cdef readonly double form_factor, sectional_density

    def __init__(self, value: float,
                 drag_table: list,
                 weight: [float, Weight],
                 diameter: [float, Distance]):

        self.table = drag_table
        self.weight = weight if is_unit(weight) else Set.Units.weight(weight)
        self.diameter = Set.Units.diameter(diameter)
        self.sectional_density = self._get_sectional_density()

        if drag_table in DragTablesSet:
            self.value = value
            self.form_factor = self._get_form_factor(self.value)
            self._table_data = make_data_points(self.table)
            self._curve_data = calculate_curve(self._table_data)
        elif len(self.table) == 0:
            raise ValueError('Custom drag table must be longer than 0')
        elif len(self.table) > 0:
            # TODO: strange, both calculations get same results,
            #       but need to find way use form-factor instead of bc in drag()
            # self._form_factor = 0.999  # defined as form factor in lapua-like custom CD data
            # self.value = self._get_custom_bc()
            self.value = 1  # or 0.999
            self.form_factor = self._get_form_factor(self.value)

            self._table_data = make_data_points(self.table)
            self._curve_data = calculate_curve(self._table_data)
        elif value <= 0:
            raise ValueError('Drag coefficient must be greater than zero')
        else:
            raise ValueError('Wrong drag data')

    cpdef double drag(self, double mach):
        cdef double cd
        cd = calculate_by_curve(self._table_data, self._curve_data, mach)
        return cd * 2.08551e-04 / self.value

    cdef double _get_custom_bc(self):
        return self.sectional_density / self.form_factor

    cdef _get_form_factor(self, bc):
        return self.sectional_density / bc

    cdef double _get_sectional_density(self):
        cdef double w, d
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return w / pow(d, 2) / 7000

    cdef double standard_cd(self, double mach):
        return calculate_by_curve(self._table_data, self._curve_data, mach)

    cpdef double calculated_cd(self, double mach):
        return self.standard_cd(mach) * self.form_factor

    cpdef list calculated_drag_function(self):
        cdef standard_cd_table
        cdef list calculated_cd_table
        cdef double st_mach, st_cd, cd

        calculated_cd_table = []

        for point in self._table_data:
            st_mach = point.velocity
            st_cd = point.coeff
            cd = self.calculated_cd(st_mach)
            calculated_cd_table.append({'Mach': st_mach, 'CD': cd})

        return calculated_cd_table

cpdef list make_data_points(drag_table: list):
    return [DragDataPoint(point['CD'], point['Mach']) for point in drag_table]

cdef list calculate_curve(list data_points):

    cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
    cdef curve = []
    cdef curve_point
    cdef int num_points, len_data_points, len_data_range

    rate = (data_points[1].coeff - data_points[0].coeff) / (data_points[1].velocity - data_points[0].velocity)
    curve = [CurvePoint(0, rate, data_points[0].coeff - data_points[0].velocity * rate)]
    len_data_points = int(len(data_points))
    len_data_range = len_data_points - 1

    for i in range(1, len_data_range):
        x1 = data_points[i - 1].velocity
        x2 = data_points[i].velocity
        x3 = data_points[i + 1].velocity
        y1 = data_points[i - 1].coeff
        y2 = data_points[i].coeff
        y3 = data_points[i + 1].coeff
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_point = CurvePoint(a, b, c)
        curve.append(curve_point)

    num_points = len_data_points
    rate = (data_points[num_points - 1].coeff - data_points[num_points - 2].coeff) / \
           (data_points[num_points - 1].velocity - data_points[num_points - 2].velocity)
    curve_point = CurvePoint(0, rate, data_points[num_points - 1].coeff - data_points[num_points - 2].velocity * rate)
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
        if data[mid].velocity < mach:
            mlo = mid
        else:
            mhi = mid

    if data[mhi].velocity - mach > mach - data[mlo].velocity:
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
