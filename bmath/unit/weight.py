from bmath.unit.types import UnitsConvertor


class WeightConvertor(UnitsConvertor):
    _unit_type = 'weight'

    # the value indicating that weight value is expressed in some unit
    WeightGrain = 70
    WeightOunce = 71
    WeightGram = 72
    WeightPound = 73
    WeightKilogram = 74
    WeightNewton = 75

    _units = {
        WeightGrain: {'name': 'grn', 'accuracy': 0,
                      'to': lambda v: v,
                      'from': lambda v: v},
        WeightGram: {'name': 'grn', 'accuracy': 1,
                     'to': lambda v: v * 15.4323584,
                     'from': lambda v: v / 15.4323584},
        WeightKilogram: {'name': 'grn', 'accuracy': 3,
                         'to': lambda v: v * 15432.3584,
                         'from': lambda v: v / 15432.3584},
        WeightNewton: {'name': 'grn', 'accuracy': 3,
                       'to': lambda v: v * 151339.73750336,
                       'from': lambda v: v / 151339.73750336},
        WeightPound: {'name': 'grn', 'accuracy': 3,
                      'to': lambda v: v / 0.000142857143,
                      'from': lambda v: v * 0.000142857143},
        WeightOunce: {'name': 'grn', 'accuracy': 1,
                      'to': lambda v: v * 437.5,
                      'from': lambda v: v / 437.5},
    }


class Weight(object):
    """ Weight object keeps data about weight """

    def __init__(self, value: float, units: int):
        """
        Creates a weight value
        :param value: weight value
        :param units: WeightConvertor.consts
        """
        v, err = WeightConvertor().to_default(value, units)
        if err:
            self._value = None
            self._defaultUnits = None
        else:
            self._value = v
            self._default_units = units
        self.error = err

    def __str__(self):
        v, err = WeightConvertor().from_default(self.v, self.default_units)
        if err:
            return f'Weight: unit {self.default_units} is not supported'
        multiplier, name, accuracy = WeightConvertor()(self.default_units)
        return f'{round(v, accuracy)} {name}'

    @staticmethod
    def must_create(value: float, units: int) -> float:
        """
        Returns the weight value but panics instead of return error
        :param value: weight value
        :param units: WeightConvertor.consts
        :return: None
        """
        v, err = WeightConvertor().to_default(value, units)
        if err:
            raise ValueError(f'Weight: unit {units} is not supported')
        else:
            return v

    @staticmethod
    def value(weight: 'Weight', units: int) -> [float, Exception]:
        """
        :param weight: Weight
        :param units: WeightConvertor.consts
        :return: Value of the weight in the specified units
        """
        return WeightConvertor().from_default(weight.v, units)

    @staticmethod
    def convert(weight: 'Weight', units: int) -> 'Weight':
        """
        Returns the value into the specified units
        :param weight: Weight
        :param units: WeightConvertor.consts
        :return: Weight object in the specified units
        """
        return Weight(weight.v, units)

    @staticmethod
    def convert_in(weight: 'Weight', units: int) -> [float, Exception]:
        """
        Converts the value in the specified units.
        Returns 0 if unit conversion is not possible.
        :param weight: Weight
        :param units: WeightConvertor.consts
        :return: float
        """
        v, err = WeightConvertor().from_default(weight.v, units)
        if err:
            return 0
        return v

    @property
    def v(self):
        return self._value

    @property
    def default_units(self):
        return self._default_units

    # not needed yet because of Unit.__call__ method that returns units which the value is measured
    #
    #     func (v Weight) WeightConvertor() byte {
    #         return v.defaultUnits
    # }


if __name__ == '__main__':
    w = Weight(90, WeightConvertor.WeightGrain)  # 90 grain
    print(w.v, w.default_units)
    print(w)

    w = Weight(90, 80)  # returns error
