from libc.math cimport sqrt, fabs, pow, sin, cos, log10, floor, atan
from .unit import *
from .munition import *
from .conditions import *
from .trajectory_data import TrajectoryData

cdef double cZeroFindingAccuracy = 0.000005
cdef double cMinimumVelocity = 50.0
cdef double cMaximumDrop = -15000
cdef int cMaxIterations = 10
cdef double cGravityConstant = -32.17405

cdef struct vector:
    double x
    double y
    double z

cdef class Vector:
    cdef double _x
    cdef double _y
    cdef double _z

    def __init__(self, x: double, y: double, z: double):
        self._x = x
        self._y = y
        self._z = z

    def __str__(self):
        return f'{vector(self._x, self._y, self._z)}'

    cpdef double x(self):
        return self._x

    cpdef double y(self):
        return self._y

    cpdef double z(self):
        return self._z

    cdef string(self):
        cdef v = vector(self._x, self._y, self._z)
        return f'{v}'

    cpdef Vector copy(self):
        return Vector(self._x, self._y, self._z)

    cpdef double magnitude(self):
        cdef double m = sqrt(self._x * self._x + self._y * self._y + self._z * self._z)
        return m

    cpdef Vector multiply_by_const(self, float a):
        return Vector(self._x * a, self._y * a, self._z * a)

    cpdef double multiply_by_vector(self, b: Vector):
        cdef double var = self._x * b._x + self._y * b._y + self._z * b._z
        return var

    cpdef Vector add(self, b: Vector):
        return Vector(self._x + b._x, self._y + b._y, self._z + b._z)

    cpdef Vector subtract(self, b: Vector):
        return Vector(self._x - b._x, self._y - b._y, self._z - b._z)

    cpdef Vector negate(self):
        return Vector(-self._x, -self._y, -self._z)

    cpdef Vector normalize(self):
        cdef double m = self.magnitude()
        if fabs(m) < 1e-10:
            return Vector(self._x, self._y, self._z)
        return self.multiply_by_const(1.0 / m)

    def __add__(self, other: Vector):
        return self.add(other)

    def __radd__(self, other: Vector):
        return self.__add__(other)

    def __iadd__(self, other: Vector):
        return self.__add__(other)

    def __sub__(self, other: Vector):
        return self.subtract(other)

    def __rsub__(self, other: Vector):
        return other.subtract(self)

    def __isub__(self, other: Vector):
        return self.subtract(other)

    def __mul__(self, other: [Vector, float, int]):
        if isinstance(other, int) or isinstance(other, float):
            return self.multiply_by_const(other)
        elif isinstance(other, Vector):
            return self.multiply_by_vector(other)
        else:
            raise TypeError(other)

    def __rmul__(self, other: [Vector, float, int]):
        return self.__mul__(other)

    def __imul__(self, other: [Vector, float, int]):
        return self.__mul__(other)

    def __neg__(self):
        return self.negate()

    def __iter__(self):
        yield self.x()
        yield self.y()
        yield self.z()

cdef class TrajectoryCalc:
    cdef _max_calc_step_size

    def __init__(self, max_calc_step_size: [float, Distance] = Distance(1, Distance.Foot)):
        self.set_max_calc_step_size(max_calc_step_size)

    cpdef max_calc_step_size(self):
        return self._max_calc_step_size

    cpdef set_max_calc_step_size(self, max_calc_step_size: [float, Distance] = Distance(1, Distance.Foot)):
        self._max_calc_step_size = max_calc_step_size

    cdef double get_calculation_step(self, double step):
        cdef step_order, maximum_order
        step = step / 2
        cdef double maximum_step = self._max_calc_step_size >> Distance.Foot

        if step > maximum_step:
            step_order = int(floor(log10(step)))
            maximum_order = int(floor(log10(maximum_step)))
            step = step / pow(10, float(step_order - maximum_order + 1))

        return step

    cpdef sight_angle(self, ammo: Ammo, weapon: Weapon, atmo: Atmo):
        cdef double calculation_step, mach, density_factor, muzzle_velocity
        cdef double barrel_azimuth, barrel_elevation
        cdef double velocity, time, zero_distance, maximum_range
        cdef double delta_time, drag, zero_finding_error

        cdef int iterations_count

        cdef gravity_vector, range_vector, velocity_vector, delta_range_vector

        calculation_step = self.get_calculation_step(
            Distance(10, weapon.zero_distance.units) >> Distance.Foot)

        mach = atmo.mach >> Velocity.FPS
        density_factor = atmo.density_factor()
        muzzle_velocity = ammo.muzzle_velocity >> Velocity.FPS
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
                0.0, -(weapon.sight_height >> Distance.Foot), 0.0
            )
            velocity_vector = Vector(
                cos(barrel_elevation) * cos(barrel_azimuth),
                sin(barrel_elevation),
                cos(barrel_elevation) * sin(barrel_azimuth)
            ) * velocity

            zero_distance = weapon.zero_distance >> Distance.Foot
            maximum_range = zero_distance + calculation_step

            while range_vector.x() <= maximum_range:
                if velocity < cMinimumVelocity or range_vector.y() < cMaximumDrop:
                    break

                delta_time = calculation_step / velocity_vector.x()
                velocity = velocity_vector.magnitude()
                drag = density_factor * velocity * ammo.projectile.dm.drag(velocity / mach)

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
        return Angular(barrel_elevation, Angular.Radian)

    cpdef trajectory(self, ammo: Ammo, weapon: Weapon, atmo: Atmo,
                     shot_info: Shot, winds: list[Wind]):
        cdef double range_to, step, calculation_step, bullet_weight, stability_coefficient
        cdef double barrel_azimuth, barrel_elevation, alt0, density_factor, mach
        cdef double next_wind_range, time, muzzle_velocity, velocity, windage, delta_time, drag
        cdef double maximum_range, next_range_distance, twist_coefficient
        cdef int current_item, ranges_length, current_wind, len_winds
        cdef calculate_drift, ranges, wind_vector
        cdef windage_adjustment, velocity_adjusted, delta_range_vector
        cdef gravity_vector, drop_adjustment, range_vector, velocity_vector

        range_to = (shot_info.max_range >> Distance.Foot) + 1  # + 1 needs to include last point to output
        step = shot_info.step >> Distance.Foot

        calculation_step = self.get_calculation_step(step)

        bullet_weight = ammo.projectile.weight >> Weight.Grain

        stability_coefficient = 1.0

        ranges_length = int(floor(range_to / step)) + 1
        ranges = []

        barrel_azimuth = .0
        barrel_elevation = shot_info.sight_angle >> Angular.Radian
        barrel_elevation = barrel_elevation + (shot_info.shot_angle >> Angular.Radian)
        alt0 = atmo.altitude >> Distance.Foot

        # Never used in upstream, uncomment on need
        # density_factor, mach = atmo.get_density_factor_and_mach_for_altitude(alt0)

        current_wind = 0
        next_wind_range = 1e7

        len_winds = int(len(winds))

        if len_winds < 1:
            wind_vector = Vector(0, 0, 0)
        else:
            if len(winds) > 1:
                next_wind_range = winds[0].until_distance() >> Distance.Foot
            wind_vector = wind_to_vector(shot_info, winds[0])

        muzzle_velocity = ammo.muzzle_velocity >> Velocity.FPS
        gravity_vector = Vector(0, cGravityConstant, 0)
        velocity = muzzle_velocity
        time = .0

        # x - distance towards target,
        # y - drop and
        # z - windage

        range_vector = Vector(.0, -(weapon.sight_height >> Distance.Foot), 0)
        velocity_vector = Vector(cos(barrel_elevation) * cos(barrel_azimuth), sin(barrel_elevation),
                                 cos(barrel_elevation) * sin(barrel_azimuth)) * velocity
        current_item = 0

        maximum_range = range_to
        next_range_distance = 0

        twist_coefficient = .0

        calculate_drift = False

        if weapon.twist != 0 and ammo.projectile.length and ammo.projectile.diameter:
            stability_coefficient = calculate_stability_coefficient(
                ammo, weapon, atmo
            )
            calculate_drift = True
            twist_coefficient = -1 if weapon.twist > 0 else 1

        while range_vector.x() <= maximum_range + calculation_step:

            if velocity < cMinimumVelocity or range_vector.y() < cMaximumDrop:
                break

            density_factor, mach = atmo.get_density_factor_and_mach_for_altitude(alt0 + range_vector.y())

            if range_vector.x() >= next_wind_range:
                current_wind += 1
                wind_vector = wind_to_vector(shot_info, winds[current_wind])

                if current_wind == len_winds - 1:
                    next_wind_range = 1e7
                else:
                    next_wind_range = winds[current_wind].until_distance() >> Distance.Foot

            if range_vector.x() >= next_range_distance:
                windage = range_vector.z()
                if calculate_drift:
                    windage += (1.25 * (stability_coefficient + 1.2) * pow(time, 1.83) * twist_coefficient) / 12

                drop_adjustment = get_correction(range_vector.x(), range_vector.y())
                windage_adjustment = get_correction(range_vector.x(), windage)

                ranges.append(TrajectoryData(
                    time=time,
                    distance=Distance(range_vector.x(), Distance.Foot),
                    drop=Distance(range_vector.y(), Distance.Foot),
                    drop_adj=Angular(drop_adjustment if drop_adjustment else 0, Angular.Radian),
                    windage=Distance(windage, Distance.Foot),
                    windage_adj=Angular(windage_adjustment if windage_adjustment else 0, Angular.Radian),
                    velocity=Velocity(velocity, Velocity.FPS),
                    mach=velocity / mach,
                    energy=Energy(calculate_energy(bullet_weight, velocity), Energy.FootPound),
                    ogw=Weight(calculate_ogv(bullet_weight, velocity), Weight.Pound))
                )

                next_range_distance += step
                current_item += 1
                if current_item == ranges_length:
                    break

            delta_time = calculation_step / velocity_vector.x()
            velocity_adjusted = velocity_vector - wind_vector
            velocity = velocity_adjusted.magnitude()

            drag = density_factor * velocity * ammo.projectile.dm.drag(velocity / mach)

            velocity_vector = velocity_vector - (velocity_adjusted * drag - gravity_vector) * delta_time
            delta_range_vector = Vector(calculation_step,
                                        velocity_vector.y() * delta_time,
                                        velocity_vector.z() * delta_time)
            range_vector = range_vector + delta_range_vector
            velocity = velocity_vector.magnitude()
            time = time + delta_range_vector.magnitude() / velocity

        return ranges

cdef double calculate_stability_coefficient(ammo, rifle, atmo):
    cdef double weight = ammo.projectile.weight >> Weight.Grain
    cdef double diameter = ammo.projectile.diameter >> Distance.Inch
    cdef double twist = fabs(rifle.twist >> Distance.Inch) / diameter
    cdef double length = (ammo.projectile.length >> Distance.Inch) / diameter
    cdef double sd = 30 * weight / (pow(twist, 2) * pow(diameter, 3) * length * (1 + pow(length, 2)))
    cdef double mv = ammo.muzzle_velocity >> Velocity.FPS
    cdef double fv = pow(mv / 2800, 1.0 / 3.0)
    cdef double ft = atmo.temperature >> Temperature.Fahrenheit
    cdef double pt = atmo.pressure >> Pressure.InHg
    cdef double ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)

    return sd * fv * ftp

cdef wind_to_vector(shot, wind):
    cdef double sight_cosine = cos(shot.sight_angle >> Angular.Radian)
    cdef double sight_sine = sin(shot.sight_angle >> Angular.Radian)
    cdef double cant_cosine = cos(shot.cant_angle >> Angular.Radian)
    cdef double cant_sine = sin(shot.cant_angle >> Angular.Radian)
    cdef double range_velocity = (wind.velocity >> Velocity.FPS) * cos(wind.direction >> Angular.Radian)
    cdef double cross_component = (wind.velocity >> Velocity.FPS) * sin(wind.direction >> Angular.Radian)
    cdef double range_factor = -range_velocity * sight_sine
    return Vector(range_velocity * sight_cosine,
                  range_factor * cant_cosine + cross_component * cant_sine,
                  cross_component * cant_cosine - range_factor * cant_sine)

cdef get_correction(double distance, double offset):
    if distance != 0:
        return atan(offset / distance)
    return None

cdef double calculate_energy(double bullet_weight, double velocity):
    return bullet_weight * pow(velocity, 2) / 450400

cdef double calculate_ogv(double bullet_weight, double velocity):
    return pow(bullet_weight, 2) * pow(velocity, 3) * 1.5e-12
