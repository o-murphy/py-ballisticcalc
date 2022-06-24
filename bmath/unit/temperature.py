class TemperatureUnits:

    _unit_type = 'temperature'

    # the value indicating that weight value is expressed in some unit
    TemperatureFahrenheit = 70
    TemperatureCelsius = 71
    TemperatureKelvin = 72
    TemperatureRankin = 73

    _units = {}  # TODO: Need some edits to count this
    #     TemperatureFahrenheit: {'multiplier': 1 / 1, 'name': 'm/s', 'accuracy': 0},
    #     TemperatureCelsius: {'multiplier': 1 / 3.6, 'name': 'km/h', 'accuracy': 0},
    #     TemperatureKelvin: {'multiplier': 1 / 3.2808399, 'name': 'ft/s', 'accuracy': 0},
    #     TemperatureRankin: {'multiplier': 1 / 2.23693629, 'name': 'mph', 'accuracy': 0},

    # return the units in which the value is measured
    def __call__(self, units):
        return self._units[units]

    @staticmethod
    def to_default(value: float, units: int) -> [float, Exception]:
        try:
            multiplier = TemperatureUnits()(units)['multiplier']
            return value * multiplier, None
        except KeyError as error:
            return 0, f'KeyError: {TemperatureUnits._unit_type}: unit {error} is not supported'

    @staticmethod
    def from_default(value: float, units: int) -> [float, Exception]:
        try:
            multiplier = TemperatureUnits()(units)['multiplier']
            return value / multiplier, None
        except KeyError as error:
            return 0, f'KeyError: {TemperatureUnits()._unit_type}: unit {error} is not supported'


class Temperature(object):
    """ Temperature object keeps temperature or speed values """

    def __init__(self, value: float, units: int):
        f"""
        Creates a temperature value
        :param value: temperature value
        :param units: TemperatureUnits.consts
        """
        v, err = TemperatureUnits.to_default(value, units)
        if err:
            self._value = None
            self._defaultUnits = None
        else:
            self._value = v
            self._default_units = units
        self.error = err

    def __str__(self):
        v, err = TemperatureUnits.from_default(self.v, self.default_units)
        if err:
            return f'Temperature: unit {self.default_units} is not supported'
        multiplier, name, accuracy = TemperatureUnits()(self.default_units)
        return f'{round(v, accuracy)} {name}'

    @staticmethod
    def must_create(value: float, units: int) -> float:
        """
        Returns the temperature value but panics instead of return error
        :param value: temperature value
        :param units: TemperatureUnits.consts
        :return: None
        """
        v, err = TemperatureUnits.to_default(value, units)
        if err:
            raise ValueError(f'Temperature: unit {units} is not supported')
        else:
            return v

    @staticmethod
    def value(temperature: 'Temperature', units: int) -> [float, Exception]:
        """
        :param temperature: Temperature
        :param units: TemperatureUnits.consts
        :return: Value of the temperature in the specified units
        """
        return TemperatureUnits.from_default(temperature.v, units)

    @staticmethod
    def convert(temperature: 'Temperature', units: int) -> 'Temperature':
        """
        Returns the value into the specified units
        :param temperature: Temperature
        :param units: TemperatureUnits.consts
        :return: Temperature object in the specified units
        """
        return Temperature(temperature.v, units)

    @staticmethod
    def convert_in(temperature: 'Temperature', units: int) -> [float, Exception]:
        """
        Converts the value in the specified units.
        Returns 0 if unit conversion is not possible.
        :param temperature: Temperature
        :param units: TemperatureUnits.consts
        :return: float
        """
        v, err = TemperatureUnits.from_default(temperature.v, units)
        if err:
            return 0
        return v

    @property
    def v(self):
        return self._value

    @property
    def default_units(self):
        return self._default_units


if __name__ == '__main__':
    pass
