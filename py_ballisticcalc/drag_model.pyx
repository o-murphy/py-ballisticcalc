from libc.math cimport floor, pow

from .settings import Settings as Set
from .unit import *
from .drag_tables import DragTablesSet
from typing import NamedTuple


__all__ = ('DragDataPoint', 'DragModel', 'calculate_by_curve')


class DragDataPoint(NamedTuple):
    coeff: float  # BC or CD
    velocity: float  # muzzle velocity or Mach


cdef class DragModel:
    cdef double _value
    cdef list _table
    cdef list _table_data
    cdef list _curve_data
    cdef _weight, _diameter
    cdef double _sectional_density, _form_factor

    def __init__(self, value: double,
                 drag_table: list,
                 weight: [float, Weight],
                 diameter: [float, Distance]):

        self._table = drag_table

        self._weight = weight if is_unit(weight) else Weight(weight, Set.Units.weight)
        self._diameter = Distance(diameter, Set.Units.diameter)
        self._sectional_density = self._get_sectional_density()

        if drag_table in DragTablesSet:
            self._value = value
            self._form_factor = self._get_form_factor()
            self._table_data = make_data_points(self._table)
            self._curve_data = calculate_curve(self._table_data)
        elif len(self._table) == 0:
            raise ValueError('Custom drag table must be longer than 0')
        elif len(self._table) > 0:
            # TODO: strange but both calculations working same, but need to find way use form-factor instead of bc in drag()

            # self._form_factor = 0.999  # defined as form factor in lapua-like custom CD data
            # self._value = self._get_custom_bc()
            self._value = 1  # or 0.999
            self._form_factor = self._get_form_factor()

            self._table_data = make_data_points(self._table)
            self._curve_data = calculate_curve(self._table_data)
        elif value <= 0:
            raise ValueError('Drag coefficient must be greater than zero')
        else:
            raise ValueError('Wrong drag data')

    cpdef double drag(self, double mach):
        cdef double cd
        cd = calculate_by_curve(self._table_data, self._curve_data, mach)
        return cd * 2.08551e-04 / self._value

    cpdef double value(self):
        return self._value

    cpdef list table(self):
        return self._table

    cpdef weight(self):
        return self._weight

    cpdef diameter(self):
        return self._diameter

    cdef double _get_custom_bc(self):
        return self._sectional_density / self._form_factor

    cdef double _get_form_factor(self):
        return self._sectional_density / self._value

    cdef double _get_sectional_density(self):
        cdef double w, d
        w = self._weight.get_in(Weight.Grain)
        d = self._diameter.get_in(Distance.Inch)
        return w / pow(d, 2) / 7000

    cpdef double standard_cd(self, double mach):
        return calculate_by_curve(self._table_data, self._curve_data, mach)

    cpdef double calculated_cd(self, double mach):
        return self.standard_cd(mach) * self._form_factor

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

    cpdef form_factor(self):
        return self._form_factor

cdef class CurvePoint:
    cdef double _a, _b, _c

    def __init__(self, a: double, b: double, c: double):
        self._a = a
        self._b = b
        self._c = c

    cpdef double a(self):
        return self._a

    cpdef double b(self):
        return self._b

    cpdef double c(self):
        return self._c

cpdef list make_data_points(drag_table: list):
    table: list = []
    cdef data_point
    for point in drag_table:
        data_point = DragDataPoint(point['CD'], point['Mach'])
        table.append(data_point)
    return table

cpdef list calculate_curve(list data_points):
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


cpdef double calculate_by_curve(data: list, curve: list, mach: double):
    cdef int num_points, mlo, mhi, mid

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
    return curve[m].c() + mach * (curve[m].b() + curve[m].a() * mach)
