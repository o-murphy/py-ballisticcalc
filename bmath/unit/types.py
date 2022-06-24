class UnitsConvertor(object):
    """ Basic convertor class, needs _units dict """
    unit_type = 'unit'

    _units = {}

    # return the units in which the value is measured
    def __call__(self, units):
        return self._units[units]

    def to_default(self, value: float, units: int) -> [float, Exception]:
        try:
            return self._units[units]['to'](value), None
        except KeyError as error:
            return 0, f'KeyError: {self.unit_type}: unit {error} is not supported'

    def from_default(self, value: float, units: int) -> [float, Exception]:
        try:
            return self._units[units]['from'](value), None
        except KeyError as error:
            return 0, f'KeyError: {self.unit_type}: unit {error} is not supported'


class Units(object):
    """ Basic units class, store units and value """
    convertor = UnitsConvertor

    def __init__(self, value: float = None, units: int = None):
        f"""
        Creates a units value
        :param value: units value
        :param units: UnitsConvertor constsS
        """
        v, err = self.convertor().to_default(value, units)
        if err:
            self._value = None
            self._defaultUnits = units
        else:
            self._value = v
            self._default_units = units
        self.error = err

    def __str__(self):
        v, err = self.convertor().from_default(self.v, self.default_units)
        if err:
            return f'{self.convertor().unit_type}: unit {self.default_units} is not supported'
        multiplier, name, accuracy = self.convertor()(self.default_units)
        return f'{round(v, accuracy)} {name}'

    def must_create(self) -> 'Units':
        """
        Returns the temperature value but panics instead of return error
        :param value: temperature value
        :param units: Unit consts
        :return: None
        """
        err = self.error
        if err:
            raise ValueError(f'{self.convertor.unit_type}: unit {self.default_units} is not supported')
        else:
            return self

    def value(self, value: 'Units', units: int) -> [float, Exception]:
        """
        :param value: Units
        :param units: Units consts
        :return: Value of the unit in the specified units
        """
        return self.convertor().from_default(value.v, units)

    def convert(self, value: 'Units', units: int) -> 'Units':
        """
        Returns the value into the specified units
        :param value: Units
        :param units: Units consts
        :return: Units object in the specified units
        """
        return self.__class__(value.v, units)

    def get_in(self, units: int) -> [float, Exception]:
        """
        Converts the value in the specified units.
        Returns 0 if unit conversion is not possible.
        :param units: Units consts
        :return: float
        """
        v, err = self.convertor().from_default(self.v, units)
        if err:
            return 0
        return v

    @property
    def v(self):
        return self._value

    @property
    def default_units(self):
        return self._default_units
