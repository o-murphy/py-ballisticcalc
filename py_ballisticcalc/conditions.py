"""Classes to define zeroing or current environment conditions"""

import math
from dataclasses import dataclass, field

from .settings import Settings as Set
from .unit import Distance, Velocity, Temperature, Pressure, TypedUnits, Angular
from .munition import Weapon, Ammo

__all__ = ('Atmo', 'Wind', 'Shot')

cDegreesFtoR: float = 459.67  # °R = °F + 459.67
cDegreesCtoK: float = 273.15  # °K = °C + 273.15
cLapseRateImperial: float = -3.56616e-03  # Lapse rate, °F/ft
cPressureExponent: float = -5.255876      # =g*M/R*L
cSpeedOfSoundImperial: float = 49.0223    # Mach1 in fps = cSpeedOfSound * sqrt(°R)
cSpeedOfSoundMetric: float = 331.3        # Mach1 in m/s = cSpeedOfSound * sqrt(°K)
cDensityImperialToMetric: float = 16.0185 # lb/ft^3 to kg/m^3
cA0: float = 1.24871
cA1: float = 0.0988438
cA2: float = 0.00152907
cA3: float = -3.07031e-06
cA4: float = 4.21329e-07
cA5: float = 3.342e-04
# ICAO standard atmosphere:
cStandardTemperatureR: float = 518.67  # °R=59°F
cStandardTemperatureF: float = 59.0    # °F
cStandardPressure: float = 29.92       # InHg
cStandardDensity: float = 0.076474     # lb/ft^3
cStandardHumidity: float = 0.0         # Relative Humidity

@dataclass
class Atmo(TypedUnits):  # pylint: disable=too-many-instance-attributes
    """Atmospheric conditions and density calculations"""
    altitude: [float, Distance] = field(default_factory=lambda: Set.Units.distance)
    pressure: [float, Pressure] = field(default_factory=lambda: Set.Units.pressure)
    temperature: [float, Temperature] = field(default_factory=lambda: Set.Units.temperature)
    humidity: float = 0
    density: float = field(init=False)
    mach: Velocity = field(init=False)
    _mach1: Velocity = field(init=False)
    _a0: float = field(init=False)
    _t0: float = field(init=False)
    _p0: float = field(init=False)
    _ta: float = field(init=False)

    def __post_init__(self):
        if self.humidity > 1:
            self.humidity = self.humidity / 100.0
        if not 0 <= self.humidity <= 1:
            self.humidity = 0.0
        if not self.altitude:
            self.altitude = Distance.Foot(0)
        if not self.temperature:
            self.temperature = Atmo.standard_temperature(self.altitude)
        if not self.pressure:
            self.pressure = Atmo.standard_pressure(self.altitude)#, self.temperature)

        self.calculate()

    @staticmethod
    def standard_temperature(altitude: Distance) -> Temperature:
        """ICAO standard temperature for altitude"""
        return Temperature.Fahrenheit(cStandardTemperatureF
                    + (altitude >> Distance.Foot) * cLapseRateImperial)

    @staticmethod
    def standard_pressure(altitude: Distance) -> Pressure:
        """ICAO standard pressure for altitude"""
        return Pressure.InHg(0.02953
            * math.pow(3.73145 - (2.56555e-05) * (altitude >> Distance.Foot),
                       -cPressureExponent)
            )

    @staticmethod
    def standard(altitude: [float, Distance] = 0, temperature: Temperature=None):
        return Atmo.icao(altitude, temperature)

    @staticmethod
    def icao(altitude: [float, Distance] = 0, temperature: Temperature=None):
        """Creates standard ICAO atmosphere at given altitude.
            If temperature not specified uses standard temperature.
        """
        altitude = Set.Units.distance(altitude)
        if temperature is None:
            temperature = Atmo.standard_temperature(altitude)

        # TODO: Pretty sure this needs to be a function of altitude too?
        pressure = Pressure.InHg(
            cStandardPressure * math.pow(cStandardTemperatureR
                / ((temperature >> Temperature.Fahrenheit) + cDegreesFtoR),
                                         cPressureExponent
                                        )
        )

        return Atmo(
            altitude >> Set.Units.distance,
            pressure >> Set.Units.pressure,
            temperature >> Set.Units.temperature,
            cStandardHumidity
        )

    @staticmethod
    def machF(fahrenheit: float) -> float:
        """:return: Mach 1 in fps for Fahrenheit temperature"""
        return math.sqrt(fahrenheit + cDegreesFtoR) * cSpeedOfSoundImperial

    @staticmethod
    def machC(celsius: float) -> float:
        """:return: Mach 1 in m/s for Celsius temperature"""
        return math.sqrt(1+celsius / cDegreesCtoK) * cSpeedOfSoundMetric

    def temperature_at_altitude(self, altitude: float) -> float:
        """ Interpolated temperature at altitude
        :return: temperature in °F
        """
        return (altitude - self._a0) * cLapseRateImperial + self._t0

    def density_factor(self) -> float:
        """:return: projectile density_factor"""
        return self.density / cStandardDensity

    def calculate0(self, t, p) -> (float, float):
        """:return: density and mach with specified atmosphere"""
        if t > 0:
            et0 = cA0 + t * (cA1 + t * (cA2 + t * (cA3 + t * cA4)))
            et = cA5 * self.humidity * et0
            hc = (p - 0.3783 * et) / cStandardPressure
        else:
            hc = 1.0

        density = cStandardDensity * (
                cStandardTemperatureR / (t + cDegreesFtoR)
        ) * hc
        mach = math.sqrt(t + cDegreesFtoR) * cSpeedOfSoundImperial
        return density, mach

    def calculate(self) -> None:
        """prepare the data for the calculation"""
        self._t0 = self.temperature >> Temperature.Fahrenheit
        self._p0 = self.pressure >> Pressure.InHg
        self._a0 = self.altitude >> Distance.Foot
        self._ta = self._a0 * cLapseRateImperial + cStandardTemperatureF

        self.density, self._mach1 = self.calculate0(self._t0, self._p0)
        self.mach = Velocity(self._mach1, Velocity.FPS)

    def get_density_factor_and_mach_for_altitude(self, altitude: float):
        """:return: density factor for the specified altitude"""
        if math.fabs(self._a0 - altitude) < 30:
            density = self.density / cStandardDensity
            mach = self._mach1
            return density, mach

        tb = altitude * cLapseRateImperial + cStandardTemperatureF
        t = self._t0 + self._ta - tb
        p = self._p0 * math.pow(self._t0 / t, cPressureExponent)

        density, mach = self.calculate0(t, p)
        return density / cStandardDensity, mach


@dataclass
class Wind(TypedUnits):
    """
    Wind direction and velocity by down-range distance.
    direction_from = 0 is blowing from behind shooter. 
    direction_from = 90 degrees is blowing from shooter's left towards right.
    """
    velocity: [float, Velocity] = field(default_factory=lambda: Set.Units.velocity)
    direction_from: [float, Angular] = field(default_factory=lambda: Set.Units.angular)
    until_distance: [float, Distance] = field(default_factory=lambda: Set.Units.distance)

    def __post_init__(self):
        if not self.until_distance:
            self.until_distance = Distance.Meter(9999)  # TODO: Set to a fundamental max value
        if not self.direction_from or not self.velocity:
            self.direction_from = 0
            self.velocity = 0


@dataclass
class Shot(TypedUnits):
    """
    Stores shot parameters for the trajectory calculation.
    
    :param look_angle: Angle of sight line relative to horizontal.
        If look_angle != 0 then any target in sight crosshairs will be at a different altitude:
            With target_distance = sight distance to a target (i.e., as through a rangefinder):
                * Horizontal distance X to target = cos(look_angle) * target_distance
                * Vertical distance Y to target = sin(look_angle) * target_distance
    :param relative_angle: Elevation adjustment added to weapon.zero_elevation for a particular shot.
    :param cant_angle: Tilt of gun from vertical, which shifts any barrel elevation
        from the vertical plane into the horizontal plane by sine(cant_angle)
    """
    look_angle: [float, Angular] = field(default_factory=lambda: Set.Units.angular)
    relative_angle: [float, Angular] = field(default_factory=lambda: Set.Units.angular)
    cant_angle: [float, Angular] = field(default_factory=lambda: Set.Units.angular)

    weapon: Weapon = field(default=None)
    ammo: Ammo = field(default=None)
    atmo: Atmo = field(default=None)
    winds: list[Wind] = field(default=None)

    @property
    def barrel_elevation(self) -> Angular:
        """Barrel elevation in vertical plane from horizontal"""
        return Angular.Radian((self.look_angle >> Angular.Radian)
                              + math.cos(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                               + (self.relative_angle >> Angular.Radian)))

    @property
    def barrel_azimuth(self) -> Angular:
        """Horizontal angle of barrel relative to sight line"""
        return Angular.Radian(math.sin(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                               + (self.relative_angle >> Angular.Radian)))

    def __post_init__(self):
        if not self.look_angle:
            self.look_angle = 0
        if not self.relative_angle:
            self.relative_angle = 0
        if not self.cant_angle:
            self.cant_angle = 0
        if not self.atmo:
            self.atmo = Atmo.icao()
        if not self.winds:
            self.winds = [Wind()]
