from ..drag import *
from ..bmath import unit


class BallisticCoefficientExtended(BallisticCoefficient):

    def __init__(self, value: float, drag_table: int, diameter: unit.Distance, weight: unit.Weight):
        super(BallisticCoefficientExtended, self).__init__(value, drag_table)
        self._weight = weight
        self._diameter = diameter
        self._form_factor = self.form_factor()
        # self._multi_bc = [
        #     {'A': 1000, 'B': 0.275},
        #     {'A': 800, 'B': 0.275},
        #     {'A': 700, 'B': 0.27},
        #     {'A': 500, 'B': 0.255},
        #     {'A': 0, 'B': 0.255},
        # ]
        #
        # if not self._error and self._multi_bc:
        #     self._bc_factory = DragCalculateExtended.multi_bc_factory(self._multi_bc)
        # else:
        #     self._bc_factory = None

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

    # def bc_at_velocity(self, velocity: unit.Velocity):
    #     return self._bc_factory(velocity.get_in(unit.VelocityMPS))

    # def form_factor_at_velocity(self, velocity: unit.Velocity):
    #     bc = self._bc_factory(velocity.get_in(unit.VelocityMPS))
    #     w = self._weight.get_in(unit.WeightGrain)
    #     d = self._diameter.get_in(unit.DistanceInch)
    #     return w / (d ** 2) / 7000 / bc

    # def drag_with_bc(self, mach: float, velocity: unit.Velocity):
    #     return self._drag(mach) * 2.08551e-04 / self.bc_at_velocity(velocity)

    # def calculated_cd_at_velocity(self, mach: float, velocity: unit.Velocity):
    #     ff = self.form_factor_at_velocity(velocity)
    #     return self._drag(mach) * ff

    # def calculated_drag_function_with_mbc(self):
    #     standard_cd_table = DRAG_TABLES[self._table]
    #     calculated_cd_table = []
    #
    #     for point in standard_cd_table:
    #         st_mach, st_cd = point.values()
    #         standard_cd_by_curve = ammunition.bullet.ballistic_coefficient.standard_cd(st_mach)
    #         cd = self.calculated_cd_at_velocity(st_mach, unit.Velocity(st_mach * 346, unit.VelocityMPS))
    #         calculated_cd_table.append({'A': round(st_mach, 4), 'B': cd})
    #
    #     return calculated_cd_table

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


class DragCalculateExtended(DragCalculate):

    @staticmethod
    def multi_bc_factory(multi_bc):
        try:
            table = DragCalculateExtended.make_data_points(multi_bc)
            curve = DragCalculateExtended.calculate_curve(table)
            return lambda velocity: DragCalculate.calculate_by_curve(table, curve, velocity)
        except KeyError:
            raise ValueError("Unknown drag table type")
