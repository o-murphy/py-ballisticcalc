PressureMmHg = 40
PressureInHg = 41
PressureBar = 42
PressureHP = 43
PressurePSI = 44


cdef class Pressure:
    cdef double _value
    cdef int _default_units
    cdef __name__

    def __init__(self, value: double, units: int):
        self.__name__ = 'Pressure'
        self._value = self.to_default(value, units)
        self._default_units = units

    cdef double to_default(self, value: double, units: int):
            if units == PressureMmHg:
                return value
            elif units == PressureInHg:
                return value * 25.4
            elif units == PressureBar:
                return value * 750.061683
            elif units == PressureHP:
                return value * 750.061683 / 1000
            elif units == PressurePSI:
                return value * 51.714924102396
            else:
                raise KeyError(f'{self.__name__}: unit {units} is not supported')

    cdef double from_default(self, value: double, units: int):
        if units == PressureMmHg:
            return value
        elif units == PressureInHg:
            return value / 25.4
        elif units == PressureBar:
            return value / 750.061683
        elif units == PressureHP:
            return value / 750.061683 * 1000
        elif units == PressurePSI:
            return value / 51.714924102396
        else:
            raise KeyError(f'KeyError: {self.__name__}: unit {units} is not supported')

    cpdef double get_value(self):
        return self.from_default(self._value, self._default_units)

    cpdef double get_in(self, units: int):
        return self.from_default(self._value, units)

    cpdef Pressure convert(self, units: int):
        cdef double value = self.get_in(units)
        return Pressure(value, units)

    def __str__(self):
        return self.string()

    cdef string(self):
        cdef name
        cdef int accuracy
        cdef int default = self._default_units
        cdef double v = self.from_default(self._value, default)
        if default == PressureMmHg:
            name = 'mmHg'
            accuracy = 0
        elif default == PressureMmHg:
            name = 'inHg'
            accuracy = 2
        elif default == PressureBar:
            name = 'bar'
            accuracy = 2
        elif default == PressureHP:
            name = 'hPa'
            accuracy = 4
        elif default == PressurePSI:
            name = 'psi'
            accuracy = 4
        else:
            name = '?'
            accuracy = 6

        return f'{round(v, accuracy)} {name}'

    cpdef int units(self):
        return self._default_units
