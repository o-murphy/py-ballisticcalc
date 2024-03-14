import typing

from libc.math cimport pow

from py_ballisticcalc.settings import Settings as Set
from py_ballisticcalc.unit import Weight, Distance
from py_ballisticcalc.drag_tables import DragTablesSet

__all__ = ('DragModel', 'make_data_points')

cdef class DragDataPoint:
    cdef readonly double CD  # Drag coefficient
    cdef readonly Mach       # Velocity in Mach units

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
    """
    :param BC: Ballistic Coefficient of bullet = weight / diameter^2 / i,
        where weight is in pounds, diameter is in inches, and
        i is the bullet's form factor relative to the selected drag model
    :param drag_table: List of {Mach, Cd} pairs defining the standard drag model
    :param weight: Bullet weight in grains
    :param diameter: Bullet diameter in inches
    :param length: Bullet length in inches
    NOTE: .weight, .diameter, .length are only relevant for computing spin drift
    """
    cdef:
        readonly object weight, diameter, length
        readonly list drag_table
        readonly double BC, form_factor
        double sectional_density

    def __init__(self, double BC,
                 drag_table: typing.Iterable,
                 weight: [float, Weight]=0,
                 diameter: [float, Distance]=0,
                 length: [float, Distance]=0):
        self.__post__init__(BC, drag_table, weight, diameter, length)

    cdef __post__init__(DragModel self, double BC, object drag_table, double weight, double diameter, double length):
        cdef:
            double table_len = len(drag_table)
            str error = ''

        if table_len <= 0:
            error = 'Custom drag table must be longer than 0'
        elif BC <= 0:
            error = 'Ballistic coefficient must be greater than zero'

        if error:
            raise ValueError(error)

        if drag_table in DragTablesSet:
            self.BC = BC
        elif table_len > 0:
            self.BC = 1.0
        else:
            raise ValueError('Wrong drag data')

        self.length = Set.Units.length(length)
        self.weight = Set.Units.weight(weight)
        self.diameter = Set.Units.diameter(diameter)
        if weight != 0 and diameter != 0:
            self.sectional_density = self._get_sectional_density()
            self.form_factor = self._get_form_factor(self.BC)
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
