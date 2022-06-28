try:
    from ..unit.types import UnitsConvertor, Units
except ImportError:
    from py_ballisticcalc.bmath.unit.types import UnitsConvertor, Units

# the value indicating that temperature value is expressed in some unit
TemperatureFahrenheit = 70
TemperatureCelsius = 71
TemperatureKelvin = 72
TemperatureRankin = 73


class TemperatureConvertor(UnitsConvertor):
    unit_type = 'temperature'

    _units = {
        TemperatureFahrenheit: {'name': '°F', 'accuracy': 1,
                                'to': lambda v: v,
                                'from': lambda v: v},
        TemperatureRankin: {'name': '°R', 'accuracy': 1,
                            'to': lambda v: v - 459.67,
                            'from': lambda v: v + 459.67},
        TemperatureCelsius: {'name': '°C', 'accuracy': 1,
                             'to': lambda v: v * 9 / 5 + 32,
                             'from': lambda v: (v - 32) / 5 / 9},
        TemperatureKelvin: {'name': '°K', 'accuracy': 1,
                            'to': lambda v: (v - 273.15) * 9 / 5 + 32,
                            'from': lambda v: (v - 32) * 5 / 9 + 273.15},
    }


class Temperature(Units):
    """ Temperature object keeps temperature or speed values """
    convertor = TemperatureConvertor
