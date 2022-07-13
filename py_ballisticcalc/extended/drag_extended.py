import math

from ..drag import BallisticCoefficient, DragCalculate, DRAG_TABLES, DragFunction
from ..bmath import unit


class BallisticCoefficientExtended(BallisticCoefficient):

    def __init__(self, value: [float, None], drag_table: int, diameter: unit.Distance, weight: unit.Weight,
                 custom_drag_table: list[dict[str, float]] = None):
        """
        creates ballistic coefficient object using the
        ballistic coefficient value and ballistic table,
        also can use custom drag tables
        :param value:
        :param drag_table: drag_table flag, 0 if custom drag table specified
        :param diameter: unit.Distance instance
        :param weight: unit.Weight instance
        :param custom_drag_table: custom drag table - optional
        """
        self._value = value
        self._table = drag_table

        self._weight = weight
        self._diameter = diameter
        self._sectional_density = self._get_sectional_density()
        self._custom_drag_table = custom_drag_table

        # check for custom drag table
        if self._table != 0 or not custom_drag_table:
            self._error = f"BallisticCoefficient: Unknown custom drag table {drag_table}"

        # init with custom drag table
        else:
            self._form_factor = 0.999  # defined as form factor in lapua-like custom CD data
            self._value = self._get_custom_bc()
            self._drag = DragCalculateExtended.drag_function_factory(drag_table, custom_drag_table)
            self._error = None

        # try to init as standard BallisticCoefficient with standard drag function
        if self._error:
            super(BallisticCoefficientExtended, self).__init__(value, drag_table)
            self._form_factor = self._get_form_factor()
            self._error = None

    def _get_sectional_density(self) -> float:
        """
        :return: sectional density of current bullet with the parameters specified
        """
        w = self._weight.get_in(unit.WeightGrain)
        d = self._diameter.get_in(unit.DistanceInch)
        return w / math.pow(d, 2) / 7000

    def _get_form_factor(self) -> float:
        """
        :return: form factor of a bullet with BC value specified
        """
        return self._sectional_density / self._value

    def _get_custom_bc(self) -> float:
        """
        :return: BC value for current drag function with form factor specified
        """
        return self._sectional_density / self._form_factor

    def standard_cd(self, mach) -> float:
        """
        :param mach: velocity in mach
        :return: cd value of current drag function
        """
        return self._drag(mach)

    def calculated_cd(self, mach) -> float:
        """
        :param mach:
        :return: calculated drag function with form factor specified
        """
        print(mach, self.drag(mach), self._form_factor, self._drag(mach) * self._form_factor)
        return self._drag(mach) * self._form_factor

    def calculated_drag_function(self) -> list[dict[str, float]]:
        """
        Calculates the drag_function with the parameters specified
        :return: calculated_drag_table with the parameters specified
        """

        # uploading specified drag table
        if self._table == 0:
            standard_cd_table = self._custom_drag_table
        else:
            standard_cd_table = DRAG_TABLES[self._table]
        calculated_cd_table = []

        for point in standard_cd_table:
            st_mach, st_cd = point.values()
            cd = self.calculated_cd(st_mach)
            # print(st_mach, cd)
            calculated_cd_table.append({'A': round(st_mach, 4), 'B': cd})

        return calculated_cd_table


class DragCalculateExtended(DragCalculate):

    # @staticmethod
    # def multi_bc_factory(multi_bc):
    #     try:
    #         table = DragCalculateExtended.make_data_points(multi_bc)
    #         curve = DragCalculateExtended.calculate_curve(table)
    #         return lambda velocity: DragCalculate.calculate_by_curve(table, curve, velocity)
    #     except KeyError:
    #         raise ValueError("Unknown drag table type")

    @staticmethod
    def drag_function_factory(drag_table: int, custom_drag_table: list = None) -> [DragFunction, float]:
        try:
            if drag_table == 0:
                table = DragCalculateExtended.make_data_points(custom_drag_table)
            else:
                table = DragCalculateExtended.make_data_points(DRAG_TABLES[drag_table])
            curve = DragCalculateExtended.calculate_curve(table)
            return lambda mach: DragCalculateExtended.calculate_by_curve(table, curve, mach)
        except KeyError:
            raise ValueError("Unknown drag table type")
