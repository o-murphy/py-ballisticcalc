import math

from ..drag import *
from ..bmath import unit


class BallisticCoefficientExtended(object):

    def __init__(self, value: float, drag_table: int, diameter: unit.Distance, weight: unit.Weight,
                 custom_drag_table: list = None):
        # super(BallisticCoefficientExtended, self).__init__(value, drag_table)

        self._error = None

        if drag_table < DragTableG1 or DragTableG1 > DragTableGI:
            self._error = f"BallisticCoefficient: Unknown drag table {drag_table}"

        if value <= 0:
            self._error = 'BallisticCoefficient: Drag coefficient must be greater than zero'

        self._value = value
        self._table = drag_table

        self._weight = weight
        self._diameter = diameter
        self._custom_drag_table = custom_drag_table

        # if not self._error:
        #     self._form_factor = self._get_form_factor()

        if self._error and self._table == 0 and custom_drag_table:
            self._form_factor = 0.999
            self._value = self._get_custom_bc()
            self._drag = DragCalculateExtended.drag_function_factory(drag_table, custom_drag_table)
        else:
            self._form_factor = self._get_form_factor()
            self._drag = DragCalculateExtended.drag_function_factory(drag_table)
            self._error = f"BallisticCoefficient: Unknown drag table {drag_table}"

        # self._multi_bc = [
        #     {'A': 1000, 'B': 0.275},
        #     {'A': 800, 'B': 0.275},
        #     {'A': 700, 'B': 0.27},
        #     {'A': 500, 'B': 0.255},
        #     {'A': 0, 'B': 0.255},
        # ]

        # if not self._error and self._multi_bc:
        #     self._bc_factory = DragCalculateExtended.multi_bc_factory(self._multi_bc)
        # else:
        #     self._bc_factory =

    @property
    def value(self) -> float:
        """
        :return: the ballistic coefficient value
        """
        return self._value

    @property
    def table(self) -> int:
        """
        :return: the name of the ballistic table
        """
        return self._table

    def drag(self, mach) -> float:
        return self._drag(mach) * 2.08551e-04 / self._value

    def _sectional_density(self):
        w = self._weight.get_in(unit.WeightGrain)
        d = self._diameter.get_in(unit.DistanceInch)
        return w / math.pow(d, 2) / 7000

    def _get_form_factor(self):
        return self._sectional_density() / self._value

    def _get_custom_bc(self):
        return self._sectional_density() / self._form_factor

    def standard_cd(self, mach):
        return self._drag(mach)

    def calculated_cd(self, mach):
        return self._drag(mach) * self._form_factor

    # def bc_at_velocity(self, velocity: unit.Velocity):
    #     return self._bc_factory(velocity.get_in(unit.VelocityMPS))
    #
    # def form_factor_at_velocity(self, velocity: unit.Velocity):
    #     bc = self._bc_factory(velocity.get_in(unit.VelocityMPS))
    #     w = self._weight.get_in(unit.WeightGrain)
    #     d = self._diameter.get_in(unit.DistanceInch)
    #     return w / (d ** 2) / 7000 / bc

    def calculated_drag_function(self):
        """
        Calculates the drag_function with the parameters specified
        :param ammunition: Ammunition instance
        :return: calculated_drag_function with the parameters specified
        """

        if self._table == 0:
            standard_cd_table = self._custom_drag_table
        else:
            standard_cd_table = DRAG_TABLES[self._table]
        calculated_cd_table = []

        for point in standard_cd_table:
            st_mach, st_cd = point.values()
            # standard_cd_by_curve = ammunition.bullet.ballistic_coefficient.standard_cd(st_mach)
            cd = self.calculated_cd(st_mach)
            calculated_cd_table.append({'A': round(st_mach, 4), 'B': cd})

        return calculated_cd_table


class DragCalculateExtended(object):

    @staticmethod
    def multi_bc_factory(multi_bc):
        try:
            table = DragCalculateExtended.make_data_points(multi_bc)
            curve = DragCalculateExtended.calculate_curve(table)
            return lambda velocity: DragCalculate.calculate_by_curve(table, curve, velocity)
        except KeyError:
            raise ValueError("Unknown drag table type")

    @staticmethod
    def make_data_points(drag_table) -> list[DataPoint]:
        return [DataPoint(*point.values()) for point in drag_table]

    @staticmethod
    def calculate_curve(data_points: list[DataPoint]) -> list[CurvePoint]:
        rate = (data_points[1].b - data_points[0].b) / (data_points[1].a - data_points[0].a)
        curve = [CurvePoint(0, rate, data_points[0].b - data_points[0].a * rate)]

        """ rest as 2nd degree polynomials on three adjacent points """
        for i in range(1, len(data_points)-1):
            x1 = data_points[i - 1].a
            x2 = data_points[i].a
            x3 = data_points[i + 1].a
            y1 = data_points[i - 1].b
            y2 = data_points[i].b
            y3 = data_points[i + 1].b
            a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                        (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
            b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
            c = y1 - (a * x1 * x1 + b * x1)
            curve.append(CurvePoint(a, b, c))

        num_points = len(data_points)
        rate = (data_points[num_points - 1].b - data_points[num_points - 2].b) / \
               (data_points[num_points - 1].a - data_points[num_points - 2].a)
        curve.append(CurvePoint(0, rate, data_points[num_points - 1].b - data_points[num_points - 2].a * rate))
        return curve


    @staticmethod
    def drag_function_factory(drag_table: int, custom_drag_table: list = None) -> [DragFunction, float]:
        try:
            if drag_table == 0:
                table = DragCalculateExtended.make_data_points(custom_drag_table)
            else:
                table = DragCalculateExtended.make_data_points(DRAG_TABLES[drag_table])
            curve = DragCalculate.calculate_curve(table)
            return lambda mach: DragCalculate.calculate_by_curve(table, curve, mach)
        except KeyError:
            raise ValueError("Unknown drag table type")


    @staticmethod
    def calculate_by_curve(data: list[DataPoint], curve: list[CurvePoint], mach: float) -> float:
        num_points = len(curve)
        mlo = 0
        mhi = num_points - 2

        while mhi - mlo > 1:
            mid = int(math.floor(mhi + mlo) / 2.0)
            if data[mid].a < mach:
                mlo = mid
            else:
                mhi = mid

        if data[mhi].a - mach > mach - data[mlo].a:
            m = mlo
        else:
            m = mhi
        return curve[m].c + mach * (curve[m].b + curve[m].a * mach)
