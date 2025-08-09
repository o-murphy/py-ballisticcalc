# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2, fmin, fmax, pow
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport TrajFlag_t, BaseTrajData, TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    Config_t,
    ShotData_t,
    ShotData_t_dragByMach,
    Atmosphere_t_updateDensityFactorAndMachForAltitude,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
    TrajDataFilter_t,

    WindSock_t_currentVector,
    WindSock_t_vectorForRange,

    create_trajectory_row,

    TrajDataFilter_t_create,
    TrajDataFilter_t_setup_seen_zero,
    TrajDataFilter_t_should_record,
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT, add, sub, mag, mulS


import warnings

from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.trajectory_data import HitResult

__all__ = (
    'CythonizedRK4IntegrationEngine'
)

cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):

    cdef double get_calc_step(CythonizedRK4IntegrationEngine self):
        return 0.0015 * CythonizedBaseIntegrationEngine.get_calc_step(self)  # like super().get_calc_step()

    cdef object _integrate(CythonizedRK4IntegrationEngine self,
                                 double range_limit_ft, double range_step_ft,
                                 double time_step, int filter_flags,
                                 bint dense_output):
        cdef:
            double velocity, delta_time
            double density_ratio = .0
            double mach = .0
            list[object] ranges = []
            double time = .0
            double drag = .0
            V3dT range_vector, velocity_vector
            V3dT relative_velocity
            V3dT gravity_vector = V3dT(.0, self._config_s.cGravityConstant, .0)
            double min_step
            double calc_step = self._shot_s.calc_step

            # region Initialize wind-related variables to first wind reading (if any)
            V3dT wind_vector = WindSock_t_currentVector(self._wind_sock)
            # endregion

            TrajDataFilter_t data_filter
            BaseTrajData data

        cdef:
            # early bindings
            double _cMinimumVelocity = self._config_s.cMinimumVelocity
            double _cMinimumAltitude = self._config_s.cMinimumAltitude
            double _cMaximumDrop = -abs(self._config_s.cMaximumDrop)  # Ensure it's negative

        cdef:
            double last_recorded_range
            str termination_reason

        # temp variables
        cdef:
            double relative_speed
            V3dT _dir_vector, _temp_add_operand, _temp_v_result
            V3dT _v_sum_intermediate, _p_sum_intermediate
            V3dT v1, v2, v3, v4, p1, p2, p3, p4

        # region Initialize velocity and position of projectile
        velocity = self._shot_s.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = V3dT(.0, -self._shot_s.cant_cosine * self._shot_s.sight_height,
                            -self._shot_s.cant_sine * self._shot_s.sight_height)
        _dir_vector = V3dT(
            cos(self._shot_s.barrel_elevation) * cos(self._shot_s.barrel_azimuth),
            sin(self._shot_s.barrel_elevation),
            cos(self._shot_s.barrel_elevation) * sin(self._shot_s.barrel_azimuth)
        )
        velocity_vector = mulS(&_dir_vector, velocity)
        # endregion

        min_step = fmin(calc_step, range_step_ft)
        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = TrajDataFilter_t_create(filter_flags=filter_flags, range_step=range_step_ft,
                                                initial_position_ptr=&range_vector,
                                                initial_velocity_ptr=&velocity_vector,
                                                time_step=time_step)
        TrajDataFilter_t_setup_seen_zero(&data_filter, range_vector.y, &self._shot_s)

        #region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        termination_reason = None
        last_recorded_range = 0.0

        while (range_vector.x <= range_limit_ft + min_step) or (
                last_recorded_range <= range_limit_ft - 1e-6):
            self.integration_step_count += 1

            # Update wind reading at current point in trajectory
            if range_vector.x >= self._wind_sock.next_range:  # require check before call to improve performance
                wind_vector = WindSock_t_vectorForRange(self._wind_sock, range_vector.x)

            # Update air density at current point in trajectory
            # overwrite density_ratio and mach by pointer
            Atmosphere_t_updateDensityFactorAndMachForAltitude(&self._shot_s.atmo,
                self._shot_s.alt0 + range_vector.y, &density_ratio, &mach)

            # region Check whether to record TrajectoryData row at current point
            data = TrajDataFilter_t_should_record(&data_filter, &range_vector, &velocity_vector, mach, time)
            if data is not None:
                ranges.append(create_trajectory_row(
                    data.time, &data.position, &data.velocity, data.mach,
                    &self._shot_s, density_ratio, drag, data_filter.current_flag
                ))
                last_recorded_range = data.position.x
            # endregion

            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            relative_velocity = sub(&velocity_vector, &wind_vector)
            relative_speed = mag(&relative_velocity)

            delta_time = calc_step
            km = density_ratio * ShotData_t_dragByMach(&self._shot_s, relative_speed / mach)
            drag = km * relative_speed

            # # region RK4 integration
            # region for Reference:
            # cdef V3dT f(V3dT v):  # dv/dt
            #     # Bullet velocity changes due to both drag and gravity
            #     return self.gravity_vector - km * v * v.magnitude()
            #
            # v1 = f(relative_velocity)
            # v2 = f(relative_velocity + 0.5 * delta_time * v1)
            # v3 = f(relative_velocity + 0.5 * delta_time * v2)
            # v4 = f(relative_velocity + delta_time * v3)
            # p1 = velocity_vector
            # p2 = (velocity_vector + 0.5 * delta_time * v1)
            # p3 = (velocity_vector + 0.5 * delta_time * v2)
            # p4 = (velocity_vector + delta_time * v3)
            # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (delta_time / 6.0)
            # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (delta_time / 6.0)
            # # endregion for Reference

            # v1 = f(relative_velocity)
            v1 = _f_dvdt(&relative_velocity, &gravity_vector, km)

            # v2 = f(relative_velocity + 0.5 * delta_time * v1)
            _temp_add_operand = mulS(&v1, 0.5 * delta_time)
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            v2 = _f_dvdt(&_temp_v_result, &gravity_vector, km)

            # v3 = f(relative_velocity + 0.5 * delta_time * v2)
            _temp_add_operand = mulS(&v2, 0.5 * delta_time)
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            v3 = _f_dvdt(&_temp_v_result, &gravity_vector, km)

            # v4 = f(relative_velocity + delta_time * v3)
            _temp_add_operand = mulS(&v3, delta_time)
            _temp_v_result = add(&relative_velocity, &_temp_add_operand)
            v4 = _f_dvdt(&_temp_v_result, &gravity_vector, km)

            # p1 = velocity_vector
            p1 = velocity_vector

            # p2 = (velocity_vector + 0.5 * delta_time * v1)
            _temp_add_operand = mulS(&v1, 0.5 * delta_time)
            p2 = add(&velocity_vector, &_temp_add_operand)

            # p3 = (velocity_vector + 0.5 * delta_time * v2)
            _temp_add_operand = mulS(&v2, 0.5 * delta_time)
            p3 = add(&velocity_vector, &_temp_add_operand)

            # p4 = (velocity_vector + delta_time * v3)
            _temp_add_operand = mulS(&v3, delta_time)
            p4 = add(&velocity_vector, &_temp_add_operand)

            # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (delta_time / 6.0)
            # Break down the sum and scalar multiplication to avoid "non-lvalue" errors
            _temp_add_operand = mulS(&v2, 2.0)
            _v_sum_intermediate = add(&v1, &_temp_add_operand)
            _temp_add_operand = mulS(&v3, 2.0)
            _v_sum_intermediate = add(&_v_sum_intermediate, &_temp_add_operand)
            _v_sum_intermediate = add(&_v_sum_intermediate, &v4)
            _v_sum_intermediate = mulS(&_v_sum_intermediate, (delta_time / 6.0))
            velocity_vector = add(&velocity_vector, &_v_sum_intermediate)

            # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (delta_time / 6.0)
            # Break down the sum and scalar multiplication
            _temp_add_operand = mulS(&p2, 2.0)
            _p_sum_intermediate = add(&p1, &_temp_add_operand)
            _temp_add_operand = mulS(&p3, 2.0)
            _p_sum_intermediate = add(&_p_sum_intermediate, &_temp_add_operand)
            _p_sum_intermediate = add(&_p_sum_intermediate, &p4)
            _p_sum_intermediate = mulS(&_p_sum_intermediate, (delta_time / 6.0))
            range_vector = add(&range_vector, &_p_sum_intermediate)
            # endregion RK4 integration

            # region for Reference: Euler integration
            # velocity_vector -= (relative_velocity * drag - self.gravity_vector) * delta_time
            # delta_range_vector = velocity_vector * delta_time
            # range_vector += delta_range_vector
            # endregion Euler integration

            velocity = mag(&velocity_vector)
            time += delta_time

            if (velocity < _cMinimumVelocity
                or range_vector.y < _cMaximumDrop
                or self._shot_s.alt0 + range_vector.y < _cMinimumAltitude
            ):
                if velocity < _cMinimumVelocity:
                    termination_reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    termination_reason = RangeError.MaximumDropReached
                else:
                    termination_reason = RangeError.MinimumAltitudeReached
                break
        #endregion Trajectory Loop
        data = TrajDataFilter_t_should_record(&data_filter, &range_vector, &velocity_vector, mach, time)
        if data is not None:
            ranges.append(create_trajectory_row(
                data.time, &data.position, &data.velocity, data.mach,
                &self._shot_s, density_ratio, drag, data_filter.current_flag
            ))
        # Ensure that we have at least two data points in trajectory, or 1 if filter_flags==NONE
        # ... as well as last point if we had an incomplete trajectory
        if (filter_flags and ((len(ranges) < 2) or termination_reason)) or len(ranges) == 0:
            if len(ranges) > 0 and ranges[-1].time == time:  # But don't duplicate the last point.
                pass
            else:
                ranges.append(create_trajectory_row(
                    time, &range_vector, &velocity_vector, mach,
                    &self._shot_s, density_ratio, drag, TrajFlag_t.NONE
                ))

        error = None
        if termination_reason is not None:
            error = RangeError(termination_reason, ranges)
        return (ranges, error)

# This function calculates dv/dt for velocity (v) affected by gravity and drag.
# It now takes gravity_vector and km as explicit arguments.
cdef V3dT _f_dvdt(const V3dT *v_ptr, const V3dT *gravity_vector_ptr, double km_coeff):
    cdef V3dT drag_force_component
    # Bullet velocity changes due to both drag and gravity
    # Original: return self.gravity_vector - km * v * v.magnitude()
    drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr))
    return sub(gravity_vector_ptr, &drag_force_component)
