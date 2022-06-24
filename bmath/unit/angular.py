from bmath.unit.types import UnitsConvertor, Units


class AngularConvertor(UnitsConvertor):
    unit_type = 'angular'


class Angular(Units):
    """ Angular object keeps information about angular units """
    convertor = AngularConvertor

    def __init__(self, value: float, units: int):
        super(Angular, self).__init__(value, units)
