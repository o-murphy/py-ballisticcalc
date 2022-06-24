from bmath.unit.types import UnitsConvertor, Units

# the value indicating that energy value is expressed in some unit
EnergyFootPound = 30
EnergyJoule = 31


class EnergyConvertor(UnitsConvertor):
    unit_type = 'energy'

    _units = {
        EnergyFootPound: {'name': 'ft*lb', 'accuracy': 0,
                          'to': lambda v: v,
                          'from': lambda v: v},
        EnergyJoule: {'name': 'J', 'accuracy': 0,
                      'to': lambda v: v / 0.737562149277,
                      'from': lambda v: v * 0.737562149277}
    }


class Energy(Units):
    """ Energy object keeps information about kinetic energy """
    convertor = EnergyConvertor
