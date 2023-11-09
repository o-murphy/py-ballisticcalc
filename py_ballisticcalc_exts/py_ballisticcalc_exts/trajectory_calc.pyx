from libc.math cimport sqrt, fabs, pow, sin, cos, tan, atan, log10, floor
cimport cython

from py_ballisticcalc.conditions import Atmo, Shot
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.settings import Settings
from py_ballisticcalc.trajectory_data import TrajectoryData
from py_ballisticcalc.unit import *

__all__ = ('TrajectoryCalc',)

cdef double cZeroFindingAccuracy = 0.000005
cdef double cMinimumVelocity = 50.0
cdef double cMaximumDrop = -15000
cdef int cMaxIterations = 20
cdef double cGravityConstant = -32.17405

cdef struct CurvePoint:
    double a, b, c

cdef enum CTrajFlag:
    NONE = 0
    ZERO_UP = 1
    ZERO_DOWN = 2
    MACH = 4
    RANGE = 8
    DANGER = 16
    ZERO = ZERO_UP | ZERO_DOWN
    ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | DANGER

cdef class Vector:
    cdef double x
    cdef double y
    cdef double z

    def __cinit__(Vector self, double x, double y, double z):
        self.x = x
        self.y = y
        self.z = z

    cdef double magnitude(Vector self):
        return sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    cdef Vector mul_by_const(Vector self, double a):
        return Vector(self.x * a, self.y * a, self.z * a)

    cdef double mul_by_vector(Vector self, Vector b):
        return self.x * b.x + self.y * b.y + self.z * b.z

    cdef Vector add(Vector self, Vector b):
        return Vector(self.x + b.x, self.y + b.y, self.z + b.z)

    cdef Vector subtract(Vector self, Vector b):
        return Vector(self.x - b.x, self.y - b.y, self.z - b.z)

    cdef Vector negate(Vector self):
        return Vector(-self.x, -self.y, -self.z)

    cdef Vector normalize(Vector self):
        cdef double m = self.magnitude()
        if fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.mul_by_const(1.0 / m)

    def __add__(Vector self, Vector other):
        return self.add(other)

    def __radd__(Vector self, Vector other):
        return self.add(other)

    def __iadd__(Vector self, Vector other):
        return self.add(other)

    def __sub__(Vector self, Vector other):
        return self.subtract(other)

    def __rsub__(Vector self, Vector other):
        return self.subtract(other)

    def __isub__(Vector self, Vector other):
        return self.subtract(other)

    def __mul__(Vector self, object other):
        if isinstance(other, (int, float)):
            return self.mul_by_const(other)
        if isinstance(other, Vector):
            return self.mul_by_vector(other)
        raise TypeError(other)

    def __rmul__(Vector self, object other):
        return self.__mul__(other)

    def __imul__(Vector self, object other):
        return self.__mul__(other)

    def __neg__(Vector self):
        return self.negate()

cdef class TrajectoryCalc:
    cdef:
        object ammo
        double step
        list _curve
        list _table_data
        double _bc

    def __init__(self, ammo: Ammo):
        self.ammo = ammo
        self._bc = self.ammo.dm.value
        self._table_data = ammo.dm.drag_table
        self._curve = calculate_curve(self._table_data)

    cdef double get_calc_step(self, double step):
        cdef:
            int step_order, maximum_order
            double maximum_step = Settings._MAX_CALC_STEP_SIZE

        step /= 2

        if step > maximum_step:
            step_order = int(floor(log10(step)))
            maximum_order = int(floor(log10(maximum_step)))
            step /= pow(10, step_order - maximum_order + 1)

        return step

    def zero_angle(self, weapon: Weapon, atmo: Atmo):
        return self._zero_angle(self.ammo, weapon, atmo)

    def trajectory(self, weapon: Weapon, shot_info: Shot, step: [float, Distance],
                   extra_data: bool = False):
        cdef:
            object dist_step = Settings.Units.distance(step)
            object atmo = shot_info.atmo
            list winds = shot_info.winds
            CTrajFlag filter_flags = CTrajFlag.RANGE

        if extra_data:
            print('ext', extra_data)
            dist_step = Distance.Foot(0.2)
            filter_flags = CTrajFlag.ALL
        return self._trajectory(self.ammo, weapon, atmo, shot_info, winds, dist_step, filter_flags)

    cdef _zero_angle(TrajectoryCalc self, object ammo, object weapon, object atmo):
        cdef:
            double calc_step = self.get_calc_step(weapon.zero_distance.units(10) >> Distance.Foot)
            double zero_distance = cos(weapon.zero_look_angle >> Angular.Radian) * (weapon.zero_distance >> Distance.Foot)
            double height_at_zero = sin(weapon.zero_look_angle >> Angular.Radian) * (weapon.zero_distance >> Distance.Foot)
            double maximum_range = zero_distance + calc_step
            double sight_height = weapon.sight_height >> Distance.Foot
            double mach = atmo.mach >> Velocity.FPS
            double density_factor = atmo.density_factor()
            double muzzle_velocity = ammo.mv >> Velocity.FPS
            double barrel_azimuth = 0.0
            double barrel_elevation = atan(height_at_zero / zero_distance)
            int iterations_count = 0
            double zero_finding_error = cZeroFindingAccuracy * 2
            Vector gravity_vector = Vector(.0, cGravityConstant, .0)
            double velocity, time, delta_time, drag
            Vector range_vector, velocity_vector, delta_range_vector

        # x - distance towards target, y - drop and z - windage
        while zero_finding_error > cZeroFindingAccuracy and iterations_count < cMaxIterations:
            velocity = muzzle_velocity
            time = 0.0
            range_vector = Vector(.0, -sight_height, .0)
            velocity_vector = Vector(
                cos(barrel_elevation) * cos(barrel_azimuth),
                sin(barrel_elevation),
                cos(barrel_elevation) * sin(barrel_azimuth)
            ) * velocity

            while range_vector.x <= maximum_range:
                if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                    break

                delta_time = calc_step / velocity_vector.x

                drag = density_factor * velocity * self.drag_by_mach(velocity / mach)

                velocity_vector -= (velocity_vector * drag - gravity_vector) * delta_time
                delta_range_vector = Vector(calc_step, velocity_vector.y * delta_time,
                                            velocity_vector.z * delta_time)
                range_vector += delta_range_vector
                velocity = velocity_vector.magnitude()
                time += delta_range_vector.magnitude() / velocity

                if fabs(range_vector.x - zero_distance) < 0.5 * calc_step:
                    zero_finding_error = fabs(range_vector.y - height_at_zero)
                    if zero_finding_error > cZeroFindingAccuracy:
                        barrel_elevation -= (range_vector.y - height_at_zero) / range_vector.x
                    break

            iterations_count += 1

        return Angular.Radian(barrel_elevation)

    cdef _trajectory(TrajectoryCalc self, object ammo, object weapon, object atmo,
                     object shot_info, list[object] winds, object dist_step, CTrajFlag filter_flags):
        cdef:
            double density_factor, mach
            double time, velocity, windage, delta_time, drag

            double look_angle = weapon.zero_look_angle >> Angular.Radian
            double twist = weapon.twist >> Distance.Inch
            double length = ammo.length >> Distance.Inch
            double diameter = ammo.dm.diameter >> Distance.Inch
            double weight = ammo.dm.weight >> Weight.Grain

            # double step = shot_info.step >> Distance.Foot
            double step = dist_step >> Distance.Foot
            double calc_step = self.get_calc_step(step)

            double maximum_range = (shot_info.max_range >> Distance.Foot) + 1

            int ranges_length = int(maximum_range / step) + 1
            int len_winds = len(winds)
            int current_item, current_wind, twist_coefficient

            double stability_coefficient = 1.0
            double next_wind_range = 1e7

            double barrel_elevation = (shot_info.zero_angle >> Angular.Radian) + (
                    shot_info.relative_angle >> Angular.Radian)
            double alt0 = atmo.altitude >> Distance.Foot
            double sight_height = weapon.sight_height >> Distance.Foot

            double next_range_distance = .0
            double barrel_azimuth = .0
            double previous_mach = .0

            Vector gravity_vector = Vector(.0, cGravityConstant, .0)
            Vector range_vector = Vector(.0, -sight_height, .0)
            Vector velocity_vector, velocity_adjusted, delta_range_vector, wind_vector

            list ranges = []

            object _flag, seen_zero  # CTrajFlag

        if len_winds < 1:
            wind_vector = Vector(.0, .0, .0)
        else:
            if len_winds > 1:
                next_wind_range = winds[0].until_distance() >> Distance.Foot
            wind_vector = wind_to_vector(shot_info, winds[0])

        if Settings.USE_POWDER_SENSITIVITY:
            velocity = ammo.get_velocity_for_temp(atmo.temperature) >> Velocity.FPS
        else:
            velocity = ammo.mv >> Velocity.FPS

        # x - distance towards target, y - drop and z - windage
        velocity_vector = Vector(cos(barrel_elevation) * cos(barrel_azimuth), sin(barrel_elevation),
                                 cos(barrel_elevation) * sin(barrel_azimuth)) * velocity

        if twist != 0 and length and diameter:
            stability_coefficient = calculate_stability_coefficient(ammo, weapon, atmo)
            twist_coefficient = -1 if twist > 0 else 1

        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        seen_zero = CTrajFlag.NONE  # Record when we see each zero crossing so we only register one
        if range_vector.y >= 0:
            seen_zero |= CTrajFlag.ZERO_UP  # We're starting above zero; we can only go down
        elif range_vector.y < 0 and barrel_elevation < look_angle:
            seen_zero |= CTrajFlag.ZERO_DOWN  # We're below and pointing down from look angle; no zeroes!

        while range_vector.x <= maximum_range + calc_step:
            _flag = CTrajFlag.NONE

            if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                break

            density_factor, mach = atmo.get_density_factor_and_mach_for_altitude(alt0 + range_vector.y)

            if range_vector.x >= next_wind_range:
                current_wind += 1
                wind_vector = wind_to_vector(shot_info, winds[current_wind])

                if current_wind == len_winds - 1:
                    next_wind_range = 1e7
                else:
                    next_wind_range = winds[current_wind].until_distance() >> Distance.Foot

            # Zero-crossing checks
            if range_vector.x > 0:
                # Zero reference line is the sight line defined by look_angle
                reference_height = range_vector.x * tan(look_angle)
                # If we haven't seen ZERO_UP, we look for that first
                if not seen_zero & CTrajFlag.ZERO_UP:
                    if range_vector.y >= reference_height:
                        _flag |= CTrajFlag.ZERO_UP
                        seen_zero |= CTrajFlag.ZERO_UP
                # We've crossed above sight line; now look for crossing back through it
                elif not seen_zero & CTrajFlag.ZERO_DOWN:
                    if range_vector.y < reference_height:
                        _flag |= CTrajFlag.ZERO_DOWN
                        seen_zero |= CTrajFlag.ZERO_DOWN

            # Mach crossing check
            if (velocity / mach <= 1) and (previous_mach > 1):
                _flag |= CTrajFlag.MACH

            # Next range check
            if range_vector.x >= next_range_distance:
                _flag |= CTrajFlag.RANGE
                next_range_distance += step
                current_item += 1

            if _flag & filter_flags:

                windage = range_vector.z

                if twist != 0:
                    windage += (1.25 * (stability_coefficient + 1.2)
                                * pow(time, 1.83) * twist_coefficient) / 12

                ranges.append(create_trajectory_row(
                    time, range_vector, velocity_vector,
                    velocity, mach, windage, weight, _flag
                ))

                if current_item == ranges_length:
                    break

            previous_mach = velocity / mach

            velocity_adjusted = velocity_vector - wind_vector

            delta_time = calc_step / velocity_vector.x
            velocity = velocity_adjusted.magnitude()

            drag = density_factor * velocity * self.drag_by_mach(velocity / mach)

            velocity_vector -= (velocity_adjusted * drag - gravity_vector) * delta_time
            delta_range_vector = Vector(calc_step,
                                        velocity_vector.y * delta_time,
                                        velocity_vector.z * delta_time)
            range_vector += delta_range_vector
            velocity = velocity_vector.magnitude()
            time += delta_range_vector.magnitude() / velocity

        return ranges

    cdef double drag_by_mach(self, double mach):
        cdef double cd = calculate_by_curve(self._table_data, self._curve, mach)
        return cd * 2.08551e-04 / self._bc

    @property
    def cdm(self):
        return self._cdm()

    cdef _cdm(self):
        """
        Returns custom drag function based on input data
        """
        cdef:
            # double ff = self.ammo.dm.form_factor
            list drag_table = self.ammo.dm.drag_table
            list cdm = []
            double bc = self.ammo.dm.value

        for point in drag_table:
            st_mach = point['Mach']
            st_cd = calculate_by_curve(drag_table, self._curve, st_mach)
            # cd = st_cd * ff
            cd = st_cd * bc
            cdm.append({'CD': cd, 'Mach': st_mach})

        return cdm

cdef double calculate_stability_coefficient(object ammo, object rifle, object atmo):
    cdef:
        double weight = ammo.dm.weight >> Weight.Grain
        double diameter = ammo.dm.diameter >> Distance.Inch
        double twist = fabs(rifle.twist >> Distance.Inch) / diameter
        double length = (ammo.length >> Distance.Inch) / diameter
        double ft = atmo.temperature >> Temperature.Fahrenheit
        double mv = ammo.mv >> Velocity.FPS
        double pt = atmo.pressure >> Pressure.InHg
        double sd = 30 * weight / (pow(twist, 2) * pow(diameter, 3) * length * (1 + pow(length, 2)))
        double fv = pow(mv / 2800, 1.0 / 3.0)
        double ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
    return sd * fv * ftp

cdef Vector wind_to_vector(object shot, object wind):
    cdef:
        double sight_cosine = cos(shot.zero_angle >> Angular.Radian)
        double sight_sine = sin(shot.zero_angle >> Angular.Radian)
        double cant_cosine = cos(shot.cant_angle >> Angular.Radian)
        double cant_sine = sin(shot.cant_angle >> Angular.Radian)
        double range_velocity = (wind.velocity >> Velocity.FPS) * cos(wind.direction_from >> Angular.Radian)
        double cross_component = (wind.velocity >> Velocity.FPS) * sin(wind.direction_from >> Angular.Radian)
        double range_factor = -range_velocity * sight_sine
    return Vector(range_velocity * sight_cosine,
                  range_factor * cant_cosine + cross_component * cant_sine,
                  cross_component * cant_cosine - range_factor * cant_sine)

cdef create_trajectory_row(double time, Vector range_vector, Vector velocity_vector,
                           double velocity, double mach, double windage, double weight, object flag):
    cdef:
        double drop_adjustment = get_correction(range_vector.x, range_vector.y)
        double windage_adjustment = get_correction(range_vector.x, windage)
        double trajectory_angle = atan(velocity_vector.y / velocity_vector.x)

    return TrajectoryData(
        time=time,
        distance=Distance.Foot(range_vector.x),
        drop=Distance.Foot(range_vector.y),
        drop_adj=Angular.Radian(drop_adjustment),
        windage=Distance.Foot(windage),
        windage_adj=Angular.Radian(windage_adjustment),
        velocity=Velocity.FPS(velocity),
        mach=velocity / mach,
        energy=Energy.FootPound(calculate_energy(weight, velocity)),
        angle=Angular.Radian(trajectory_angle),
        ogw=Weight.Pound(calculate_ogv(weight, velocity)),
        flag=flag
    )

@cython.cdivision(True)
cdef double get_correction(double distance, double offset):
    if distance != 0:
        return atan(offset / distance)
    return 0  # better None

cdef double calculate_energy(double bullet_weight, double velocity):
    return bullet_weight * pow(velocity, 2) / 450400

cdef double calculate_ogv(double bullet_weight, double velocity):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12

cdef list calculate_curve(list data_points):
    cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
    cdef list curve = []
    cdef CurvePoint curve_point
    cdef int num_points, len_data_points, len_data_range

    rate = (data_points[1]['CD'] - data_points[0]['CD']) / (data_points[1]['Mach'] - data_points[0]['Mach'])
    curve = [CurvePoint(0, rate, data_points[0]['CD'] - data_points[0]['Mach'] * rate)]
    len_data_points = int(len(data_points))
    len_data_range = len_data_points - 1

    for i in range(1, len_data_range):
        x1 = data_points[i - 1]['Mach']
        x2 = data_points[i]['Mach']
        x3 = data_points[i + 1]['Mach']
        y1 = data_points[i - 1]['CD']
        y2 = data_points[i]['CD']
        y3 = data_points[i + 1]['CD']
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_point = CurvePoint(a, b, c)
        curve.append(curve_point)

    num_points = len_data_points
    rate = (data_points[num_points - 1]['CD'] - data_points[num_points - 2]['CD']) / \
           (data_points[num_points - 1]['Mach'] - data_points[num_points - 2]['Mach'])
    curve_point = CurvePoint(0, rate, data_points[num_points - 1]['CD'] - data_points[num_points - 2]['Mach'] * rate)
    curve.append(curve_point)
    return curve

cdef double calculate_by_curve(list data, list curve, double mach):
    cdef int num_points, mlo, mhi, mid
    cdef CurvePoint curve_m

    num_points = int(len(curve))
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = int(floor(mhi + mlo) / 2.0)
        if data[mid]['Mach'] < mach:
            mlo = mid
        else:
            mhi = mid

    if data[mhi]['Mach'] - mach > mach - data[mlo]['Mach']:
        m = mlo
    else:
        m = mhi
    curve_m = curve[m]
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)
