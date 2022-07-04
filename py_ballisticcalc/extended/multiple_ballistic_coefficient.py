from ..bmath import unit
from ..drag import DataPoint, DRAG_TABLES
from ..tools import CramerSpeedOfSound
from ..atmosphere import Atmosphere
import math

# from py_ballisticcalc.bmath import unit
# from py_ballisticcalc.drag import *
# from py_ballisticcalc.tools import CramerSpeedOfSound
# from py_ballisticcalc.atmosphere import Atmosphere


class BCDataPoint(object):
    """ Contains input or calculated bc point data"""
    def __init__(self, bc: float, v: float):
        self.bc = bc
        self.v = v


class MultipleBallisticCoefficient(object):
    """ MultipleBallisticCoefficient object contains multiple bc with specified data """

    def __init__(self, multiple_bc_table: list[(float, float)], velocity_units_flag: int, drag_table: int,
                 diameter: unit.Distance, weight: unit.Weight):

        self._weight = weight
        self._diameter = diameter
        self._units = velocity_units_flag
        self._sectional_density = self._get_sectional_density()

        self.atmosphere = Atmosphere.create_icao(unit.Distance(0, unit.DistanceFoot))

        self._speed_of_sound = CramerSpeedOfSound.at_atmosphere(
            self.atmosphere.temperature.get_in(unit.TemperatureCelsius),
            self.atmosphere.pressure.get_in(unit.PressureMmHg),
            self.atmosphere.humidity * 100
        )

        self._bc_table = []
        multiple_bc_table.sort(reverse=True, key=lambda x: x[1])
        for bc, v in multiple_bc_table:
            data_point = BCDataPoint(bc, unit.Velocity(v, self._units).get_in(unit.VelocityMPS))
            self._bc_table.append(data_point)

        self._df_table = []
        for point in DRAG_TABLES[drag_table]:
            self._df_table.append(DataPoint(*point.values()))

    @property
    def bc_table(self) -> list[tuple]:
        return [(point.bc, point.v) for point in self._bc_table]

    @property
    def weight(self) -> unit.Weight:
        return self._weight

    @property
    def diameter(self) -> unit.Distance:
        return self._diameter

    @property
    def speed_of_sound(self) -> unit.Velocity:
        return unit.Velocity(self._speed_of_sound, unit.VelocityMPS)

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

    def calculate_custom_drag_func(self) -> list[dict[str, float]]:
        bc_extended = self._bc_extended()
        drag_function = []
        for i, point in enumerate(self._df_table):
            bc = bc_extended[len(bc_extended) - 1 - i]
            form_factor = self._get_form_factor(bc)
            cd = self._get_counted_cd(form_factor, point.b)
            drag_function.append({'A': point.a, 'B': cd})
        return drag_function

    def calculate_with_extended_output(self) -> list[dict[str, float]]:
        bc_extended = self._bc_extended()
        drag_function = []
        for i, point in enumerate(self._df_table):
            bc = bc_extended[len(bc_extended) - 1 - i]
            form_factor = self._get_form_factor(bc)
            cd = self._get_counted_cd(form_factor, point.b)
            drag_function.append({'A': point.a, 'B': round(cd, 4), 'bc': round(bc, 4), 'cdst': point.b})
        return drag_function


if __name__ == '__main__':
    pass
    # mbc = MultipleBallisticCoefficient([[0.275, 800], [0.271, 500], [0.27, 700], ],
    #                                    unit.VelocityMPS,
    #                                    DragTableG7,
    #                                    unit.Distance(0.308, unit.DistanceInch),
    #                                    unit.Weight(178, unit.WeightGrain))
    # custom_drag_function = mbc.calculate_with_extended_output()
    # # print('\n'.join([f"{p['B']}\t{p['cdst']}".replace('.', ',') for p in custom_drag_function]))
