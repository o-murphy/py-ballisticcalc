from libc.math cimport sqrt, fabs, pow, sin, cos, tan, atan, floor
cimport cython

from py_ballisticcalc.conditions import Shot, Wind
from py_ballisticcalc.munition import Ammo
from py_ballisticcalc.trajectory_data import TrajectoryData
from py_ballisticcalc.unit import *

__all__ = (
    'TrajectoryCalc',
    'get_global_max_calc_step_size',
    'get_global_use_powder_sensitivity',
    'set_global_max_calc_step_size',
    'set_global_use_powder_sensitivity',
    'reset_globals'
)

cdef double cZeroFindingAccuracy = 0.000005
cdef double cMinimumVelocity = 50.0
cdef double cMaximumDrop = -15000
cdef int cMaxIterations = 20
cdef double cGravityConstant = -32.17405

cdef int _globalUsePowderSensitivity = False
cdef object _globalMaxCalcStepSize = Distance.Foot(0.5)

def get_global_max_calc_step_size() -> Distance:
    return _globalMaxCalcStepSize


def get_global_use_powder_sensitivity() -> bool:
    return bool(_globalUsePowderSensitivity)


def set_global_max_calc_step_size(value: [object, float]) -> None:
    global _globalMaxCalcStepSize
    if (_value := PreferredUnits.distance(value)).raw_value <= 0:
        raise ValueError("_globalMaxCalcStepSize have to be > 0")
    _globalMaxCalcStepSize = PreferredUnits.distance(value)


def set_global_use_powder_sensitivity(value: bool) -> None:
    global _globalUsePowderSensitivity
    if not isinstance(value, bool):
        raise TypeError(f"set_global_use_powder_sensitivity {value=} is not a boolean")
    _globalUsePowderSensitivity = int(value)


def reset_globals() -> None:
    global _globalUsePowderSensitivity, _globalMaxCalcStepSize
    _globalUsePowderSensitivity = False
    _globalMaxCalcStepSize = Distance.Foot(0.5)


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
        double _bc
        list _table_data
        list _curve
        Vector gravity_vector
        double look_angle
        double twist
        double length
        double diameter
        double weight
        double barrel_elevation
        double barrel_azimuth
        double sight_height
        double cant_cosine
        double cant_sine
        double alt0
        double calc_step
        double muzzle_velocity
        double stability_coefficient

    def __init__(self, ammo: Ammo):
        self.ammo = ammo
        self._bc = self.ammo.dm.BC
        self._table_data = ammo.dm.drag_table
        self._curve = calculate_curve(self._table_data)
        self.gravity_vector = Vector(.0, cGravityConstant, .0)

    def zero_angle(self, shot_info: Shot, distance: Distance):
        return self._zero_angle(shot_info, distance)

    def trajectory(self, shot_info: Shot, max_range: Distance, dist_step: Distance,
                   extra_data: bool = False):
        cdef:
            # object atmo = shot_info.atmo
            # list winds = shot_info.winds
            CTrajFlag filter_flags = CTrajFlag.RANGE

        dist_step = PreferredUnits.distance(dist_step)  #  was unused there ???

        if extra_data:
            dist_step = Distance.Foot(0.2)
            filter_flags = CTrajFlag.ALL

        self._init_trajectory(shot_info)            
        return self._trajectory(shot_info, max_range >> Distance.Foot, dist_step >> Distance.Foot, filter_flags)

    cdef _init_trajectory(self, shot_info: Shot):
        self.look_angle = shot_info.look_angle >> Angular.Radian
        self.twist = shot_info.weapon.twist >> Distance.Inch
        self.length = shot_info.ammo.dm.length >> Distance.Inch
        self.diameter = shot_info.ammo.dm.diameter >> Distance.Inch
        self.weight = shot_info.ammo.dm.weight >> Weight.Grain
        self.barrel_elevation = shot_info.barrel_elevation >> Angular.Radian
        self.barrel_azimuth = shot_info.barrel_azimuth >> Angular.Radian
        self.sight_height = shot_info.weapon.sight_height >> Distance.Foot
        self.cant_cosine = cos(shot_info.cant_angle >> Angular.Radian)
        self.cant_sine = sin(shot_info.cant_angle >> Angular.Radian)
        self.alt0 = shot_info.atmo.altitude >> Distance.Foot
        self.calc_step = get_calc_step()
        if _globalUsePowderSensitivity:
            self.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.temperature) >> Velocity.FPS
        else:
            self.muzzle_velocity = shot_info.ammo.mv >> Velocity.FPS
        self.stability_coefficient = self.calc_stability_coefficient(shot_info.atmo)

    cdef _zero_angle(TrajectoryCalc self, object shot_info, object distance):
        cdef:
            double zero_distance = cos(shot_info.look_angle >> Angular.Radian) * (distance >> Distance.Foot)
            double height_at_zero = sin(shot_info.look_angle >> Angular.Radian) * (distance >> Distance.Foot)
            double maximum_range = zero_distance
            int iterations_count = 0
            double zero_finding_error = cZeroFindingAccuracy * 2

            object t
            double height

        self._init_trajectory(shot_info)
        self.barrel_azimuth = 0.0
        self.barrel_elevation = atan(height_at_zero / zero_distance)
        self.twist = 0
        maximum_range -= 1.5*self.calc_step

        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > cZeroFindingAccuracy and iterations_count < cMaxIterations:
            t = self._trajectory(shot_info, maximum_range, zero_distance, CTrajFlag.NONE)[0]
            height = t.height >> Distance.Foot
            zero_finding_error = fabs(height - height_at_zero)
            if zero_finding_error > cZeroFindingAccuracy:
                self.barrel_elevation -= (height - height_at_zero) / zero_distance
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1
        if zero_finding_error > cZeroFindingAccuracy:
            raise Exception(f'Zero vertical error {zero_finding_error} feet, after {iterations_count} iterations.')
        return Angular.Radian(self.barrel_elevation)

    cdef _trajectory(TrajectoryCalc self, object shot_info,
                     double maximum_range, double step, int filter_flags):
        cdef:
            int _flag, seen_zero  # CTrajFlag
            double density_factor, mach, velocity, delta_time
            list ranges = []
            int ranges_length = int(maximum_range / step) + 1
            int current_item = 0
            double time = .0
            double previous_mach = .0
            double drag = .0

            int len_winds = len(shot_info.winds)
            int current_wind = 0
            double next_range_distance = .0
            double next_wind_range = Wind.MAX_DISTANCE_FEET
            double _max_wind_distance_feed = Wind.MAX_DISTANCE_FEET

            double reference_height

            Vector velocity_vector, velocity_adjusted
            Vector range_vector, delta_range_vector, wind_vector

        if len_winds < 1:
            wind_vector = Vector(.0, .0, .0)
        else:
            wind_vector = wind_to_vector(shot_info.winds[0])
            next_wind_range = shot_info.winds[0].until_distance >> Distance.Foot

        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -self.cant_cosine*self.sight_height, -self.cant_sine*self.sight_height)
        velocity_vector = Vector(cos(self.barrel_elevation) * cos(self.barrel_azimuth),
                                 sin(self.barrel_elevation),
                                 cos(self.barrel_elevation) * sin(self.barrel_azimuth)) * velocity


        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        seen_zero = CTrajFlag.NONE  # Record when we see each zero crossing so we only register one
        if range_vector.y >= 0:
            seen_zero |= CTrajFlag.ZERO_UP  # We're starting above zero; we can only go down
        elif range_vector.y < 0 and self.barrel_elevation < self.look_angle:
            seen_zero |= CTrajFlag.ZERO_DOWN  # We're below and pointing down from look angle; no zeroes!

        #region Trajectory Loop
        while range_vector.x <= maximum_range + self.calc_step:
            _flag = CTrajFlag.NONE

            if range_vector.x >= next_wind_range:
                current_wind += 1
                if current_wind >= len_winds:  # No more winds listed after this range
                    wind_vector = Vector(.0, .0, .0)
                    next_wind_range = _max_wind_distance_feed  # better for cython optimization
                else:
                    wind_vector = wind_to_vector(shot_info.winds[current_wind])
                    next_wind_range = shot_info.winds[current_wind].until_distance >> Distance.Foot

            density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(
                self.alt0 + range_vector.y)

            if filter_flags:
                # Zero-crossing checks
                if range_vector.x > 0:
                    # Zero reference line is the sight line defined by look_angle
                    reference_height = range_vector.x * tan(self.look_angle)
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
                # if (velocity / mach <= 1) and (previous_mach > 1):
                if velocity / mach <= 1 < previous_mach:  # better cython optimization
                    _flag |= CTrajFlag.MACH

                # Next range check
                if range_vector.x >= next_range_distance:
                    _flag |= CTrajFlag.RANGE
                    next_range_distance += step
                    current_item += 1

                # Record TrajectoryData row
                if _flag & filter_flags:
                    ranges.append(create_trajectory_row(
                        time, range_vector, velocity_vector,
                        velocity, mach, self.spin_drift(time), self.look_angle,
                        density_factor, drag, self.weight, _flag
                    ))
                    if current_item == ranges_length:
                        break

            previous_mach = velocity / mach

            #region Ballistic calculation step
            delta_time = self.calc_step / velocity_vector.x

            # using .subtract insstead of "/" better optimized by cython
            velocity_adjusted = velocity_vector - wind_vector
            velocity = velocity_adjusted.magnitude()
            drag = density_factor * velocity * self.drag_by_mach(velocity / mach)
            velocity_vector -= (velocity_adjusted * drag - self.gravity_vector) * delta_time
            delta_range_vector = Vector(self.calc_step,
                                        velocity_vector.y * delta_time,
                                        velocity_vector.z * delta_time)
            range_vector += delta_range_vector
            velocity = velocity_vector.magnitude()
            time += delta_range_vector.magnitude() / velocity

            if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                break
            #endregion
        #endregion
        # If filter_flags == 0 then all we want is the ending value
        if not filter_flags:
            ranges.append(create_trajectory_row(
                        time, range_vector, velocity_vector,
                        velocity, mach, self.spin_drift(time), self.look_angle,
                        density_factor, drag, self.weight, _flag))
        return ranges

    cdef double drag_by_mach(self, double mach):
        """ Drag force = V^2 * Cd * AirDensity * S / 2m where:
            cStandardDensity of Air = 0.076474 lb/ft^3
            S is cross-section = d^2 pi/4, where d is bullet diameter in inches
            m is bullet mass in pounds
        bc contains m/d^2 in units lb/in^2, which we multiply by 144 to convert to lb/ft^2
        Thus: The magic constant found here = StandardDensity * pi / (4 * 2 * 144)
        """
        cdef double cd = calculate_by_curve(self._table_data, self._curve, mach)
        return cd * 2.08551e-04 / self._bc

    cdef double spin_drift(self, double time):
        """Litz spin-drift approximation
        :param time: Time of flight
        :return: windage due to spin drift, in feet
        """
        cdef int sign
        if self.twist != 0:
            sign = 1 if self.twist > 0 else -1
            return sign * (1.25 * (self.stability_coefficient + 1.2) * pow(time, 1.83) ) / 12
        return 0

    cdef double calc_stability_coefficient(self, object atmo):
        """Miller stability coefficient"""
        cdef:
            double twist_rate, length, sd, fv, ft, pt, ftp
        if self.twist and self.length and self.diameter:
            twist_rate = fabs(self.twist) / self.diameter
            length = self.length / self.diameter
            sd = 30 * self.weight / (pow(twist_rate, 2) * pow(self.diameter, 3) * length * (1 + pow(length, 2)))
            fv = pow(self.muzzle_velocity / 2800, 1.0 / 3.0)
            ft = atmo.temperature >> Temperature.Fahrenheit
            pt = atmo.pressure >> Pressure.InHg
            ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
            return sd * fv * ftp
        return 0

cdef Vector wind_to_vector(object wind):
    cdef:
        double range_component = (wind.velocity >> Velocity.FPS) * cos(wind.direction_from >> Angular.Radian)
        double cross_component = (wind.velocity >> Velocity.FPS) * sin(wind.direction_from >> Angular.Radian)
    return Vector(range_component, 0., cross_component)

cdef create_trajectory_row(double time, Vector range_vector, Vector velocity_vector,
                           double velocity, double mach, double spin_drift, double look_angle,
                           double density_factor, double drag, double weight, object flag):
    cdef:
        double windage = range_vector.z + spin_drift
        double drop_adjustment = get_correction(range_vector.x, range_vector.y)
        double windage_adjustment = get_correction(range_vector.x, windage)
        double trajectory_angle = atan(velocity_vector.y / velocity_vector.x)

    return TrajectoryData(
        time=time,
        distance=Distance.Foot(range_vector.x),
        velocity=Velocity.FPS(velocity),
        mach=velocity / mach,
        height=Distance.Foot(range_vector.y),
        target_drop=Distance.Foot((range_vector.y - range_vector.x * tan(look_angle)) * cos(look_angle)),
        drop_adj=Angular.Radian(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=Distance.Foot(windage),
        windage_adj=Angular.Radian(windage_adjustment),
        look_distance= Distance.Foot(range_vector.x / cos(look_angle)),
        angle=Angular.Radian(trajectory_angle),
        density_factor = density_factor-1,
        drag = drag,
        energy=Energy.FootPound(calculate_energy(weight, velocity)),
        ogw=Weight.Pound(calculate_ogv(weight, velocity)),
        flag=flag
    )

@cython.cdivision(True)
cdef double get_correction(double distance, double offset):
    if distance != 0:
        return atan(offset / distance)
    return 0  # better None

@cython.cdivision(True)
cdef double get_calc_step(double step = 0):
    cdef double preferred_step = _globalMaxCalcStepSize >> Distance.Foot
    # cdef double defined_max = 0.5  # const will be better optimized with cython
    if step == 0:
        return preferred_step / 2.0
    return min(step, preferred_step) / 2.0

cdef double calculate_energy(double bullet_weight, double velocity):
    return bullet_weight * pow(velocity, 2) / 450400

cdef double calculate_ogv(double bullet_weight, double velocity):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12

cdef list calculate_curve(list data_points):
    cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
    cdef list curve = []
    cdef CurvePoint curve_point
    cdef int i, num_points, len_data_points, len_data_range

    rate = (data_points[1].CD - data_points[0].CD) / (data_points[1].Mach - data_points[0].Mach)
    curve = [CurvePoint(0, rate, data_points[0].CD - data_points[0].Mach * rate)]
    len_data_points = int(len(data_points))
    len_data_range = len_data_points - 1

    for i in range(1, len_data_range):
        x1 = data_points[i - 1].Mach
        x2 = data_points[i].Mach
        x3 = data_points[i + 1].Mach
        y1 = data_points[i - 1].CD
        y2 = data_points[i].CD
        y3 = data_points[i + 1].CD
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_point = CurvePoint(a, b, c)
        curve.append(curve_point)

    num_points = len_data_points
    rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
           (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
    curve_point = CurvePoint(0, rate, data_points[num_points - 1].CD - data_points[num_points - 2].Mach * rate)
    curve.append(curve_point)
    return curve

cdef double calculate_by_curve(list data, list curve, double mach):
    cdef int num_points, mlo, mhi, mid, m
    cdef CurvePoint curve_m

    num_points = int(len(curve))
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = int(floor(mhi + mlo) / 2.0)
        if data[mid].Mach < mach:
            mlo = mid
        else:
            mhi = mid

    if data[mhi].Mach - mach > mach - data[mlo].Mach:
        m = mlo
    else:
        m = mhi
    curve_m = curve[m]
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)
