cdef class Weapon:
    cdef:
        public object sight_height
        public object twist
        public object zero_elevation
        public object sight

cdef class Ammo:
    cdef:
        public object dm
        public object mv
        public object powder_temp
        public double temp_modifier
        public bint use_powder_sensitivity

    cdef double _calc_powder_sens(Ammo self, object other_velocity, object other_temperature)
    cdef object _get_velocity_for_temp(Ammo self, object current_temp)
