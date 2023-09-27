from libc.math cimport sqrt, fabs, pow, sin, cos, log10, floor, atan
cimport cython

from .conditions import *
from .munition import *
from .settings import Settings
from .trajectory_data import TrajectoryData
from .unit import *

cdef double cZeroFindingAccuracy = 0.000005
cdef double cMinimumVelocity = 50.0
cdef double cMaximumDrop = -15000
cdef int cMaxIterations = 10
cdef double cGravityConstant = -32.17405

cdef class Vector:
    cdef double x
    cdef double y
    cdef double z

    def __cinit__(Vector self, double x, double y, double z):
        self.x = x
        self.y = y
        self.z = z

    cdef double magnitude(Vector self):
        return sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    cdef Vector mul_by_const(Vector self, double a):
        return Vector(self.x * a, self.y * a, self.z * a)

    cdef double mul_by_vector(Vector self, Vector b):
        return self.x * b.x + self.y * b.y + self.z * b.z

    cdef Vector add(Vector self, Vector b):
        return Vector(self.x + b.x, self.y + b.y, self.z + b.z)

    cdef Vector subtract(Vector self, Vector b):
        return Vector(self.x - b.x, self.y - b.y, self.z - b.z)

    cdef Vector negate(Vector self):
        return Vector(-self.x, -self.y, -self.z)

    cdef Vector normalize(Vector self):
        cdef double m = self.magnitude()
        if fabs(m) < 1e-10:
            return Vector(self.x, self.y, self.z)
        return self.mul_by_const(1.0 / m)

    def __add__(Vector self, Vector other):
        return self.add(other)

    def __radd__(Vector self, Vector other):
        return self.add(other)

    def __iadd__(Vector self, Vector other):
        return self.add(other)

    def __sub__(Vector self, Vector other):
        return self.subtract(other)

    def __rsub__(Vector self, Vector other):
        return self.subtract(other)

    def __isub__(Vector self, Vector other):
        return self.subtract(other)

    def __mul__(Vector self, object other):
        if isinstance(other, (int, float)):
            return self.mul_by_const(other)
        elif isinstance(other, Vector):
            return self.mul_by_vector(other)
        raise TypeError(other)

    def __rmul__(Vector self, object other):
        return self.__mul__(other)

    def __imul__(Vector self, object other):
        return self.__mul__(other)

    def __neg__(Vector self):
        return self.negate()


cdef class TrajectoryCalc:

    cdef double get_calculation_step(self, double step):
        cdef:
            int step_order, maximum_order
            double step
            double maximum_step = Settings._MIN_CALC_STEP_SIZE

        step = step / 2

        if step > maximum_step:
            step_order = int(floor(log10(step)))
            maximum_order = int(floor(log10(maximum_step)))
            step = step / pow(10, step_order - maximum_order + 1)

        return step

    def sight_angle(self, ammo: Ammo, weapon: Weapon, atmo: Atmo):
        return self._sight_angle(ammo, weapon, atmo)

    def trajectory(self, ammo: Ammo, weapon: Weapon, atmo: Atmo,
                   shot_info: Shot, winds: list[Wind]):
        return self._trajectory(ammo, weapon, atmo, shot_info, winds)

    cdef _sight_angle(TrajectoryCalc self, object ammo, object weapon, object atmo):
        cdef:
            double calculation_step, mach, density_factor, muzzle_velocity
            double barrel_azimuth, barrel_elevation
            double velocity, time, zero_distance, maximum_range
            double delta_time, drag, zero_finding_error, sight_height
            int iterations_count
            Vector gravity_vector, range_vector, velocity_vector, delta_range_vector

        calculation_step = self.get_calculation_step(
            Distance(10, weapon.zero_distance.units) >> Distance.Foot)
        zero_distance = weapon.zero_distance >> Distance.Foot
        maximum_range = zero_distance + calculation_step

        sight_height = weapon.sight_height >> Distance.Foot

        mach = atmo.mach >> Velocity.FPS
        density_factor = atmo.density_factor()
        muzzle_velocity = ammo.muzzle_velocity >> Velocity.FPS
        barrel_azimuth = 0.0
        barrel_elevation = 0.0

        iterations_count = 0

        zero_finding_error = cZeroFindingAccuracy * 2
        gravity_vector = Vector(.0, cGravityConstant, .0)
        while zero_finding_error > cZeroFindingAccuracy and iterations_count < cMaxIterations:
            velocity = muzzle_velocity
            time = 0.0

            # x - distance towards target,
            # y - drop and
            # z - windage

            range_vector = Vector(.0, -sight_height, .0)
            velocity_vector = Vector(
                cos(barrel_elevation) * cos(barrel_azimuth),
                sin(barrel_elevation),
                cos(barrel_elevation) * sin(barrel_azimuth)
            ) * velocity

            while range_vector.x <= maximum_range:
                if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                    break

                delta_time = calculation_step / velocity_vector.x
                velocity = velocity_vector.magnitude()
                drag = density_factor * velocity * ammo.projectile.dm.drag(velocity / mach)

                velocity_vector = velocity_vector - (velocity_vector * drag - gravity_vector) * delta_time
                delta_range_vector = Vector(calculation_step,
                                            velocity_vector.y * delta_time,
                                            velocity_vector.z * delta_time)
                range_vector = range_vector + delta_range_vector
                velocity = velocity_vector.magnitude()
                time = time + delta_range_vector.magnitude() / velocity
                if fabs(range_vector.x - zero_distance) < 0.5 * calculation_step:
                    zero_finding_error = fabs(range_vector.y)
                    barrel_elevation = barrel_elevation - range_vector.y / range_vector.x
                    break

                iterations_count += 1
        return Angular.Radian(barrel_elevation)

    cdef _trajectory(TrajectoryCalc self, object ammo, object weapon, object atmo,
                     object shot_info, list[object] winds):
        cdef:
            double step, calculation_step, bullet_weight, stability_coefficient
            double barrel_azimuth, barrel_elevation, alt0, density_factor, mach
            double next_wind_range, time, muzzle_velocity, velocity, windage, delta_time, drag
            double maximum_range, next_range_distance, sight_height
            int current_item, ranges_length, current_wind, len_winds, twist_coefficient
            ranges
            double windage_adjustment, drop_adjustment

            Vector gravity_vector, range_vector, velocity_vector, velocity_adjusted, delta_range_vector
            Vector wind_vector

            double twist = weapon.twist >> Distance.Inch
            double proj_length = ammo.projectile.length >> Distance.Inch
            double proj_diameter = ammo.projectile.diameter >> Distance.Inch

        maximum_range = (shot_info.max_range >> Distance.Foot) + 1
        step = shot_info.step >> Distance.Foot

        calculation_step = self.get_calculation_step(step)

        bullet_weight = ammo.projectile.weight >> Weight.Grain

        stability_coefficient = 1.0

        ranges_length = int(floor(maximum_range / step)) + 1
        ranges = []

        barrel_azimuth = .0
        barrel_elevation = shot_info.sight_angle >> Angular.Radian
        barrel_elevation = barrel_elevation + (shot_info.shot_angle >> Angular.Radian)
        alt0 = atmo.altitude >> Distance.Foot

        # Never used in upstream, uncomment on need
        # density_factor, mach = atmo.get_density_factor_and_mach_for_altitude(alt0)

        current_wind = 0
        next_wind_range = 1e7

        len_winds = len(winds)

        if len_winds < 1:
            wind_vector = Vector(.0, .0, .0)
        else:
            if len_winds > 1:
                next_wind_range = winds[0].until_distance() >> Distance.Foot
            wind_vector = wind_to_vector(shot_info, winds[0])

        if Settings.USE_POWDER_SENSITIVITY:
            muzzle_velocity = ammo.get_velocity_for_temp(atmo.temperature) >> Velocity.FPS
        else:
            muzzle_velocity = ammo.muzzle_velocity >> Velocity.FPS

        gravity_vector = Vector(.0, cGravityConstant, .0)
        velocity = muzzle_velocity
        time = .0

        # x - distance towards target,
        # y - drop and
        # z - windage

        sight_height = weapon.sight_height >> Distance.Foot
        range_vector = Vector(.0, -sight_height, .0)
        velocity_vector = Vector(cos(barrel_elevation) * cos(barrel_azimuth), sin(barrel_elevation),
                                 cos(barrel_elevation) * sin(barrel_azimuth)) * velocity
        current_item = 0

        next_range_distance = .0

        twist_coefficient = 0

        if twist != 0 and proj_length and proj_diameter:
            stability_coefficient = calculate_stability_coefficient(
                ammo, weapon, atmo
            )

            twist_coefficient = -1 if twist > 0 else 1

        while range_vector.x <= maximum_range + calculation_step:

            if velocity < cMinimumVelocity or range_vector.y < cMaximumDrop:
                break

            density_factor, mach = atmo.get_density_factor_and_mach_for_altitude(alt0 + range_vector.y)

            if range_vector.x >= next_wind_range:
                current_wind += 1
                wind_vector = wind_to_vector(shot_info, winds[current_wind])

                if current_wind == len_winds - 1:
                    next_wind_range = 1e7
                else:
                    next_wind_range = winds[current_wind].until_distance() >> Distance.Foot

            if range_vector.x >= next_range_distance:
                windage = range_vector.z

                if twist != 0:
                    windage += (1.25 * (stability_coefficient + 1.2) * pow(time, 1.83) * twist_coefficient) / 12

                drop_adjustment = get_correction(range_vector.x, range_vector.y)
                windage_adjustment = get_correction(range_vector.x, windage)

                ranges.append(TrajectoryData(
                    time=time,
                    distance=Distance.Foot(range_vector.x),
                    drop=Distance.Foot(range_vector.y),
                    drop_adj=Angular.Radian(drop_adjustment),
                    windage=Distance.Foot(windage),
                    windage_adj=Angular.Radian(windage_adjustment),
                    velocity=Velocity.FPS(velocity),
                    mach=velocity / mach,
                    energy=Energy.FootPound(calculate_energy(bullet_weight, velocity)),
                    ogw=Weight.Pound(calculate_ogv(bullet_weight, velocity))
                ))

                next_range_distance += step
                current_item += 1
                if current_item == ranges_length:
                    break

            velocity_adjusted = velocity_vector - wind_vector

            delta_time = calculation_step / velocity_vector.x
            velocity = velocity_adjusted.magnitude()
            drag = density_factor * velocity * ammo.projectile.dm.drag(velocity / mach)

            velocity_vector = velocity_vector - (velocity_adjusted * drag - gravity_vector) * delta_time
            delta_range_vector = Vector(calculation_step,
                                        velocity_vector.y * delta_time,
                                        velocity_vector.z * delta_time)
            range_vector = range_vector + delta_range_vector
            velocity = velocity_vector.magnitude()
            time = time + delta_range_vector.magnitude() / velocity

        return ranges


cdef double calculate_stability_coefficient(object ammo, object rifle, object atmo):
    cdef:
        double weight = ammo.projectile.weight >> Weight.Grain
        double diameter = ammo.projectile.diameter >> Distance.Inch
        double twist = fabs(rifle.twist >> Distance.Inch) / diameter
        double length = (ammo.projectile.length >> Distance.Inch) / diameter
        double ft = atmo.temperature >> Temperature.Fahrenheit
        double mv = ammo.muzzle_velocity >> Velocity.FPS
        double pt = atmo.pressure >> Pressure.InHg
        double sd = 30 * weight / (pow(twist, 2) * pow(diameter, 3) * length * (1 + pow(length, 2)))
        double fv = pow(mv / 2800, 1.0 / 3.0)
        double ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
    return sd * fv * ftp

cdef Vector wind_to_vector(object shot, object wind):
    cdef:
        double sight_cosine = cos(shot.sight_angle >> Angular.Radian)
        double sight_sine = sin(shot.sight_angle >> Angular.Radian)
        double cant_cosine = cos(shot.cant_angle >> Angular.Radian)
        double cant_sine = sin(shot.cant_angle >> Angular.Radian)
        double range_velocity = (wind.velocity >> Velocity.FPS) * cos(wind.direction >> Angular.Radian)
        double cross_component = (wind.velocity >> Velocity.FPS) * sin(wind.direction >> Angular.Radian)
        double range_factor = -range_velocity * sight_sine
    return Vector(range_velocity * sight_cosine,
                  range_factor * cant_cosine + cross_component * cant_sine,
                  cross_component * cant_cosine - range_factor * cant_sine)

@cython.cdivision(True)
cdef double get_correction(double distance, double offset):
    if distance != 0:
        return atan(offset / distance)
    return 0  # better None

cdef double calculate_energy(double bullet_weight, double velocity):
    return bullet_weight * pow(velocity, 2) / 450400

cdef double calculate_ogv(double bullet_weight, double velocity):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12
