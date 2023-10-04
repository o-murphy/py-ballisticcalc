from typing import NamedTuple, Iterable
from math import pow as math_pow

from .unit import Distance, Weight, Velocity, Unit
from .conditions import Atmo
from .drag_model import make_data_points


__all__ = ('MultiBC', 'DragTableRow', 'MultiBCRow')


class DragTableRow(NamedTuple):
    CD: float
    Mach: float


class MultiBCRow(NamedTuple):
    BC: float
    Velocity: float


class BCMachRow(NamedTuple):
    BC: float
    Mach: float


class MultiBC:
    def __init__(self, drag_table: Iterable, diameter: Distance, weight: Weight,
                 multiple_bc_table: Iterable[MultiBCRow], velocity_units_flag: Unit):

        self.multiple_bc_table = multiple_bc_table
        self.table = drag_table
        self.weight = weight
        self.diameter = diameter
        self.velocity_units = velocity_units_flag
        self.sectional_density = self._get_sectional_density()

        atmosphere = Atmo.icao()

        altitude = Distance.Meter(0) >> Distance.Foot
        density, mach = atmosphere.get_density_factor_and_mach_for_altitude(altitude)
        self.speed_of_sound = Velocity.FPS(mach) >> Velocity.MPS

        self._table_data = make_data_points(self.table)
        self._bc_table = self._create_bc_table_data_points()

    def _get_sectional_density(self):
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return w / math_pow(d, 2) / 7000

    def _get_form_factor(self, bc):
        return self.sectional_density / bc

    @staticmethod
    def _get_counted_cd(form_factor, standard_cd):
        return standard_cd * form_factor

    def _create_bc_table_data_points(self):
        for bc, v in sorted(self.multiple_bc_table, reverse=True, key=lambda x: x.Velocity):
            yield MultiBCRow(bc, self.velocity_units(v) >> Velocity.MPS)

    def _interpolate_bc_table(self):
        """
        Extends input bc table by creating bc value for each point of standard Drag Model
        """
        bc_table = tuple(self._bc_table)
        bc_mah = [BCMachRow(bc_table[0].BC, self._table_data[-1].Mach)]
        bc_mah.extend(
            [BCMachRow(point.BC, point.Velocity / self.speed_of_sound) for point in bc_table]
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

    def cdm_generator(self):
        bc_extended = reversed(list(self._interpolate_bc_table()))
        form_factors = [self._get_form_factor(bc) for bc in bc_extended]

        for i, point in enumerate(self._table_data):
            cd = form_factors[i] * point.CD
            yield {'CD': cd, 'Mach': point.Mach}
