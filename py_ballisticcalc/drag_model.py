"""Drag model of projectile"""

import math
from dataclasses import dataclass, field
from typing import Union

from .unit import Weight, Distance, Velocity, PreferredUnits, Dimension

__all__ = ('DragModel', 'DragDataPoint', 'BCPoint', 'DragModelMultiBC')

cSpeedOfSoundMetric = 340.0  # Speed of sound in standard atmosphere, in m/s


@dataclass
class DragDataPoint:
    """Drag coefficient at Mach number"""
    Mach: float  # Velocity in Mach units
    CD: float  # Drag coefficient


@dataclass(order=True)
class BCPoint:
    """For multi-bc drag models, designed to sort by Mach ascending"""
    BC: float = field(compare=False)  # Ballistic Coefficient at the given Mach number
    Mach: float = field(default=-1, compare=True)  # Velocity in Mach units
    # Velocity only referenced if Mach number not supplied
    V: Velocity = Dimension(prefer_units='velocity', compare=False)

    def __post_init__(self):
        # If Mach not defined then convert V using standard atmosphere
        if self.Mach < 0:
            self.Mach = (self.V >> Velocity.MPS) / cSpeedOfSoundMetric
        if self.BC <= 0:
            raise ValueError('Ballistic coefficient must be positive')


DragTableDataType = [list[dict[str, float]], list[DragDataPoint]]


class DragModel:
    """
    :param bc: Ballistic Coefficient of bullet = weight / diameter^2 / i,
            where weight is in pounds, diameter is in inches, and
            is the bullet's form factor relative to the selected drag model.
    :param drag_table: If passed as List of {Mach, CD} dictionaries, this
            will be converted to a List of DragDataPoints.
    :param weight: Bullet weight in grains
    :param diameter: Bullet diameter in inches
    :param length: Bullet length in inches
    NOTE: .weight, .diameter, .length are only relevant for computing spin drift
    """

    def __init__(self, bc: float,
                 drag_table: DragTableDataType,
                 weight: [float, Weight] = 0,
                 diameter: [float, Distance] = 0,
                 length: [float, Distance] = 0):

        if len(drag_table) <= 0:
            # TODO: maybe have to require minimum size, cause few values don't give a valid result
            raise ValueError('Received empty drag table')
        elif bc <= 0:
            raise ValueError('Ballistic coefficient must be positive')

        self.drag_table = make_data_points(drag_table)

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


def make_data_points(drag_table: DragTableDataType) -> list[DragDataPoint]:
    """Convert drag table from list of dictionaries to list of DragDataPoints"""
    if isinstance(drag_table[0], DragDataPoint):
        return drag_table
    return [DragDataPoint(point['Mach'], point['CD']) for point in drag_table]


def sectional_density(weight: float, diameter: float) -> float:
    """
    :param weight: Projectile weight in grains
    :param diameter: Projectile diameter in inches
    :return: Sectional density in lbs/in^2
    """
    return weight / math.pow(diameter, 2) / 7000


def DragModelMultiBC(bc_points: list[BCPoint],
                     drag_table: DragTableDataType,
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
        bc = sectional_density(weight >> Weight.Grain, diameter >> Distance.Inch)
    else:
        bc = 1.0

    drag_table = make_data_points(drag_table)  # Convert from list of dicts to list of DragDataPoints

    bc_points.sort()  # Make sure bc_points are sorted for linear interpolation
    bc_interp = linear_interpolation([x.Mach for x in drag_table],
                                     [x.Mach for x in bc_points],
                                     [x.BC / bc for x in bc_points])

    for i, point in enumerate(drag_table):
        point.CD = point.CD / bc_interp[i]
    return DragModel(bc, drag_table, weight, diameter, length)


def linear_interpolation(x: Union[list[float], tuple[float]],
                         xp: Union[list[float], tuple[float]],
                         yp: Union[list[float], tuple[float]]) -> Union[list[float], tuple[float]]:
    """Piecewise linear interpolation
    :param x: List of points for which we want interpolated values
    :param xp: List of existing points (x coordinate), *sorted in ascending order*
    :param yp: List of values for existing points (y coordinate)
    :return: List of interpolated values y for inputs x
    """
    assert len(xp) == len(yp), "xp and yp lists must have same length"

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
                if xi < xp[mid]:
                    right = mid
                else:
                    left = mid + 1
            if left == right:
                y.append(yp[left])
    return y
