from bmath.unit.types import UnitsConvertor, Units

# the value indicating that pressure value is expressed in some unit
PressureMmHg = 40
PressureInHg = 41
PressureBar = 42
PressureHP = 43
PressurePSI = 44


class PressureConvertor(UnitsConvertor):
    unit_type = 'pressure'

    _units = {
        PressureMmHg: {'name': 'mmHg', 'accuracy': 0,
                       'to': lambda v: v,
                       'from': lambda v: v},
        PressureInHg: {'name': 'inHg', 'accuracy': 2,
                       'to': lambda v: v * 25.4,
                       'from': lambda v: v / 25.4},
        PressureBar: {'name': 'bar', 'accuracy': 2,
                      'to': lambda v: v * 750.061683,
                      'from': lambda v: v / 750.061683},
        PressureHP: {'name': 'hPa', 'accuracy': 4,
                     'to': lambda v: v * 750.061683 / 1000,
                     'from': lambda v: v / 750.061683 * 1000},
        PressurePSI: {'name': 'psi', 'accuracy': 4,
                      'to': lambda v: v * 51.714924102396,
                      'from': lambda v: v / 51.714924102396}
    }


class Pressure(Units):
    """ Pressure object keeps velocity or speed values """
    convertor = PressureConvertor
