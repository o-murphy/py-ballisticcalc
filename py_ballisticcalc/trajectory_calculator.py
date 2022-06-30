import math
from .bmath import unit, Vector
from .projectile import Ammunition
from .weapon import Weapon, TwistLeft
from .atmosphere import Atmosphere
from .shot_parameters import ShotParameters
from .wind import WindInfo
from .trajectory_data import TrajectoryData, Timespan

cZeroFindingAccuracy = 0.000005
cMinimumVelocity = 50.0
cMaximumDrop = -15000
cMaxIterations = 10
cGravityConstant = -32.17405


class TrajectoryCalculator(object):
    """
    TrajectoryCalculator table is used to calculate the trajectory
    of a projectile shot with the parameters specified
    """

    def __init__(self):
        self._maximum_calculator_step_size = unit.Distance(1, unit.DistanceFoot).validate()

    @property
    def maximum_calculator_step_size(self) -> unit.Distance:
        """
        :return: the maximum size of one calculation iteration.
        """
        return self._maximum_calculator_step_size

    @maximum_calculator_step_size.setter
    def maximum_calculator_step_size(self, value: unit.Distance):
        """
        Sets the maximum size of one calculation iteration.
        As the generic rule, the maximum step of the calculation must not be greater than
        a half of the step used in the short parameter. The smaller value is, the calculation is more precise but
        takes more time to calculate. From practical standpoint the value in range from 0.5 to 5 feet produces
        good enough accuracy.
        :param value: unit.Distance instance
        :return: None
        """
        self._maximum_calculator_step_size = value

    def get_calculation_step(self, step: float) -> float:
        step = step / 2  # do it twice for increased accuracy of velocity calculation and 10 times per step
        maximum_step: float = self._maximum_calculator_step_size.get_in(unit.DistanceFoot)

        if step > maximum_step:
            step_order = int(math.floor(math.log10(step)))
            maximum_order = int(math.floor(math.log10(maximum_step)))
            step = step / math.pow(10, float(step_order - maximum_order + 1))

        return step

    def sight_angle(self, ammunition: Ammunition, weapon: Weapon, atmosphere: Atmosphere) -> unit.Angular:
        """
        The calculated value is to be used as sightAngle parameter of the ShotParameters structure
        :param ammunition: Ammunition instance
        :param weapon: Weapon instance
        :param atmosphere: Atmosphere instance
        :return: sight angle for a rifle with scope height specified and zeroed using the ammo specified at
        the range specified and under the conditions (atmosphere) specified
        """

        calculation_step = self.get_calculation_step(
            unit.Distance(10, weapon.zero.zero_distance.units).validate().get_in(unit.DistanceFoot))

        mach = atmosphere.mach.get_in(unit.VelocityFPS)
        density_factor = atmosphere.density_factor
        muzzle_velocity = ammunition.muzzle_velocity.get_in(unit.VelocityFPS)
        barrel_azimuth = 0.0
        barrel_elevation = 0

        iterations_count = 0

        zero_finding_error = cZeroFindingAccuracy * 2
        gravity_vector = Vector(0, cGravityConstant, 0)
        while zero_finding_error > cZeroFindingAccuracy and iterations_count < cMaxIterations:
            velocity = muzzle_velocity
            time = 0.0

            # x - distance towards target,
            # y - drop and
            # z - windage

            range_vector = Vector(0.0, -weapon.sight_height.get_in(unit.DistanceFoot), 0)
            velocity_vector = Vector(
                math.cos(barrel_elevation) * math.cos(barrel_azimuth),
                math.sin(barrel_elevation),
                math.cos(barrel_elevation) * math.sin(barrel_azimuth)
            ).multiply_by_const(velocity)

            zero_distance: float = weapon.zero.zero_distance.get_in(unit.DistanceFoot)
            maximum_range = zero_distance + calculation_step

            while range_vector.x <= maximum_range:
                if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                    break

                delta_time = calculation_step / velocity_vector.x
                velocity = velocity_vector.magnitude()
                drag = density_factor * velocity * ammunition.bullet.ballistic_coefficient.drag(velocity / mach)
                velocity_vector = velocity_vector.subtract(
                    (
                        velocity_vector.multiply_by_const(drag).subtract(gravity_vector)
                    ).multiply_by_const(delta_time)
                )
                delta_range_vector = Vector(calculation_step, velocity_vector.y * delta_time,
                                            velocity_vector.z * delta_time)
                range_vector = range_vector.add(delta_range_vector)
                velocity = velocity_vector.magnitude()
                time = time + delta_range_vector.magnitude() / velocity
                if math.fabs(range_vector.x - zero_distance) < 0.5 * calculation_step:
                    zero_finding_error = math.fabs(range_vector.y)
                    barrel_elevation = barrel_elevation - range_vector.y / range_vector.x
                    break

                iterations_count += 1
        return unit.Angular(barrel_elevation, unit.AngularRadian).validate()

    def trajectory(self, ammunition: Ammunition, weapon: Weapon, atmosphere: Atmosphere,
                   shot_info: ShotParameters, wind_info: list[WindInfo]) -> list[TrajectoryData]:
        """
        Calculates the trajectory with the parameters specified
        :param ammunition: Ammunition instance
        :param weapon: Weapon instance
        :param atmosphere: Atmosphere instance
        :param shot_info: ShotParameters instance
        :param wind_info: list[WindInfo]
        :return: trajectory with the parameters specified
        """
        range_to: float = shot_info.maximum_distance.get_in(unit.DistanceFoot)
        step: float = shot_info.step.get_in(unit.DistanceFoot)

        calculation_step = self.get_calculation_step(step)

        bullet_weight = ammunition.bullet.bullet_weight.get_in(unit.WeightGrain)

        stability_coefficient = 1.0

        calculate_drift: bool = False

        if weapon.has_twist and ammunition.bullet.has_dimensions:
            stability_coefficient = self.calculate_stability_coefficient(
                ammunition, weapon, atmosphere
            )
            calculate_drift = True

        ranges_length = int(math.floor(range_to / step)) + 1
        ranges = []

        barrel_azimuth = .0
        barrel_elevation = shot_info.sight_angle.get_in(unit.AngularRadian)
        barrel_elevation = barrel_elevation + shot_info.shot_angle.get_in(unit.AngularRadian)
        alt0: float = atmosphere.altitude.get_in(unit.DistanceFoot)

        # Never used in upstream, uncomment on need
        # density_factor, mach = atmosphere.get_density_factor_and_mach_for_altitude(alt0)

        current_wind = 0
        next_wind_range = 1e7

        if len(wind_info) < 1:
            wind_vector = Vector(0, 0, 0)
        else:
            if len(wind_info) > 1:
                next_wind_range = wind_info[0].until_distance.get_in(unit.DistanceFoot)
            wind_vector = self.wind_to_vector(shot_info, wind_info[0])

        muzzle_velocity = ammunition.muzzle_velocity.get_in(unit.VelocityFPS)
        gravity_vector = Vector(0, cGravityConstant, 0)
        velocity = muzzle_velocity
        time = .0

        # x - distance towards target,
        # y - drop and
        # z - windage

        range_vector = Vector(.0, -weapon.sight_height.get_in(unit.DistanceFoot), 0)
        velocity_vector = Vector(math.cos(barrel_elevation) * math.cos(barrel_azimuth), math.sin(barrel_elevation),
                                 math.cos(barrel_elevation) * math.sin(barrel_azimuth)).multiply_by_const(velocity)

        current_item = 0

        maximum_range = range_to
        next_range_distance = 0

        twist_coefficient = .0

        if calculate_drift:
            if weapon.twist.direction == TwistLeft:
                twist_coefficient = 1
            else:
                twist_coefficient = -1

        while range_vector.x <= maximum_range + calculation_step:
            if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                break

            density_factor, mach = atmosphere.get_density_factor_and_mach_for_altitude(alt0 + range_vector.y)

            if range_vector.x >= next_wind_range:
                current_wind += 1
                wind_vector = self.wind_to_vector(shot_info, wind_info[current_wind])

                if current_wind == len(wind_info) - 1:
                    next_wind_range = 1e7
                else:
                    next_wind_range = wind_info[current_wind].until_distance.get_in(unit.DistanceFoot)

            if range_vector.x >= next_range_distance:
                windage: float = range_vector.z
                if calculate_drift:
                    windage += (1.25 * (stability_coefficient + 1.2) * math.pow(time, 1.83) * twist_coefficient) / 12

                drop_adjustment = self.get_correction(range_vector.x, range_vector.y)
                windage_adjustment = self.get_correction(range_vector.x, windage)

                ranges.append(TrajectoryData(
                    time=Timespan(time),
                    travel_distance=unit.Distance(range_vector.x, unit.DistanceFoot).validate(),
                    drop=unit.Distance(range_vector.y, unit.DistanceFoot).validate(),
                    drop_adjustment=unit.Angular(drop_adjustment, unit.AngularRadian).validate(),
                    windage=unit.Distance(windage, unit.DistanceFoot).validate(),
                    windage_adjustment=unit.Angular(windage_adjustment, unit.AngularRadian),
                    velocity=unit.Velocity(velocity, unit.VelocityFPS),
                    mach=velocity / mach,
                    energy=unit.Energy(self.calculate_energy(bullet_weight, velocity),
                                       unit.EnergyFootPound),
                    optimal_game_weight=unit.Weight(self.calculate_ogv(bullet_weight, velocity),
                                                    unit.WeightPound))
                              )

                next_range_distance += step
                current_item += 1
                if current_item == ranges_length:
                    break

            delta_time = calculation_step / velocity_vector.x
            velocity_adjusted = velocity_vector.subtract(wind_vector)
            velocity = velocity_adjusted.magnitude()

            drag = density_factor * velocity * ammunition.bullet.ballistic_coefficient.drag(velocity / mach)
            velocity_vector = velocity_vector.subtract(
                (velocity_adjusted.multiply_by_const(drag).subtract(gravity_vector)).multiply_by_const(delta_time)
            )
            delta_range_vector = Vector(
                calculation_step, velocity_vector.y * delta_time, velocity_vector.z * delta_time
            )
            range_vector = range_vector.add(delta_range_vector)
            velocity = velocity_vector.magnitude()
            time = time + delta_range_vector.magnitude() / velocity

        return ranges

    @staticmethod
    def calculate_stability_coefficient(ammunition_info: Ammunition,
                                        rifle_info: Weapon, atmosphere: Atmosphere) -> float:
        weight: float = ammunition_info.bullet.bullet_weight.get_in(unit.WeightGrain)
        diameter: float = ammunition_info.bullet.bullet_diameter.get_in(unit.DistanceInch)
        twist: float = rifle_info.twist.twist.get_in(unit.DistanceInch) / diameter
        length: float = ammunition_info.bullet.bullet_length.get_in(unit.DistanceInch) / diameter
        sd = 30 * weight / (math.pow(twist, 2) * math.pow(diameter, 3) * length * (1 + math.pow(length, 2)))
        fv = math.pow(ammunition_info.muzzle_velocity.get_in(unit.VelocityFPS) / 2800, 1.0 / 3.0)
        ft: float = atmosphere.temperature.get_in(unit.TemperatureFahrenheit)
        pt: float = atmosphere.pressure.get_in(unit.PressureInHg)
        ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)

        return sd * fv * ftp

    @staticmethod
    def wind_to_vector(shot: ShotParameters, wind: WindInfo) -> Vector:
        sight_cosine = math.cos(shot.sight_angle.get_in(unit.AngularRadian))
        sight_sine = math.sin(shot.sight_angle.get_in(unit.AngularRadian))
        cant_cosine = math.cos(shot.cant_angle.get_in(unit.AngularRadian))
        cant_sine = math.sin(shot.cant_angle.get_in(unit.AngularRadian))
        range_velocity = wind.velocity.get_in(unit.VelocityFPS) * math.cos(wind.direction.get_in(unit.AngularRadian))
        cross_component = wind.velocity.get_in(unit.VelocityFPS) * math.sin(wind.direction.get_in(unit.AngularRadian))
        range_factor = -range_velocity * sight_sine
        return Vector(range_velocity * sight_cosine,
                      range_factor * cant_cosine + cross_component * cant_sine,
                      cross_component * cant_cosine - range_factor * cant_sine)

    @staticmethod
    def get_correction(distance: float, offset: float) -> [float, None]:
        if distance != 0:
            return math.atan(offset / distance)
        return

    @staticmethod
    def calculate_energy(bullet_weight: float, velocity: float) -> float:
        return bullet_weight * math.pow(velocity, 2) / 450400

    @staticmethod
    def calculate_ogv(bullet_weight: float, velocity: float) -> float:
        return math.pow(bullet_weight, 2) * math.pow(velocity, 3) * 1.5e-12
