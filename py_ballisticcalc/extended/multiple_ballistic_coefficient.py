from ..bmath import unit
from ..drag import DataPoint, DRAG_TABLES
from ..extended.drag_extended import BallisticCoefficientExtended
from ..atmosphere import Atmosphere
import math


class BCDataPoint(object):
    """ Contains input or calculated bc point data"""

    def __init__(self, bc: float, v: float):
        self.bc = bc
        self.v = v


class MultipleBallisticCoefficient(object):
    """ MultipleBallisticCoefficient object contains multiple bc with specified data """

    def __init__(self, multiple_bc_table: list[(float, float)], velocity_units_flag: int, drag_table: int,
                 diameter: unit.Distance, weight: unit.Weight):
        """
        :param multiple_bc_table: list[(bc: float, velocity: float)]
        :param velocity_units_flag: flag of velocity units
        :param drag_table: flag of default drag function
        :param diameter: bullet diameter
        :param weight: bullet weight
        """

        self._weight = weight
        self._diameter = diameter
        self._units = velocity_units_flag
        self._sectional_density = self._get_sectional_density()

        self.atmosphere = Atmosphere.create_icao(unit.Distance(0, unit.DistanceFoot))

        altitude = unit.Distance(0, unit.DistanceMeter).get_in(unit.DistanceFoot)
        density, speed_of_sound = self.atmosphere.get_density_factor_and_mach_for_altitude(altitude)
        self._speed_of_sound = unit.Velocity(speed_of_sound, unit.VelocityFPS).get_in(unit.VelocityMPS)

        self._df_table = self._create_drag_func_data_points(drag_table)
        self._bc_table = self._create_bc_table_data_points(multiple_bc_table)

    @property
    def bc_table(self) -> list[tuple]:
        """
        :return: specified bc table
        """
        return [(point.bc, point.v) for point in self._bc_table]

    @property
    def weight(self) -> unit.Weight:
        """
        :return: bullet weight
        """
        return self._weight

    @property
    def diameter(self) -> unit.Distance:
        """
        :return: bullet diameter
        """
        return self._diameter

    @property
    def speed_of_sound(self) -> unit.Velocity:
        """
        :return: speed of sound with specified atmosphere instance
        """
        return unit.Velocity(self._speed_of_sound, unit.VelocityMPS)

    @staticmethod
    def _create_drag_func_data_points(drag_table) -> list[DataPoint]:
        df_table = []
        for point in DRAG_TABLES[drag_table]:
            df_table.append(DataPoint(*point.values()))
        return df_table

    def _create_bc_table_data_points(self, multiple_bc_table) -> list[BCDataPoint]:
        multiple_bc_table.sort(reverse=True, key=lambda x: x[1])
        bc_table = []
        for bc, v in multiple_bc_table:
            data_point = BCDataPoint(bc, unit.Velocity(v, self._units).get_in(unit.VelocityMPS))
            bc_table.append(data_point)
        return bc_table

    def _get_sectional_density(self) -> float:
        """
        :return: sectional density of current bullet with the parameters specified
        """
        w = self.weight.get_in(unit.WeightGrain)
        d = self.diameter.get_in(unit.DistanceInch)
        return w / math.pow(d, 2) / 7000

    def _get_form_factor(self, bc) -> float:
        """
        :return: form factor of a bullet with BC value specified
        """
        return self._sectional_density / bc

    @staticmethod
    def _get_counted_cd(form_factor, cdst) -> float:
        """
        :param form_factor: form factor of a bullet with BC value specified
        :param cdst: default CD at specified point of drag
        :return: counted CD at specified point of drag and BC value
        """
        return cdst * form_factor

    def _bc_extended(self) -> list[float]:
        """
        linear interpolation of bc table
        :return: interpolated bc table for default drag function length
        """
        bc_mah = [BCDataPoint(point.bc, point.v / self._speed_of_sound) for point in self._bc_table]
        bc_mah[0].v = self._df_table[-1].a
        bc_mah.insert(len(bc_mah), BCDataPoint(bc_mah[-1].bc, self._df_table[0].a))
        bc_extended = [bc_mah[0].bc, ]

        for i in range(1, len(bc_mah)):
            bc_max = bc_mah[i - 1]
            bc_min = bc_mah[i]
            df_part = list(filter(lambda point: bc_max.v > point.a >= bc_min.v, self._df_table))
            ddf = len(df_part)
            bc_delta = (bc_max.bc - bc_min.bc) / ddf
            for j in range(ddf):
                bc_extended.append(bc_max.bc - bc_delta * j)

        return bc_extended

    def calculate_custom_drag_func(self, extended_output: bool = False) -> list[dict[str, float]]:
        """
        :param extended_output: set this flag True if you want include
        bc values for each point of default drag function to output
        :return: custom drag table calculated by multiple bc
        """
        bc_extended = self._bc_extended()
        drag_function = []
        for i, point in enumerate(self._df_table):
            bc = bc_extended[len(bc_extended) - 1 - i]
            form_factor = self._get_form_factor(bc)
            cd = self._get_counted_cd(form_factor, point.b)
            if extended_output:
                drag_function.append({'A': point.a, 'B': round(cd, 4), 'bc': round(bc, 4), 'cdst': point.b})
            else:
                drag_function.append({'A': point.a, 'B': cd})
        return drag_function

    def create_extended_ballistic_coefficient(self):
        custom_df = self.calculate_custom_drag_func()
        bc = BallisticCoefficientExtended(0, 0, self.diameter, self.weight, custom_df)
        return bc
