from ..drag import *
from ..bmath import unit


class BallisticCoefficientExtended(BallisticCoefficient):

    def __init__(self, value: float, drag_table: int, weight: unit.Weight, diameter: unit.Distance):
        super(BallisticCoefficientExtended, self).__init__(value, drag_table)
        # if not self._error:
        #     self._calculated_cd = DragCalculateExtended.calculated_cd()
        #     self._standard_cd = DragCalculateExtended.
        # else:
        #     self._drag = None
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


class DragCalculateExtended(DragCalculate):
    pass
    # @staticmethod
    # def drag(self, mach) -> float:
    #     return self._drag(mach) * 2.08551e-04 / self._value
    #
    # @staticmethod
    # def form_factor(weight: unit.Weight, diameter: unit.Distance, bc_value: float):
    #     w = weight.get_in(unit.WeightGrain)
    #     d = diameter.get_in(unit.DistanceInch)
    #     return w / (d ** 2) / 7000 / bc_value
    #
    # @staticmethod
    # def standard_cd(self, mach):
    #     return self._drag(mach)
    #
    # @staticmethod
    # def calculated_cd(self, mach, weight: unit.Weight, diameter: unit.Distance, bc_value: float):
    #     form_factor = DragCalculateExtended.form_factor(weight, diameter, bc_value)
    #     return self._drag(mach) * form_factor
