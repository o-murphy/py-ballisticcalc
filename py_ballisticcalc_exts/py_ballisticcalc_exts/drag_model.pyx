import numpy
import typing
from dataclasses import dataclass, field
from libc.math cimport pow

from py_ballisticcalc.settings import Settings as Set
from py_ballisticcalc.unit import Weight, Distance, Velocity

__all__ = ('DragModel', 'DragDataPoint', 'BCpoint')

cSpeedOfSoundMetric = 340.0  # Speed of sound in standard atmosphere, in m/s

cdef class DragDataPoint:
    cdef readonly double Mach  # Velocity in Mach units
    cdef readonly double CD    # Drag coefficient

    def __cinit__(self, mach: float, cd: float):
        self.Mach = mach
        self.CD = cd

@dataclass(order=True)
class BCpoint:
    "For multi-BC drag models, designed to sort by Mach ascending"
    BC: float = field(compare=False)  # Ballistic Coefficient at the given Mach number
    Mach: float = field(default=-1, compare=True)  # Velocity in Mach units
    # Velocity only referenced if Mach number not supplied
    V: Velocity = field(default_factory=lambda: Set.Units.velocity, compare=False)

    def __post_init__(self):
        # If Mach not defined then convert V using standard atmosphere
        if self.Mach < 0:
            self.Mach = (self.V >> Velocity.MPS) / cSpeedOfSoundMetric
        if self.BC <= 0:
            raise ValueError('BC must be positive')

cdef class DragModel:
    """
    :param BC: Ballistic Coefficient of bullet = weight / diameter^2 / i,
            where weight is in pounds, diameter is in inches, and
            i is the bullet's form factor relative to the selected drag model.
        Or List[BCpoint], and BC will be interpolated and applied to the .drag_table
            (in which case self.BC = 1)
    :param drag_table: If passed as List of {Mach, CD} dictionaries, this
            will be converted to a List of DragDataPoints.
    :param weight: Bullet weight in grains
    :param diameter: Bullet diameter in inches
    :param length: Bullet length in inches
    NOTE: .weight, .diameter, .length are only relevant for computing spin drift
    """
    cdef:
        readonly object weight, diameter, length
        list drag_table
        double BC
        double sectional_density, form_factor

    def __init__(self, BC: [float, list[BCpoint]],
                 drag_table: typing.Iterable,
                 weight: [float, Weight]=0,
                 diameter: [float, Distance]=0,
                 length: [float, Distance]=0):
        error = ''
        if len(drag_table) <= 0:
            error = 'Received empty drag table'
        elif isinstance(BC, float) and (BC <= 0):
            error = 'Ballistic coefficient must be positive'
        if error:
            raise ValueError(error)

        if isinstance(drag_table[0], DragDataPoint):
            self.drag_table = drag_table
        else:  # Convert from list of dicts to list of DragDataPoints
            self.drag_table = make_data_points(drag_table)

        # BC is a list, so generate new drag table by interpolating the BCpoints
        if hasattr(BC, '__getitem__'):
            BC = sorted(BC)  # Make sure we're sorted for np.interp
            self.BCinterp = numpy.interp([x['Mach'] for x in drag_table],
                                         [x.Mach for x in BC],
                                         [x.BC for x in BC])
            for i in range(len(self.drag_table)):
                self.drag_table[i].CD = self.drag_table[i].CD / self.BCinterp[i]
            self.BC = 1.0
        else:
            self.BC = BC

        self.length = Set.Units.length(length)
        self.weight = Set.Units.weight(weight)
        self.diameter = Set.Units.diameter(diameter)
        if weight > 0 and diameter > 0:
            self.sectional_density = self._get_sectional_density()
            self.form_factor = self._get_form_factor(self.BC)

    cdef double _get_form_factor(self, double bc):
        return self.sectional_density / bc

    cdef double _get_sectional_density(self):
        cdef double w, d
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return sectional_density(w, d)


cpdef list make_data_points(drag_table: typing.Iterable):
    "Convert drag table from list of dictionaries to list of DragDataPoints"
    return [DragDataPoint(point['Mach'], point['CD']) for point in drag_table]


cdef double sectional_density(double weight, double diameter):
    "Sectional density in lbs/in^2"
    return weight / pow(diameter, 2) / 7000
