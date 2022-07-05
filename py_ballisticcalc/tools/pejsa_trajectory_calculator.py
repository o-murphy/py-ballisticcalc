"""
It's adaptation of Arthur J. Pejsa trajectory calculation algorithm
for py_ballisticcalc (Python3) library
Sources from http://accurateshooter.net/Downloads/pejsajacksonballistics.xls, now unavailable
You can use this method as alternative for standard trajectory calculator
It isn't recommended for regular calculations due to lack of precision and lack of support for BC other than G1
Use standard and extended classes for the best results that we currently have
"""


from ..profile import *


class PejsaTrajectoryCalculator(object):
    """
    NOTICE:
    NOT USE FOR THE REGULAR CALCULATIONS
    """
    start_range = 0  # yard
    mayewski_constant = 246
    standard_pressure = 1000  # mbar

    def __init__(self,
                 atmosphere: Atmosphere,
                 ammunition: Ammunition,
                 weapon: Weapon,
                 wind_info: WindInfo,
                 retard_coeff_rate: float,
                 impact_height: unit.Distance,
                 moa_value: unit.Angular
                 ):
        self._muzzle_velocity = ammunition.muzzle_velocity.get_in(unit.VelocityFPS)
        self._bullet_weight = ammunition.bullet.bullet_weight.get_in(unit.WeightGrain)
        self._bc = ammunition.bullet.ballistic_coefficient.value

        self._zero_range = weapon.zero.zero_distance.get_in(unit.DistanceYard)

        self._wind_velocity = wind_info.velocity.get_in(unit.VelocityMPH)
        self._wind_direction = wind_info.direction.get_in(unit.AngularDegree) / 30

        self._temperature = atmosphere.temperature.get_in(unit.TemperatureFahrenheit)
        self._altitude = atmosphere.altitude.get_in(unit.DistanceFoot)
        self._pressure = atmosphere.pressure.get_in(unit.PressureBar) / 1000

        self._sight_height = weapon.sight_height.get_in(unit.DistanceInch)
        self._retard_coeff_rate = retard_coeff_rate

        self._adjusted_bc = self.adjusted_bc
        self._retardation_coeff = self.retardation_coeff
        self._adj_retard_coeff = self.adj_retard_coeff
        self._drop_at_zero = self.drop_at_zero()

        self._impact_height = impact_height.get_in(unit.DistanceInch)
        self._moa_value = moa_value.get_in(unit.AngularInchesPer100Yd)

    @property
    def adjusted_bc(self):
        return self._bc * (460 + self._temperature) / (519 - self._altitude / 280) * math.exp(
            self._altitude / 31654) * (
                       2 - self._pressure / self.standard_pressure)

    @property
    def retardation_coeff(self):
        return self._bc * self.mayewski_constant * math.pow(self._muzzle_velocity, 0.45)

    @property
    def adj_retard_coeff(self):
        return self._retardation_coeff * (460 + self._temperature) / (519 - self._altitude / 280) * math.exp(
            self._altitude / 31654) * (2 - self._pressure / self.standard_pressure)

    def velocity_at_distance(self, distance: unit.Distance) -> unit.Velocity:
        """
        :param distance: unit.Distance instance
        :return: unit.Velocity instance at specified distance
        """
        velocity = self._muzzle_velocity * math.pow(
            1 - 3 * self._retard_coeff_rate * distance.get_in(unit.DistanceYard) / self._adj_retard_coeff,
            1 / self._retard_coeff_rate)
        return unit.Velocity(velocity, unit.VelocityFPS)

    def energy_at_velocity(self, velocity: unit.Velocity) -> unit.Energy:
        """
        :param velocity: unit.Velocity instance
        :return: unit.Energy instance at specified velocity
        """
        energy = self._bullet_weight * math.pow(velocity.get_in(unit.VelocityFPS), 2) / 450380
        return unit.Energy(energy, unit.EnergyFootPound)

    def drop_at_zero(self):
        zero_drop = math.pow(
            ((41.68 / self._muzzle_velocity) / ((1 / (0 + self._zero_range)) - (1 / (self.adj_retard_coeff - (
                    0.75 + 0.00006 * self._zero_range) * self._retard_coeff_rate * self._zero_range)))), 2)
        return unit.Distance(zero_drop, unit.DistanceInch)

    def drop_at_distance(self, energy: unit.Energy, distance: unit.Distance):
        dist = distance.get_in(unit.DistanceYard)
        if dist == 0:
            return self.drop_at_zero()
        elif energy:
            drop = math.pow(((41.68 / self._muzzle_velocity) / ((1 / (0 + dist)) - (
                    1 / (self._adj_retard_coeff - (0.75 + 0.00006 * dist) * self._retard_coeff_rate * dist)))), 2)
            return unit.Distance(drop, unit.DistanceInch)
        return None

    def path_at_distance(self, energy: unit.Energy, drop: unit.Distance, distance: unit.Distance):
        if energy and drop:
            dist = distance.get_in(unit.DistanceYard)
            drop_ = drop.get_in(unit.DistanceInch)
            zero_drop = self._drop_at_zero.get_in(unit.DistanceInch)
            path = -(drop_ + self._sight_height) + (
                    zero_drop + self._sight_height + self._impact_height) * dist / self._zero_range
            return unit.Distance(path, unit.DistanceInch)
        return None

    def elevation_at_distance(self, energy: unit.Energy, path: unit.Distance, distance: unit.Distance):
        dist = distance.get_in(unit.DistanceYard)
        path__ = path.get_in(unit.DistanceInch)
        if energy and path and dist > 0:
            elevation = - path__ / dist / self._moa_value * 100
            return unit.Angular(elevation, unit.AngularMOA)
        return None

    def windage_at_distance(self, energy: unit.Energy, distance: unit.Distance):
        dist = distance.get_in(unit.DistanceYard)

        if energy and dist > 0:
            windage = (79.2 * dist * self._wind_velocity / self._muzzle_velocity / (
                    self._adj_retard_coeff / dist - 1 - self._retard_coeff_rate)
                       ) / dist / self._moa_value * 100 * math.sin(
                self._wind_direction / 12 * 2 * math.pi)
            return unit.Angular(windage, unit.AngularMOA)
        return None

    def time_at_velocity(self, energy: unit.Energy, speed: unit.Velocity):
        speed_ = speed.get_in(unit.VelocityFPS)
        if energy:
            time = (self._adj_retard_coeff / self._muzzle_velocity) / (1 - self._retard_coeff_rate) * (
                    (self._muzzle_velocity / speed_) ** (1 - self._retard_coeff_rate) - 1)
            return round(time, 2)
        return None

    def trajectory(self, max_distance: int, calc_step: int, units: int):

        distances = []
        for val in range(0, max_distance, calc_step):
            distances.append(unit.Distance(val, units))

        _output = []

        for _dist in distances:
            _v = self.velocity_at_distance(_dist)
            _en = self.energy_at_velocity(_v)
            _drop = self.drop_at_distance(_en, _dist)
            _path = self.path_at_distance(_en, _drop, _dist)
            _elvn = self.elevation_at_distance(_en, _path, _dist)
            _wndg = self.windage_at_distance(_en, _dist)
            _time = self.time_at_velocity(_en, _v)

            _output.append({
                'distance': _dist,
                'velocity': _v,
                'drop': _drop,
                'path': _path,
                'elevation': _elvn,
                'windage': _wndg,
                'time': _time
            })

        return _output


# usage example
if __name__ == '__main__':
    atmo = Atmosphere.create_icao(unit.Distance(0, unit.DistanceFoot))
    bc = BallisticCoefficient(0.530, DragTableG1)
    bullet = Projectile(bc, unit.Weight(105, unit.WeightGrain))
    ammo = Ammunition(bullet, unit.Velocity(2900, unit.VelocityFPS))
    zero = ZeroInfo.create_with_another_ammo_and_atmosphere(unit.Distance(100, unit.DistanceYard), ammo, atmo)
    wpn = Weapon(unit.Distance(1.75, unit.DistanceInch), zero)
    wind = WindInfo(unit.Distance(0, unit.DistanceFoot), unit.Velocity(0, unit.VelocityMPS),
                    unit.Angular(0, unit.AngularDegree))
    trajectory_calc = PejsaTrajectoryCalculator(atmo, ammo, wpn, wind,
                                                retard_coeff_rate=0.5,
                                                impact_height=unit.Distance(0, unit.DistanceInch),
                                                moa_value=unit.Angular(1.05, unit.AngularInchesPer100Yd))

    print(trajectory_calc.trajectory(1000, 100, unit.DistanceYard))
