# Total Score: 158, Possible Score: 12400
# Total Non-Empty Lines: 124
# Python Overhead Lines: 19
# Cythonization Percentage: 98.73%
# Python Overhead Lines Percentage: 15.32%


# noinspection PyUnresolvedReferences
from cython cimport final
from libc.math cimport fabs, sin, cos, tan, atan, atan2, fmin, fmax
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.vector cimport CVector, add, sub, mag, mul_c, mul_v, neg, norm, mag
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport CTrajFlag, BaseTrajData, TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    Config_t,
    ShotData_t,
    update_density_factor_and_mach_for_altitude,
    cy_spin_drift,
    cy_drag_by_mach,
)
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport (
    CythonizedBaseIntegrationEngine,
    _TrajectoryDataFilter,
    _WindSock,
    create_trajectory_row,
)

import warnings

from py_ballisticcalc.exceptions import RangeError


__all__ = (
    'CythonizedEulerIntegrationEngine'
)


cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):

    cdef list[object] _integrate(CythonizedEulerIntegrationEngine self,
                                 double maximum_range, double record_step, int filter_flags, double time_step = 0.0):
        cdef:
            double velocity, delta_time
            double density_factor = .0
            double mach = .0
            list[object] ranges = []
            double time = .0
            double drag = .0
            CVector range_vector, velocity_vector
            CVector delta_range_vector, velocity_adjusted
            CVector gravity_vector = CVector(.0, self._config_s.cGravityConstant, .0)
            double min_step
            double calc_step = self._shot_s.calc_step

            # region Initialize wind-related variables to first wind reading (if any)
            CVector wind_vector = self.ws.current_vector()
            # endregion

            _TrajectoryDataFilter data_filter
            BaseTrajData data

        cdef:
            # early bindings
            double _cMinimumVelocity = self._config_s.cMinimumVelocity
            double _cMaximumDrop = self._config_s.cMaximumDrop
            double _cMinimumAltitude = self._config_s.cMinimumAltitude

        cdef:
            # temp vector
            CVector _tv

        # region Initialize velocity and position of projectile
        velocity = self._shot_s.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = CVector(.0, -self._shot_s.cant_cosine * self._shot_s.sight_height, -self._shot_s.cant_sine * self._shot_s.sight_height)
        _tv = CVector(cos(self._shot_s.barrel_elevation) * cos(self._shot_s.barrel_azimuth),
                                 sin(self._shot_s.barrel_elevation),
                                 cos(self._shot_s.barrel_elevation) * sin(self._shot_s.barrel_azimuth))
        velocity_vector = mul_c(&_tv, velocity)
        # endregion

        min_step = fmin(calc_step, record_step)
        # With non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=record_step,
                        initial_position=range_vector, initial_velocity=velocity_vector, time_step=time_step)
        data_filter.setup_seen_zero(range_vector.y, self._shot_s.barrel_elevation, self._shot_s.look_angle)

        #region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop

        while range_vector.x <= maximum_range + min_step:

            data_filter.current_flag = CTrajFlag.NONE

            # Update wind reading at current point in trajectory
            if range_vector.x >= self.ws.next_range:  # require check before call to improve performance
                wind_vector = self.ws.vector_for_range(range_vector.x)

            # overwrite density_factor and mach by pointer
            update_density_factor_and_mach_for_altitude(&self._shot_s.atmo,
                self._shot_s.alt0 + range_vector.y, &density_factor, &mach)

            if filter_flags:

                # Record TrajectoryData row
                data = data_filter.should_record(range_vector, velocity_vector, mach, time)
                if data is not None:        
                    ranges.append(create_trajectory_row(
                        data.time, data.position, data.velocity, mag(&data.velocity), data.mach,
                        cy_spin_drift(&self._shot_s, time), self._shot_s.look_angle,
                        density_factor, drag, self._shot_s.weight, data_filter.current_flag
                    ))

            #region Ballistic calculation step
            # use just cdef methods to maximize speed

            velocity_adjusted = sub(&velocity_vector, &wind_vector)
            velocity = mag(&velocity_adjusted)
            delta_time = calc_step / fmax(1.0, velocity)
            drag = density_factor * velocity * cy_drag_by_mach(&self._shot_s, velocity / mach)

            _tv = mul_c(&velocity_adjusted, drag)
            _tv = sub(&_tv, &gravity_vector)
            _tv = mul_c(&_tv, delta_time)

            velocity_vector = sub(&velocity_vector, &_tv)

            delta_range_vector = mul_c(&velocity_vector, delta_time)
            range_vector = add(&range_vector, &delta_range_vector)

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
