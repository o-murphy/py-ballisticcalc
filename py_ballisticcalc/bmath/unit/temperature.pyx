TemperatureFahrenheit: int = 50
TemperatureCelsius: int = 51
TemperatureKelvin: int = 52
TemperatureRankin: int = 53


cdef class Temperature:
    cdef double _value
    cdef int _default_units
    cdef __name__

    def __init__(self, value: double, units: int):
        self.__name__ = 'Temperature'
        self._value = self.to_default(value, units)
        self._default_units = units

    cdef double to_default(self, value: double, units: int):
            if units == TemperatureFahrenheit:
                return value
            elif units == TemperatureRankin:
                return value - 459.67
            elif units == TemperatureCelsius:
                return value * 9 / 5 + 32
            elif units == TemperatureKelvin:
                return (value - 273.15) * 9 / 5 + 32
            else:
                raise KeyError(f'{self.__name__}: unit {units} is not supported')

    cdef double from_default(self, value: double, units: int):
        if units == TemperatureFahrenheit:
            return value
        elif units == TemperatureRankin:
            return value + 459.67
        elif units == TemperatureCelsius:
            return (value - 32) * 5 / 9
        elif units == TemperatureKelvin:
            return (value - 32) * 5 / 9 + 273.15
        else:
            raise KeyError(f'KeyError: {self.__name__}: unit {units} is not supported')

    cpdef double get_value(self):
        return self.from_default(self._value, self._default_units)

    cpdef double get_in(self, units: int):
        return self.from_default(self._value, units)

    cpdef Temperature convert(self, units: int):
        cdef double value = self.get_in(units)
        return Temperature(value, units)

    def __str__(self):
        return self.string()

    cdef string(self):
        cdef name
        cdef int accuracy
        cdef int default = self._default_units
        cdef double v = self.from_default(self._value, default)
        if default == TemperatureFahrenheit:
            name = '°F'
            accuracy = 1
        elif default == TemperatureRankin:
            name = '°R'
            accuracy = 1
        elif default == TemperatureCelsius:
            name = '°C'
            accuracy = 1
        elif default == TemperatureKelvin:
            name = '°K'
            accuracy = 1
        else:
            name = '?'
            accuracy = 6
        return f'{round(v, accuracy)} {name}'

    cpdef int units(self):
        return self._default_units
