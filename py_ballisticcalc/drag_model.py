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

    CD: float
    Mach: float

    def __iter__(self):
        yield self.CD
        yield self.Mach

    def __repr__(self):
        return f"DragDataPoint(CD={self.CD}, Mach={self.Mach})"


class DragModel:

    def __init__(self, value: float,
                 drag_table: typing.Iterable,
                 weight: [float, Weight],
                 diameter: [float, Distance]):
        self.__post__init__(value, drag_table, weight, diameter)

    def __post__init__(self, value: float, drag_table, weight, diameter):
        table_len = len(drag_table)
        error = ''

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
