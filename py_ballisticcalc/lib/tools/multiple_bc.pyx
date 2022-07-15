from py_ballisticcalc.lib.drag import load_drag_table
from py_ballisticcalc.lib.bmath.unit import *
from py_ballisticcalc.lib.atmosphere import IcaoAtmosphere
from libc.math cimport pow

cdef class BCDataPoint:
    cdef double _bc
    cdef double _v

    def __init__(self, bc: double, v: double):
        self._bc = bc
        self._v = v

    cpdef double bc(self):
        return self._bc

    cpdef double v(self):
        return self._v

    cpdef set_v(self, float value):
        self._v = value


cdef class MultipleBallisticCoefficient:
    cdef list _custom_drag_table, _table_data, _bc_table, _multiple_bc_table
    cdef double _sectional_density, _speed_of_sound
    cdef int _units, _table
    cdef _weight, _diameter

    def __init__(self, drag_table: int, diameter: Distance, weight: Weight,
                 multiple_bc_table: list[(double, double)], velocity_units_flag: int):

        cdef double altitude, density, mach
        cdef _atmosphere

        self._multiple_bc_table = multiple_bc_table
        self._table = drag_table
        self._weight = weight
        self._diameter = diameter
        self._units = velocity_units_flag
        self._sectional_density = self._get_sectional_density()

        _atmosphere = IcaoAtmosphere(Distance(0, DistanceFoot))

        altitude = Distance(0, DistanceMeter).get_in(DistanceFoot)
        density, mach = _atmosphere.get_density_factor_and_mach_for_altitude(altitude)
        self._speed_of_sound = Velocity(mach, VelocityFPS).get_in(VelocityMPS)

        self._table_data = load_drag_table(self._table)
        self._bc_table = self._create_bc_table_data_points()
        self._custom_drag_table = []

    cdef double _get_sectional_density(self):
        cdef double w, d
        w = self._weight.get_in(WeightGrain)
        d = self._diameter.get_in(DistanceInch)
        return w / pow(d, 2) / 7000

    cdef double _get_form_factor(self, double bc):
        return self._sectional_density / bc

    cdef list _bc_extended(self):
        cdef list bc_mah, bc_extended, df_part
        cdef bc_max, bc_min
        cdef int ddf
        cdef double bc_delta

        bc_mah = [BCDataPoint(point.bc(), point.v() / self._speed_of_sound) for point in self._bc_table]
        bc_mah.insert(len(bc_mah), BCDataPoint(bc_mah[-1].bc(), self._table_data[0].a()))
        bc_mah.insert(0, BCDataPoint(bc_mah[0].bc(), self._table_data[-1].a()))
        bc_extended = [bc_mah[0].bc(), ]

        for i in range(1, len(bc_mah)):
            bc_max = bc_mah[i - 1]
            bc_min = bc_mah[i]
            df_part = list(filter(lambda point: bc_max.v() > point.a() >= bc_min.v(), self._table_data))
            ddf = len(df_part)
            bc_delta = (bc_max.bc() - bc_min.bc()) / ddf
            for j in range(ddf):
                bc_extended.append(bc_max.bc() - bc_delta * j)

        return bc_extended

    cdef double _get_counted_cd(self, double form_factor, double cdst):
        return cdst * form_factor

    cdef list _create_bc_table_data_points(self):
        cdef list bc_table
        cdef data_point
        cdef double bc, v,
        self._multiple_bc_table.sort(reverse=True, key=lambda x: x[1])
        bc_table = []
        for bc, v in self._multiple_bc_table:
            data_point = BCDataPoint(bc, Velocity(v, self._units).get_in(VelocityMPS))
            bc_table.append(data_point)
        return bc_table

    cdef list _calculate_custom_drag_func(self):
        cdef list bc_extended, drag_function
        cdef int i
        cdef point
        cdef double form_factor, cd, bc

        bc_extended = self._bc_extended()
        drag_function = []
        for i, point in enumerate(self._table_data):
            bc = bc_extended[len(bc_extended) - 1 - i]
            form_factor = self._get_form_factor(bc)
            cd = form_factor * point.b()
            drag_function.append({'A': point.a(), 'B': cd})
        self._custom_drag_table = drag_function

    cpdef list custom_drag_func(self):
        self._calculate_custom_drag_func()
        return self._custom_drag_table
