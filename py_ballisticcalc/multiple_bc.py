"""Module to create custom drag function based on Multiple ballistic coefficients"""
import typing
from math import pow as math_pow
from typing import NamedTuple, Iterable

from .conditions import Atmo
# pylint: disable=import-error,no-name-in-module
from .backend import make_data_points
from .settings import Settings as Set
from .unit import Distance, Weight, Velocity

__all__ = ('MultiBC', )


class MultiBCRow(NamedTuple):
    """Multi-BC point, for internal usage"""
    BC: float
    V: Set.Units.velocity


class DragTableRow(NamedTuple):
    """CDM point, for internal usage"""
    CD: float
    Mach: float


class BCMachRow(NamedTuple):
    """BC-Mach point, for internal usage"""
    BC: float
    Mach: float


class MultiBC:  # pylint: disable=too-few-public-methods
    """Creates instance to calculate custom drag tabel based on input multi-bc table"""

    def __init__(self, drag_table: Iterable[dict], diameter: Distance, weight: Weight,
                 mbc_table: Iterable[dict]):

        self.mbc_table = mbc_table
        self.weight = weight
        self.diameter = diameter
        self.sectional_density = self._get_sectional_density()

        atmosphere = Atmo.icao()

        altitude = Distance.Meter(0) >> Distance.Foot
        _, mach = atmosphere.get_density_factor_and_mach_for_altitude(altitude)
        self.speed_of_sound = Velocity.FPS(mach) >> Velocity.MPS

        self._table_data = make_data_points(drag_table)
        self._bc_table = self._parse_mbc(mbc_table)

    def _parse_mbc(self, mbc_table):
        table = []
        for p in mbc_table:
            print(p['V'], Set.Units.velocity)
            print(Set.Units.velocity(p['V']))
            v = Set.Units.velocity(p['V']) >> Velocity.MPS
            mbc = MultiBCRow(p['BC'], v)
            table.append(mbc)
        return sorted(table, reverse=True)

    def _get_sectional_density(self) -> float:
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return w / math_pow(d, 2) / 7000

    def _get_form_factor(self, bc) -> float:
        return self.sectional_density / bc

    @staticmethod
    def _get_counted_cd(form_factor, standard_cd):
        return standard_cd * form_factor

    def _interpolate_bc_table(self) -> typing.Generator:
        """
        Extends input bc table by creating bc value for each point of standard Drag Model
        """
        bc_table = tuple(self._bc_table)
        bc_mah = [BCMachRow(bc_table[0].BC, self._table_data[-1].Mach)]
        bc_mah.extend(
            [BCMachRow(point.BC, point.V / self.speed_of_sound) for point in bc_table]
        )
        bc_mah.append(BCMachRow(bc_mah[-1].BC, self._table_data[0].Mach))

        yield bc_mah[0].BC

        for bc_max, bc_min in zip(bc_mah, bc_mah[1:]):
            df_part = [
                point for point in self._table_data if bc_max.Mach > point.Mach >= bc_min.Mach
            ]
            ddf = len(df_part)
            bc_delta = (bc_max.BC - bc_min.BC) / ddf
            for j in range(ddf):
                yield bc_max.BC - bc_delta * j

    def _cdm_generator(self) -> typing.Generator:
        bc_extended = reversed(list(self._interpolate_bc_table()))
        form_factors = [self._get_form_factor(bc) for bc in bc_extended]

        for i, point in enumerate(self._table_data):
            cd = form_factors[i] * point.CD
            yield {'CD': cd, 'Mach': point.Mach}

    @property
    def cdm(self) -> list[dict]:
        """
        :return: custom drag function based on input multiple ballistic coefficients
        """
        return list(self._cdm_generator())
