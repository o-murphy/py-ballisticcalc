from libc.math cimport fmod, floor
from .bmath.unit import *

cdef class Timespan:
    cdef double _time

    def __init__(self, time: double):
        self._time = time

    cpdef double total_seconds(self):
        return self._time

    cpdef seconds(self):
        return fmod(floor(self._time), 60)

    cpdef minutes(self):
        return fmod(floor(self._time / 60), 60)

TRAJECTORY = 1
ZERO = 2
MACH1 = 3

cdef class TrajectoryData:
    cdef _time
    cdef _travel_distance
    cdef _velocity
    cdef _angle  # Trajectory angle
    cdef double _mach
    cdef _drop
    cdef _drop_adjustment
    cdef _windage
    cdef _windage_adjustment
    cdef _energy
    cdef _optimal_game_weight
    cdef _row_type

    def __init__(self,
                 time: Timespan,
                 travel_distance: Distance,
                 velocity: Velocity,
                 angle: [Angular, None],
                 mach: double,
                 drop: Distance,
                 drop_adjustment: [Angular, None],
                 windage: Distance,
                 windage_adjustment: [Angular, None],
                 energy: Energy,
                 optimal_game_weight: Weight,
                 row_type: int = TRAJECTORY  #ROW_TYPE = ROW_TYPE.TRAJECTORY
                 ):
        self._time = time
        self._travel_distance = travel_distance
        self._velocity = velocity
        self._angle = angle
        self._mach = mach
        self._drop = drop
        self._drop_adjustment = drop_adjustment
        self._windage = windage
        self._windage_adjustment = windage_adjustment
        self._energy = energy
        self._optimal_game_weight = optimal_game_weight
        self._row_type = row_type

    cpdef row_type(self):
        return self._row_type

    cpdef time(self):
        return self._time

    cpdef travelled_distance(self):
        return self._travel_distance

    cpdef velocity(self):
        return self._velocity

    cpdef angle(self):
        return self._angle

    cpdef double mach_velocity(self):
        return self._mach

    cpdef drop(self):
        return self._drop

    cpdef drop_adjustment(self):
        return self._drop_adjustment

    cpdef windage(self):
        return self._windage

    cpdef windage_adjustment(self):
        return self._windage_adjustment

    cpdef energy(self):
        return self._energy

    def optimal_game_weight(self):
        return self._optimal_game_weight
