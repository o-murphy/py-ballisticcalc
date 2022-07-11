VelocityMPS = 60
VelocityKMH = 61
VelocityFPS = 62
VelocityMPH = 63
VelocityKT = 64


cdef class Velocity:
    cdef float _value
    cdef int _default_units
    cdef __name__

    def __init__(self, value: float, units: int):
        self.__name__ = 'Energy'
        self._value = self.to_default(value, units)
        self._default_units = units

    cdef float to_default(self, value: float, units: int):
        if units == VelocityMPS:
            return value
        elif units == VelocityKMH:
            return value / 3.6
        elif units == VelocityFPS:
            return value / 3.2808399
        elif units == VelocityMPH:
            return value / 2.23693629
        elif units == VelocityKT:
            return value / 1.94384449
        else:
            raise KeyError(f'{self.__name__}: unit {units} is not supported')

    cdef float from_default(self, value: float, units: int):
        if units == VelocityMPS:
            return value
        elif units == VelocityKMH:
            return value * 3.6
        elif units == VelocityFPS:
            return value * 3.2808399
        elif units == VelocityMPH:
            return value * 2.23693629
        elif units == VelocityKT:
            return value * 1.94384449
        else:
            raise KeyError(f'KeyError: {self.__name__}: unit {units} is not supported')

    cpdef float value(self, units: int):
        return self.from_default(self._value, units)

    cpdef Velocity convert(self, units: int):
        cdef float value = self.get_in(units)
        return Velocity(value, units)

    cpdef float get_in(self, units: int):
        return self.from_default(self._value, units)

    def __str__(self):
        return self.string()

    cdef string(self):
        cdef name
        cdef int accuracy
        cdef int default = self._default_units
        cdef float v = self.from_default(self._value, default)
        if default == VelocityMPS:
            name = "m/s"
            accuracy = 0
        elif default == VelocityKMH:
            name = "km/h"
            accuracy = 1
        elif default == VelocityFPS:
            name = "ft/s"
            accuracy = 1
        elif default == VelocityMPH:
            name = "mph"
            accuracy = 1
        elif default == VelocityKT:
            name = "kt"
            accuracy = 1
        else:
            name = '?'
            accuracy = 6
        return f'{round(v, accuracy)} {name}'

    cpdef int units(self):
        return self._default_units
