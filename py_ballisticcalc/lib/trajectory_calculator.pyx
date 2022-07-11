from libc.math cimport fabs, pow, sin, cos, log10, floor, atan
from py_ballisticcalc.lib.bmath.unit import *
from py_ballisticcalc.lib.bmath.vector import Vector
from py_ballisticcalc.lib.projectile import Ammunition
from py_ballisticcalc.lib.weapon import Weapon, TwistLeft
from py_ballisticcalc.lib.atmosphere import Atmosphere
from py_ballisticcalc.lib.shot_parameters import ShotParameters
from py_ballisticcalc.lib.wind import WindInfo
from py_ballisticcalc.lib.trajectory_data import TrajectoryData, Timespan

cdef float cZeroFindingAccuracy = 0.000005
cdef float cMinimumVelocity = 50.0
cdef float cMaximumDrop = -15000
cdef int cMaxIterations = 10
cdef float cGravityConstant = -32.17405

cdef class TrajectoryCalculator:
    cdef _maximum_calculator_step_size

    def __init__(self):
        self._maximum_calculator_step_size = Distance(1, DistanceFoot)

    cpdef maximum_calculator_step_size(self):
        return self._maximum_calculator_step_size

    cpdef set_maximum_calculator_step_size(self, value: Distance):
        self._maximum_calculator_step_size = value

    cdef float get_calculation_step(self, step: float):
        cdef step_order, maximum_order
        step = step / 2
        cdef float maximum_step = self._maximum_calculator_step_size.get_in(DistanceFoot)

        if step > maximum_step:
            step_order = int(floor(log10(step)))
            maximum_order = int(floor(log10(maximum_step)))
            step = step / pow(10, float(step_order - maximum_order + 1))

        return step

    cpdef sight_angle(self, ammunition: Ammunition, weapon: Weapon, atmosphere: Atmosphere):
        cdef float calculation_step, mach, density_factor, muzzle_velocity
        cdef float barrel_azimuth, barrel_elevation
        cdef float velocity, time, zero_distance, maximum_range
        cdef float delta_time, drag, zero_finding_error

        cdef int iterations_count

        cdef gravity_vector, range_vector, velocity_vector, delta_range_vector

        calculation_step = self.get_calculation_step(
            Distance(10, weapon.zero().zero_distance().units()).get_in(DistanceFoot))

        mach = atmosphere.mach().get_in(VelocityFPS)
        density_factor = atmosphere.density_factor()
        muzzle_velocity = ammunition.muzzle_velocity().get_in(VelocityFPS)
        barrel_azimuth = 0.0
        barrel_elevation = 0.0

        iterations_count = 0

        zero_finding_error = cZeroFindingAccuracy * 2
        gravity_vector = Vector(0, cGravityConstant, 0)
        while zero_finding_error > cZeroFindingAccuracy and iterations_count < cMaxIterations:
            velocity = muzzle_velocity
            time = 0.0

            # x - distance towards target,
            # y - drop and
            # z - windage

            range_vector = Vector(
                0.0, -weapon.sight_height().get_in(DistanceFoot), 0.0
            )
            velocity_vector = Vector(
                cos(barrel_elevation) * cos(barrel_azimuth),
                sin(barrel_elevation),
                cos(barrel_elevation) * sin(barrel_azimuth)
            ).multiply_by_const(velocity)

            zero_distance = weapon.zero().zero_distance().get_in(DistanceFoot)
            maximum_range = zero_distance + calculation_step

            while range_vector.x() <= maximum_range:
                if velocity < cMinimumVelocity or range_vector.y() < cMaximumDrop:
                    break

                delta_time = calculation_step / velocity_vector.x()
                velocity = velocity_vector.magnitude()
                drag = density_factor * velocity * ammunition\
                    .bullet()\
                    .ballistic_coefficient()\
                    .drag(velocity / mach)

                velocity_vector = velocity_vector.subtract(
                    (
                        velocity_vector.multiply_by_const(drag).subtract(
                            gravity_vector)
                    ).multiply_by_const(delta_time)
                )

                delta_range_vector = Vector(calculation_step,
                                            velocity_vector.y() * delta_time,
                                            velocity_vector.z() * delta_time)
                range_vector = range_vector.add(delta_range_vector)
                velocity = velocity_vector.magnitude()
                time = time + delta_range_vector.magnitude() / velocity
                if fabs(range_vector.x() - zero_distance) < 0.5 * calculation_step:
                    zero_finding_error = fabs(range_vector.y())
                    barrel_elevation = barrel_elevation - range_vector.y() / range_vector.x()
                    break

                iterations_count += 1
        return Angular(barrel_elevation, AngularRadian)

    cpdef trajectory(self, ammunition: Ammunition, weapon: Weapon, atmosphere: Atmosphere,
                     shot_info: ShotParameters, wind_info: list[WindInfo]):
        cdef float range_to, step, calculation_step, bullet_weight, stability_coefficient
        cdef float barrel_azimuth, barrel_elevation, alt0, density_factor, mach
        cdef float next_wind_range, time, muzzle_velocity, velocity, windage, delta_time, drag
        cdef float maximum_range, next_range_distance, twist_coefficient
        cdef int current_item, ranges_length, current_wind, len_wind_info
        cdef calculate_drift, ranges, wind_vector
        cdef windage_adjustment, velocity_adjusted, delta_range_vector
        cdef gravity_vector, drop_adjustment, range_vector, velocity_vector

        range_to = shot_info.maximum_distance().get_in(DistanceFoot)
        step = shot_info.step().get_in(DistanceFoot)

        calculation_step = self.get_calculation_step(step)

        bullet_weight = ammunition.bullet().bullet_weight().get_in(WeightGrain)

        stability_coefficient = 1.0

        calculate_drift = False

        if weapon.has_twist and ammunition.bullet().has_dimensions():
            stability_coefficient = calculate_stability_coefficient(
                ammunition, weapon, atmosphere
            )
            calculate_drift = True

        ranges_length = int(floor(range_to / step)) + 1
        ranges = []

        barrel_azimuth = .0
        barrel_elevation = shot_info.sight_angle().get_in(AngularRadian)
        barrel_elevation = barrel_elevation + shot_info.shot_angle().get_in(AngularRadian)
        alt0 = atmosphere.altitude().get_in(DistanceFoot)

        # Never used in upstream, uncomment on need
        # density_factor, mach = atmosphere.get_density_factor_and_mach_for_altitude(alt0)

        current_wind = 0
        next_wind_range = 1e7

        len_wind_info = int(len(wind_info))

        if len_wind_info < 1:
            wind_vector = Vector(0, 0, 0)
        else:
            if len(wind_info) > 1:
                next_wind_range = wind_info[0].until_distance().get_in(DistanceFoot)
            wind_vector = wind_to_vector(shot_info, wind_info[0])

        muzzle_velocity = ammunition.muzzle_velocity().get_in(VelocityFPS)
        gravity_vector = Vector(0, cGravityConstant, 0)
        velocity = muzzle_velocity
        time = .0

        # x - distance towards target,
        # y - drop and
        # z - windage

        range_vector = Vector(.0, -weapon.sight_height().get_in(DistanceFoot), 0)
        velocity_vector = Vector(cos(barrel_elevation) * cos(barrel_azimuth), sin(barrel_elevation),
                                      cos(barrel_elevation) * sin(barrel_azimuth)).multiply_by_const(velocity)
        current_item = 0

        maximum_range = range_to
        next_range_distance = 0

        twist_coefficient = .0

        if calculate_drift:
            if weapon.twist().direction() == TwistLeft:
                twist_coefficient = 1
            else:
                twist_coefficient = -1

        while range_vector.x() <= maximum_range + calculation_step:

            if velocity < cMinimumVelocity or range_vector.y() < cMaximumDrop:
                break

            density_factor, mach = atmosphere.get_density_factor_and_mach_for_altitude(alt0 + range_vector.y())

            if range_vector.x() >= next_wind_range:
                current_wind += 1
                wind_vector = wind_to_vector(shot_info, wind_info[current_wind])

                if current_wind == len_wind_info - 1:
                    next_wind_range = 1e7
                else:
                    next_wind_range = wind_info[current_wind].until_distance().get_in(DistanceFoot)

            if range_vector.x() >= next_range_distance:
                windage = range_vector.z()
                if calculate_drift:
                    windage += (1.25 * (stability_coefficient + 1.2) * pow(time, 1.83) * twist_coefficient) / 12

                drop_adjustment = get_correction(range_vector.x(), range_vector.y())
                windage_adjustment = get_correction(range_vector.x(), windage)

                ranges.append(TrajectoryData(
                    time=Timespan(time),
                    travel_distance=Distance(range_vector.x(), DistanceFoot),
                    drop=Distance(range_vector.y(), DistanceFoot),
                    drop_adjustment=Angular(drop_adjustment, AngularRadian) if drop_adjustment else None,
                    windage=Distance(windage, DistanceFoot),
                    windage_adjustment=Angular(windage_adjustment, AngularRadian) if windage_adjustment else None,
                    velocity=Velocity(velocity, VelocityFPS),
                    mach=velocity / mach,
                    energy=Energy(calculate_energy(bullet_weight, velocity),
                                  EnergyFootPound),
                    optimal_game_weight=Weight(calculate_ogv(bullet_weight, velocity),
                                               WeightPound))
                )

                next_range_distance += step
                current_item += 1
                if current_item == ranges_length:
                    break

            delta_time = calculation_step / velocity_vector.x()
            velocity_adjusted = velocity_vector.subtract(wind_vector)
            velocity = velocity_adjusted.magnitude()

            drag = density_factor * velocity * ammunition.bullet().ballistic_coefficient().drag(velocity / mach)
            velocity_vector = velocity_vector.subtract(
                (velocity_adjusted.multiply_by_const(drag).subtract(gravity_vector)).multiply_by_const(delta_time)
            )
            delta_range_vector = Vector(
                calculation_step, velocity_vector.y() * delta_time, velocity_vector.z() * delta_time
            )
            range_vector = range_vector.add(delta_range_vector)
            velocity = velocity_vector.magnitude()
            time = time + delta_range_vector.magnitude() / velocity

        return ranges

cdef float calculate_stability_coefficient(ammunition_info: Ammunition,
                                           rifle_info: Weapon, atmosphere: Atmosphere):
    cdef float weight = ammunition_info.bullet().bullet_weight().get_in(WeightGrain)
    cdef float diameter = ammunition_info.bullet().bullet_diameter().get_in(DistanceInch)
    cdef float twist = rifle_info.twist().twist().get_in(DistanceInch) / diameter
    cdef float length = ammunition_info.bullet().bullet_length().get_in(DistanceInch) / diameter
    cdef float sd = 30 * weight / (pow(twist, 2) * pow(diameter, 3) * length * (1 + pow(length, 2)))
    cdef float mv = ammunition_info.muzzle_velocity().get_in(VelocityFPS)
    cdef float fv = pow(mv / 2800, 1.0 / 3.0)
    cdef float ft = atmosphere.temperature().get_in(TemperatureFahrenheit)
    cdef float pt = atmosphere.pressure().get_in(PressureInHg)
    cdef float ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)

    return sd * fv * ftp

cdef wind_to_vector(shot: ShotParameters, wind: WindInfo):
    cdef float sight_cosine = cos(shot.sight_angle().get_in(AngularRadian))
    cdef float sight_sine = sin(shot.sight_angle().get_in(AngularRadian))
    cdef float cant_cosine = cos(shot.cant_angle().get_in(AngularRadian))
    cdef float cant_sine = sin(shot.cant_angle().get_in(AngularRadian))
    cdef float range_velocity = wind.velocity().get_in(VelocityFPS) * cos(wind.direction().get_in(AngularRadian))
    cdef float cross_component = wind.velocity().get_in(VelocityFPS) * sin(wind.direction().get_in(AngularRadian))
    cdef float range_factor = -range_velocity * sight_sine
    return Vector(range_velocity * sight_cosine,
                  range_factor * cant_cosine + cross_component * cant_sine,
                  cross_component * cant_cosine - range_factor * cant_sine)

cdef get_correction(distance: float, offset: float):
    if distance != 0:
        return atan(offset / distance)
    return None

cdef float calculate_energy(bullet_weight: float, velocity: float):
    return bullet_weight * pow(velocity, 2) / 450400

cdef float calculate_ogv(bullet_weight: float, velocity: float):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12
