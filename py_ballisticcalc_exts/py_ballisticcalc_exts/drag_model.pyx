import typing

from libc.math cimport pow

from py_ballisticcalc.settings import Settings as Set
from py_ballisticcalc.unit import Weight, Distance
from py_ballisticcalc.drag_tables import DragTablesSet

__all__ = ('DragModel', 'make_data_points')

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
        readonly double value, form_factor
        double sectional_density

    def __init__(self, double value,
                 drag_table: typing.Iterable,
                 weight: [float, Weight],
                 diameter: [float, Distance]):
        self.__post__init__(value, drag_table, weight, diameter)

    cdef __post__init__(DragModel self, double value, object drag_table, double weight, double diameter):
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

        self.weight = Set.Units.weight(weight)
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

    @staticmethod
    def from_mbc(mbc: 'MultiBC'):
        return DragModel(1, mbc.cdm, mbc.weight, mbc.diameter)


cpdef list make_data_points(drag_table: typing.Iterable):
    return [DragDataPoint(point['CD'], point['Mach']) for point in drag_table]


cdef double sectional_density(double weight, double diameter):
    return weight / pow(diameter, 2) / 7000
