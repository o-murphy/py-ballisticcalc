"""Classes to define zeroing or current environment conditions"""

import math
import warnings
from dataclasses import dataclass

from typing_extensions import List, Union, Optional, Tuple

from py_ballisticcalc.munition import Weapon, Ammo
from py_ballisticcalc.vector import Vector
from py_ballisticcalc.unit import Distance, Velocity, Temperature, Pressure, Angular, PreferredUnits
from py_ballisticcalc.constants import *  # pylint: disable=wildcard-import,unused-wildcard-import

__all__ = ('Atmo', 'Wind', 'Shot')


@dataclass
class Atmo:  # pylint: disable=too-many-instance-attributes
    """
    A base class for creating Atmo.
    Atmospheric conditions and density calculations

    Attributes:
        altitude: Altitude relative to sea level
        pressure: Atmospheric pressure
        temperature: Atmospheric temperature
        humidity: Atmospheric humidity
        powder_temp: Custom temperature of powder different to atmospheric.
            Uses together with Ammo.use_powder_sensitivity
        density_ratio: Density ratio
        mach: Velocity instance that keeps velocity in mach for current atmosphere
    """

    altitude: Distance
    pressure: Pressure
    temperature: Temperature
    humidity: float  # Relative humidity [0% to 100%]
    powder_temp: Temperature

    density_ratio: float
    mach: Velocity
    _mach1: float
    _a0: float
    _t0: float
    _p0: float
    _ta: float

    def __init__(self,
                 altitude: Optional[Union[float, Distance]] = None,
                 pressure: Optional[Union[float, Pressure]] = None,
                 temperature: Optional[Union[float, Temperature]] = None,
                 humidity: float = 0.0,
                 powder_t: Optional[Union[float, Temperature]] = None):
        """
        Create a new Atmo instance with given parameters

        Args:
            altitude: Altitude relative to sea level
            pressure: Atmospheric pressure
            temperature: Atmospheric temperature
            humidity: Atmospheric humidity in percents
            powder_t: Custom temperature of powder different to atmospheric.
                Uses together with Ammo.use_powder_sensitivity

        Example:
            This is how you can create an Atmo
            ```python
            from py_ballisticcalc import Atmo
            wind = Wind(
                altitude=Unit.Meter(100),
                pressure=Unit.hPa(1000),
                temperature=Unit.Celsius(20),
                humidity=50,
                powder_t=1.23
            )
            ```
        """

        self.humidity = humidity or 0.0
        if self.humidity > 1:
            self.humidity = humidity / 100.0
        if not 0 <= self.humidity <= 1:
            self.humidity = 0.0

        self.altitude = PreferredUnits.distance(altitude or 0)
        self.pressure = PreferredUnits.pressure(pressure or Atmo.standard_pressure(self.altitude))
        self.temperature = PreferredUnits.temperature(temperature or Atmo.standard_temperature(self.altitude))
        # ensure that if powder_temperature are not provided we use atmospheric temperature
        self.powder_temp = PreferredUnits.temperature(powder_t or self.temperature)

        self._t0 = self.temperature >> Temperature.Fahrenheit
        self._p0 = self.pressure >> Pressure.InHg
        self._a0 = self.altitude >> Distance.Foot
        self._ta = self._a0 * cLapseRateImperial + cStandardTemperatureF
        self.density_ratio = self.calculate_density(self._t0, self._p0) / cStandardDensity
        self._mach1 = Atmo.machF(self._t0)
        self.mach = Velocity.FPS(self._mach1)

    @staticmethod
    def standard_temperature(altitude: Distance) -> Temperature:
        """
        Returns:
            ICAO standard temperature for altitude
        """
        return Temperature.Fahrenheit(cStandardTemperatureF
                                      + (altitude >> Distance.Foot) * cLapseRateImperial)

    @staticmethod
    def standard_pressure(altitude: Distance) -> Pressure:
        """
        Returns:
            ICAO standard pressure for altitude
        """
        return Pressure.InHg(0.02953
                             * math.pow(3.73145 - 2.56555e-05 * (altitude >> Distance.Foot),
                                        cPressureExponent)
                             )
        # # Metric formula
        # Pressure.hPa(cStandardPressureMetric
        #     * math.pow(1 - cLapseRateMetric * (altitude >> Distance.Meter) / (cStandardTemperatureC + cDegreesCtoK),
        #                cPressureExponent))

    @staticmethod
    def standard(altitude: Union[float, Distance] = 0, temperature: Optional[Temperature] = None) -> 'Atmo':
        """
        Args:
            altitude: relative to sea level
            temperature: Temperature instance
        Returns:
            Atmo instance. Creates standard ICAO atmosphere at given altitude.
            If temperature not specified uses standard temperature.
        """
        return Atmo.icao(altitude, temperature)

    @staticmethod
    def icao(altitude: Union[float, Distance] = 0, temperature: Optional[Temperature] = None) -> 'Atmo':
        """
        Args:
            altitude: relative to sea level
            temperature: Temperature instance
        Returns:
            Atmo instance. Creates standard ICAO atmosphere at given altitude.
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
        """
        Args:
            fahrenheit: Fahrenheit temperature
        Returns:
            Mach 1 in fps for Fahrenheit temperature
        """
        if fahrenheit < -cDegreesFtoR:
            fahrenheit = -cDegreesFtoR
            warnings.warn(f"Invalid temperature: {fahrenheit}°F. Adjusted to absolute zero "
                          f"It must be >= {-cDegreesFtoR} to avoid a domain error."
                          f"redefine 'cDegreesFtoR' constant to increase it", RuntimeWarning)
        return math.sqrt(fahrenheit + cDegreesFtoR) * cSpeedOfSoundImperial

    @staticmethod
    def machC(celsius: float) -> float:
        """
        Args:
            celsius: Celsius temperature
        Returns:
            Mach 1 in m/s for Celsius temperature
        """
        if celsius < -cDegreesCtoK:
            celsius = -cDegreesCtoK
            warnings.warn(f"Invalid temperature: {celsius}°C. Adjusted to absolute zero "
                          f"It must be >= {-cDegreesCtoK} to avoid a domain error."
                          f"redefine 'cDegreesCtoK' constant to increase it", RuntimeWarning)
        return math.sqrt(1 + celsius / cDegreesCtoK) * cSpeedOfSoundMetric

    @staticmethod
    def air_density(t: Temperature, p: Pressure, humidity: float) -> float:
        """
        Wiki: [Density_of_air](https://en.wikipedia.org/wiki/Density_of_air#Humid_air)

        Args:
            t: Temperature instance
            p: Pressure instance
            humidity: Humidity instance

        Returns:
            Density in Imperial units (lb/ft^3)
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
        """
        Returns:
            density in kg/m^3
        """
        return self.density_ratio * cStandardDensityMetric

    @property
    def density_imperial(self) -> float:
        """
        Returns:
             density in lb/ft^3
        """
        return self.density_ratio * cStandardDensity

    def temperature_at_altitude(self, altitude: float) -> float:
        """
        Interpolated temperature at altitude
        Args:
             altitude: ASL in ft
        Returns:
            temperature in °F
        """
        t = (altitude - self._a0) * cLapseRateImperial + self._t0
        if t < cLowestTempF:
            t = cLowestTempF
            warnings.warn(f"Reached minimum temperature limit. Adjusted to {cLowestTempF}°F "
                          "redefine 'cLowestTempF' constant to increase it ", RuntimeWarning)
        return t

    def calculate_density(self, t: float, p: float) -> float:
        """
        Args:
            t: temperature in °F
            p: pressure in inHg
        Returns:
            density with specified atmosphere
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

    def get_density_factor_and_mach_for_altitude(self, altitude: float) -> Tuple[float, float]:
        """
        Args:
            altitude: ASL in units of feet
        Returns:
            density ratio and Mach 1 (fps) for the specified altitude
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
class Wind:
    """
    A base class for creating Wind.
    Wind direction and velocity by down-range distance.

    Attributes:
        velocity: speed of wind
        direction_from: 0 is blowing from behind shooter.
            90 degrees is blowing from shooter's left towards right.
        until_distance: until which distance the specified wind blows
        MAX_DISTANCE_FEET: Optional custom max wind distance
    """

    velocity: Velocity
    direction_from: Angular
    until_distance: Distance
    MAX_DISTANCE_FEET: float = cMaxWindDistanceFeet

    def __init__(self,
                 velocity: Optional[Union[float, Velocity]] = None,
                 direction_from: Optional[Union[float, Angular]] = None,
                 until_distance: Optional[Union[float, Distance]] = None,
                 *,
                 max_distance_feet: Optional[float] = cMaxWindDistanceFeet):
        """
        Create a new wind instance with given parameters

        Args:
            velocity: speed of wind
            direction_from: 0 is blowing from behind shooter.
                90 degrees is blowing from shooter's left towards right.
            until_distance: until which distance the specified wind blows
            MAX_DISTANCE_FEET: Optional custom max wind distance

        Example:
            This is how you can create a wind
            ```python
            from py_ballisticcalc import Wind
            wind = Wind(
                velocity=Unit.FPS(2700),
                direction_from=Unit.Degree(20)
            )
            ```
        """

        self.MAX_DISTANCE_FEET = float(max_distance_feet or cMaxWindDistanceFeet)
        self.velocity = PreferredUnits.velocity(velocity or 0)
        self.direction_from = PreferredUnits.angular(direction_from or 0)
        self.until_distance = PreferredUnits.distance(until_distance or Distance.Foot(self.MAX_DISTANCE_FEET))

    @property
    def vector(self) -> Vector:
        """
        Returns:
            vector representation of the Wind instance
        """
        wind_velocity_fps = self.velocity >> Velocity.FPS
        wind_direction_rad = self.direction_from >> Angular.Radian
        # Downrange (x-axis) wind velocity component:
        range_component = wind_velocity_fps * math.cos(wind_direction_rad)
        # Cross (z-axis) wind velocity component:
        cross_component = wind_velocity_fps * math.sin(wind_direction_rad)
        return Vector(range_component, 0, cross_component)


@dataclass
class Shot:
    """
    A base class for creating Shot.
    Stores shot parameters for the trajectory calculation.

    Attributes:
        look_angle: Angle of sight line relative to horizontal.
            If the look_angle != 0 then any target in sight crosshairs will be at a different altitude:
                With target_distance = sight distance to a target (i.e., as through a rangefinder):
                    * Horizontal distance X to target = cos(look_angle) * target_distance
                    * Vertical distance Y to target = sin(look_angle) * target_distance
        relative_angle: Elevation adjustment added to weapon.zero_elevation for a particular shot.
        cant_angle: Tilt of gun from vertical, which shifts any barrel elevation
            from the vertical plane into the horizontal plane by sine(cant_angle)
        weapon: Weapon instance uses for making shot
        ammo: Ammo instance uses for making shot
        atmo: Atmo instance uses for making shot
    """

    look_angle: Angular
    relative_angle: Angular
    cant_angle: Angular

    weapon: Weapon
    ammo: Ammo
    atmo: Atmo
    _winds: List[Wind]  # use property Shot.winds to get sorted winds

    # pylint: disable=too-many-positional-arguments
    def __init__(self,
                 weapon: Weapon,
                 ammo: Ammo,
                 look_angle: Optional[Union[float, Angular]] = None,
                 relative_angle: Optional[Union[float, Angular]] = None,
                 cant_angle: Optional[Union[float, Angular]] = None,

                 atmo: Optional[Atmo] = None,
                 winds: Optional[List[Wind]] = None
                 ):
        """
        A base class for creating Shot.
        Stores shot parameters for the trajectory calculation.

        Args:
            look_angle: Angle of sight line relative to horizontal.
                If the look_angle != 0 then any target in sight crosshairs will be at a different altitude:
                    With target_distance = sight distance to a target (i.e., as through a rangefinder):
                        * Horizontal distance X to target = cos(look_angle) * target_distance
                        * Vertical distance Y to target = sin(look_angle) * target_distance
            relative_angle: Elevation adjustment added to weapon.zero_elevation for a particular shot.
            cant_angle: Tilt of gun from vertical, which shifts any barrel elevation
                from the vertical plane into the horizontal plane by sine(cant_angle)
            weapon: Weapon instance used for making shot
            ammo: Ammo instance used for making shot
            atmo: Atmo instance used for making shot
            winds: list of winds used for making shot

        Example:
            This is how you can create a shot
            ```python
            from py_ballisticcalc import Weapon, Ammo, Atmo, Wind
            shot = Shot(
                weapon=Weapon(...),
                ammo=Ammo(...),
                look_angle=Unit.Degree(5),
                relative_angle=Unit.Degree(0),
                cant_angle=Unit.Degree(0),
                atmo=Atmo(...),
                winds=[Wind(...), ... ]
            )
            ```
        """
        self.look_angle = PreferredUnits.angular(look_angle or 0)
        self.relative_angle = PreferredUnits.angular(relative_angle or 0)
        self.cant_angle = PreferredUnits.angular(cant_angle or 0)
        self.weapon = weapon
        self.ammo = ammo
        self.atmo = atmo or Atmo.icao()
        self._winds = winds or [Wind()]

    @property
    def winds(self) -> Tuple[Wind, ...]:
        """
        Property that returns winds sorted by until distance

        Returns:
            Tuple[Wind, ...] sorted by until distance
        """
        # guarantee that winds returns sorted by Wind.until distance
        return tuple(sorted(self._winds, key=lambda wind: wind.until_distance.raw_value))

    @winds.setter
    def winds(self, winds: Optional[List[Wind]]):
        """
        Property that allows set list of winds for the shot

        Args:
            winds: list of the winds for the shot
        """
        self._winds = winds or [Wind()]

    @property
    def barrel_elevation(self) -> Angular:
        """
        Barrel elevation in vertical plane from horizontal

        Returns:
            Angle of barrel elevation in vertical plane from horizontal
        """
        return Angular.Radian((self.look_angle >> Angular.Radian)
                              + math.cos(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                                 + (self.relative_angle >> Angular.Radian)))

    @property
    def barrel_azimuth(self) -> Angular:
        """
        Horizontal angle of barrel relative to sight line

        Returns:
            Horizontal angle of barrel relative to sight line
        """
        return Angular.Radian(math.sin(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                                 + (self.relative_angle >> Angular.Radian)))
