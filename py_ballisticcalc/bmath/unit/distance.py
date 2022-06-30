from ..unit.convertor import Convertor

# the value indicating that distance value is expressed in some unit
DistanceInch = 10
DistanceFoot = 11
DistanceYard = 12
DistanceMile = 13
DistanceNauticalMile = 14
DistanceMillimeter = 15
DistanceCentimeter = 16
DistanceMeter = 17
DistanceKilometer = 18
DistanceLine = 19


class Distance(Convertor):
    """ Distance structure keeps the The distance value """

    __name__ = 'Distance'

    _units = {
        DistanceInch: {'name': 'in', 'accuracy': 1,
                       'to': lambda v: v,
                       'from': lambda v: v},
        DistanceFoot: {'name': 'ft', 'accuracy': 2,
                       'to': lambda v: v * 12,
                       'from': lambda v: v / 12},
        DistanceYard: {'name': 'yd', 'accuracy': 3,
                       'to': lambda v: v * 36,
                       'from': lambda v: v / 36},
        DistanceMile: {'name': 'mi', 'accuracy': 3,
                       'to': lambda v: v * 63360,
                       'from': lambda v: v / 63360},
        DistanceNauticalMile: {'name': 'nm', 'accuracy': 3,
                               'to': lambda v: v * 72913.3858,
                               'from': lambda v: v / 72913.3858},
        DistanceLine: {'name': 'ln', 'accuracy': 1,
                       'to': lambda v: v / 10,
                       'from': lambda v: v * 10},
        DistanceMillimeter: {'name': 'mm', 'accuracy': 0,
                             'to': lambda v: v / 25.4,
                             'from': lambda v: v * 25.4},
        DistanceCentimeter: {'name': 'cm', 'accuracy': 1,
                             'to': lambda v: v / 2.54,
                             'from': lambda v: v * 2.54},
        DistanceMeter: {'name': 'm', 'accuracy': 2,
                        'to': lambda v: v / 25.4 * 1000,
                        'from': lambda v: v * 25.4 / 1000},
        DistanceKilometer: {'name': 'km', 'accuracy': 3,
                            'to': lambda v: v / 25.4 * 1000000,
                            'from': lambda v: v * 25.4 / 1000000},
    }
