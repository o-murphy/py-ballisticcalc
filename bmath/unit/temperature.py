from bmath.unit.types import UnitsConvertor, Units


class TemperatureConvertor(UnitsConvertor):
    unit_type = 'temperature'

    # the value indicating that temperature value is expressed in some unit
    TemperatureFahrenheit = 70
    TemperatureCelsius = 71
    TemperatureKelvin = 72
    TemperatureRankin = 73

    _units = {
        TemperatureFahrenheit: {'name': 'm/s', 'accuracy': 1,
                                'to': lambda v: v,
                                'from': lambda v: v},
        TemperatureCelsius: {'name': 'km/h', 'accuracy': 1,
                             'to': lambda v: v - 459.67,
                             'from': lambda v: v + 459.67},
        TemperatureKelvin: {'name': 'ft/s', 'accuracy': 1,
                            'to': lambda v: v * 9 / 5 + 32,
                            'from': lambda v: (v - 32) / 5 / 9},
        TemperatureRankin: {'name': 'mph', 'accuracy': 1,
                            'to': lambda v: (v - 273.15) * 9 / 5 + 32,
                            'from': lambda v: (v - 32) * 5 / 9 + 273.15},
    }


class Temperature(Units):
    """ Temperature object keeps temperature or speed values """
    convertor = TemperatureConvertor

    def __init__(self, value: float, units: int):
        super(Temperature, self).__init__(value, units)
