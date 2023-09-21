from libc.math cimport pi, atan, tan

AngularRadian = 0
AngularDegree = 1
AngularMOA = 2
AngularMil = 3
AngularMRad = 4
AngularThousand = 5
AngularInchesPer100Yd = 6
AngularCmPer100M = 7

cdef class Angular:
    cdef double _value
    cdef int _default_units
    cdef __name__

    def __init__(self, value: double, units: int):
        self.__name__ = 'Angular'
        self._value = self.to_default(value, units)
        self._default_units = units

    cdef double to_default(self, value: double, units: int):
        if units == AngularRadian:
            return value
        elif units == AngularDegree:
            return value / 180 * pi
        elif units == AngularMOA:
            return value / 180 * pi / 60
        elif units == AngularMil:
            return value / 3200 * pi
        elif units == AngularMRad:
            return value / 1000
        elif units == AngularThousand:
            return value / 3000 * pi
        elif units == AngularInchesPer100Yd:
            return atan(value / 3600)
        elif units == AngularCmPer100M:
            return atan(value / 10000)
        else:
            raise KeyError(f'{self.__name__}: unit {units} is not supported')

    cdef double from_default(self, value: double, units: int):
        if units == AngularRadian:
            return value
        elif units == AngularDegree:
            return value * 180 / pi
        elif units == AngularMOA:
            return value * 180 / pi * 60
        elif units == AngularMil:
            return value * 3200 / pi
        elif units == AngularMRad:
            return value * 1000
        elif units == AngularThousand:
            return value * 3000 / pi
        elif units == AngularInchesPer100Yd:
            return tan(value) * 3600
        elif units == AngularCmPer100M:
            return tan(value) * 10000
        else:
            raise KeyError(f'KeyError: {self.__name__}: unit {units} is not supported')

    cpdef double value(self):
        return self._value

    cpdef Angular convert(self, units: int):
        cdef double value = self.get_in(units)
        return Angular(value, units)

    cpdef double get_in(self, units: int):
        return self.from_default(self._value, units)

    def __str__(self):
        return self.string()

    cdef string(self):
        cdef name
        cdef int accuracy
        cdef int default = self._default_units
        cdef double v = self.from_default(self._value, default)
        if default == AngularRadian:
            name = 'rad'
            accuracy = 6
        elif default == AngularDegree:
            name = '°'
            accuracy = 4
        elif default == AngularMOA:
            name = 'moa'
            accuracy = 2
        elif default == AngularMil:
            name = 'mil'
            accuracy = 2
        elif default == AngularMRad:
            name = 'mrad'
            accuracy = 2
        elif default == AngularThousand:
            name = 'ths'
            accuracy = 2
        elif default == AngularInchesPer100Yd:
            name = 'in/100yd'
            accuracy = 2
        elif default == AngularCmPer100M:
            name = 'cm/100m'
            accuracy = 2
        else:
            name = '?'
            accuracy = 6

        return f'{round(v, accuracy)} {name}'

    cpdef int units(self):
        return self._default_units
