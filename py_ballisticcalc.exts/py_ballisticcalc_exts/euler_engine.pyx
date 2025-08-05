# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2, fmin, fmax
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
    'CythonizedEulerIntegrationEngine'
)


cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):

    cdef double get_calc_step(CythonizedEulerIntegrationEngine self):
        return 0.5 * CythonizedBaseIntegrationEngine.get_calc_step(self)  # like super().get_calc_step()

    cdef object _integrate(CythonizedEulerIntegrationEngine self,
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
            V3dT  range_vector, velocity_vector
            V3dT  delta_range_vector, velocity_adjusted
            V3dT  gravity_vector = V3dT(.0, self._config_s.cGravityConstant, .0)
            double min_step
            double calc_step = self._shot_s.calc_step / 2.0

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
            # temp vector
            V3dT _tv

        cdef:
            double last_recorded_range
            str termination_reason

        # region Initialize velocity and position of projectile
        velocity = self._shot_s.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = V3dT(.0, -self._shot_s.cant_cosine * self._shot_s.sight_height, -self._shot_s.cant_sine * self._shot_s.sight_height)
        _tv = V3dT(cos(self._shot_s.barrel_elevation) * cos(self._shot_s.barrel_azimuth),
                                 sin(self._shot_s.barrel_elevation),
                                 cos(self._shot_s.barrel_elevation) * sin(self._shot_s.barrel_azimuth))
        velocity_vector = mulS(&_tv, velocity)
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

            #region Ballistic calculation step
            # use just cdef methods to maximize speed

            velocity_adjusted = sub(&velocity_vector, &wind_vector)
            velocity = mag(&velocity_adjusted)
            delta_time = calc_step / fmax(1.0, velocity)
            drag = density_ratio * velocity * ShotData_t_dragByMach(&self._shot_s, velocity / mach)

            _tv = mulS(&velocity_adjusted, drag)
            _tv = sub(&_tv, &gravity_vector)
            _tv = mulS(&_tv, delta_time)

            velocity_vector = sub(&velocity_vector, &_tv)

            delta_range_vector = mulS(&velocity_vector, delta_time)
            range_vector = add(&range_vector, &delta_range_vector)

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
            #endregion Ballistic calculation step
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
