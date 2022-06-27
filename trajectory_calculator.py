import math
from bmath import unit, Vector
from projectile import Ammunition
from weapon import Weapon
from atmosphere import Atmosphere

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
        self._maximum_calculator_step_size = unit.Distance(1, unit.DistanceFoot).must_create()

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

        calculation_step = self.get_calculation_step(
            unit.Distance(10, weapon.zero.zero_distance.units()).must_create().get_in(unit.DistanceFoot))

        mach = atmosphere.mach().get_in(unit.VelocityFPS)
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
                range_vector = range_vector.Add(delta_range_vector)
                velocity = velocity_vector.magnitude()
                time = time + delta_range_vector.magnitude() / velocity
                if abs(range_vector.x - zero_distance) < 0.5 * calculation_step:
                    zero_finding_error = math.fabs(range_vector.y)
                    barrel_elevation = barrel_elevation - range_vector.y / range_vector.x
                    break

                iterations_count += 1
        return unit.Angular(barrel_elevation, unit.AngularRadian).must_create()
