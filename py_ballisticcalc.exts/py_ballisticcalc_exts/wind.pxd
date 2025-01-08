cdef double _WIND_MAX_DISTANCE_FEET

cdef class Wind:
    """
    Wind direction and velocity by down-range distance.
    direction_from = 0 is blowing from behind shooter.
    direction_from = 90 degrees is blowing from shooter's left towards right.
    """

    cdef:
        public object velocity
        public object direction_from
        public object until_distance
        public double MAX_DISTANCE_FEET

# from cython.dataclasses cimport dataclass
# try:
#     import typing
#     import dataclasses
# except ImportError:
#     pass  # The modules don't actually have to exist for Cython to use them as annotations
#
#
# cdef double _MAX_DISTANCE_FEET
#
# @dataclass
# cdef class Wind:
#     """
#     Wind direction and velocity by down-range distance.
#     direction_from = 0 is blowing from behind the shooter.
#     direction_from = 90 degrees is blowing from shooter's left towards right.
#     """
#     cdef public object velocity
#     cdef public object direction_from
#     cdef public object until_distance
#     cdef public double MAX_DISTANCE_FEET
