"""Bootstrap to load binary TrajectoryCalc, Vector extensions"""

import math

from typing_extensions import Union, List

from py_ballisticcalc.conditions import Atmo, Shot
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_calc import *
from py_ballisticcalc.trajectory_calc import _get_only_mach_data, calculate_curve, CurvePoint, \
    _calculate_by_curve_and_mach_list
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Distance, Angular, Velocity, Weight, Pressure, Temperature
from py_ballisticcalc.vector import Vector


# pylint: disable=too-many-instance-attributes
class TrajectoryCalc:
    """
    All calculations are done in units of feet and fps.

    Attributes:
        barrel_azimuth (float): The azimuth angle of the barrel.
        barrel_elevation (float): The elevation angle of the barrel.
        twist (float): The twist rate of the barrel.
        gravity_vector (Vector): The gravity vector.
    """

    barrel_azimuth: float
    barrel_elevation: float
    twist: float
    gravity_vector: Vector

    def __init__(self, _config: Config):
        """
        Initializes the TrajectoryCalc class.

        Args:
            _config (Config): The configuration object.
        """
        self._config: Config = _config
        self.gravity_vector: Vector = Vector(.0, self._config.cGravityConstant, .0)

    @property
    def table_data(self) -> List[DragDataPoint]:
        """
        Gets the drag model table data.

        Returns:
            List[DragDataPoint]: A list of drag data points.
        """
        return self._table_data

    def get_calc_step(self, step: float = 0) -> float:
        """
        Keep step under max_calc_step_size

        Args:
            step (float, optional): proposed step size. Defaults to 0.

        Returns:
            float: step size for calculations (in feet)
        """
        preferred_step = self._config.max_calc_step_size_feet
        if step == 0:
            return preferred_step / 2.0
        return min(step, preferred_step) / 2.0

    def trajectory(self, shot_info: Shot, max_range: Distance, dist_step: Distance,
                   extra_data: bool = False, time_step: float = 0.0) -> List[TrajectoryData]:
        """
        Calculates the trajectory of a projectile.

        Args:
            shot_info (Shot): Information about the shot.
            max_range (Distance): The maximum range of the trajectory.
            dist_step (Distance): The distance step for calculations.
            extra_data (bool, optional): Flag to include extra data. Defaults to False.
            time_step (float, optional): The time step for calculations. Defaults to 0.0.

        Returns:
            List[TrajectoryData]: A list of trajectory data points.
        """
        filter_flags = TrajFlag.RANGE

        if extra_data:
            # dist_step = Distance.Foot(self._config.chart_resolution)
            filter_flags = TrajFlag.ALL

        self._init_trajectory(shot_info)
        return self._integrate(shot_info, max_range >> Distance.Foot,
                               dist_step >> Distance.Foot, filter_flags, time_step)

    def _init_trajectory(self, shot_info: Shot) -> None:
        """
        Initializes the trajectory calculation.

        Args:
            shot_info (Shot): Information about the shot.
        """
        self._bc: float = shot_info.ammo.dm.BC
        self._table_data: List[DragDataPoint] = shot_info.ammo.dm.drag_table
        self._curve: List[CurvePoint] = calculate_curve(self._table_data)

        # use calculation over list[double] instead of list[DragDataPoint]
        self.__mach_list: List[float] = _get_only_mach_data(self._table_data)

        self.look_angle = shot_info.look_angle >> Angular.Radian
        self.twist = shot_info.weapon.twist >> Distance.Inch
        self.length = shot_info.ammo.dm.length >> Distance.Inch
        self.diameter = shot_info.ammo.dm.diameter >> Distance.Inch
        self.weight = shot_info.ammo.dm.weight >> Weight.Grain
        self.barrel_elevation = shot_info.barrel_elevation >> Angular.Radian
        self.barrel_azimuth = shot_info.barrel_azimuth >> Angular.Radian
        self.sight_height = shot_info.weapon.sight_height >> Distance.Foot
        self.cant_cosine = math.cos(shot_info.cant_angle >> Angular.Radian)
        self.cant_sine = math.sin(shot_info.cant_angle >> Angular.Radian)
        self.alt0 = shot_info.atmo.altitude >> Distance.Foot
        self.calc_step = self.get_calc_step()
        self.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp) >> Velocity.FPS
        self.stability_coefficient = self.calc_stability_coefficient(shot_info.atmo)

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero

        Args:
            shot_info (Shot): Shot parameters
            distance (Distance): Zero distance

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance
        """
        self._init_trajectory(shot_info)

        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations

        distance_feet = distance >> Distance.Foot  # no need convert it twice
        zero_distance = math.cos(self.look_angle) * distance_feet
        height_at_zero = math.sin(self.look_angle) * distance_feet

        iterations_count = 0
        zero_finding_error = _cZeroFindingAccuracy * 2
        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > _cZeroFindingAccuracy and iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current self.barrel_elevation)
            try:
                t = self._integrate(shot_info, zero_distance, zero_distance, TrajFlag.NONE)[0]
                height = t.height >> Distance.Foot
            except RangeError as e:
                if e.last_distance is None:
                    raise e
                last_distance_foot = e.last_distance >> Distance.Foot
                proportion = (last_distance_foot) / zero_distance
                height = (e.incomplete_trajectory[-1].height >> Distance.Foot) / proportion

            zero_finding_error = math.fabs(height - height_at_zero)

            if zero_finding_error > _cZeroFindingAccuracy:
                # Adjust barrel elevation to close height at zero distance
                self.barrel_elevation -= (height - height_at_zero) / zero_distance
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1
        if zero_finding_error > _cZeroFindingAccuracy:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self.barrel_elevation))
        return Angular.Radian(self.barrel_elevation)

    def _acceleration_pure_python(self, velocity_vector: Vector, density_factor: float, mach: float,
                                  wind_vector: Vector) -> Vector:
        """
        Calculates the acceleration vector (a = F/m) using pure Python Vector operations.
        """
        velocity_adjusted = velocity_vector.subtract(wind_vector)
        velocity_mag = velocity_adjusted.magnitude()

        # Handle potential division by zero for mach
        current_mach = velocity_mag / mach if mach != 0 else 1.0  # Use 1.0 or appropriate default if mach is zero

        drag_coeff = self.drag_by_mach(current_mach)
        drag_force_magnitude = density_factor * velocity_mag * drag_coeff

        # Drag force is opposite to velocity_adjusted direction
        # Ensure velocity_adjusted is not zero to avoid division by zero in normalization
        if velocity_mag > 1e-10:  # Check for near-zero velocity to prevent division by zero
            drag_force_vector = velocity_adjusted.mul_by_const(-drag_force_magnitude / velocity_mag)
        else:
            drag_force_vector = Vector(0.0, 0.0, 0.0)  # No drag if no velocity

        gravity_vector_py = self.gravity_vector  # Already a Vector object

        # Net force = Drag Force + Gravity Force
        net_force = drag_force_vector.add(gravity_vector_py)

        return net_force.mul_by_const(1.0 / self.weight)  # a = F/m (implicitly using weight as mass proxy)

    def _integrate_leapfrog_pure_python(self, shot_info: Shot, maximum_range: float, record_step: float,
                                        filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List[
        "TrajectoryData"]:
        """
        Calculate trajectory for specified shot using Leapfrog integration with pure Python Vector operations.
        """

        _cMinimumVelocity = self._config.cMinimumVelocity
        _cMaximumDrop = self._config.cMaximumDrop
        _cMinimumAltitude = self._config.cMinimumAltitude

        ranges: List[TrajectoryData] = []

        # Initial state
        time = 0.0
        range_vector = Vector(.0, -self.cant_cosine * self.sight_height, -self.cant_sine * self.sight_height)
        velocity_vector = Vector(
            self.muzzle_velocity * math.cos(self.barrel_elevation) * math.cos(self.barrel_azimuth),
            self.muzzle_velocity * math.sin(self.barrel_elevation),
            self.muzzle_velocity * math.cos(self.barrel_elevation) * math.sin(self.barrel_azimuth)
        )

        # Initial time step (dt) - will be adjusted based on current velocity
        dt = self.calc_step / max(1.0, velocity_vector.magnitude())

        wind_sock = _WindSock(shot_info.winds)
        wind_vector = wind_sock.current_vector()

        data_filter = _TrajectoryDataFilter(filter_flags=filter_flags, range_step=record_step,
                                            initial_position=range_vector,
                                            initial_velocity=velocity_vector,
                                            time_step=time_step)
        data_filter.setup_seen_zero(range_vector.y, self.barrel_elevation, self.look_angle)

        # Calculate initial acceleration to get v(t + dt/2)
        altitude_initial = self.alt0 + range_vector.y
        density_factor_initial, mach_initial = shot_info.atmo.get_density_factor_and_mach_for_altitude(altitude_initial)

        # Calculate acceleration at t
        accel_t = self._acceleration_pure_python(velocity_vector, density_factor_initial, mach_initial, wind_vector)

        # First half-step for velocity
        velocity_vector_half = velocity_vector.add(accel_t.mul_by_const(0.5 * dt))

        it = 0
        while range_vector.x <= maximum_range + min(self.calc_step, record_step):
            it += 1
            data_filter.clear_current_flag()

            current_range = range_vector.x
            if current_range >= wind_sock.next_range:
                wind_vector = wind_sock.vector_for_range(current_range)

            # Update position for full step
            range_vector = range_vector.add(velocity_vector_half.mul_by_const(dt))
            time += dt

            # Update air density and mach at new position
            altitude = self.alt0 + range_vector.y
            density_factor, mach = shot_info.atmo.get_density_factor_and_mach_for_altitude(altitude)

            # Calculate acceleration at t + dt (using v_half and new position)
            accel_t_plus_dt = self._acceleration_pure_python(velocity_vector_half, density_factor, mach, wind_vector)

            # Update velocity for second half-step
            velocity_vector = velocity_vector_half.add(accel_t_plus_dt.mul_by_const(0.5 * dt))

            # Prepare for next iteration: new velocity_vector_half
            accel_next = self._acceleration_pure_python(velocity_vector, density_factor, mach, wind_vector)
            velocity_vector_half = velocity_vector.add(accel_next.mul_by_const(0.5 * dt))

            velocity_mag = velocity_vector.magnitude()

            # Check whether to record TrajectoryData row at current point
            if filter_flags:
                if (data := data_filter.should_record(range_vector, velocity_vector, mach, time)) is not None:
                    # Recalculate drag for TrajectoryData if needed
                    current_drag_val = density_factor * velocity_mag * self.drag_by_mach(velocity_mag / mach)
                    ranges.append(create_trajectory_row(data.time, data.position, data.velocity,
                                                        velocity_mag, data.mach,
                                                        self.spin_drift(data.time), self.look_angle,
                                                        density_factor, current_drag_val, self.weight,
                                                        data_filter.current_flag))

            # Check termination conditions
            if (velocity_mag < _cMinimumVelocity or range_vector.y < _cMaximumDrop or
                    self.alt0 + range_vector.y < _cMinimumAltitude):
                current_drag_val = density_factor * velocity_mag * self.drag_by_mach(velocity_mag / mach)
                ranges.append(create_trajectory_row(
                    time, range_vector, velocity_vector,
                    velocity_mag, mach, self.spin_drift(time), self.look_angle,
                    density_factor, current_drag_val, self.weight, data_filter.current_flag
                ))
                reason = RangeError.MinimumVelocityReached if velocity_mag < _cMinimumVelocity else \
                    RangeError.MaximumDropReached if range_vector.y < _cMaximumDrop else \
                        RangeError.MinimumAltitudeReached
                raise RangeError(reason, ranges)

            # Adjust time step for next iteration based on new velocity
            dt = self.calc_step / max(1.0, velocity_mag)

        # Final record if loop terminates without error
        if len(ranges) < 2:
            velocity_mag = velocity_vector.magnitude()  # Ensure velocity_mag is up-to-date
            current_drag_val = density_factor * velocity_mag * self.drag_by_mach(velocity_mag / mach)
            ranges.append(create_trajectory_row(
                time, range_vector, velocity_vector,
                velocity_mag, mach, self.spin_drift(time), self.look_angle,
                density_factor, current_drag_val, self.weight, TrajFlag.NONE))

        logger.debug(f"euler leapfrog py it {it}")
        return ranges

    def _integrate(self, shot_info: Shot, maximum_range: float, record_step: float,
                   filter_flags: Union[TrajFlag, int], time_step: float = 0.0) -> List["TrajectoryData"]:
        # Choose the pure Python Leapfrog implementation
        return self._integrate_leapfrog_pure_python(shot_info, maximum_range, record_step, filter_flags, time_step)

    def drag_by_mach(self, mach: float) -> float:
        """
        Calculates the drag coefficient at a given Mach number.

        The drag force is calculated using the following formula:
        Drag force = V^2 * Cd * AirDensity * S / 2m

        Where:
            - cStandardDensity of Air = 0.076474 lb/ft^3
            - S is cross-section = d^2 pi/4, where d is bullet diameter in inches
            - m is bullet mass in pounds
            - bc contains m/d^2 in units lb/in^2, which is multiplied by 144 to convert to lb/ft^2

        Thus:
            - The magic constant found here = StandardDensity * pi / (4 * 2 * 144)

        Args:
            mach (float): The Mach number.

        Returns:
            float: The drag coefficient at the given Mach number.
        """
        # cd = calculate_by_curve(self._table_data, self._curve, mach)
        # use calculation over list[double] instead of list[DragDataPoint]
        cd = _calculate_by_curve_and_mach_list(self.__mach_list, self._curve, mach)
        return cd * 2.08551e-04 / self._bc

    def spin_drift(self, time) -> float:
        """
        Litz spin-drift approximation

        Args:
            time: Time of flight

        Returns:
            windage due to spin drift, in feet
        """
        if (self.stability_coefficient != 0) and (self.twist != 0):
            sign = 1 if self.twist > 0 else -1
            return sign * (1.25 * (self.stability_coefficient + 1.2)
                           * math.pow(time, 1.83)) / 12
        return 0

    def calc_stability_coefficient(self, atmo: Atmo) -> float:
        """
        Calculates the Miller stability coefficient.

        Args:
            atmo (Atmo): Atmospheric conditions.

        Returns:
            float: The Miller stability coefficient.
        """
        if self.twist and self.length and self.diameter and atmo.pressure.raw_value:
            twist_rate = math.fabs(self.twist) / self.diameter
            length = self.length / self.diameter
            # Miller stability formula
            sd = 30 * self.weight / (
                    math.pow(twist_rate, 2) * math.pow(self.diameter, 3) * length * (1 + math.pow(length, 2))
            )
            # Velocity correction factor
            fv = math.pow(self.muzzle_velocity / 2800, 1.0 / 3.0)
            # Atmospheric correction
            ft = atmo.temperature >> Temperature.Fahrenheit
            pt = atmo.pressure >> Pressure.InHg
            ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
            return sd * fv * ftp
        return 0


__all__ = (
    'TrajectoryCalc',
    'get_global_max_calc_step_size',
    'set_global_max_calc_step_size',
    'reset_globals',
    'cZeroFindingAccuracy',
    'cMinimumVelocity',
    'cMaximumDrop',
    'cMaxIterations',
    'cGravityConstant',
    'cMinimumAltitude',
    'Config',
    '_TrajectoryDataFilter',
    '_WindSock'
)
