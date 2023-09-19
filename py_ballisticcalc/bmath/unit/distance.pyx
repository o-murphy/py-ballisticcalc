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

cdef class Distance:
    cdef double _value
    cdef int _default_units
    cdef __name__

    def __init__(self, value: double, units: int):
        self.__name__ = 'Distance'
        self._value = self.to_default(value, units)
        self._default_units = units

    cdef double to_default(self, value: double, units: int):
        if units == DistanceInch:
            return value
        elif units == DistanceFoot:
            return value * 12
        elif units == DistanceYard:
            return value * 36
        elif units == DistanceMile:
            return value * 63360
        elif units == DistanceNauticalMile:
            return value * 72913.3858
        elif units == DistanceLine:
            return value / 10
        elif units == DistanceMillimeter:
            return value / 25.4
        elif units == DistanceCentimeter:
            return value / 2.54
        elif units == DistanceMeter:
            return value / 25.4 * 1000
        elif units == DistanceKilometer:
            return value / 25.4 * 1000000
        else:
            raise KeyError(f'{self.__name__}: unit {units} is not supported')

    cdef double from_default(self, value: double, units: int):
        if units == DistanceInch:
            return value
        elif units == DistanceFoot:
            return value / 12
        elif units == DistanceYard:
            return value / 36
        elif units == DistanceMile:
            return value / 63360
        elif units == DistanceNauticalMile:
            return value / 72913.3858
        elif units == DistanceLine:
            return value * 10
        elif units == DistanceMillimeter:
            return value * 25.4
        elif units == DistanceCentimeter:
            return value * 2.54
        elif units == DistanceMeter:
            return value * 25.4 / 1000
        elif units == DistanceKilometer:
            return value * 25.4 / 1000000
        else:
            raise KeyError(f'KeyError: {self.__name__}: unit {units} is not supported')

    cpdef double value(self, units: int = 0):
        if units == 0: units = self._default_units
        return self.from_default(self._value, units)

    cpdef Distance convert(self, units: int):
        cdef double value = self.get_in(units)
        return Distance(value, units)

    cpdef double get_in(self, units: int):
        return self.from_default(self._value, units)

    def __str__(self):
        return self.string()

    cdef string(self):
        cdef name
        cdef int accuracy
        cdef int default = self._default_units
        cdef double v = self.from_default(self._value, default)
        if default == DistanceInch:
            name = 'in'
            accuracy = 1
        elif default == DistanceFoot:
            name = 'ft'
            accuracy = 2
        elif default == DistanceYard:
            name = 'yd'
            accuracy = 3
        elif default == DistanceMile:
            name = 'mi'
            accuracy = 3
        elif default == DistanceNauticalMile:
            name = 'nm'
            accuracy = 3
        elif default == DistanceLine:
            name = 'ln'
            accuracy = 1
        elif default == DistanceMillimeter:
            name = 'mm'
            accuracy = 0
        elif default == DistanceCentimeter:
            name = 'cm'
            accuracy = 1
        elif default == DistanceMeter:
            name = 'm'
            accuracy = 2
        elif default == DistanceKilometer:
            name = 'km'
            accuracy = 3
        else:
            name = '?'
            accuracy = 6

        return f'{round(v, accuracy)} {name}'

    cpdef int units(self):
        return self._default_units
