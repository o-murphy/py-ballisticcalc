import typing
from math import pow

from .unit import *
from .conditions import Atmo
from .drag_model import make_data_points, DragDataPoint


__all__ = ('MultiBC', )


class MultiBC:
    def __init__(self, drag_table: typing.Iterable, diameter: Distance, weight: Weight,
                 multiple_bc_table: typing.Iterable, velocity_units_flag: Unit):

        self.multiple_bc_table = multiple_bc_table
        self.table = drag_table
        self.weight = weight
        self.diameter = diameter
        self.velocity_units = velocity_units_flag
        self.sectional_density = self._get_sectional_density()

        atmosphere = Atmo.ICAO()

        altitude = Distance.Meter(0) >> Distance.Foot
        density, mach = atmosphere.get_density_factor_and_mach_for_altitude(altitude)
        self.speed_of_sound = Velocity.FPS(mach) >> Velocity.MPS

        self._table_data = make_data_points(self.table)
        self._bc_table = self._create_bc_table_data_points()

    def _get_sectional_density(self):
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return w / pow(d, 2) / 7000

    def _get_form_factor(self, bc):
        return self.sectional_density / bc

    def _get_counted_cd(self, form_factor, standard_cd):
        return standard_cd * form_factor

    def _create_bc_table_data_points(self):
        # for bc, v in sorted(self.multiple_bc_table, reverse=True, key=lambda x: x[1]):
        for bc, v in sorted(self.multiple_bc_table, reverse=True, key=lambda x: x.velocity):
            yield DragDataPoint(bc, self.velocity_units(v) >> Velocity.MPS)

    def _interpolate_bc_table(self):
        """
        Extends input bc table by creating bc value for each point of standard Drag Model
        """
        bc_mah = [DragDataPoint(point.coeff, point.velocity / self.speed_of_sound) for point in self._bc_table]
        bc_mah.append(DragDataPoint(bc_mah[-1].coeff, self._table_data[0].velocity))
        bc_mah.insert(0, DragDataPoint(bc_mah[0].coeff, self._table_data[-1].velocity))

        yield bc_mah[0].coeff

        for bc_max, bc_min in zip(bc_mah, bc_mah[1:]):
            df_part = [point for point in self._table_data if bc_max.velocity > point.velocity >= bc_min.velocity]
            ddf = len(df_part)
            bc_delta = (bc_max.coeff - bc_min.coeff) / ddf
            for j in range(ddf):
                yield bc_max.coeff - bc_delta * j

    def cdm_generator(self):
        bc_extended = reversed(list(self._interpolate_bc_table()))
        form_factors = [self._get_form_factor(bc) for bc in bc_extended]

        for i, point in enumerate(self._table_data):
            cd = form_factors[i] * point.coeff
            yield {'Mach': point.velocity, 'CD': cd}
