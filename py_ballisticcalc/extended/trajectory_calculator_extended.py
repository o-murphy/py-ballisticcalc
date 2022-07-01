from ..trajectory_calculator import *
from .drag_extended import *


class TrajectoryCalculatorExtended(TrajectoryCalculator):
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
        ammunition.bullet._ballistic_coefficient = BallisticCoefficientExtended(
            ammunition.bullet.ballistic_coefficient.value,
            ammunition.bullet.ballistic_coefficient.table,
            ammunition.bullet.bullet_weight,
            ammunition.bullet.bullet_diameter
        )

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
                    windage += (1.25 * (stability_coefficient + 1.2) * math.pow(time,
                                                                                1.83) * twist_coefficient) / 12

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

            cdst = ammunition.bullet.ballistic_coefficient.standard_cd(velocity / mach)
            cd = ammunition.bullet.ballistic_coefficient.calculated_cd(velocity / mach)

            print(velocity / mach, cdst, cd)

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
