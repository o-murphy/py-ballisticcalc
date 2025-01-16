from py_ballisticcalc_exts.vector cimport CVector
from py_ballisticcalc_exts.munition cimport Weapon, Ammo

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

    cdef CVector c_vector(Wind self)

cdef class Shot:
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

        public Weapon weapon
        public Ammo ammo
        public object atmo
        list[Wind] _winds

    cdef object _barrel_elevation(Shot self)
    cdef object _barrel_azimuth(Shot self)
