# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
import math
import warnings

from typing_extensions import Union, List, override

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.engines.base_engine import (BaseIntegrationEngine,
                                                  BaseEngineConfigDict,
                                                  _TrajectoryDataFilter,
                                                  _WindSock,
                                                  create_trajectory_row)
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from examples.integrators.vector_inline_op import Vector

__all__ = ('RK4IntegrationEngine',)


class RK4IntegrationEngine(BaseIntegrationEngine[BaseEngineConfigDict]):

    @override
    def get_calc_step(self, step: float = 0) -> float:
        # RK steps can be larger than calc_step default on Euler integrator
        # min_step ensures that with small record steps the loop runs far enough to get desired points
        # adjust Euler default step to RK4 algorythm
        # NOTE: pow(step, 0.5) recommended by https://github.com/serhiy-yevtushenko
        # return super().get_calc_step(step) ** 0.5
        # FIXME: the tests/test_incomplete_shots.py::test_vertical_shot fails with atol 0.1,
        #   should be adjusted?
        print("STEEEP", math.pow(super().get_calc_step(step), 0.5))
        return math.pow(super().get_calc_step(step), 0.5)

    @override
    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List[TrajectoryData]:
        """
        Calculate trajectory for specified shot

        Args:
            shot_info (Shot): Information about the shot.
            maximum_range (float): Feet down range to stop calculation
            record_step (float): Frequency (in feet down range) to record TrajectoryData
            filter_flags (Union[TrajFlag, int]): Flags to filter trajectory data.
            time_step (float, optional): If > 0 then record TrajectoryData after this many seconds elapse
                since last record, as could happen when trajectory is nearly vertical
                and there is too little movement downrange to trigger a record based on range.
                Defaults to 0.0

        Returns:
            List[TrajectoryData]: list of TrajectoryData, one for each dist_step, out to max_range
        """

        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = self._config.cMaximumDrop
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: List[TrajectoryData] = []  # Record of TrajectoryData points to return
        time: float = .0
        drag: float = .0

        # guarantee that mach and density_ratio would be referenced before assignment
        mach: float = .0
        density_ratio: float = .0

        # region Initialize wind-related variables to first wind reading (if any)
        wind_sock = _WindSock(shot_info.winds)
        wind_vector = wind_sock.current_vector()
        # endregion

        # region Initialize velocity and position of projectile
        velocity = self.muzzle_velocity
        # x: downrange distance, y: drop, z: windage
        range_vector = Vector(.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
        velocity_vector: Vector = Vector(
            math.cos(self.barrel_elevation_rad) * math.cos(self.barrel_azimuth_rad),
            math.sin(self.barrel_elevation_rad),
            math.cos(self.barrel_elevation_rad) * math.sin(self.barrel_azimuth_rad)
        ).mul_by_const(velocity)  # type: ignore
        # endregion

        min_step = min(self.calc_step, record_step)
        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=record_step,
                                            initial_position=range_vector, initial_velocity=velocity_vector,
                                            barrel_angle_rad=self.barrel_elevation_rad, look_angle_rad=self.look_angle_rad,
                                            time_step=time_step)

        # region Trajectory Loop
        warnings.simplefilter("once")  # used to avoid multiple warnings in a loop
        last_recorded_range = 0.0

        it = 0  # iteration counter

        # gravity vector individual components
        gx, gy, gz = self.gravity_vector.x, self.gravity_vector.y, self.gravity_vector.z

        while (range_vector.x <= maximum_range + min_step) or (
                filter_flags and last_recorded_range <= maximum_range - 1e-6):
            it += 1

            # Update wind reading at current point in trajectory
            if range_vector.x >= wind_sock.next_range:  # require check before call to improve performance
                wind_vector = wind_sock.vector_for_range(range_vector.x)

            # Update air density at current point in trajectory
            density_ratio, mach = shot_info.atmo.get_density_and_mach_for_altitude(
                self.alt0 + range_vector.y)

            # region Check whether to record TrajectoryData row at current point
            if filter_flags:  # require check before call to improve performance
                # Record TrajectoryData row
                if (data := data_filter.record(range_vector, velocity_vector, mach, time)) is not None:
                    ranges.append(create_trajectory_row(data.time, data.position, data.velocity,
                                                        data.velocity.magnitude(), data.mach,
                                                        self.spin_drift(data.time), self.look_angle_rad,
                                                        density_ratio, drag, self.weight, data_filter.current_flag
                                                        ))
                    last_recorded_range = data.position.x
            # endregion

            # Air resistance seen by bullet is ground velocity minus wind velocity relative to ground
            rel_vel_x = velocity_vector.x - wind_vector.x
            rel_vel_y = velocity_vector.y - wind_vector.y
            rel_vel_z = velocity_vector.z - wind_vector.z

            # Recalculate magnitude using individual components
            relative_speed = math.hypot(rel_vel_x, rel_vel_y, rel_vel_z)  # Velocity relative to air
            # Time step is normalized by velocity so that we take smaller steps when moving faster
            delta_time = self.calc_step / max(1.0, relative_speed)
            km = density_ratio * self.drag_by_mach(relative_speed / mach)
            drag = km * relative_speed

            # region RK4 integration (component-wise)
            # dv/dt = gravity_vector - km * v * |v|
            # We define f as a function that operates on components
            def _f_dvdt(vx: float, vy: float, vz: float, magnitude: float) -> tuple[float, float, float]:
                # Bullet velocity changes due to both drag and gravity
                # Gravity is in the negative Y direction
                fx = gx - km * vx * magnitude
                fy = gy - km * vy * magnitude
                fz = gz - km * vz * magnitude
                return fx, fy, fz

            # --- k values for velocity update (dv/dt) ---
            # k1
            k1_vx, k1_vy, k1_vz = _f_dvdt(rel_vel_x, rel_vel_y, rel_vel_z, relative_speed)
            k1_vx *= delta_time
            k1_vy *= delta_time
            k1_vz *= delta_time

            # k2
            k2_rel_vx = rel_vel_x + 0.5 * k1_vx
            k2_rel_vy = rel_vel_y + 0.5 * k1_vy
            k2_rel_vz = rel_vel_z + 0.5 * k1_vz
            k2_rel_magnitude = math.hypot(k2_rel_vx, k2_rel_vy, k2_rel_vz)
            k2_vx, k2_vy, k2_vz = _f_dvdt(k2_rel_vx, k2_rel_vy, k2_rel_vz, k2_rel_magnitude)
            k2_vx *= delta_time
            k2_vy *= delta_time
            k2_vz *= delta_time

            # k3
            k3_rel_vx = rel_vel_x + 0.5 * k2_vx
            k3_rel_vy = rel_vel_y + 0.5 * k2_vy
            k3_rel_vz = rel_vel_z + 0.5 * k2_vz
            k3_rel_magnitude = math.hypot(k3_rel_vx, k3_rel_vy, k3_rel_vz)
            k3_vx, k3_vy, k3_vz = _f_dvdt(k3_rel_vx, k3_rel_vy, k3_rel_vz, k3_rel_magnitude)
            k3_vx *= delta_time
            k3_vy *= delta_time
            k3_vz *= delta_time

            # k4
            k4_rel_vx = rel_vel_x + k3_vx
            k4_rel_vy = rel_vel_y + k3_vy
            k4_rel_vz = rel_vel_z + k3_vz
            k4_rel_magnitude = math.hypot(k4_rel_vx, k4_rel_vy, k4_rel_vz)
            k4_vx, k4_vy, k4_vz = _f_dvdt(k4_rel_vx, k4_rel_vy, k4_rel_vz, k4_rel_magnitude)
            k4_vx *= delta_time
            k4_vy *= delta_time
            k4_vz *= delta_time

            # --- k values for position update (dr/dt = v) ---
            # For position, the derivative is just the velocity vector itself.
            # So, p_k = delta_time * v_at_k_step

            # p1
            p1_vx = delta_time * velocity_vector.x
            p1_vy = delta_time * velocity_vector.y
            p1_vz = delta_time * velocity_vector.z

            # p2 (v_at_k2 = velocity_vector + 0.5 * k1_v)
            p2_vx = delta_time * (velocity_vector.x + 0.5 * k1_vx)
            p2_vy = delta_time * (velocity_vector.y + 0.5 * k1_vy)
            p2_vz = delta_time * (velocity_vector.z + 0.5 * k1_vz)

            # p3 (v_at_k3 = velocity_vector + 0.5 * k2_v)
            p3_vx = delta_time * (velocity_vector.x + 0.5 * k2_vx)
            p3_vy = delta_time * (velocity_vector.y + 0.5 * k2_vy)
            p3_vz = delta_time * (velocity_vector.z + 0.5 * k2_vz)

            # p4 (v_at_k4 = velocity_vector + k3_v)
            p4_vx = delta_time * (velocity_vector.x + k3_vx)
            p4_vy = delta_time * (velocity_vector.y + k3_vy)
            p4_vz = delta_time * (velocity_vector.z + k3_vz)

            # --- Update velocity_vector and range_vector ---
            # velocity_vector += (v1 + 2 * v2 + 2 * v3 + v4) * (1 / 6.0)
            factor_div_6 = (1 / 6.0)

            new_vel_x = velocity_vector.x + (k1_vx + 2 * k2_vx + 2 * k3_vx + k4_vx) * factor_div_6
            new_vel_y = velocity_vector.y + (k1_vy + 2 * k2_vy + 2 * k3_vy + k4_vy) * factor_div_6
            new_vel_z = velocity_vector.z + (k1_vz + 2 * k2_vz + 2 * k3_vz + k4_vz) * factor_div_6
            velocity_vector = Vector(new_vel_x, new_vel_y, new_vel_z)  # One Vector object created

            # range_vector += (p1 + 2 * p2 + 2 * p3 + p4) * (1 / 6.0)
            new_range_x = range_vector.x + (p1_vx + 2 * p2_vx + 2 * p3_vx + p4_vx) * factor_div_6
            new_range_y = range_vector.y + (p1_vy + 2 * p2_vy + 2 * p3_vy + p4_vy) * factor_div_6
            new_range_z = range_vector.z + (p1_vz + 2 * p2_vz + 2 * p3_vz + p4_vz) * factor_div_6
            range_vector = Vector(new_range_x, new_range_y, new_range_z)  # One Vector object created

            # endregion RK4 integration

            velocity = math.hypot(new_vel_x, new_vel_y, new_vel_z)  # Velocity relative to ground
            time += delta_time

            if (
                    velocity < _cMinimumVelocity
                    or range_vector.y < _cMaximumDrop
                    or self.alt0 + range_vector.y < _cMinimumAltitude
            ):
                ranges.append(create_trajectory_row(
                    time, range_vector, velocity_vector,
                    velocity, mach, self.spin_drift(time), self.look_angle_rad,
                    density_ratio, drag, self.weight, data_filter.current_flag
                ))
                if velocity < _cMinimumVelocity:
                    reason = RangeError.MinimumVelocityReached
                elif range_vector.y < _cMaximumDrop:
                    reason = RangeError.MaximumDropReached
                else:
                    reason = RangeError.MinimumAltitudeReached
                raise RangeError(reason, ranges)
                # break
        # endregion Trajectory Loop

        # Ensure that we have at least two data points in trajectory
        if len(ranges) < 2:
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity, mach, self.spin_drift(time), self.look_angle_rad,
                density_ratio, drag, self.weight, TrajFlag.NONE))
        logger.debug(f"RK4 ran {it} iterations")
        return ranges
