from py_ballisticcalc.lib.bmath.unit import *


cdef class WindInfo:
    cdef _until_distance
    cdef _velocity
    cdef _direction

    def __init__(self, until_distance: Distance = None,
                 velocity: Velocity = None, direction: Angular = None):
        self._until_distance = until_distance
        self._velocity = velocity
        self._direction = direction

    def __str__(self):
        return f'Until distance: {self._until_distance}, Velocity: {self._velocity}, Direction: {self._direction}'

    cdef string(self):
        return f'Until distance: {self._until_distance}, Velocity: {self._velocity}, Direction: {self._direction}'

    cpdef until_distance(self):
        return self._until_distance

    cpdef velocity(self):
        return self._velocity

    cpdef direction(self):
        return self._direction

cpdef create_no_wind():
    w = WindInfo()
    return [w]

cpdef create_only_wind_info(wind_velocity: Velocity, direction: Angular):
    cdef until_distance, w
    until_distance = Distance(9999, DistanceKilometer)
    w = [WindInfo(until_distance, wind_velocity, direction)]
    return w

# cpdef add_wind_info(until_distance: Distance,
#                     velocity: Velocity, direction: Angular):
#     return WindInfo(until_distance, velocity, direction)
#
# cdef Wind

def create_wind_info(*winds: 'WindInfo') -> list['WindInfo']:
    return list(winds)
