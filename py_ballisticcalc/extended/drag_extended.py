from ..drag import *
from ..bmath import unit


class BallisticCoefficientExtended(BallisticCoefficient):

    def __init__(self, value: float, drag_table: int, diameter: unit.Distance, weight: unit.Weight):
        super(BallisticCoefficientExtended, self).__init__(value, drag_table)
        self._weight = weight
        self._diameter = diameter
        self._form_factor = self.form_factor()

    def drag(self, mach) -> float:
        return self._drag(mach) * 2.08551e-04 / self._value

    def form_factor(self):
        w = self._weight.get_in(unit.WeightGrain)
        d = self._diameter.get_in(unit.DistanceInch)
        return w / (d ** 2) / 7000 / self._value

    # def custom_drag_function_bc(self):
    #     w = self._weight.get_in(unit.WeightGrain)
    #     d = self._diameter.get_in(unit.DistanceInch)
    #     self._value = w / (d ** 2) / 7000

    def standard_cd(self, mach):
        return self._drag(mach)

    def calculated_cd(self, mach):
        return self._drag(mach) * self._form_factor

    def calculated_drag_function(self):
        """
        Calculates the drag_function with the parameters specified
        :param ammunition: Ammunition instance
        :return: calculated_drag_function with the parameters specified
        """

        standard_cd_table = DRAG_TABLES[self._table]
        calculated_cd_table = []

        for point in standard_cd_table:
            st_mach, st_cd = point.values()
            # standard_cd_by_curve = ammunition.bullet.ballistic_coefficient.standard_cd(st_mach)
            cd = self.calculated_cd(st_mach)
            calculated_cd_table.append({'A': round(st_mach, 4), 'B': cd})

        return calculated_cd_table
