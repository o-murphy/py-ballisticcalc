"""Drag model of projectile"""

import math
import numpy
import typing
from dataclasses import dataclass, field

from .settings import Settings as Set
from .unit import Weight, Distance, Velocity
#from .drag_tables import DragTablesSet

__all__ = ('DragModel', 'DragDataPoint', 'BCpoint')

cSpeedOfSoundMetric = 340.0  # Speed of sound in standard atmosphere, in m/s

@dataclass
class DragDataPoint:
    "Drag coefficient at Mach number"
    Mach: float  # Velocity in Mach units
    CD: float    # Drag coefficient

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

class DragModel:
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

        self.drag_table = drag_table if isinstance(drag_table[0], DragDataPoint)\
            else make_data_points(drag_table) # Convert from list of dicts to list of DragDataPoints

        # BC is a list, so generate new drag table by interpolating the BCpoints
        if isinstance(BC, list):
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

    def __repr__(self) -> str:
        return f"DragModel(BC={self.BC}, wgt={self.weight}, dia={self.diameter}, len={self.length})"

    def _get_form_factor(self, bc: float) -> float:
        return self.sectional_density / bc

    def _get_sectional_density(self) -> float:
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return sectional_density(w, d)


def make_data_points(drag_table: typing.Iterable) -> list[BCpoint]:
    "Convert drag table from list of dictionaries to list of DragDataPoints"
    return [DragDataPoint(point['Mach'], point['CD']) for point in drag_table]


def sectional_density(weight: float, diameter: float) -> float:
    "Sectional density in lbs/in^2"
    return weight / math.pow(diameter, 2) / 7000
