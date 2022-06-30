from ..unit.convertor import Convertor

# the value indicating that weight value is expressed in some unit
WeightGrain = 70
WeightOunce = 71
WeightGram = 72
WeightPound = 73
WeightKilogram = 74
WeightNewton = 75

#
# class WeightConvertor(UnitsConvertor):
#     unit_type = 'weight'
#
#     _units = {
#         WeightGrain: {'name': 'grn', 'accuracy': 0,
#                       'to': lambda v: v,
#                       'from': lambda v: v},
#         WeightGram: {'name': 'grn', 'accuracy': 1,
#                      'to': lambda v: v * 15.4323584,
#                      'from': lambda v: v / 15.4323584},
#         WeightKilogram: {'name': 'grn', 'accuracy': 3,
#                          'to': lambda v: v * 15432.3584,
#                          'from': lambda v: v / 15432.3584},
#         WeightNewton: {'name': 'grn', 'accuracy': 3,
#                        'to': lambda v: v * 151339.73750336,
#                        'from': lambda v: v / 151339.73750336},
#         WeightPound: {'name': 'grn', 'accuracy': 3,
#                       'to': lambda v: v / 0.000142857143,
#                       'from': lambda v: v * 0.000142857143},
#         WeightOunce: {'name': 'grn', 'accuracy': 1,
#                       'to': lambda v: v * 437.5,
#                       'from': lambda v: v / 437.5},
#     }


class Weight(Convertor):
    """ Weight object keeps data about weight """
    # convertor = WeightConvertor

    __name__ = 'Weight'

    _units = {
        WeightGrain: {'name': 'grn', 'accuracy': 0,
                      'to': lambda v: v,
                      'from': lambda v: v},
        WeightGram: {'name': 'grn', 'accuracy': 1,
                     'to': lambda v: v * 15.4323584,
                     'from': lambda v: v / 15.4323584},
        WeightKilogram: {'name': 'grn', 'accuracy': 3,
                         'to': lambda v: v * 15432.3584,
                         'from': lambda v: v / 15432.3584},
        WeightNewton: {'name': 'grn', 'accuracy': 3,
                       'to': lambda v: v * 151339.73750336,
                       'from': lambda v: v / 151339.73750336},
        WeightPound: {'name': 'grn', 'accuracy': 3,
                      'to': lambda v: v / 0.000142857143,
                      'from': lambda v: v * 0.000142857143},
        WeightOunce: {'name': 'grn', 'accuracy': 1,
                      'to': lambda v: v * 437.5,
                      'from': lambda v: v / 437.5},
    }

    def __init__(self, value: float, units: int):
        super(Weight, self).__init__(value, units)
