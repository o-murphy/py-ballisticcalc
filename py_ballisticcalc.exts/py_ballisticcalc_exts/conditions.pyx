from libc.math cimport cos, sin
from py_ballisticcalc_exts._data_repr cimport _DataRepr
from py_ballisticcalc.unit import Distance, PreferredUnits, Angular

cdef double _WIND_MAX_DISTANCE_FEET = 1e8


cdef class Wind(_DataRepr):
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
        self.MAX_DISTANCE_FEET = <double> (max_distance_feet or _WIND_MAX_DISTANCE_FEET)
        self.velocity = PreferredUnits.velocity(velocity or 0)
        self.direction_from = PreferredUnits.angular(direction_from or 0)
        self.until_distance = PreferredUnits.distance(until_distance or Distance.Foot(_WIND_MAX_DISTANCE_FEET))


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

    def __cinit__(Shot self,
                  object weapon,
                  object ammo,
                  object look_angle = None,
                  object relative_angle = None,
                  object cant_angle = None,

                  object atmo = None,
                  list[Wind] winds = None
                  ):
        self.look_angle = PreferredUnits.angular(look_angle or 0)
        self.relative_angle = PreferredUnits.angular(relative_angle or 0)
        self.cant_angle = PreferredUnits.angular(cant_angle or 0)
        self.weapon = weapon
        self.ammo = ammo
        from py_ballisticcalc.conditions import Atmo
        self.atmo = atmo or Atmo.icao()
        self._winds = winds or [Wind()]

    @property
    def winds(self) -> tuple[Wind, ...]:
        """Returns sorted Tuple[Wind, ...]"""
        # guarantee that winds returns sorted by Wind.until distance
        return tuple(sorted(self._winds, key=lambda wind: wind.until_distance.raw_value))

    @winds.setter
    def winds(self, list[Wind] winds):
        self._winds = winds or [Wind()]

    @property
    def barrel_elevation(self) -> Angular:
        """Barrel elevation in vertical plane from horizontal"""
        return Angular.Radian((self.look_angle >> Angular.Radian)
                              + cos(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                                 + (self.relative_angle >> Angular.Radian)))

    @property
    def barrel_azimuth(self) -> Angular:
        """Horizontal angle of barrel relative to sight line"""
        return Angular.Radian(sin(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                                 + (self.relative_angle >> Angular.Radian)))

    def __reduce__(self):
        return (self.__class__, (self.weapon,
                                 self.ammo,
                                 self.look_angle,
                                 self.relative_angle,
                                 self.cant_angle,
                                 self.atmo,
                                 self._winds))

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
