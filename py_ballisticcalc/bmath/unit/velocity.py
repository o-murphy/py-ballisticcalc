from ..unit.types import UnitsConvertor, Units

# the value indicating that velocity value is expressed in some unit
VelocityMPS = 60
VelocityKMH = 61
VelocityFPS = 62
VelocityMPH = 63
VelocityKT = 64


class VelocityConvertor(UnitsConvertor):
    unit_type = 'velocity'

    _units = {
        VelocityMPS: {'name': 'm/s', 'accuracy': 0,
                      'to': lambda v: v,
                      'from': lambda v: v},
        VelocityKMH: {'name': 'km/h', 'accuracy': 1,
                      'to': lambda v: v / 3.6,
                      'from': lambda v: v * 3.6},
        VelocityFPS: {'name': 'ft/s', 'accuracy': 1,
                      'to': lambda v: v / 3.2808399,
                      'from': lambda v: v * 3.2808399},
        VelocityMPH: {'name': 'mph', 'accuracy': 1,
                      'to': lambda v: v / 2.23693629,
                      'from': lambda v: v * 2.23693629},
        VelocityKT: {'name': 'kt', 'accuracy': 1,
                     'to': lambda v: v / 1.94384449,
                     'from': lambda v: v * 1.94384449},
    }


class Velocity(Units):
    """ Velocity object keeps velocity or speed values """
    convertor = VelocityConvertor
