EnergyFootPound: int = 30
EnergyJoule: int = 31


cdef class Energy:
    cdef double _value
    cdef int _default_units
    cdef __name__

    def __init__(self, value: double, units: int):
        self.__name__ = 'Energy'
        self._value = self.to_default(value, units)
        self._default_units = units

    cdef double to_default(self, value: double, units: int):
        if units == EnergyFootPound:
            return value
        elif units == EnergyJoule:
            return value * 0.737562149277
        else:
            raise KeyError(f'{self.__name__}: unit {units} is not supported')

    cdef double from_default(self, value: double, units: int):
        if units == EnergyFootPound:
            return value
        elif units == EnergyJoule:
            return value / 0.737562149277
        else:
            raise KeyError(f'KeyError: {self.__name__}: unit {units} is not supported')

    cpdef double value(self, units: int):
        return self.from_default(self._value, units)

    cpdef Energy convert(self, units: int):
        cdef double value = self.get_in(units)
        return Energy(value, units)

    cpdef double get_in(self, units: int):
        return self.from_default(self._value, units)

    def __str__(self):
        return self.string()

    cdef string(self):
        cdef name
        cdef int accuracy
        cdef int default = self._default_units
        cdef double v = self.from_default(self._value, default)
        if default == EnergyFootPound:
            name = "ft·lb"
            accuracy = 0
        elif default == EnergyJoule:
            name = "J"
            accuracy = 0
        else:
            name = '?'
            accuracy = 6
        return f'{round(v, accuracy)} {name}'

    cpdef int units(self):
        return self._default_units
