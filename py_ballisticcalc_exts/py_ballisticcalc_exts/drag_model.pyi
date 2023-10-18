from .settings import Settings as Set
from .unit import *


__all__ = ('DragDataPoint', 'DragModel', 'make_data_points')


class DragDataPoint:

    def __init__(self, coeff: float, velocity: float):
        self.coeff = coeff
        self.velocity = velocity

    def __iter__(self):
        yield self.coeff
        yield self.velocity


class DragModel:
    table: list
    weight: Weight
    diameter: Distance
    value: float

    def __init__(self, value: float,
                 drag_table: list,
                 weight: [float, Weight],
                 diameter: [float, Distance]):
        pass

    def drag(self, mach: float) -> float:
        pass

    def cdm(self) -> list[dict]:
        pass

    @staticmethod
    def from_mbc(mbc: 'MultiBC') -> DragModel:
        pass



def make_data_points(drag_table: list) -> list:
    ...
