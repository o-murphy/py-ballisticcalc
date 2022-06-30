from ..unit.convertor import Convertor

# the value indicating that energy value is expressed in some unit
EnergyFootPound = 30
EnergyJoule = 31


class Energy(Convertor):
    """ Energy object keeps information about kinetic energy """

    __name__ = 'Energy'

    _units = {
        EnergyFootPound: {'name': 'ft*lb', 'accuracy': 0,
                          'to': lambda v: v,
                          'from': lambda v: v},
        EnergyJoule: {'name': 'J', 'accuracy': 0,
                      'to': lambda v: v * 0.737562149277,
                      'from': lambda v: v / 0.737562149277}
    }
