from py_ballisticcalc.lib.bmath.unit import *
from py_ballisticcalc.lib.atmosphere import Atmosphere
from py_ballisticcalc.lib.projectile import Ammunition

cdef class ZeroInfo:
    cdef _has_ammunition
    cdef _has_atmosphere
    cdef _zero_distance
    cdef _ammunition
    cdef _zero_atmosphere

    def __init__(self, distance: Distance,
                 has_ammunition: bool = False,
                 has_atmosphere: bool = False,
                 ammunition: Ammunition = None, atmosphere: Atmosphere = None):
        self._has_ammunition = has_ammunition
        self._has_atmosphere = has_atmosphere
        self._zero_distance = distance
        self._ammunition = ammunition
        self._zero_atmosphere = atmosphere

    cpdef has_ammunition(self):
        return self._has_ammunition

    cpdef ammunition(self):
        return self._ammunition

    cpdef has_atmosphere(self):
        return self._has_atmosphere

    cpdef atmosphere(self):
        return self._zero_atmosphere

    cpdef zero_distance(self):
        return self._zero_distance

cdef class ZeroInfoDef(ZeroInfo):
    def __init__(self, distance: Distance):
        super(ZeroInfoDef, self).__init__(
            has_ammunition=False,
            has_atmosphere=False,
            distance=distance
        )

cdef class ZeroInfoWithAtmosphere(ZeroInfo):
    def __init__(self, distance: Distance, atmosphere: Atmosphere):
        super(ZeroInfoWithAtmosphere, self).__init__(
            has_ammunition=False,
            has_atmosphere=True,
            distance=distance,
            atmosphere=atmosphere
        )

cdef class ZeroInfoWithAmmo(ZeroInfo):
    def __init__(self, distance: Distance, ammo: Ammunition):
        super(ZeroInfoWithAmmo, self).__init__(
            has_ammunition=True,
            has_atmosphere=False,
            distance=distance,
            ammunition=ammo
        )

cdef class ZeroInfoWithAmmoAndAtmo(ZeroInfo):
    def __init__(self, distance: Distance, ammo: Ammunition, atmosphere: Atmosphere):
        super(ZeroInfoWithAmmoAndAtmo, self).__init__(
            has_ammunition=True,
            has_atmosphere=False,
            distance=distance,
            ammunition=ammo,
            atmosphere=atmosphere
        )

TwistRight: int = 1
TwistLeft: int = 2

cdef class TwistInfo:
    cdef int _twist_direction
    cdef _rifling_twist

    def __init__(self, direction: int, twist: Distance):
        self._twist_direction = direction
        self._rifling_twist = twist

    cpdef direction(self):
        return self._twist_direction

    cpdef twist(self):
        return self._rifling_twist

cdef class Weapon:
    cdef _sight_height
    cdef _zero_info
    cdef _has_twist_info
    cdef _twist
    cdef _click_value

    def __init__(self, sight_height: Distance, zero_info: ZeroInfo,
                 has_twist_info: bool = False, twist: TwistInfo = None, click_value: Angular = None):
        self._sight_height = sight_height
        self._zero_info = zero_info
        self._has_twist_info = has_twist_info
        self._twist = twist
        self._click_value = click_value

    cpdef sight_height(self):
        return self._sight_height

    cpdef zero(self):
        return self._zero_info

    cpdef has_twist(self):
        return self._has_twist_info

    cpdef twist(self):
        return self._twist

    cpdef click_value(self):
        return self._click_value

    cpdef set_click_value(self, click: Angular):
        self._click_value = click

cdef class WeaponWithTwist(Weapon):
    def __init__(self, sight_height: Distance, zero_info: ZeroInfo, twist: TwistInfo):
        super(WeaponWithTwist, self).__init__(sight_height, zero_info, True, twist)
