from bmath.unit.types import UnitsConvertor, Units


class EnergyConvertor(UnitsConvertor):
    unit_type = 'energy'

    EnergyFootPound = 30
    EnergyJoule = 31

    _units = {
        EnergyFootPound: {'name': 'mmHg', 'accuracy': 0,
                          'to': lambda v: v,
                          'from': lambda v: v},
        EnergyJoule: {'name': 'mmHg', 'accuracy': 0,
                      'to': lambda v: v / 0.737562149277,
                      'from': lambda v: v * 0.737562149277}
    }


class Energy(Units):
    """ Energy object keeps information about kinetic energy """
    convertor = EnergyConvertor

    def __init__(self, value: float, units: int):
        super(Energy, self).__init__(value, units)
