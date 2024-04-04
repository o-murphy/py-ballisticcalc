"""Classes to define zeroing or current environment conditions"""

import math
from dataclasses import dataclass, field

from .munition import Weapon, Ammo
# from .settings import Settings as Set
from .unit import Distance, Velocity, Temperature, Pressure, Angular, Dimension, PreferredUnits

__all__ = ('Atmo', 'Wind', 'Shot')

cStandardHumidity: float = 0.0  # Relative Humidity
cPressureExponent: float = 5.255876  # =g*M/R*L
cA0: float = 1.24871
cA1: float = 0.0988438
cA2: float = 0.00152907
cA3: float = -3.07031e-06
cA4: float = 4.21329e-07
cA5: float = 3.342e-04
# ISA, metric prefer_units: (https://www.engineeringtoolbox.com/international-standard-atmosphere-d_985.html)
cDegreesCtoK: float = 273.15  # °K = °C + 273.15
cStandardTemperatureC: float = 15.0  # °C
cLapseRateMetric: float = -6.5e-03  # Lapse Rate, °C/m
cStandardPressureMetric: float = 1013.25  # hPa
cSpeedOfSoundMetric: float = 331.3  # Mach1 in m/s = cSpeedOfSound * sqrt(°K)
cStandardDensityMetric: float = 1.2250  # kg/m^3
cDensityImperialToMetric: float = 16.0185  # lb/ft^3 to kg/m^3
# ICAO standard atmosphere:
cDegreesFtoR: float = 459.67  # °R = °F + 459.67
cStandardTemperatureF: float = 59.0  # °F
cLapseRateImperial: float = -3.56616e-03  # Lapse rate, °F/ft
cStandardPressure: float = 29.92  # InHg
cSpeedOfSoundImperial: float = 49.0223  # Mach1 in fps = cSpeedOfSound * sqrt(°R)
cStandardDensity: float = 0.076474  # lb/ft^3


@dataclass
class Atmo(PreferredUnits.Mixin):  # pylint: disable=too-many-instance-attributes
    """Atmospheric conditions and density calculations"""

    altitude: [float, Pressure] = Dimension(prefer_units="distance")
    pressure: [float, Pressure] = Dimension(prefer_units="pressure")
    temperature: [float, Temperature] = Dimension(prefer_units="temperature")

    humidity: float = 0.0  # Relative humidity [0% to 100%]
    density_ratio: float = field(init=False)  # Density / cStandardDensity
    mach: Velocity = field(init=False)  # Mach 1 in reference atmosphere
    _mach1: float = field(init=False)  # Mach 1 in reference atmosphere in fps
    _a0: float = field(init=False)  # Initial reference altitude (ft)
    _t0: float = field(init=False)  # Temperature given at reference altitude °F
    _p0: float = field(init=False)  # Barometric pressure (sea level)
    _ta: float = field(init=False)  # Standard temperature at reference altitude °F

    def __post_init__(self) -> None:
        if self.humidity > 1:
            self.humidity = self.humidity / 100.0
        if not 0 <= self.humidity <= 1:
            self.humidity = 0.0
        if not self.altitude:
            self.altitude = Distance.Foot(0)
        if not self.temperature:
            self.temperature = Atmo.standard_temperature(self.altitude)
        if not self.pressure:
            self.pressure = Atmo.standard_pressure(self.altitude)

        self._t0 = self.temperature >> Temperature.Fahrenheit
        self._p0 = self.pressure >> Pressure.InHg
        self._a0 = self.altitude >> Distance.Foot
        self._ta = self._a0 * cLapseRateImperial + cStandardTemperatureF
        self.density_ratio = self.calculate_density(self._t0, self._p0) / cStandardDensity
        self._mach1 = Atmo.machF(self._t0)
        self.mach = Velocity.FPS(self._mach1)

    @staticmethod
    def standard_temperature(altitude: Distance) -> Temperature:
        """ICAO standard temperature for altitude"""
        return Temperature.Fahrenheit(cStandardTemperatureF
                                      + (altitude >> Distance.Foot) * cLapseRateImperial)

    @staticmethod
    def standard_pressure(altitude: Distance) -> Pressure:
        """ICAO standard pressure for altitude"""
        return Pressure.InHg(0.02953
                             * math.pow(3.73145 - 2.56555e-05 * (altitude >> Distance.Foot),
                                        cPressureExponent)
                             )
        # # Metric formula
        # Pressure.hPa(cStandardPressureMetric
        #     * math.pow(1 - cLapseRateMetric * (altitude >> Distance.Meter) / (cStandardTemperatureC + cDegreesCtoK),
        #                cPressureExponent))

    @staticmethod
    def standard(altitude: [float, Distance] = 0, temperature: Temperature = None) -> 'Atmo':
        """Creates standard ICAO atmosphere at given altitude.
            If temperature not specified uses standard temperature.
        """
        return Atmo.icao(altitude, temperature)

    @staticmethod
    def icao(altitude: [float, Distance] = 0, temperature: Temperature = None) -> 'Atmo':
        """Creates standard ICAO atmosphere at given altitude.
            If temperature not specified uses standard temperature.
        """
        altitude = PreferredUnits.distance(altitude)
        if temperature is None:
            temperature = Atmo.standard_temperature(altitude)
        pressure = Atmo.standard_pressure(altitude)

        return Atmo(
            altitude >> PreferredUnits.distance,
            pressure >> PreferredUnits.pressure,
            temperature >> PreferredUnits.temperature,
            cStandardHumidity
        )

    @staticmethod
    def machF(fahrenheit: float) -> float:
        """:return: Mach 1 in fps for Fahrenheit temperature"""
        return math.sqrt(fahrenheit + cDegreesFtoR) * cSpeedOfSoundImperial

    @staticmethod
    def machC(celsius: float) -> float:
        """:return: Mach 1 in m/s for Celsius temperature"""
        return math.sqrt(1 + celsius / cDegreesCtoK) * cSpeedOfSoundMetric

    @staticmethod
    def air_density(t: Temperature, p: Pressure, humidity: float) -> float:
        """Source: https://en.wikipedia.org/wiki/Density_of_air#Humid_air
        :return: Density in Imperial units (lb/ft^3)
        """
        tC = t >> Temperature.Celsius
        pM = (p >> Pressure.hPa) * 100  # Pressure in Pascals
        # Tetens approximation to saturation vapor pressure:
        psat = 6.1078 * math.pow(10, 17.27 * tC / (tC + 237.3))
        pv = humidity * psat  # Pressure of water vapor in Pascals
        pd = pM - pv  # Partial pressure of dry air in Pascals
        # Density in metric units kg/m^3
        density = (pd * 0.0289652 + pv * 0.018016) / (8.31446 * (tC + cDegreesCtoK))
        return density / cDensityImperialToMetric

    @property
    def density_metric(self) -> float:
        """Returns density in kg/m^3"""
        return self.density_ratio * cStandardDensityMetric

    @property
    def density_imperial(self) -> float:
        """Returns density in lb/ft^3"""
        return self.density_ratio * cStandardDensity

    def temperature_at_altitude(self, altitude: float) -> float:
        """ Interpolated temperature at altitude
        :param altitude: ASL in ft
        :return: temperature in °F
        """
        return (altitude - self._a0) * cLapseRateImperial + self._t0

    def calculate_density(self, t: float, p: float) -> float:
        """
        :param t: temperature in °F
        :param p: pressure in inHg
        :return: density with specified atmosphere
        """
        if t > 0:
            et0 = cA0 + t * (cA1 + t * (cA2 + t * (cA3 + t * cA4)))
            et = cA5 * self.humidity * et0
            hc = (p - 0.3783 * et) / cStandardPressure
        else:
            hc = 1.0

        density = cStandardDensity * (
                (cStandardTemperatureF + cDegreesFtoR) / (t + cDegreesFtoR)
        ) * hc
        return density

    def get_density_factor_and_mach_for_altitude(self, altitude: float) -> (float, float):
        """
        :param altitude: ASL in units of feet
        :return: density ratio and Mach 1 (fps) for the specified altitude
        """
        # Within 30 ft of initial altitude use initial values
        if math.fabs(self._a0 - altitude) < 30:
            density_ratio = self.density_ratio
            mach = self._mach1
        else:
            # https://en.wikipedia.org/wiki/Density_of_air#Exponential_approximation
            density_ratio = math.exp(-altitude / 34112.0)
            t = self.temperature_at_altitude(altitude)
            mach = Atmo.machF(t)
        return density_ratio, mach


@dataclass
class Wind(PreferredUnits.Mixin):
    """
    Wind direction and velocity by down-range distance.
    direction_from = 0 is blowing from behind shooter. 
    direction_from = 90 degrees is blowing from shooter's left towards right.
    """

    velocity: [float, Velocity] = Dimension(prefer_units='velocity')
    direction_from: [float, Angular] = Dimension(prefer_units='angular')
    until_distance: [float, Distance] = Dimension(prefer_units='distance')
    MAX_DISTANCE_FEET = 1e8

    def __post_init__(self) -> None:
        if not self.until_distance:
            self.until_distance = Distance.Foot(Wind.MAX_DISTANCE_FEET)
        if not self.direction_from or not self.velocity:
            self.direction_from = 0
            self.velocity = 0


@dataclass
class Shot(PreferredUnits.Mixin):
    """
    Stores shot parameters for the trajectory calculation.
    
    :param look_angle: Angle of sight line relative to horizontal.
        If the look_angle != 0 then any target in sight crosshairs will be at a different altitude:
            With target_distance = sight distance to a target (i.e., as through a rangefinder):
                * Horizontal distance X to target = cos(look_angle) * target_distance
                * Vertical distance Y to target = sin(look_angle) * target_distance
    :param relative_angle: Elevation adjustment added to weapon.zero_elevation for a particular shot.
    :param cant_angle: Tilt of gun from vertical, which shifts any barrel elevation
        from the vertical plane into the horizontal plane by sine(cant_angle)
    """

    look_angle: [float, Angular] = Dimension(prefer_units='angular')
    relative_angle: [float, Angular] = Dimension(prefer_units='angular')
    cant_angle: [float, Angular] = Dimension(prefer_units='angular')

    weapon: Weapon = field(default=None)
    ammo: Ammo = field(default=None)
    atmo: Atmo = field(default=None)
    winds: list[Wind] = field(default=None)

    # NOTE: Calculator assumes that winds are sorted by Wind.until_distance (ascending)

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

    def __post_init__(self) -> None:
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
