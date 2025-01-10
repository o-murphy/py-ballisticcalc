"""
# Total Score: 2394, Possible Score: 45200
# Total Non-Empty Lines: 452
# Python Overhead Lines: 152
# Cythonization Percentage: 94.70%
# Python Overhead Lines Percentage: 33.63%
"""

from cython cimport final
from libc.math cimport fabs, pow, sin, cos, tan, atan, atan2
from py_ballisticcalc_exts.vector cimport Vector
from py_ballisticcalc_exts.conditions cimport Wind, Shot, _WIND_MAX_DISTANCE_FEET
from py_ballisticcalc_exts.trajectory_data cimport TrajectoryData, CTrajFlag
from py_ballisticcalc_exts._early_bind_atmo cimport _EarlyBindAtmo
from py_ballisticcalc_exts._early_bind_config cimport _ConfigStruct, _early_bind_config

import warnings
from typing_extensions import Type

from py_ballisticcalc.unit import *
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError


__all__ = (
    'TrajectoryCalc',
)

cdef struct CurvePoint:
    double a, b, c

@final
cdef class _TrajectoryDataFilter:
    cdef:
        int filter, current_flag, seen_zero
        int current_item, ranges_length
        double previous_mach, previous_time, next_range_distance, time_step

    def __cinit__(_TrajectoryDataFilter self,
                  int filter_flags, int ranges_length, double time_step = 0.0) -> None:
        self.filter = filter_flags
        self.current_flag = CTrajFlag.NONE
        self.seen_zero = CTrajFlag.NONE
        self.time_step = time_step
        self.current_item = 0
        self.ranges_length = ranges_length
        self.previous_mach = 0.0
        self.previous_time = 0.0
        self.next_range_distance = 0.0

    cdef void setup_seen_zero(_TrajectoryDataFilter self, double height, double barrel_elevation, double look_angle):
        if height >= 0:
            self.seen_zero |= CTrajFlag.ZERO_UP
        elif height < 0 and barrel_elevation < look_angle:
            self.seen_zero |= CTrajFlag.ZERO_DOWN

    cdef void clear_current_flag(_TrajectoryDataFilter self):
        self.current_flag = CTrajFlag.NONE

    cdef bint should_record(_TrajectoryDataFilter self,
                            Vector range_vector,
                            double velocity,
                            double mach,
                            double step,
                            double look_angle,
                            double time,
                            ):
        self.check_zero_crossing(range_vector, look_angle)
        self.check_mach_crossing(velocity, mach)
        if self.check_next_range(range_vector.x, step):
            self.previous_time = time
        elif self.time_step > 0:
            self.check_next_time(time)
        return (self.current_flag & self.filter) != 0

    cdef bint should_break(_TrajectoryDataFilter self):
        return self.current_item == self.ranges_length

    cdef bint check_next_range(_TrajectoryDataFilter self, double next_range, double step):
        # Next range check
        if next_range >= self.next_range_distance:
            self.current_flag |= CTrajFlag.RANGE
            self.next_range_distance += step
            self.current_item += 1
            return True
        return False

    cdef void check_next_time(self, double time):
        if time > self.previous_time + self.time_step:
            self.current_flag |= CTrajFlag.RANGE
            self.previous_time = time

    cdef void check_mach_crossing(_TrajectoryDataFilter self, double velocity, double mach):
        # Mach crossing check
        cdef double current_mach = velocity / mach
        if self.previous_mach > 1 >= current_mach:
            self.current_flag |= CTrajFlag.MACH
        self.previous_mach = current_mach

    cdef void check_zero_crossing(_TrajectoryDataFilter self, Vector range_vector, double look_angle):
        # Zero-crossing checks

        if range_vector._x > 0:
            # Zero reference line is the sight line defined by look_angle
            reference_height = range_vector._x * tan(look_angle)
            # If we haven't seen ZERO_UP, we look for that first
            if not (self.seen_zero & CTrajFlag.ZERO_UP):
                if range_vector._x >= reference_height:
                    self.current_flag |= CTrajFlag.ZERO_UP
                    self.seen_zero |= CTrajFlag.ZERO_UP
            # We've crossed above sight line; now look for crossing back through it
            elif not (self.seen_zero & CTrajFlag.ZERO_DOWN):
                if range_vector._x < reference_height:
                    self.current_flag |= CTrajFlag.ZERO_DOWN
                    self.seen_zero |= CTrajFlag.ZERO_DOWN

@final
cdef class _WindSock:
    cdef tuple[Wind] winds
    cdef int current
    cdef double next_range
    cdef Vector _last_vector_cache
    cdef int _length

    def __cinit__(_WindSock self, tuple[Wind] winds):
        self.winds = winds or tuple()
        self.current = 0
        self.next_range = _WIND_MAX_DISTANCE_FEET
        self._last_vector_cache = None
        self._length = len(self.winds)

        # Initialize cache correctly
        self.update_cache()

    cdef Vector current_vector(_WindSock self):
        if not self._last_vector_cache:
            raise RuntimeError(f"No cached wind vector")
        return self._last_vector_cache

    cdef void update_cache(_WindSock self):
        cdef Wind cur_wind
        if self.current < self._length:
            cur_wind = self.winds[self.current]
            self._last_vector_cache = wind_to_vector(cur_wind)
            self.next_range = cur_wind.until_distance >> Distance.Foot
        else:
            self._last_vector_cache = Vector(0.0, 0.0, 0.0)
            self.next_range = _WIND_MAX_DISTANCE_FEET

    cdef Vector vector_for_range(_WindSock self, double next_range):
        if next_range >= self.next_range:
            self.current += 1
            if self.current >= self._length:
                self._last_vector_cache = Vector(0.0, 0.0, 0.0)
                self.next_range = _WIND_MAX_DISTANCE_FEET
            else:
                self.update_cache()  # This will trigger cache updates.
        return self._last_vector_cache


cdef class TrajectoryCalc:
    cdef:
        object ammo
        double _bc
        list _table_data
        list[CurvePoint] _curve
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

        list[double] __mach_list
        _ConfigStruct __config

    def __cinit__(TrajectoryCalc self, object ammo, object _config):
        self.ammo = ammo
        self.__config = _early_bind_config(_config)

        self._bc = self.ammo.dm.BC
        self._table_data = ammo.dm.drag_table
        self._curve = calculate_curve(self._table_data)
        self.gravity_vector = Vector(.0, self.__config.cGravityConstant, .0)

        # get list[double] instead of list[DragDataPoint]
        self.__mach_list = _get_only_mach_data(self._table_data)

    cdef double get_calc_step(self, double step = 0):
        cdef double preferred_step = self.__config.max_calc_step_size_feet
        # cdef double defined_max = 0.5  # const will be better optimized with cython
        if step == 0:
            return preferred_step / 2.0
        return min(step, preferred_step) / 2.0

    @property
    def table_data(self) -> list:
        return self._table_data

    def zero_angle(self, Shot shot_info, object distance):
        return self._zero_angle(shot_info, distance)

    def trajectory(self, object shot_info, object max_range, object dist_step,
                   bint extra_data = False, double time_step = 0.0) -> Type[list[TrajectoryData]]:
        cdef:
            CTrajFlag filter_flags = CTrajFlag.RANGE

        dist_step = PreferredUnits.distance(dist_step)  #  was unused there ???

        if extra_data:
            dist_step = Distance.Foot(self.__config.chart_resolution)
            filter_flags = CTrajFlag.ALL

        self._init_trajectory(shot_info)
        return self._trajectory(shot_info, max_range._feet, dist_step._feet, filter_flags, time_step)

    cdef void _init_trajectory(self, Shot shot_info):
        self.look_angle = shot_info.look_angle._rad
        self.twist = shot_info.weapon.twist._inch
        self.length = shot_info.ammo.dm.length._inch
        self.diameter = shot_info.ammo.dm.diameter._inch
        self.weight = shot_info.ammo.dm.weight._grain
        self.barrel_elevation = shot_info.barrel_elevation._rad
        self.barrel_azimuth = shot_info.barrel_azimuth._rad
        self.sight_height = shot_info.weapon.sight_height._feet
        self.cant_cosine = cos(shot_info.cant_angle._rad)
        self.cant_sine = sin(shot_info.cant_angle._rad)
        self.alt0 = shot_info.atmo.altitude._feet
        self.calc_step = self.get_calc_step()
        if self.__config.use_powder_sensitivity:
            self.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(
                shot_info.atmo.temperature)._fps  # shortcut for >> Velocity.FPS
        else:
            self.muzzle_velocity = shot_info.ammo.mv._fps  # shortcut for >> Velocity.FPS
        self.stability_coefficient = self.calc_stability_coefficient(shot_info.atmo)

    cdef object _zero_angle(TrajectoryCalc self, Shot shot_info, object distance):
        cdef:
            # early bindings
            double _cZeroFindingAccuracy = self.__config.cZeroFindingAccuracy
            double _cMaxIterations = self.__config.cMaxIterations

        cdef:
            double zero_distance = cos(shot_info.look_angle._rad) * distance._feet
            double height_at_zero = sin(shot_info.look_angle._rad) * distance._feet
            double maximum_range = zero_distance
            int iterations_count = 0
            double zero_finding_error = _cZeroFindingAccuracy * 2

            object t
            double height

        self._init_trajectory(shot_info)
        self.barrel_azimuth = 0.0
        self.barrel_elevation = atan(height_at_zero / zero_distance)
        self.twist = 0
        maximum_range -= 1.5 * self.calc_step

        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > _cZeroFindingAccuracy and iterations_count < _cMaxIterations:
            t = self._trajectory(shot_info, maximum_range, zero_distance, CTrajFlag.NONE)[0]
            height = t.height._feet  # use there internal shortcut instead of (t.height >> Distance.Foot)
            zero_finding_error = fabs(height - height_at_zero)
            if zero_finding_error > _cZeroFindingAccuracy:
                self.barrel_elevation -= (height - height_at_zero) / zero_distance
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1
        if zero_finding_error > _cZeroFindingAccuracy:
            raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self.barrel_elevation))
        return Angular.Radian(self.barrel_elevation)

    cdef list[TrajectoryData] _trajectory(TrajectoryCalc self, Shot shot_info,
                          double maximum_range, double step, int filter_flags, double time_step = 0.0):
        cdef:
            double velocity, delta_time
            double density_factor = .0
            double mach = .0
            list[TrajectoryData] ranges = []
            double time = .0
            double drag = .0
            Vector velocity_vector, velocity_adjusted
            Vector range_vector, delta_range_vector

            # region Initialize wind-related variables to first wind reading (if any)
            _WindSock wind_sock = _WindSock(shot_info.winds)
            Vector wind_vector = wind_sock.current_vector()
            # endregion

            _TrajectoryDataFilter data_filter

        cdef:
            # early bindings
            _EarlyBindAtmo atmo = _EarlyBindAtmo(shot_info.atmo)
            double _cMinimumVelocity = self.__config.cMinimumVelocity
            double _cMaximumDrop = self.__config.cMaximumDrop
            double _cMinimumAltitude = self.__config.cMinimumAltitude

        # region Initialize velocity and position of projectile
        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
        velocity_vector = Vector(cos(self.barrel_elevation) * cos(self.barrel_azimuth),
                                 sin(self.barrel_elevation),
                                 cos(self.barrel_elevation) * sin(self.barrel_azimuth)).mul_by_const(velocity)
        # endregion

        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags,
                                            ranges_length=<int> ((maximum_range / step) + 1),
                                            time_step=time_step)
        data_filter.setup_seen_zero(range_vector._y, self.barrel_elevation, self.look_angle)

        #region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        while range_vector._x <= maximum_range + self.calc_step:
            data_filter.clear_current_flag()

            # Update wind reading at current point in trajectory
            if range_vector._x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector._x)

            # overwrite density_factor and mach by pointer
            atmo.get_density_factor_and_mach_for_altitude(
                self.alt0 + range_vector._y, &density_factor, &mach)

            if filter_flags:

                # Record TrajectoryData row
                if data_filter.should_record(range_vector, velocity, mach, step, self.look_angle, time):
                    ranges.append(create_trajectory_row(
                        time, range_vector, velocity_vector,
                        velocity, mach, self.spin_drift(time), self.look_angle,
                        density_factor, drag, self.weight, data_filter.current_flag
                    ))
                    if data_filter.should_break():
                        break

            #region Ballistic calculation step
            # use just cdef methods to
            # using .subtract .add instead of "/" better optimized by cython
            velocity_adjusted = velocity_vector.subtract(wind_vector)
            velocity = velocity_adjusted.magnitude()
            delta_time = self.calc_step / max(1.0, velocity)
            drag = density_factor * velocity * self.drag_by_mach(velocity / mach)
            velocity_vector = velocity_vector.subtract(
                (velocity_adjusted.mul_by_const(drag).subtract(self.gravity_vector)).mul_by_const(delta_time))
            delta_range_vector = velocity_vector.mul_by_const(delta_time)
            range_vector = range_vector.add(delta_range_vector)
            velocity = velocity_vector.magnitude()
            # time += delta_range_vector.magnitude() / velocity
            time += delta_time

            if (
                    velocity < _cMinimumVelocity
                    or range_vector._y < _cMaximumDrop
                    or self.alt0 + range_vector._y < _cMinimumAltitude
            ):
                if velocity < _cMinimumVelocity:
                    reason = RangeError.MinimumVelocityReached
                elif range_vector._y < _cMaximumDrop:
                    reason = RangeError.MaximumDropReached
                else:
                    reason = RangeError.MinimumAltitudeReached
                raise RangeError(reason, ranges)
            #endregion

        #endregion
        # If filter_flags == 0 then all we want is the ending value
        if not filter_flags:
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity, mach, self.spin_drift(time), self.look_angle,
                density_factor, drag, self.weight, CTrajFlag.NONE))
        return ranges

    cdef double drag_by_mach(self, double mach):
        """ Drag force = V^2 * Cd * AirDensity * S / 2m where:
            cStandardDensity of Air = 0.076474 lb/ft^3
            S is cross-section = d^2 pi/4, where d is bullet diameter in inches
            m is bullet mass in pounds
        bc contains m/d^2 in units lb/in^2, which we multiply by 144 to convert to lb/ft^2
        Thus: The magic constant found here = StandardDensity * pi / (4 * 2 * 144)
        """
        # cdef double cd = calculate_by_curve(self._table_data, self._curve, mach)
        # use calculation over list[double] instead of list[DragDataPoint]
        cdef double cd = _calculate_by_curve_and_mach_list(self.__mach_list, self._curve, mach)
        return cd * 2.08551e-04 / self._bc

    cdef double spin_drift(self, double time):
        """Litz spin-drift approximation
        :param time: Time of flight
        :return: windage due to spin drift, in feet
        """
        cdef int sign
        if self.twist != 0:
            sign = 1 if self.twist > 0 else -1
            return sign * (1.25 * (self.stability_coefficient + 1.2) * pow(time, 1.83)) / 12
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
            ft = atmo.temperature._F
            pt = atmo.pressure._inHg
            ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
            return sd * fv * ftp
        return 0

cdef Vector wind_to_vector(Wind wind):
    cdef:
        # no need convert it twice
        double wind_velocity_fps = wind.velocity._fps  # shortcut for (wind.velocity >> Velocity.FPS)
        double wind_direction_rad = wind.direction_from._rad  # shortcut for (wind.direction_from >> Angular.Radian)
        # Downrange (x-axis) wind velocity component:
        double range_component = wind_velocity_fps * cos(wind_direction_rad)
        # Downrange (x-axis) wind velocity component:
        double cross_component = wind_velocity_fps * sin(wind_direction_rad)
    return Vector(range_component, 0., cross_component)

cdef TrajectoryData create_trajectory_row(double time, Vector range_vector, Vector velocity_vector,
                           double velocity, double mach, double spin_drift, double look_angle,
                           double density_factor, double drag, double weight, object flag):

    cdef:
        double windage = range_vector._z + spin_drift
        double drop_adjustment = get_correction(range_vector._x, range_vector._y)
        double windage_adjustment = get_correction(range_vector._x, windage)
        double trajectory_angle = atan2(velocity_vector._y, velocity_vector._x);

    return TrajectoryData(
        time=time,
        distance=Distance.Foot(range_vector._x),
        velocity=Velocity.FPS(velocity),
        mach=velocity / mach,
        height=Distance.Foot(range_vector._y),
        target_drop=Distance.Foot((range_vector._y - range_vector._x * tan(look_angle)) * cos(look_angle)),
        drop_adj=Angular.Radian(drop_adjustment - (look_angle if range_vector._x else 0)),
        windage=Distance.Foot(windage),
        windage_adj=Angular.Radian(windage_adjustment),
        look_distance=Distance.Foot(range_vector._x / cos(look_angle)),
        angle=Angular.Radian(trajectory_angle),
        density_factor=density_factor - 1,
        drag=drag,
        energy=Energy.FootPound(calculate_energy(weight, velocity)),
        ogw=Weight.Pound(calculate_ogv(weight, velocity)),
        flag=flag
    )

cdef double get_correction(double distance, double offset):
    if distance != 0:
        return atan(offset / distance)
    return 0  # better None

cdef double calculate_energy(double bullet_weight, double velocity):
    return bullet_weight * pow(velocity, 2) / 450400

cdef double calculate_ogv(double bullet_weight, double velocity):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12

cdef list[CurvePoint] calculate_curve(list data_points):
    cdef double rate, x1, x2, x3, y1, y2, y3, a, b, c
    cdef list[CurvePoint] curve = []
    cdef CurvePoint curve_point
    cdef int i, num_points, len_data_points, len_data_range

    rate = (data_points[1].CD - data_points[0].CD) / (data_points[1].Mach - data_points[0].Mach)
    curve = [CurvePoint(0, rate, data_points[0].CD - data_points[0].Mach * rate)]
    len_data_points = len(data_points)
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

# use get_only_mach_data with calculate_by_curve_and_mach_data cause it faster
cdef double calculate_by_curve(list data, list[CurvePoint] curve, double mach):
    cdef int num_points, mlo, mhi, mid, m
    cdef CurvePoint curve_m

    num_points = len(curve)
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = (mhi + mlo) // 2
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

cdef list[double] _get_only_mach_data(list data):
    cdef int data_len = len(data)
    cdef list[double] result = []  # [.0] * data_len # Preallocate the list to avoid resizing during appending
    cdef int i
    cdef object dp  # Assuming dp is an object with a Mach attribute

    for i in range(data_len):
        dp = data[i]  # Direct indexing is more efficient than using `PyList_GET_ITEM`
        result.append(dp.Mach)  # result[i] = dp.Mach # Directly assign the value to the pre-allocated result list

    return result

cdef double _calculate_by_curve_and_mach_list(list[double] mach_list, list[CurvePoint] curve, double mach):
    cdef int num_points, mlo, mhi, mid, m
    cdef CurvePoint curve_m

    num_points = len(curve)
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = (mhi + mlo) // 2
        if mach_list[mid] < mach:
            mlo = mid
        else:
            mhi = mid

    if mach_list[mhi] - mach > mach - mach_list[mlo]:
        m = mlo
    else:
        m = mhi
    curve_m = curve[m]
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)
