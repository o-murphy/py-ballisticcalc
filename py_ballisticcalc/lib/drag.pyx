from libc.math cimport floor, pow
from py_ballisticcalc.lib.bmath.unit import *
from py_ballisticcalc.lib.drag_tables import *

DragTableG1: int = 1
DragTableG2: int = 2
DragTableG5: int = 3
DragTableG6: int = 4
DragTableG7: int = 5
DragTableG8: int = 6
DragTableGS: int = 7
DragTableGI: int = 8

cdef class BallisticCoefficient:
    cdef double _value
    cdef int _table
    cdef list _table_data
    cdef list _curve_data
    cdef _weight, _diameter
    cdef double _sectional_density, _form_factor
    cdef list _custom_drag_table

    def __init__(self, value: double, drag_table: int, weight: Weight, diameter: Distance, custom_drag_table: list):

        self._table = drag_table

        self._weight = weight
        self._diameter = diameter
        self._sectional_density = self._get_sectional_density()
        self._custom_drag_table = custom_drag_table

        if self._table == 0 and len(custom_drag_table) > 0:
            self._form_factor = 0.999  # defined as form factor in lapua-like custom CD data
            self._value = self._get_custom_bc()
            self._table_data = make_data_points(self._custom_drag_table)
            self._curve_data = calculate_curve(self._table_data)

        elif drag_table < DragTableG1 or DragTableG1 > DragTableGI:
            raise ValueError(f"BallisticCoefficient: Unknown drag table {drag_table}")
        elif value <= 0:
            raise ValueError('BallisticCoefficient: Drag coefficient must be greater than zero')
        elif self._table == 0 and len(custom_drag_table) == 0:
            raise ValueError('BallisticCoefficient: Custom drag table must be longer than 0')
        else:
            self._value = value
            self._form_factor = self._get_form_factor()
            self._table_data = load_drag_table(self._table)
            self._curve_data = calculate_curve(self._table_data)

    cpdef double drag(self, double mach):
        cdef double cd
        cd = calculate_by_curve(self._table_data, self._curve_data, mach)
        return cd * 2.08551e-04 / self._value

    cpdef double value(self):
        return self._value

    cpdef int table(self):
        return self._table

    cdef double _get_custom_bc(self):
        return self._sectional_density / self._form_factor

    cdef double _get_form_factor(self):
        return self._sectional_density / self._value

    cdef double _get_sectional_density(self):
        cdef double w, d
        w = self._weight.get_in(WeightGrain)
        d = self._diameter.get_in(DistanceInch)
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
            st_mach = point.a()
            st_cd = point.b()
            cd = self.calculated_cd(st_mach)
            calculated_cd_table.append({'A': st_mach, 'B': cd})

        return calculated_cd_table

    cpdef form_factor(self):
        return self._form_factor

cdef class DataPoint:
    cdef double _a, _b

    def __init__(self, a: double, b: double):
        self._a = a
        self._b = b

    cpdef double a(self):
        return self._a

    cpdef double b(self):
        return self._b

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
        data_point = DataPoint(point['A'], point['B'])
        table.append(data_point)
    return table

cpdef list calculate_curve(list data_points):
    cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
    cdef curve = []
    cdef curve_point
    cdef int num_points, len_data_points, len_data_range

    rate = (data_points[1].b() - data_points[0].b()) / (data_points[1].a() - data_points[0].a())
    curve = [CurvePoint(0, rate, data_points[0].b() - data_points[0].a() * rate)]
    len_data_points = int(len(data_points))
    len_data_range = len_data_points - 1

    for i in range(1, len_data_range):
        x1 = data_points[i - 1].a()
        x2 = data_points[i].a()
        x3 = data_points[i + 1].a()
        y1 = data_points[i - 1].b()
        y2 = data_points[i].b()
        y3 = data_points[i + 1].b()
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                    (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_point = CurvePoint(a, b, c)
        curve.append(curve_point)

    num_points = len_data_points
    rate = (data_points[num_points - 1].b() - data_points[num_points - 2].b()) / \
           (data_points[num_points - 1].a() - data_points[num_points - 2].a())
    curve_point = CurvePoint(0, rate, data_points[num_points - 1].b() - data_points[num_points - 2].a() * rate)
    curve.append(curve_point)
    return curve

cpdef list load_drag_table(drag_table: int):
    cdef table

    if drag_table == DragTableG1:
        table = make_data_points(TableG1)
    elif drag_table == DragTableG2:
        table = make_data_points(TableG2)
    elif drag_table == DragTableG5:
        table = make_data_points(TableG5)
    elif drag_table == DragTableG6:
        table = make_data_points(TableG6)
    elif drag_table == DragTableG7:
        table = make_data_points(TableG7)
    elif drag_table == DragTableG8:
        table = make_data_points(TableG8)
    elif drag_table == DragTableGI:
        table = make_data_points(TableGI)
    elif drag_table == DragTableGS:
        table = make_data_points(TableGS)
    else:
        raise ValueError("Unknown drag table type")
    return table

cpdef double calculate_by_curve(data: list, curve: list, mach: double):
    cdef int num_points, mlo, mhi, mid

    num_points = int(len(curve))
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = int(floor(mhi + mlo) / 2.0)
        if data[mid].a() < mach:
            mlo = mid
        else:
            mhi = mid

    if data[mhi].a() - mach > mach - data[mlo].a():
        m = mlo
    else:
        m = mhi
    return curve[m].c() + mach * (curve[m].b() + curve[m].a() * mach)
