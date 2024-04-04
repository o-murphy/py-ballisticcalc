"""Drag model of projectile"""

import math
from dataclasses import dataclass, field
from typing import Mapping, Union

from .unit import Weight, Distance, Velocity, PreferredUnits
from .drag_tables import DragTablesSet

__all__ = ('DragModel', 'DragDataPoint', 'BCpoint', 'DragModelMultiBC')

cSpeedOfSoundMetric = 340.0  # Speed of sound in standard atmosphere, in m/s


@dataclass
class DragDataPoint:
    """Drag coefficient at Mach number"""
    Mach: float  # Velocity in Mach units
    CD: float  # Drag coefficient


@dataclass(order=True)
class BCpoint:
    """For multi-bc drag models, designed to sort by Mach ascending"""
    BC: float = field(compare=False)  # Ballistic Coefficient at the given Mach number
    Mach: float = field(default=-1, compare=True)  # Velocity in Mach units
    # Velocity only referenced if Mach number not supplied
    V: Velocity = Dimension(preferred_units='velocity', compare=False)

    def __post_init__(self):
        # If Mach not defined then convert V using standard atmosphere
        if self.Mach < 0:
            self.Mach = (self.V >> Velocity.MPS) / cSpeedOfSoundMetric
        if self.BC <= 0:
            raise ValueError('bc must be positive')


class DragModel:
    """
    :param bc: Ballistic Coefficient of bullet = weight / diameter^2 / i,
            where weight is in pounds, diameter is in inches, and
            i is the bullet's form factor relative to the selected drag model.
    :param drag_table: If passed as List of {Mach, CD} dictionaries, this
            will be converted to a List of DragDataPoints.
    :param weight: Bullet weight in grains
    :param diameter: Bullet diameter in inches
    :param length: Bullet length in inches
    NOTE: .weight, .diameter, .length are only relevant for computing spin drift
    """

    def __init__(self, bc: float,
                 drag_table: list[Mapping[float, float]],
                 weight: [float, Weight] = 0,
                 diameter: [float, Distance] = 0,
                 length: [float, Distance] = 0):
        error = ''
        if len(drag_table) <= 0:
            error = 'Received empty drag table'
        elif bc <= 0:
            error = 'Ballistic coefficient must be positive'
        if error:
            raise ValueError(error)

        self.drag_table = drag_table if isinstance(drag_table[0], DragDataPoint) \
            else make_data_points(drag_table)  # Convert from list of dicts to list of DragDataPoints

        self.BC = bc
        self.length = PreferredUnits.length(length)
        self.weight = PreferredUnits.weight(weight)
        self.diameter = PreferredUnits.diameter(diameter)
        if weight > 0 and diameter > 0:
            self.sectional_density = self._get_sectional_density()
            self.form_factor = self._get_form_factor(self.BC)

    def __repr__(self) -> str:
        return f"DragModel(bc={self.BC}, wgt={self.weight}, dia={self.diameter}, len={self.length})"

    def _get_form_factor(self, bc: float) -> float:
        return self.sectional_density / bc

    def _get_sectional_density(self) -> float:
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return sectional_density(w, d)


def make_data_points(drag_table: list[Mapping[float, float]]) -> list[DragDataPoint]:
    """Convert drag table from list of dictionaries to list of DragDataPoints"""
    return [DragDataPoint(point['Mach'], point['CD']) for point in drag_table]


def sectional_density(weight: float, diameter: float) -> float:
    """
    :param weight: Projectile weight in grains
    :param diameter: Projectile diameter in inches
    :return: Sectional density in lbs/in^2
    """
    return weight / math.pow(diameter, 2) / 7000


def DragModelMultiBC(bc_points: list[BCpoint],
                     drag_table: list[Mapping[float, float]],
                     weight: [float, Weight] = 0,
                     diameter: [float, Distance] = 0,
                     length: [float, Distance] = 0) -> DragModel:
    """
    Compute a drag model based on multiple BCs.
    If weight and diameter are provided then we set bc=sectional density.
    Otherwise, we set bc=1 and the drag_table contains final drag terms.
    :param bc_points:
    :param drag_table: list of dicts containing drag table data
    :param weight: Bullet weight in grains
    :param diameter: Bullet diameter in inches
    :param length: Bullet length in inches
    """
    weight = PreferredUnits.weight(weight)
    diameter = PreferredUnits.diameter(diameter)
    if weight > 0 and diameter > 0:
        BC = sectional_density(weight >> Weight.Grain, diameter >> Distance.Inch)
    else:
        BC = 1.0

    drag_table = drag_table if isinstance(drag_table[0], DragDataPoint) \
        else make_data_points(drag_table)  # Convert from list of dicts to list of DragDataPoints

    bc_points = sorted(bc_points)  # Make sure bc_points are sorted for linear interpolation
    BCinterp = linear_interpolation([x.Mach for x in drag_table],
                                    [x.Mach for x in bc_points],
                                    [x.BC / BC for x in bc_points])
    for i in range(len(drag_table)):
        drag_table[i].CD = drag_table[i].CD / BCinterp[i]
    return DragModel(BC, drag_table, weight, diameter, length)


def linear_interpolation(x: Union[list[float], tuple[float]],
                         xp: Union[list[float], tuple[float]],
                         yp: Union[list[float], tuple[float]]) -> Union[list[float], tuple[float]]:
    """Piecewise linear interpolation
    :param x: List of points for which we want interpolated values
    :param xp: List of existing points (x coordinate), *sorted in ascending order*
    :param yp: List of values for existing points (y coordinate)
    :return: List of interpolated values y for inputs x
    """
    if len(xp) != len(yp):
        raise ValueError("xp and yp lists must have same length")

    y = []

    for xi in x:
        if xi <= xp[0]:
            y.append(yp[0])
        elif xi >= xp[-1]:
            y.append(yp[-1])
        else:
            # Binary search to find interval containing xi
            left, right = 0, len(xp) - 1
            while left < right:
                mid = (left + right) // 2
                if xp[mid] <= xi < xp[mid + 1]:
                    slope = (yp[mid + 1] - yp[mid]) / (xp[mid + 1] - xp[mid])
                    y.append(yp[mid] + slope * (xi - xp[mid]))  # Interpolated value for xi
                    break
                elif xi < xp[mid]:
                    right = mid
                else:
                    left = mid + 1
            if left == right:
                y.append(yp[left])
    return y
