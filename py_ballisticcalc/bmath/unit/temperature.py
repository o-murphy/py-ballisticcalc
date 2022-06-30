from ..unit.convertor import Convertor


# the value indicating that temperature value is expressed in some unit
TemperatureFahrenheit = 50
TemperatureCelsius = 51
TemperatureKelvin = 52
TemperatureRankin = 53


class Temperature(Convertor):
    """ Temperature object keeps temperature or speed values """

    __name__ = 'Temperature'

    _units = {
        TemperatureFahrenheit: {'name': '°F', 'accuracy': 1,
                                'to': lambda v: v,
                                'from': lambda v: v},
        TemperatureRankin: {'name': '°R', 'accuracy': 1,
                            'to': lambda v: v - 459.67,
                            'from': lambda v: v + 459.67},
        TemperatureCelsius: {'name': '°C', 'accuracy': 1,
                             'to': lambda v: v * 9 / 5 + 32,
                             'from': lambda v: (v - 32) * 5 / 9},
        TemperatureKelvin: {'name': '°K', 'accuracy': 1,
                            'to': lambda v: (v - 273.15) * 9 / 5 + 32,
                            'from': lambda v: (v - 32) * 5 / 9 + 273.15},
    }
