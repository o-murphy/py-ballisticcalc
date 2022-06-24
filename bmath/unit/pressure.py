from bmath.unit.types import UnitsConvertor, Units

# the value indicating that pressure value is expressed in some unit
UniPressureMmHg = 40
UniPressureInHg = 41
UniPressureBar = 42
UniPressureHP = 43
UniPressurePSI = 44


class PressureConvertor(UnitsConvertor):
    unit_type = 'pressure'

    _units = {
        UniPressureMmHg: {'name': 'mmHg', 'accuracy': 0,
                          'to': lambda v: v,
                          'from': lambda v: v},
        UniPressureInHg: {'name': 'inHg', 'accuracy': 2,
                          'to': lambda v: v * 25.4,
                          'from': lambda v: v / 25.4},
        UniPressureBar: {'name': 'bar', 'accuracy': 2,
                         'to': lambda v: v * 750.061683,
                         'from': lambda v: v / 750.061683},
        UniPressureHP: {'name': 'hPa', 'accuracy': 4,
                        'to': lambda v: v * 750.061683 / 1000,
                        'from': lambda v: v / 750.061683 * 1000},
        UniPressurePSI: {'name': 'psi', 'accuracy': 4,
                         'to': lambda v: v * 51.714924102396,
                         'from': lambda v: v / 51.714924102396}
    }


class Pressure(Units):
    """ Pressure object keeps velocity or speed values """
    convertor = PressureConvertor
