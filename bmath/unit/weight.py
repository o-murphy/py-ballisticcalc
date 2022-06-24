class WeightUnits:

    _unit_type = 'weight'

    # the value indicating that weight value is expressed in some unit
    WeightGrain = 70
    WeightOunce = 71
    WeightGram = 72
    WeightPound = 73
    WeightKilogram = 74
    WeightNewton = 75

    _units = {
        WeightGrain: {'multiplier': 1, 'name': 'grn', 'accuracy': 0},
        WeightGram: {'multiplier': 15.4323584, 'name': 'grn', 'accuracy': 1},
        WeightKilogram: {'multiplier': 15432.3584, 'name': 'grn', 'accuracy': 3},
        WeightNewton: {'multiplier': 151339.73750336, 'name': 'grn', 'accuracy': 3},
        WeightPound: {'multiplier': 1 / 0.000142857143, 'name': 'grn', 'accuracy': 3},
        WeightOunce: {'multiplier': 437.5, 'name': 'grn', 'accuracy': 1},
    }

    # return the units in which the value is measured
    def __call__(self, units):
        return self._units[units]

    @staticmethod
    def to_default(value: float, units: int) -> [float, Exception]:
        try:
            multiplier = WeightUnits()(units)['multiplier']
            return value * multiplier, None
        except KeyError as error:
            return 0, f'KeyError: {WeightUnits._unit_type}: unit {error} is not supported'

    @staticmethod
    def from_default(value: float, units: int) -> [float, Exception]:
        try:
            multiplier = WeightUnits()(units)['multiplier']
            return value / multiplier, None
        except KeyError as error:
            return 0, f'KeyError: {WeightUnits._unit_type}: unit {error} is not supported'


class Weight(object):
    """ Weight object keeps data about weight """

    def __init__(self, value: float, units: int):
        """
        Creates a weight value
        :param value: weight value
        :param units: WeightUnits.consts
        """
        v, err = WeightUnits.to_default(value, units)
        if err:
            self._value = None
            self._defaultUnits = None
        else:
            self._value = v
            self._default_units = units
        self.error = err

    def __str__(self):
        v, err = WeightUnits.from_default(self.v, self.default_units)
        if err:
            return f'Weight: unit {self.default_units} is not supported'
        multiplier, name, accuracy = WeightUnits()(self.default_units)
        return f'{round(v, accuracy)} {name}'

    @staticmethod
    def must_create(value: float, units: int) -> float:
        """
        Returns the weight value but panics instead of return error
        :param value: weight value
        :param units: WeightUnits.consts
        :return: None
        """
        v, err = WeightUnits.to_default(value, units)
        if err:
            raise ValueError(f'Weight: unit {units} is not supported')
        else:
            return v

    @staticmethod
    def value(w: 'Weight', units: int) -> [float, Exception]:
        """
        :param w: Weight
        :param units: WeightUnits.consts
        :return: Value of the weight in the specified units
        """
        return WeightUnits.from_default(w.v, units)

    @staticmethod
    def convert(weight: 'Weight', units: int) -> 'Weight':
        """
        Returns the value into the specified units
        :param weight: Weight
        :param units: WeightUnits.consts
        :return: Weight object in the specified units
        """
        return Weight(weight.v, units)

    @staticmethod
    def convert_in(weight: 'Weight', units: int) -> [float, Exception]:
        """
        Converts the value in the specified units.
        Returns 0 if unit conversion is not possible.
        :param weight: Weight
        :param units: WeightUnits.consts
        :return: float
        """
        v, err = WeightUnits.from_default(weight.v, units)
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
    #     func (v Weight) WeightUnits() byte {
    #         return v.defaultUnits
    # }


if __name__ == '__main__':

    weight = Weight(90, WeightUnits.WeightGrain)  # 90 grain
    print(weight.v, weight.default_units)
    print(weight)

    weight = Weight(90, 80)  # returns error
