from libc.math cimport fabs

from py_ballisticcalc.unit import PreferredUnits, Unit, Velocity, Temperature

try:
    import typing
    import dataclasses
except ImportError:
    pass  # The modules don't actually have to exist for Cython to use them as annotations


@dataclasses.dataclass
cdef class Weapon:

    def __init__(Weapon self,
                 object sight_height = None,
                 object twist = None,
                 object zero_elevation = None,
                 object sight = None):
        self.sight_height = PreferredUnits.sight_height(sight_height or 0)
        self.twist = PreferredUnits.twist(twist or 0)
        self.zero_elevation = PreferredUnits.angular(zero_elevation or 0)
        self.sight = sight

@dataclasses.dataclass
cdef class Ammo:

    def __init__(self,
                 object dm,
                 object mv,
                 object powder_temp = None,
                 double temp_modifier = 0,
                 bint use_powder_sensitivity = False):
        self.dm = dm
        self.mv = PreferredUnits.velocity(mv or 0)
        self.powder_temp = PreferredUnits.temperature(powder_temp or Temperature(15, Unit.Celsius))
        self.temp_modifier = temp_modifier or 0
        self.use_powder_sensitivity = use_powder_sensitivity

    def calc_powder_sens(Ammo self, object other_velocity, object other_temperature) -> float:
        return self._calc_powder_sens(other_velocity, other_temperature)

    cdef double _calc_powder_sens(Ammo self, object other_velocity, object other_temperature):
        # cdef:
        #     double v0, t0, v1, t0, v_delta, t_delta, v_lower

        v0 = self.mv.get_in(Unit.MPS)
        t0 = self.powder_temp.get_in(Unit.Celsius)
        v1 = PreferredUnits.velocity(other_velocity).get_in(Unit.MPS)
        t1 = PreferredUnits.temperature(other_temperature).get_in(Unit.Celsius)

        v_delta = fabs(v0 - v1)
        t_delta = fabs(t0 - t1)
        v_lower = v1 if v1 < v0 else v0

        if v_delta == 0 or t_delta == 0:
            raise ValueError(
                "Temperature modifier error, other velocity"
                " and temperature can't be same as default"
            )
        self.temp_modifier = v_delta / t_delta * (15 / v_lower)  # * 100
        return self.temp_modifier

    def get_velocity_for_temp(Ammo self, object current_temp) -> Velocity:
        return self._get_velocity_for_temp(current_temp)

    cdef object _get_velocity_for_temp(Ammo self, object current_temp):
        # cdef double v0, t0, t1, t_delta, muzzle_velocity
        try:
            v0 = self.mv.get_in(Unit.MPS)
            t0 = self.powder_temp.get_in(Unit.Celsius)
            t1 = PreferredUnits.temperature(current_temp).get_in(Unit.Celsius)
            t_delta = t1 - t0
            muzzle_velocity = self.temp_modifier / (15 / v0) * t_delta + v0
        except ZeroDivisionError:
            muzzle_velocity = 0
        return Velocity(muzzle_velocity, Unit.MPS)