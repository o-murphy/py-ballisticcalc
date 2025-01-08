from py_ballisticcalc.unit import Distance, PreferredUnits

cdef double _WIND_MAX_DISTANCE_FEET = 1e8

cdef class Wind:
    """
    Wind direction and velocity by down-range distance.
    direction_from = 0 is blowing from behind shooter.
    direction_from = 90 degrees is blowing from shooter's left towards right.
    """

    def __cinit__(Wind self,
                  object velocity = None,
                  object direction_from = None,
                  object until_distance = None,
                  *,
                  double max_distance_feet = _WIND_MAX_DISTANCE_FEET):
        self.MAX_DISTANCE_FEET = <double>(max_distance_feet or _WIND_MAX_DISTANCE_FEET)
        self.velocity = PreferredUnits.velocity(velocity or 0)
        self.direction_from = PreferredUnits.angular(direction_from or 0)
        self.until_distance = PreferredUnits.distance(until_distance or Distance.Foot(_WIND_MAX_DISTANCE_FEET))


# cimport cython
# from cython.dataclasses cimport dataclass, field
# try:
#     import typing
#     import dataclasses
# except ImportError:
#     pass  # The modules don't actually have to exist for Cython to use them as annotations
#
# from py_ballisticcalc.unit import Distance, PreferredUnits
#
# cdef double _MAX_DISTANCE_FEET = 1e8
#
# @dataclass
# cdef class Wind:
#     """
#     Wind direction and velocity by down-range distance.
#     direction_from = 0 is blowing from behind the shooter.
#     direction_from = 90 degrees is blowing from shooter's left towards right.
#     """
#     # Using Cython types for variables where possible
#     velocity: object = field(default=None)
#     direction_from: object = field(default=0)
#     until_distance: object = field(default=Distance.Foot(_MAX_DISTANCE_FEET))
#
#     # Defining the constant field with a Cython type
#     MAX_DISTANCE_FEET: cython.double = _MAX_DISTANCE_FEET
#
#     # Initialization
#     def __init__(self,
#                  object velocity = None,
#                  object direction_from = None,
#                  object until_distance = None,
#                  *,
#                  double max_distance_feet = _MAX_DISTANCE_FEET):
#         self.MAX_DISTANCE_FEET = <double> (max_distance_feet or _MAX_DISTANCE_FEET)
#         self.velocity = PreferredUnits.velocity(velocity or 0)
#         self.direction_from = PreferredUnits.angular(direction_from or 0)
#         self.until_distance = PreferredUnits.distance(until_distance or Distance.Foot(self.MAX_DISTANCE_FEET))
