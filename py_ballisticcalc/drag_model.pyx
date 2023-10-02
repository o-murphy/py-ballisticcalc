from libc.math cimport floor, pow
from libc.stdlib cimport malloc, free

from .settings import Settings as Set
from .unit import *
from .drag_tables import DragTablesSet


__all__ = (
    'DragModel',
    # 'make_data_points'
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
        readonly list drag_table
        readonly double value
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
        self.drag_table = drag_table

    cdef double _get_form_factor(self, double bc):
        return self.sectional_density / bc

    cdef double _get_sectional_density(self):
        cdef double w, d
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return sectional_density(w, d)

    # cdef double _standard_cd(self, double mach):
    #     return calculate_by_curve(self.drag_table, self._curve_data, mach)
    #
    # cdef double _calculated_cd(self, double mach):
    #     return self._standard_cd(mach) * self.form_factor
    #
    # cpdef list calculated_drag_function(self):
    #     """
    #     Returns custom drag function based on input bc value
    #     """
    #     cdef:
    #         double cd, st_mach
    #         DragDataPoint point
    #         list calculated_cd_table = []
    #
    #     for point in self.drag_table:
    #         st_mach = point.Mach
    #         cd = self._calculated_cd(st_mach)
    #         calculated_cd_table.append(DragTableRow(cd, st_mach))
    #
    #     return calculated_cd_table

cpdef list make_data_points(drag_table: list):
    return [DragDataPoint(point['CD'], point['Mach']) for point in drag_table]

cdef double sectional_density(double weight, double diameter):
    return weight / pow(diameter, 2) / 7000
