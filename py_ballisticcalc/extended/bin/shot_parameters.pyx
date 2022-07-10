from py_ballisticcalc.bmath.cunit import *


cdef class ShotParameters:
    cdef _sight_angle, _shot_angle, _cant_angle, _maximum_distance, _step

    def __init__(self, sight_angle: Angular, maximum_distance: Distance, step: Distance):
        self._sight_angle = sight_angle
        self._shot_angle = Angular(0, AngularRadian)
        self._cant_angle = Angular(0, AngularRadian)
        self._maximum_distance: Distance = maximum_distance
        self._step: Distance = step

    cpdef sight_angle(self):
        return self._sight_angle

    cpdef shot_angle(self):
        return self._shot_angle

    cpdef cant_angle(self):
        return self._cant_angle

    cpdef maximum_distance(self):
        return self._maximum_distance

    cpdef step(self):
        return self._step


cdef class ShotParameterUnlevel(ShotParameters):
    cdef _sight_angle, _shot_angle, _cant_angle, _maximum_distance, _step

    def __init__(self, sight_angle: Angular, maximum_distance: Distance,
                 step: Distance, shot_angle: Angular, cant_angle: Angular):
        super(ShotParameterUnlevel, self).__init__(sight_angle, maximum_distance, step)
        self._sight_angle = sight_angle
        self._shot_angle = shot_angle
        self._cant_angle = cant_angle
        self._maximum_distance: Distance = maximum_distance
        self._step: Distance = step
