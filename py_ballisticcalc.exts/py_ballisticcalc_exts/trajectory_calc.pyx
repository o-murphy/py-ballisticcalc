"""
# Total Score: 2394, Possible Score: 45200
# Total Non-Empty Lines: 452
# Python Overhead Lines: 152
# Cythonization Percentage: 94.70%
# Python Overhead Lines Percentage: 33.63%
"""

# noinspection PyUnresolvedReferences
from cython cimport final
from libc.math cimport fabs, sin, cos, tan, atan, atan2
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.vector cimport CVector, add, sub, mag, mul_c, mul_v, neg, norm, mag
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport CTrajFlag, TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_euler cimport (
    Config_t,
    Wind_t,
    Atmosphere_t,
    ShotData_t,
    config_bind,
    update_density_factor_and_mach_for_altitude,
    cy_table_to_mach,
    cy_calculate_curve,
    cy_calculate_by_curve_and_mach_list,
    cy_spin_drift,
    cy_drag_by_mach,
    cy_get_correction,
    cy_calculate_energy,
    cy_calculate_ogw,
    cy_update_stability_coefficient,
    free_trajectory,
    wind_to_c_vector,
    _WIND_MAX_DISTANCE_FEET,
)

import warnings

from py_ballisticcalc.logger import logger
from py_ballisticcalc.unit import Angular, Unit, Velocity, Distance, Energy, Weight
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError


__all__ = (
    'TrajectoryCalc',
)


@final
cdef class _TrajectoryDataFilter:
    cdef:
        int filter, current_flag, seen_zero
        int current_item, ranges_length
        double previous_mach, previous_time, next_range_distance, time_step, look_angle

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
        self.look_angle = 0

    cdef void setup_seen_zero(_TrajectoryDataFilter self, double height, double barrel_elevation, double look_angle):
        if height >= 0:
            self.seen_zero |= CTrajFlag.ZERO_UP
        elif height < 0 and barrel_elevation < look_angle:
            self.seen_zero |= CTrajFlag.ZERO_DOWN
        self.look_angle = look_angle

    cdef void clear_current_flag(_TrajectoryDataFilter self):
        self.current_flag = CTrajFlag.NONE

    cdef bint should_record(_TrajectoryDataFilter self,
                            CVector range_vector,
                            double velocity,
                            double mach,
                            double step,
                            double time,
                            ):
        self.check_zero_crossing(range_vector)
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

    cdef void check_zero_crossing(_TrajectoryDataFilter self, CVector range_vector):
        # Zero-crossing checks

        if range_vector.x > 0:
            # Zero reference line is the sight line defined by look_angle
            reference_height = range_vector.x * tan(self.look_angle)
            # If we haven't seen ZERO_UP, we look for that first
            if not (self.seen_zero & CTrajFlag.ZERO_UP):
                if range_vector.x >= reference_height:
                    self.current_flag |= CTrajFlag.ZERO_UP
                    self.seen_zero |= CTrajFlag.ZERO_UP
            # We've crossed above sight line; now look for crossing back through it
            elif not (self.seen_zero & CTrajFlag.ZERO_DOWN):
                if range_vector.x < reference_height:
                    self.current_flag |= CTrajFlag.ZERO_DOWN
                    self.seen_zero |= CTrajFlag.ZERO_DOWN

@final
cdef class _WindSock:
    cdef list[Wind_t] winds
    cdef int current
    cdef double next_range
    # cdef Vector _last_vector_cache
    cdef CVector _last_vector_cache
    cdef int _length

    def __cinit__(_WindSock self, object winds):
        self.winds = [
            Wind_t(
                w.velocity.get_in(Unit.FPS),
                w.direction_from.get_in(Unit.Radian),
                w.until_distance.get_in(Unit.Foot),
                w.MAX_DISTANCE_FEET
            ) for w in winds
        ]
        self.current = 0
        self.next_range = _WIND_MAX_DISTANCE_FEET
        self._last_vector_cache = CVector(0.0, 0.0, 0.0)
        self._length = len(self.winds)

        # Initialize cache correctly
        self.update_cache()

    cdef CVector current_vector(_WindSock self):
        return self._last_vector_cache

    cdef void update_cache(_WindSock self):
        cdef Wind_t cur_wind
        if self.current < self._length:
            cur_wind = self.winds[self.current]
            self._last_vector_cache = wind_to_c_vector(&cur_wind)
            self.next_range = cur_wind.until_distance
        else:
            self._last_vector_cache = CVector(0.0, 0.0, 0.0)
            self.next_range = _WIND_MAX_DISTANCE_FEET

    cdef CVector vector_for_range(_WindSock self, double next_range):
        if next_range >= self.next_range:
            self.current += 1
            if self.current >= self._length:
                self._last_vector_cache = CVector(0.0, 0.0, 0.0)
                self.next_range = _WIND_MAX_DISTANCE_FEET
            else:
                self.update_cache()  # This will trigger cache updates.
        return self._last_vector_cache


cdef class TrajectoryCalc:
    cdef:
        list[object] _table_data
        CVector gravity_vector
        public object _config
        Config_t __config
        ShotData_t __shot
        _WindSock ws

    def __cinit__(TrajectoryCalc self, object _config):
        self._config = _config
        self.__config = config_bind(_config)
        self.gravity_vector = CVector(.0, self.__config.cGravityConstant, .0)

    # def __dealloc__(TrajectoryCalc self):
    #     free_trajectory(&self.__shot)

    cdef double get_calc_step(self, double step = 0):
        cdef double preferred_step = self.__config.max_calc_step_size_feet
        # cdef double defined_max = 0.5  # const will be better optimized with cython
        if step == 0:
            return preferred_step / 2.0
        return min(step, preferred_step) / 2.0

    @property
    def table_data(self) -> list[object]:
        return self._table_data

    def zero_angle(self, object shot_info, object distance) -> Angular:
        return self._zero_angle(shot_info, distance)

    def trajectory(self, object shot_info, object max_range, object dist_step,
                   bint extra_data = False, double time_step = 0.0) -> object:
        cdef:
            CTrajFlag filter_flags = CTrajFlag.RANGE

        if extra_data:
            dist_step = Distance.Foot(self.__config.chart_resolution)
            filter_flags = CTrajFlag.ALL

        self._init_trajectory(shot_info)
        cdef list[object] t = self._integrate(max_range._feet, dist_step._feet, filter_flags, time_step)
        self._free_trajectory()
        return t

    cdef void _free_trajectory(self):
        free_trajectory(&self.__shot)

    cdef void _init_trajectory(self, object shot_info):
        self._table_data = shot_info.ammo.dm.drag_table
        self.__shot = ShotData_t(
            bc=shot_info.ammo.dm.BC,
            curve=cy_calculate_curve(self._table_data),
            mach_list=cy_table_to_mach(self._table_data),
            look_angle=shot_info.look_angle._rad,
            twist=shot_info.weapon.twist._inch,
            length=shot_info.ammo.dm.length._inch,
            diameter=shot_info.ammo.dm.diameter._inch,
            weight=shot_info.ammo.dm.weight._grain,
            barrel_elevation=shot_info.barrel_elevation._rad,
            barrel_azimuth=shot_info.barrel_azimuth._rad,
            sight_height=shot_info.weapon.sight_height._feet,
            cant_cosine=cos(shot_info.cant_angle._rad),
            cant_sine=sin(shot_info.cant_angle._rad),
            alt0=shot_info.atmo.altitude._feet,
            calc_step=self.get_calc_step(),
            diameter=shot_info.ammo.dm.diameter._inch,
            stability_coefficient=0.0,
            atmo=Atmosphere_t(
                _t0=shot_info.atmo._t0,
                _a0=shot_info.atmo._a0,
                _p0=shot_info.atmo.pressure.get_in(Unit.InHg),
                _mach1=shot_info.atmo._mach1,
                density_ratio=shot_info.atmo.density_ratio,
            )
        )

        if shot_info.ammo.use_powder_sensitivity:
            self.__shot.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp)._fps
        else:
            self.__shot.muzzle_velocity = shot_info.ammo.mv._fps
        cy_update_stability_coefficient(&self.__shot)

        self.ws = _WindSock(shot_info.winds)


    cdef object _zero_angle(TrajectoryCalc self, object shot_info, object distance):
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
        self.__shot.barrel_azimuth = 0.0
        self.__shot.barrel_elevation = atan(height_at_zero / zero_distance)
        self.__shot.twist = 0
        maximum_range -= 1.5 * self.__shot.calc_step

        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > _cZeroFindingAccuracy and iterations_count < _cMaxIterations:
            t = self._integrate(maximum_range, zero_distance, CTrajFlag.NONE)[0]
            height = t.height._feet  # use there internal shortcut instead of (t.height >> Distance.Foot)
            zero_finding_error = fabs(height - height_at_zero)
            if zero_finding_error > _cZeroFindingAccuracy:
                self.__shot.barrel_elevation -= (height - height_at_zero) / zero_distance
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1
        self._free_trajectory()
        if zero_finding_error > _cZeroFindingAccuracy:
            raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self.__shot.barrel_elevation))
        return Angular.Radian(self.__shot.barrel_elevation)


    cdef list[object] _integrate(TrajectoryCalc self,
                          double maximum_range, double step, int filter_flags, double time_step = 0.0):
        cdef:
            double velocity, delta_time
            double density_factor = .0
            double mach = .0
            list[object] ranges = []
            double time = .0
            double drag = .0
            CVector range_vector, velocity_vector
            CVector delta_range_vector, velocity_adjusted
            CVector gravity_vector = CVector(.0, self.__config.cGravityConstant, .0)
            double calc_step = self.__shot.calc_step

            # region Initialize wind-related variables to first wind reading (if any)
            CVector wind_vector = self.ws.current_vector()
            # endregion

            _TrajectoryDataFilter data_filter

        cdef:
            # early bindings
            double _cMinimumVelocity = self.__config.cMinimumVelocity
            double _cMaximumDrop = self.__config.cMaximumDrop
            double _cMinimumAltitude = self.__config.cMinimumAltitude

        cdef:
            # temp vectors
            CVector _dir_vector, _temp1, _temp2, _temp3

        # region Initialize velocity and position of projectile
        velocity = self.__shot.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = CVector(.0, -self.__shot.cant_cosine * self.__shot.sight_height, -self.__shot.cant_sine * self.__shot.sight_height)
        _dir_vector = CVector(cos(self.__shot.barrel_elevation) * cos(self.__shot.barrel_azimuth),
                                 sin(self.__shot.barrel_elevation),
                                 cos(self.__shot.barrel_elevation) * sin(self.__shot.barrel_azimuth))
        velocity_vector = mul_c(&_dir_vector, velocity)
        # endregion

        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags,
                                            ranges_length=<int> ((maximum_range / step) + 1),
                                            time_step=time_step)
        data_filter.setup_seen_zero(range_vector.y, self.__shot.barrel_elevation, self.__shot.look_angle)

        #region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        cdef int it = 0
        while range_vector.x <= maximum_range + calc_step:
            it += 1
            data_filter.current_flag = CTrajFlag.NONE

            # Update wind reading at current point in trajectory
            if range_vector.x >= self.ws.next_range:  # require check before call to improve performance
                wind_vector = self.ws.vector_for_range(range_vector.x)

            # overwrite density_factor and mach by pointer
            update_density_factor_and_mach_for_altitude(&self.__shot.atmo,
                self.__shot.alt0 + range_vector.y, &density_factor, &mach)

            if filter_flags:

                # Record TrajectoryData row
                # if data_filter.should_record(range_vector, velocity, mach, step, self.look_angle, time):
                if data_filter.should_record(range_vector, velocity, mach, step, time):
                    ranges.append(create_trajectory_row(
                        time, range_vector, velocity_vector,
                        velocity, mach, cy_spin_drift(&self.__shot, time), self.__shot.look_angle,
                        density_factor, drag, self.__shot.weight, data_filter.current_flag
                    ))
                    if data_filter.should_break():
                        break

            #region Ballistic calculation step
            # use just cdef methods to

            velocity_adjusted = sub(&velocity_vector, &wind_vector)
            velocity = mag(&velocity_adjusted)
            delta_time = calc_step / max(1.0, velocity)
            drag = density_factor * velocity * cy_drag_by_mach(&self.__shot, velocity / mach)

            _temp1 = mul_c(&velocity_adjusted, drag)
            _temp2 = sub(&_temp1, &gravity_vector)
            _temp3 = mul_c(&_temp2, delta_time)

            velocity_vector = sub(&velocity_vector, &_temp3)

            delta_range_vector = mul_c(&velocity_vector, delta_time)
            range_vector = add(&range_vector, &delta_range_vector)

            velocity = mag(&velocity_vector)
            time += delta_time

            if (
                    velocity < _cMinimumVelocity
                    or range_vector.y < _cMaximumDrop
                    or self.__shot.alt0 + range_vector.y < _cMinimumAltitude
            ):
                if velocity < _cMinimumVelocity:
                    reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
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
                velocity, mach, cy_spin_drift(&self.__shot, time), self.__shot.look_angle,
                density_factor, drag, self.__shot.weight, CTrajFlag.NONE))
        logger.debug(f"euler cy it {it}")
        return ranges


cdef object create_trajectory_row(double time, CVector range_vector, CVector velocity_vector,
                           double velocity, double mach, double spin_drift, double look_angle,
                           double density_factor, double drag, double weight, int flag):

    cdef:
        double windage = range_vector.z + spin_drift
        double drop_adjustment = cy_get_correction(range_vector.x, range_vector.y)
        double windage_adjustment = cy_get_correction(range_vector.x, windage)
        double trajectory_angle = atan2(velocity_vector.y, velocity_vector.x);

    return TrajectoryData(
        time=time,
        distance=_new_feet(range_vector.x),
        velocity=_new_fps(velocity),
        mach=velocity / mach,
        height=_new_feet(range_vector.y),
        target_drop=_new_feet(
            (range_vector.y - range_vector.x * tan(look_angle)) * cos(look_angle)
        ),
        drop_adj=_new_rad(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=_new_feet(windage),
        windage_adj=_new_rad(windage_adjustment),
        look_distance=_new_feet(range_vector.x / cos(look_angle)),
        angle=_new_rad(trajectory_angle),
        density_factor=density_factor - 1,
        drag=drag,
        energy=_new_ft_lb(cy_calculate_energy(weight, velocity)),
        ogw=_new_lb(cy_calculate_ogw(weight, velocity)),
        flag=flag
    )


cdef object _new_feet(double v):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


cdef object _new_fps(double v):
    d = object.__new__(Velocity)
    d._value = v / 3.2808399
    d._defined_units = Unit.FPS
    return d


cdef object _new_rad(double v):
    d = object.__new__(Angular)
    d._value = v
    d._defined_units = Unit.Radian
    return d


cdef object _new_ft_lb(double v):
    d = object.__new__(Energy)
    d._value = v
    d._defined_units = Unit.FootPound
    return d


cdef object _new_lb(double v):
    d = object.__new__(Weight)
    d._value = v / 0.000142857143
    d._defined_units = Unit.Pound
    return d



# # using integrate_1() slower than direct operations
# integrate(&range_vector, &velocity_vector, &wind_vector, &gravity_vector, &time, &drag, &velocity,
#           density_factor, mach, calc_step, self.drag_by_mach)

# cdef void integrate_1(CVector *range_vector, CVector *velocity_vector, CVector *wind_vector,
#                       CVector *gravity_vector, double *time, double *drag, double *velocity,
#                       double density_factor, double mach, double calc_step,
#                       object drag_by_mach):
#     cdef CVector velocity_adjusted
#     cdef CVector delta_range_vector
#     cdef CVector _temp1, _temp2, _temp3
#     cdef double delta_time
#
#     velocity_adjusted = sub(velocity_vector, wind_vector)
#     velocity[0] = mag(&velocity_adjusted)
#     delta_time = calc_step / max(1.0, velocity[0])
#
#     # Call function pointer
#     drag[0] = density_factor * velocity[0] * drag_by_mach(velocity[0] / mach)
#
#     _temp1 = mul_c(&velocity_adjusted, drag[0])
#     _temp2 = sub(&_temp1, gravity_vector)
#     _temp3 = mul_c(&_temp2, delta_time)
#
#     # Modify velocity_vector in place
#     velocity_vector[0] = sub(velocity_vector, &_temp3)
#
#     delta_range_vector = mul_c(velocity_vector, delta_time)
#
#     # Modify range_vector in place
#     range_vector[0] = add(range_vector, &delta_range_vector)
#
#     velocity[0] = mag(velocity_vector)
#     time[0] += delta_time