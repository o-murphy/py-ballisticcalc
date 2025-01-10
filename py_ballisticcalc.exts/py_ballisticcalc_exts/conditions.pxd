from py_ballisticcalc_exts._data_repr cimport _DataRepr

cdef double _WIND_MAX_DISTANCE_FEET


# cdef class Atmo:
#     """Atmospheric conditions and density calculations"""
#     cdef:
#         public object altitude
#         public object pressure
#         public object temperature
#         public float humidity
#
#         public double density_ratio
#         public object mach
#         object _mach1
#         double _a0
#         double _t0
#         double _p0
#         double _ta
#         # struct _calculated


cdef class Wind(_DataRepr):
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


cdef class Shot(_DataRepr):
    """
    Stores shot parameters for the trajectory calculation.

    :param look_angle: Angle of sight line relative to horizontal.
        If the look_angle != 0 then any target in sight crosshairs will be at a different altitude:
            With target_distance = sight distance to a target (i.e., as through a rangefinder):
                * Horizontal distance X to target = cos(look_angle) * target_distance
                * Vertical distance Y to target = sin(look_angle) * target_distance
    :param relative_angle: Elevation adjustment added to weapon.zero_elevation for a particular shot.
    :param cant_angle: Tilt of gun from vertical, which shifts any barrel elevation
        from the vertical plane into the horizontal plane by sine(cant_angle)
    """

    cdef:
        public object look_angle
        public object relative_angle
        public object cant_angle

        public object weapon
        public object ammo
        public object atmo
        list[Wind] _winds


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
