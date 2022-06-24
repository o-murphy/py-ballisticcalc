from bmath.unit.types import UnitsConvertor


class VelocityConvertor(UnitConvertor):
    _unit_type = 'velocity'

    # the value indicating that weight value is expressed in some unit
    VelocityMPS = 70
    VelocityKMH = 71
    VelocityFPS = 72
    VelocityMPH = 73
    VelocityKT = 74

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


class Velocity(object):
    """ Velocity object keeps velocity or speed values """

    def __init__(self, value: float, units: int):
        f"""
        Creates a velocity value
        :param value: velocity value
        :param units: TemperatureUnits.consts
        """
        v, err = VelocityConvertor().to_default(value, units)
        if err:
            self._value = None
            self._defaultUnits = None
        else:
            self._value = v
            self._default_units = units
        self.error = err

    def __str__(self):
        v, err = VelocityConvertor().from_default(self.v, self.default_units)
        if err:
            return f'Velocity: unit {self.default_units} is not supported'
        multiplier, name, accuracy = VelocityConvertor()(self.default_units)
        return f'{round(v, accuracy)} {name}'

    @staticmethod
    def must_create(value: float, units: int) -> float:
        """
        Returns the velocity value but panics instead of return error
        :param value: velocity value
        :param units: TemperatureUnits.consts
        :return: None
        """
        v, err = VelocityConvertor().to_default(value, units)
        if err:
            raise ValueError(f'Velocity: unit {units} is not supported')
        else:
            return v

    @staticmethod
    def value(velocity: 'Velocity', units: int) -> [float, Exception]:
        """
        :param velocity: Velocity
        :param units: TemperatureUnits.consts
        :return: Value of the velocity in the specified units
        """
        return VelocityConvertor().from_default(velocity.v, units)

    @staticmethod
    def convert(velocity: 'Velocity', units: int) -> 'Velocity':
        """
        Returns the value into the specified units
        :param velocity: Velocity
        :param units: TemperatureUnits.consts
        :return: Velocity object in the specified units
        """
        return Velocity(velocity.v, units)

    @staticmethod
    def convert_in(velocity: 'Velocity', units: int) -> [float, Exception]:
        """
        Converts the value in the specified units.
        Returns 0 if unit conversion is not possible.
        :param velocity: Velocity
        :param units: TemperatureUnits.consts
        :return: float
        """
        v, err = VelocityConvertor().from_default(velocity.v, units)
        if err:
            return 0
        return v

    @property
    def v(self):
        return self._value

    @property
    def default_units(self):
        return self._default_units


if __name__ == '__main__':
    pass
