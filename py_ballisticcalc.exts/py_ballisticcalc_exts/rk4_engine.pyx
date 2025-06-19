# Total Score: 2394, Possible Score: 45200
# Total Non-Empty Lines: 452
# Python Overhead Lines: 152
# Cythonization Percentage: 94.70%
# Python Overhead Lines Percentage: 33.63%


# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2, fmin, fmax, pow
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport CTrajFlag, BaseTrajData, TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    Config_t,
    ShotData_t,
    update_density_factor_and_mach_for_altitude,
    cy_spin_drift,
    cy_drag_by_mach,
    cy_get_calc_step,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
    _TrajectoryDataFilter,
    _WindSock,
    create_trajectory_row,

    createTrajectoryDataFilter,
    should_record,
    setup_seen_zero
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT, add, sub, mag, mulS
)

import warnings

from py_ballisticcalc.exceptions import RangeError


__all__ = (
    'CythonizedRK4IntegrationEngine'
)


cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):

    cdef list[object] _integrate(CythonizedRK4IntegrationEngine self,
                                 double maximum_range, double record_step, int filter_flags, double time_step = 0.0):
        cdef:
            double velocity, delta_time
            double density_factor = .0
            double mach = .0
            list[object] ranges = []
            double time = .0
            double drag = .0
            V3dT range_vector, velocity_vector
            V3dT delta_range_vector, velocity_adjusted
            V3dT gravity_vector = V3dT(.0, self._config_s.cGravityConstant, .0)
            double min_step
            double calc_step = self._shot_s.calc_step

            # region Initialize wind-related variables to first wind reading (if any)
            V3dT wind_vector = self.ws.current_vector()
            # endregion

            _TrajectoryDataFilter data_filter
            BaseTrajData data

        cdef:
            # early bindings
            double _cMinimumVelocity = self._config_s.cMinimumVelocity
            double _cMaximumDrop = self._config_s.cMaximumDrop
            double _cMinimumAltitude = self._config_s.cMinimumAltitude

        cdef:
            double last_recorded_range, rk_calc_step

        # temp variables
        cdef:
            double relative_speed
            V3dT relative_velocity
            V3dT _dir_vector, _temp_add_operand, _temp_v_result, _temp_p_result
            V3dT _v_sum_intermediate, _p_sum_intermediate
            V3dT v1, v2, v3, v4, p1, p2, p3, p4

        # region Initialize velocity and position of projectile
        velocity = self._shot_s.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = V3dT(.0, -self._shot_s.cant_cosine * self._shot_s.sight_height, -self._shot_s.cant_sine * self._shot_s.sight_height)
        _dir_vector = V3dT(
            cos(self._shot_s.barrel_elevation) * cos(self._shot_s.barrel_azimuth),
            sin(self._shot_s.barrel_elevation),
            cos(self._shot_s.barrel_elevation) * sin(self._shot_s.barrel_azimuth)
        )
        velocity_vector = mulS(&_dir_vector, velocity)
        # endregion

        # rk_calc_step = 4. * calc_step
        # rk_calc_step = calc_step ** (1/2)  # FIXME: (1/2) allowed only with compiler directive: cdivision=False
        rk_calc_step = pow(calc_step, 0.5)  # NOTE: recommended by https://github.com/serhiy-yevtushenko

        min_step = fmin(calc_step, record_step)
        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = createTrajectoryDataFilter(filter_flags=filter_flags, range_step=record_step,
                        initial_position=range_vector, initial_velocity=velocity_vector, time_step=time_step)
        setup_seen_zero(&data_filter, range_vector.y, self._shot_s.barrel_elevation, self._shot_s.look_angle)

        #region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop

        last_recorded_range = 0.0

        while (range_vector.x <= maximum_range + min_step) or (
                filter_flags and last_recorded_range <= maximum_range - 1e-6):

            # Update wind reading at current point in trajectory
            if range_vector.x >= self.ws.next_range:  # require check before call to improve performance
                wind_vector = self.ws.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            # overwrite density_factor and mach by pointer
            update_density_factor_and_mach_for_altitude(&self._shot_s.atmo,
                self._shot_s.alt0 + range_vector.y, &density_factor, &mach)

            # region Check whether to record TrajectoryData row at current point
            if filter_flags:  # require check before call to improve performance
                # Record TrajectoryData row
                data = should_record(&data_filter, range_vector, velocity_vector, mach, time)
                if data is not None:
                    ranges.append(create_trajectory_row(
                        data.time, data.position, data.velocity, mag(&data.velocity), data.mach,
                        cy_spin_drift(&self._shot_s, time), self._shot_s.look_angle,
                        density_factor, drag, self._shot_s.weight, data_filter.current_flag
                    ))
                    last_recorded_range = data.position.x
            # endregion

            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            relative_velocity = sub(&velocity_vector, &wind_vector)
            relative_speed = mag(&relative_velocity)

            # Time step is normalized by velocity so that we take smaller steps when moving faster
            delta_time = rk_calc_step / fmax(1.0, relative_speed)
            km = density_factor * cy_drag_by_mach(&self._shot_s, relative_speed / mach)
            drag = km * relative_speed

            # # region RK4 integration

            # region for Reference:
            # cdef V3dT f(V3dT v):  # dv/dt
            #     # Bullet velocity changes due to both drag and gravity
            #     return self.gravity_vector - km * v * v.magnitude()
            #
            # v1 = delta_time * f(relative_velocity)
            # v2 = delta_time * f(relative_velocity + 0.5 * v1)
            # v3 = delta_time * f(relative_velocity + 0.5 * v2)
            # v4 = delta_time * f(relative_velocity + v3)
            # p1 = delta_time * velocity_vector
            # p2 = delta_time * (velocity_vector + 0.5 * p1)
            # p3 = delta_time * (velocity_vector + 0.5 * p2)
            # p4 = delta_time * (velocity_vector + p3)
            # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)
            # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)
            # # endregion RK4 integration

            # v1 = delta_time * f(relative_velocity)
            _temp_v_result = _f_dvdt(&relative_velocity, &gravity_vector, km)
            v1 = mulS(&_temp_v_result, delta_time)

            # v2 = delta_time * f(relative_velocity + 0.5 * v1)
            _temp_add_operand = mulS(&v1, 0.5)  # Store temporary result
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            _temp_v_result = _f_dvdt(&_temp_v_result, &gravity_vector, km)
            v2 = mulS(&_temp_v_result, delta_time)

            # v3 = delta_time * f(relative_velocity + 0.5 * v2)
            _temp_add_operand = mulS(&v2, 0.5)  # Store temporary result
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            _temp_v_result = _f_dvdt(&_temp_v_result, &gravity_vector, km)
            v3 = mulS(&_temp_v_result, delta_time)

            # v4 = delta_time * f(relative_velocity + v3)
            _temp_v_result = add(&relative_velocity, &v3)
            _temp_v_result = _f_dvdt(&_temp_v_result, &gravity_vector, km)
            v4 = mulS(&_temp_v_result, delta_time)

            # p1 = delta_time * velocity_vector
            p1 = mulS(&velocity_vector, delta_time)

            # p2 = delta_time * (velocity_vector + 0.5 * p1)
            _temp_add_operand = mulS(&p1, 0.5)  # Store temporary result
            _temp_p_result = add(&velocity_vector, &_temp_add_operand)
            p2 = mulS(&_temp_p_result, delta_time)

            # p3 = delta_time * (velocity_vector + 0.5 * p2)
            _temp_add_operand = mulS(&p2, 0.5)  # Store temporary result
            _temp_p_result = add(&velocity_vector, &_temp_add_operand)
            p3 = mulS(&_temp_p_result, delta_time)

            # p4 = delta_time * (velocity_vector + p3)
            _temp_p_result = add(&velocity_vector, &p3)
            p4 = mulS(&_temp_p_result, delta_time)

            # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)
            # Break down the sum and scalar multiplication to avoid "non-lvalue" errors
            _temp_add_operand = mulS(&v2, 2.0)
            _v_sum_intermediate = add(&v1, &_temp_add_operand)

            _temp_add_operand = mulS(&v3, 2.0)
            _v_sum_intermediate = add(&_v_sum_intermediate, &_temp_add_operand)

            _v_sum_intermediate = add(&_v_sum_intermediate, &v4)
            _v_sum_intermediate = mulS(&_v_sum_intermediate, (1.0 / 6.0))
            velocity_vector = add(&velocity_vector, &_v_sum_intermediate)

            # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)
            # Break down the sum and scalar multiplication
            _temp_add_operand = mulS(&p2, 2.0)
            _p_sum_intermediate = add(&p1, &_temp_add_operand)

            _temp_add_operand = mulS(&p3, 2.0)
            _p_sum_intermediate = add(&_p_sum_intermediate, &_temp_add_operand)

            _p_sum_intermediate = add(&_p_sum_intermediate, &p4)
            _p_sum_intermediate = mulS(&_p_sum_intermediate, (1.0 / 6.0))
            range_vector = add(&range_vector, &_p_sum_intermediate)

            # region for Reference: Euler integration
            # velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time
            # delta_range_vector = velocity_vector * delta_time
            # range_vector += delta_range_vector
            # endregion Euler integration

            velocity = mag(&velocity_vector)
            time += delta_time

            if (
                    velocity < _cMinimumVelocity
                    or range_vector.y < _cMaximumDrop
                    or self._shot_s.alt0 + range_vector.y < _cMinimumAltitude
            ):
                ranges.append(create_trajectory_row(
                    time, range_vector, velocity_vector,
                    velocity, mach, cy_spin_drift(&self._shot_s, time), self._shot_s.look_angle,
                    density_factor, drag, self._shot_s.weight, data_filter.current_flag
                ))

                if velocity < _cMinimumVelocity:
                    reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    reason = RangeError.MaximumDropReached
                else:
                    reason = RangeError.MinimumAltitudeReached
                raise RangeError(reason, ranges)
            #endregion

        #endregion
        # Ensure that we have at least two data points in trajectory
        if len(ranges) < 2:
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity, mach, cy_spin_drift(&self._shot_s, time), self._shot_s.look_angle,
                density_factor, drag, self._shot_s.weight, CTrajFlag.NONE))

        return ranges


# This function calculates dv/dt for velocity (v) affected by gravity and drag.
# It now takes gravity_vector and km as explicit arguments.
cdef V3dT _f_dvdt(V3dT *v_ptr, V3dT *gravity_vector_ptr, double km_coeff):
    cdef V3dT drag_force_component
    # Bullet velocity changes due to both drag and gravity
    # Original: return self.gravity_vector - km * v * v.magnitude()
    drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr))
    return sub(gravity_vector_ptr, &drag_force_component)