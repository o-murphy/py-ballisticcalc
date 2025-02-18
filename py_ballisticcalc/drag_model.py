"""Drag model of projectile"""

import math
from dataclasses import dataclass, field

from typing_extensions import Union, List, Tuple, Optional

from py_ballisticcalc.constants import cDegreesCtoK, cSpeedOfSoundMetric, cStandardTemperatureC
from py_ballisticcalc.unit import Weight, Distance, Velocity, PreferredUnits
from py_ballisticcalc.drag_tables import DragTablePointDictType


@dataclass
class DragDataPoint:
    """Drag coefficient at Mach number"""
    Mach: float  # Velocity in Mach units
    CD: float  # Drag coefficient


DragTableDataType = Union[List[DragTablePointDictType], List[DragDataPoint]]


@dataclass(order=True)
class BCPoint:
    """For multi-bc drag models, designed to sort by Mach ascending"""

    BC: float = field(compare=False)
    Mach: float = field(compare=True)
    V: Optional[Velocity] = field(compare=False)

    def __init__(self,
                 BC: float,
                 Mach: Optional[float] = None,
                 V: Optional[Union[float, Velocity]] = None):

        if BC <= 0:
            raise ValueError('Ballistic coefficient must be positive')

        if Mach and V:
            raise ValueError("You cannot specify both 'Mach' and 'V' at the same time")

        if not Mach and not V:
            raise ValueError("One of 'Mach' and 'V' must be specified")

        self.BC = BC
        self.V = PreferredUnits.velocity(V or 0)
        if V:
            self.Mach = (self.V >> Velocity.MPS) / self._machC()
        elif Mach:
            self.Mach = Mach

    @staticmethod
    def _machC() -> float:
        """:return: Mach 1 in m/s for Celsius temperature"""
        return math.sqrt(cStandardTemperatureC + cDegreesCtoK) * cSpeedOfSoundMetric


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

    # pylint: disable=too-many-positional-arguments
    def __init__(self, bc: float,
                 drag_table: DragTableDataType,
                 weight: Union[float, Weight] = 0,
                 diameter: Union[float, Distance] = 0,
                 length: Union[float, Distance] = 0):

        if len(drag_table) <= 0:
            # TODO: maybe have to require minimum items count, cause few values don't give a valid result
            raise ValueError('Received empty drag table')
        if bc <= 0:
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


def make_data_points(drag_table: DragTableDataType) -> List[DragDataPoint]:
    """Convert drag table from list of dictionaries to list of DragDataPoints"""
    try:
        return [
            point if isinstance(point, DragDataPoint) else DragDataPoint(point['Mach'], point['CD'])
            for point in drag_table
        ]
    except (KeyError, TypeError) as exc:
        raise TypeError(
            "All items in drag_table must be of type DragDataPoint or dict with 'Mach' and 'CD' keys"
        ) from exc


def sectional_density(weight: float, diameter: float) -> float:
    """
    :param weight: Projectile weight in grains
    :param diameter: Projectile diameter in inches
    :return: Sectional density in lbs/in^2
    """
    return weight / math.pow(diameter, 2) / 7000


def DragModelMultiBC(bc_points: List[BCPoint],
                     drag_table: DragTableDataType,
                     weight: Union[float, Weight] = 0,
                     diameter: Union[float, Distance] = 0,
                     length: Union[float, Distance] = 0) -> DragModel:
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

    bc_points.sort(key=lambda p: p.Mach)  # Make sure bc_points are sorted for linear interpolation
    bc_interp = linear_interpolation([x.Mach for x in drag_table],
                                     [x.Mach for x in bc_points],
                                     [x.BC / bc for x in bc_points])

    for i, point in enumerate(drag_table):
        point.CD = point.CD / bc_interp[i]
    return DragModel(bc, drag_table, weight, diameter, length)


def linear_interpolation(x: Union[List[float], Tuple[float]],
                         xp: Union[List[float], Tuple[float]],
                         yp: Union[List[float], Tuple[float]]) -> Union[List[float], Tuple[float]]:
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


__all__ = ('DragModel', 'DragDataPoint', 'BCPoint', 'DragModelMultiBC')
