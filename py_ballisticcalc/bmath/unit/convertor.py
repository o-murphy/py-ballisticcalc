class Convertor(object):
    """ Basic units class, store units and value """

    __name__ = 'Convertor'

    _units = {}

    def __init__(self, value: float = None, units: int = None):
        """
        Creates a units value, strongly recommended validate it with validate() method
        usage example: Convertor(value, units).validate()
        :param value: units value
        :param units: UnitsConvertor constsS
        """
        v, err = self.to_default(value, units)
        if err:
            self._value = None
            self._default_units = units
        else:
            self._value = v
            self._default_units = units
        self.error = err

    def __str__(self) -> str:
        """
        :return: formatted value in default units
        """
        v, err = self.from_default(self._value, self._default_units)
        if err:
            return f'{self.__name__}: unit {self._default_units} is not supported'
        name, accuracy, f, t = self._units[self._default_units].values()
        return f'{round(v, accuracy)} {name}'

    def to_default(self, value: float, units: int) -> [float, Exception]:
        """
        :param value: value in specified units
        :param units: specified units
        :return: value in default units
        """
        try:
            return self._units[units]['to'](value), None
        except KeyError as error:
            return 0, f'KeyError: {self.__name__}: unit {error} is not supported'

    def from_default(self, value: float, units: int) -> [float, Exception]:
        """
        :param value: value in default units
        :param units: specified units
        :return: value in specified units
        """
        try:
            return self._units[units]['from'](value), None
        except KeyError as error:
            return 0, f'KeyError: {self.__name__}: unit {error} is not supported'

    def validate(self) -> 'Convertor':
        """
        usage example: Convertor(value, units).validate()
        required to use instead of Convertor(value, units) because it raise exception if something went wrong
        :return: the temperature value but panics instead of return error
        """
        err = self.error

        if err:
            err_msg = f'{self.__name__}: unit {self._default_units} is not supported'
            raise ValueError(err_msg)
        return self

    def value(self, units: int) -> [float, Exception]:
        """
        :param units: Units consts
        :return: Value of the unit in the specified units
        """
        return self.from_default(self._value, units)

    def convert(self, units: int) -> 'Convertor':
        """
        Returns the value into the specified units
        :param units: Units consts
        :return: Units object in the specified units
        """
        return self.__class__(self.get_in(units), units)

    def get_in(self, units: int) -> [float, Exception]:
        """
        Converts the value in the specified units.
        Returns 0 if unit conversion is not possible.
        :param units: Units consts
        :return: float
        """
        v, err = self.from_default(self._value, units)
        if err:
            return 0
        return v

    @property
    def v(self):
        """
        Almost useless but can be used for debug
        :return: current value in default units
        """
        return self._value

    @property
    def units(self):
        """
        :return: default units
        """
        return self._default_units
