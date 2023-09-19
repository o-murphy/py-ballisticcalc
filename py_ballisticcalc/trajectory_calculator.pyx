from libc.math cimport fabs, pow, sin, cos, log10, floor, atan
from .bmath.unit import *
from .bmath.vector import Vector
from .projectile import Ammunition
from .atmosphere import Atmosphere
from .shot_parameters import ShotParameters
from .wind import WindInfo
from .trajectory_data import *

cdef double cZeroFindingAccuracy = 0.000005
cdef double cMinimumVelocity = 50.0
cdef double cMaximumDrop = -15000
cdef int cMaxIterations = 10
cdef double cGravityConstant = -32.17405

cdef class TrajectoryCalculator:
    cdef _maximum_calculator_step_size

    def __init__(self):
        self._maximum_calculator_step_size = Distance(1, DistanceFoot)

    cpdef maximum_calculator_step_size(self):
        return self._maximum_calculator_step_size

    cpdef set_maximum_calculator_step_size(self, value: Distance):
        self._maximum_calculator_step_size = value

    cdef double get_calculation_step(self, double step):
        cdef step_order, maximum_order
        step = step / 2
        cdef double maximum_step = self._maximum_calculator_step_size.get_in(DistanceFoot)
        if step > maximum_step:
            step_order = int(floor(log10(step)))
            maximum_order = int(floor(log10(maximum_step)))
            step = step / pow(10, float(step_order - maximum_order + 1))
        return step

    cpdef sight_angle(self, zero: Distance, sight_height: Distance,
                      ammunition: Ammunition, atmosphere: Atmosphere):
        cdef double calculation_step, mach, density_factor, muzzle_velocity
        cdef double barrel_azimuth, barrel_elevation
        cdef double velocity, time, zero_distance, maximum_range
        cdef double delta_time, drag, zero_finding_error
        cdef int iterations_count
        cdef gravity_vector, range_vector, velocity_vector, delta_range_vector

        calculation_step = self.get_calculation_step(Distance(10, zero.units()).get_in(DistanceFoot))
        mach = atmosphere.mach().get_in(VelocityFPS)
        density_factor = atmosphere.density_factor()
        muzzle_velocity = ammunition.muzzle_velocity().get_in(VelocityFPS)
        gravity_vector = Vector(0, cGravityConstant, 0)
        barrel_azimuth = 0.0
        barrel_elevation = 0.0

        zero_finding_error = cZeroFindingAccuracy * 2
        iterations_count = 0
        while zero_finding_error > cZeroFindingAccuracy and iterations_count < cMaxIterations:
            velocity = muzzle_velocity
            time = 0.0

            range_vector = Vector(0.0, -sight_height.get_in(DistanceFoot), 0.0)
            velocity_vector = Vector(
                cos(barrel_elevation) * cos(barrel_azimuth),
                sin(barrel_elevation),
                cos(barrel_elevation) * sin(barrel_azimuth)
            ) * velocity

            zero_distance = zero.get_in(DistanceFoot)
            maximum_range = zero_distance + calculation_step

            while range_vector.x() <= maximum_range:
                if velocity < cMinimumVelocity or range_vector.y() < cMaximumDrop:
                    break

                delta_time = calculation_step / velocity_vector.x()
                velocity = velocity_vector.magnitude()
                drag = density_factor * velocity * ammunition.bullet().ballistic_coefficient().drag(velocity / mach)
                velocity_vector = velocity_vector - (velocity_vector * drag - gravity_vector) * delta_time
                delta_range_vector = Vector(calculation_step,
                                            velocity_vector.y() * delta_time,
                                            velocity_vector.z() * delta_time)
                range_vector = range_vector + delta_range_vector
                velocity = velocity_vector.magnitude()
                time = time + delta_range_vector.magnitude() / velocity
                if fabs(range_vector.x() - zero_distance) < 0.5 * calculation_step:
                    zero_finding_error = fabs(range_vector.y())
                    barrel_elevation = barrel_elevation - range_vector.y() / range_vector.x()
                    break

                iterations_count += 1
        return Angular(barrel_elevation, AngularRadian)

    cpdef trajectory(self, ammunition: Ammunition, atmosphere: Atmosphere,
                     shot_info: ShotParameters, wind_info: list[WindInfo],
                     twist: Distance, sight_height: Distance,
                     stopAtZero: bool = False, stopAtMach1: bool = False):
        cdef double range_to, step, calculation_step, bullet_weight, stability_coefficient
        cdef double barrel_azimuth, barrel_elevation, alt0, density_factor, mach
        cdef double next_wind_range, time, muzzle_velocity, velocity, delta_time, drag
        cdef double maximum_range, next_range_distance, twist_coefficient
        cdef int current_item, ranges_length, current_wind, len_wind_info
        cdef ranges, wind_vector
        cdef velocity_adjusted, delta_range_vector
        cdef gravity_vector, range_vector, velocity_vector

        range_to = shot_info.maximum_distance().get_in(DistanceFoot)
        step = shot_info.step().get_in(DistanceFoot)
        ranges_length = int(floor(range_to / step)) + 1  # We might include up to two extra rows: Zero and Mach1
        ranges = []
        calculation_step = self.get_calculation_step(step)

        bullet_weight = ammunition.bullet().bullet_weight().get_in(WeightGrain)

        stability_coefficient = 1.0
        twist_coefficient = 0
        if twist.value() != 0 and ammunition.bullet().has_dimensions():
            stability_coefficient = calculate_stability_coefficient(ammunition, twist, atmosphere)
            if twist.value() < 0:
                twist_coefficient = -1
            else:
                twist_coefficient = 1

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

        # x - distance towards target
        # y - drop
        # z - windage

        range_vector = Vector(.0, -sight_height.get_in(DistanceFoot), 0)
        velocity_vector = Vector(cos(barrel_elevation) * cos(barrel_azimuth), sin(barrel_elevation),
                                 cos(barrel_elevation) * sin(barrel_azimuth)) * velocity
        current_item = 0
        maximum_range = range_to
        next_range_distance = 0
        previousY = 0  # Used to find zero-crossing
        previousMach = 0  # Used to find sound-barrier crossing

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

            if (range_vector.y() < 0) and (previousY > 0):  # Zero-crossing
                ranges.append(calculate_trajectory_row(ZERO,
                                time, range_vector, velocity_vector, velocity, mach,
                                bullet_weight, stability_coefficient, twist_coefficient))
                next_range_distance += calculation_step
                if stopAtZero:
                    break
            elif (velocity / mach < 1) and (previousMach > 1):  # Sound-crossing
                ranges.append(calculate_trajectory_row(MACH1,
                                time, range_vector, velocity_vector, velocity, mach,
                                bullet_weight, stability_coefficient, twist_coefficient))
                next_range_distance += calculation_step
                if stopAtMach1:
                    break
            elif range_vector.x() >= next_range_distance:
                ranges.append(calculate_trajectory_row(TRAJECTORY,
                                time, range_vector, velocity_vector, velocity, mach,
                                bullet_weight, stability_coefficient, twist_coefficient))
                next_range_distance += step
                current_item += 1
                if current_item == ranges_length:
                    break

            previousY = range_vector.y()
            previousMach = velocity / mach

            delta_time = calculation_step / velocity_vector.x()
            velocity_adjusted = velocity_vector - wind_vector
            velocity = velocity_adjusted.magnitude()
            drag = density_factor * velocity * ammunition.bullet().ballistic_coefficient().drag(velocity / mach)
            velocity_vector = velocity_vector - (velocity_adjusted * drag - gravity_vector) * delta_time
            delta_range_vector = Vector(calculation_step,
                                        velocity_vector.y() * delta_time,
                                        velocity_vector.z() * delta_time)
            range_vector = range_vector + delta_range_vector
            velocity = velocity_vector.magnitude()
            time = time + delta_range_vector.magnitude() / velocity

        return ranges


cpdef calculate_trajectory_row(row_type, time, range_vector, velocity_vector, velocity, mach,
                               bullet_weight, stability_coefficient, twist_coefficient):
    windage = range_vector.z()
    if twist_coefficient != 0:
        windage += (1.25 * (stability_coefficient + 1.2) * pow(time, 1.83) * twist_coefficient) / 12
    windage_adjustment = get_correction(range_vector.x(), windage)
    drop_adjustment = get_correction(range_vector.x(), range_vector.y())
    return TrajectoryData(time=Timespan(time),
            travel_distance=Distance(range_vector.x(), DistanceFoot),
            drop=Distance(range_vector.y(), DistanceFoot),
            drop_adjustment=Angular(drop_adjustment, AngularRadian),
            windage=Distance(windage, DistanceFoot),
            windage_adjustment=Angular(windage_adjustment, AngularRadian),
            velocity=Velocity(velocity, VelocityFPS),
            angle=Angular(atan(velocity_vector.y()/velocity_vector.x()), AngularRadian),
            mach=velocity / mach,
            energy=Energy(calculate_energy(bullet_weight, velocity), EnergyFootPound),
            optimal_game_weight=Weight(calculate_ogv(bullet_weight, velocity), WeightPound),
            row_type=row_type)


cdef double calculate_stability_coefficient(ammunition_info: Ammunition, barrelTwist: Distance, atmosphere: Atmosphere):
    cdef double weight = ammunition_info.bullet().bullet_weight().get_in(WeightGrain)
    cdef double diameter = ammunition_info.bullet().bullet_diameter().get_in(DistanceInch)
    cdef double twist = barrelTwist.get_in(DistanceInch) / diameter
    cdef double length = ammunition_info.bullet().bullet_length().get_in(DistanceInch) / diameter
    cdef double sd = 30 * weight / (pow(twist, 2) * pow(diameter, 3) * length * (1 + pow(length, 2)))
    cdef double mv = ammunition_info.muzzle_velocity().get_in(VelocityFPS)
    cdef double fv = pow(mv / 2800, 1.0 / 3.0)
    cdef double ft = atmosphere.temperature().get_in(TemperatureFahrenheit)
    cdef double pt = atmosphere.pressure().get_in(PressureInHg)
    cdef double ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
    return sd * fv * ftp

cdef wind_to_vector(shot, wind):
    cdef double sight_cosine = cos(shot.sight_angle().get_in(AngularRadian))
    cdef double sight_sine = sin(shot.sight_angle().get_in(AngularRadian))
    cdef double cant_cosine = cos(shot.cant_angle().get_in(AngularRadian))
    cdef double cant_sine = sin(shot.cant_angle().get_in(AngularRadian))
    cdef double range_velocity = wind.velocity().get_in(VelocityFPS) * cos(wind.direction().get_in(AngularRadian))
    cdef double cross_component = wind.velocity().get_in(VelocityFPS) * sin(wind.direction().get_in(AngularRadian))
    cdef double range_factor = -range_velocity * sight_sine
    return Vector(range_velocity * sight_cosine,
                  range_factor * cant_cosine + cross_component * cant_sine,
                  cross_component * cant_cosine - range_factor * cant_sine)

cdef get_correction(double distance, double offset):
    if distance != 0:
        return atan(offset / distance)
    return 0

cdef double calculate_energy(double bullet_weight, double velocity):
    return bullet_weight * pow(velocity, 2) / 450400

cdef double calculate_ogv(double bullet_weight, double velocity):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12
