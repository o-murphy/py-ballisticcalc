"""definitions for a bullet's drag model calculation"""

import typing
from dataclasses import dataclass

import math

from .settings import Settings as Set
from .unit import Weight, Distance
from .drag_tables import DragTablesSet

__all__ = ('DragModel', 'make_data_points')


@dataclass
class DragDataPoint:
    CD: float    # Drag coefficient
    Mach: float  # Velocity in Mach units

    def __iter__(self):
        yield self.CD
        yield self.Mach

    def __repr__(self):
        return f"DragDataPoint(CD={self.CD}, Mach={self.Mach})"


class DragModel:
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
    def __init__(self, BC: float,
                 drag_table: typing.Iterable,
                 weight: [float, Weight]=0,
                 diameter: [float, Distance]=0,
                 length: [float, Distance]=0):
        table_len = len(drag_table)
        error = ''
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

    def __repr__(self):
        return f"DragModel(BC={self.BC}, wgt={self.weight}, dia={self.diameter}, len={self.length})"

    def _get_form_factor(self, bc: float):
        return self.sectional_density / bc

    def _get_sectional_density(self) -> float:
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return sectional_density(w, d)

    @staticmethod
    def from_mbc(mbc: 'MultiBC'):
        return DragModel(1, mbc.cdm, mbc.weight, mbc.diameter)


def make_data_points(drag_table: typing.Iterable) -> list:
    return [DragDataPoint(point['CD'], point['Mach']) for point in drag_table]


def sectional_density(weight: float, diameter: float):
    return weight / math.pow(diameter, 2) / 7000
