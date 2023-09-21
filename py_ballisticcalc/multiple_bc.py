from math import pow
from .drag import load_drag_table
from .bmath.unit import *
from .atmosphere import Atmosphere
from drag_tables import DragDataPoint


class MultipleBallisticCoefficient:
    def __init__(self, drag_table: int, diameter: Distance, weight: Weight,
                 multiple_bc_table: list[DragDataPoint], velocity_units_flag: int):

        self.multiple_bc_table = multiple_bc_table
        self.table = drag_table
        self.weight = weight
        self.diameter = diameter
        self.velocity_units = velocity_units_flag
        self.sectional_density = self.get_sectional_density()

        atmosphere = Atmosphere.ICAO()

        altitude = Distance(0, DistanceMeter).get_in(DistanceFoot)
        density, mach = atmosphere.get_density_factor_and_mach_for_altitude(altitude)
        self.speed_of_sound = Velocity(mach, VelocityFPS).get_in(VelocityMPS)

        self.table_data = load_drag_table(self.table)
        self.bc_table = self.create_bc_table_data_points()
        self.custom_drag_table = []

    def get_sectional_density(self):
        w = self.weight.get_in(WeightGrain)
        d = self.diameter.get_in(DistanceInch)
        return w / pow(d, 2) / 7000

    def get_form_factor(self, bc):
        return self.sectional_density / bc

    def bc_extended(self):
        bc_mah = [DragDataPoint(point.coeff, point.velocity / self.speed_of_sound) for point in self.bc_table]
        bc_mah.insert(len(bc_mah), DragDataPoint(bc_mah[-1].coeff, self.table_data[0].a()))
        bc_mah.insert(0, DragDataPoint(bc_mah[0].coeff, self.table_data[-1].a()))
        bc_extended = [bc_mah[0].coeff, ]

        for i in range(1, len(bc_mah)):
            bc_max = bc_mah[i - 1]
            bc_min = bc_mah[i]
            df_part = list(filter(lambda point: bc_max.velocity > point.a() >= bc_min.velocity, self.table_data))
            ddf = len(df_part)
            bc_delta = (bc_max.coeff - bc_min.coeff) / ddf
            for j in range(ddf):
                bc_extended.append(bc_max.coeff - bc_delta * j)

        return bc_extended

    def get_counted_cd(self, form_factor, cdst):
        return cdst * form_factor

    def create_bc_table_data_points(self):
        self.multiple_bc_table.sort(reverse=True, key=lambda x: x[1])
        bc_table = []
        for bc, v in self.multiple_bc_table:
            data_point = DragDataPoint(bc, Velocity(v, self.velocity_units).get_in(VelocityMPS))
            bc_table.append(data_point)
        return bc_table

    def calculate_custom_drag_func(self):

        bc_extended = self.bc_extended()
        drag_function = []
        for i, point in enumerate(self.table_data):
            bc = bc_extended[len(bc_extended) - 1 - i]
            form_factor = self.get_form_factor(bc)
            cd = form_factor * point.b()
            drag_function.append({'Mach': point.a(), 'CD': cd})
        self.custom_drag_table = drag_function

    def custom_drag_func(self):
        self.calculate_custom_drag_func()
        return self.custom_drag_table
