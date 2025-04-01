"""Classes to define zeroing or current environmental conditions"""

import math
import warnings
from dataclasses import dataclass

from typing_extensions import List, Union, Optional, Tuple

from py_ballisticcalc.munition import Weapon, Ammo
from py_ballisticcalc.vector import Vector
from py_ballisticcalc.unit import Distance, Velocity, Temperature, Pressure, Angular, PreferredUnits
from py_ballisticcalc.constants import *  # pylint: disable=wildcard-import,unused-wildcard-import

__all__ = ('Atmo', 'Vacuum', 'Wind', 'Shot')


class Atmo:  # pylint: disable=too-many-instance-attributes
    """
    Atmospheric conditions and density calculations

    Properties:
        altitude: Altitude relative to sea level
        pressure: Unadjusted barometric pressure, a.k.a. station pressure
        temperature: Temperature
        humidity: Relative humidity [0% to 100%]
        powder_temp: Temperature of powder (if different from atmosphere).
            (Used when Ammo.use_powder_sensitivity is True)
        density_ratio: Ratio of current density to standard atmospheric density
        mach: Velocity of sound (Mach 1) for current atmosphere
    """

    @property
    def altitude(self) -> Distance:
        """Altitude relative to sea level"""
        return self._altitude
    @property
    def pressure(self) -> Pressure:
        """Unadjusted barometric pressure, a.k.a. station pressure"""
        return self._pressure
    @property
    def temperature(self) -> Temperature:
        """Local air temperature"""
        return self._temperature
    @property
    def powder_temp(self) -> Temperature:
        """Powder temperature"""
        return self._powder_temp
    @property
    def mach(self) -> Velocity:
        """Velocity of sound (Mach 1) for current atmosphere"""
        return Velocity.FPS(self._mach)
    @property
    def density_ratio(self) -> float:
        """Ratio of current density to standard atmospheric density"""
        return self._density_ratio

    _humidity: float  # Relative humidity [0% to 100%]
    _mach: float      # Velocity of sound (Mach 1) for current atmosphere in fps
    _a0: float        # Zero Altitude in feet
    _t0: float        # Zero Temperature in Celsius
    _p0: float        # Zero Pressure in hPa
    cLowestTempC: float = Temperature.Fahrenheit(cLowestTempF) >> Temperature.Celsius  # Lowest modelled temperature in Celsius

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
            humidity: Atmospheric relative humidity [0% to 100%]
            powder_t: Custom temperature of powder different to atmospheric.
                Used when Ammo.use_powder_sensitivity is True

        Example:
            This is how you can create an Atmo
            ```python
            from py_ballisticcalc import Atmo
            atmo = Atmo(
                altitude=Unit.Meter(100),
                pressure=Unit.hPa(1000),
                temperature=Unit.Celsius(20),
                humidity=50,
                powder_t=Unit.Celsius(15)
            )
            ```
        """
        self._initializing = True
        self._altitude = PreferredUnits.distance(altitude or 0)
        self._pressure = PreferredUnits.pressure(pressure or Atmo.standard_pressure(self.altitude))
        self._temperature = PreferredUnits.temperature(temperature or Atmo.standard_temperature(self.altitude))
        # If powder_temperature not provided we use atmospheric temperature:
        self._powder_temp = PreferredUnits.temperature(powder_t or self.temperature)
        self._t0 = self.temperature >> Temperature.Celsius
        self._p0 = self.pressure >> Pressure.hPa
        self._a0 = self.altitude >> Distance.Foot
        self._mach = Atmo.machF(self._temperature >> Temperature.Fahrenheit)
        self.humidity = humidity
        self._initializing = False
        self.update_density_ratio()

    @property
    def humidity(self) -> float:
        """
        Returns:
            Relative humidity [0% to 100%]
        """
        return self._humidity

    @humidity.setter
    def humidity(self, value: float) -> None:
        if value < 0 or value > 100:
            raise ValueError("Humidity must be between 0% and 100%.")
        if value > 1:
            value = value / 100.0  # Convert to percentage terms
        self._humidity = value
        if not self._initializing:
            self.update_density_ratio()

    def update_density_ratio(self) -> None:
        """
        Updates the density ratio based on current conditions
        """
        self._density_ratio = Atmo.calculate_air_density(self._t0, self._p0, self.humidity) / cStandardDensityMetric

    @property
    def density_metric(self) -> float:
        """
        Returns:
            density in kg/m^3
        """
        return self._density_ratio * cStandardDensityMetric

    @property
    def density_imperial(self) -> float:
        """
        Returns:
             density in lb/ft^3
        """
        return self._density_ratio * cStandardDensity

    def temperature_at_altitude(self, altitude: float) -> float:
        """
        Temperature at altitude interpolated from zero conditions using lapse rate.
        Args:
            altitude: ASL in ft
        Returns:
            temperature in °C
        """
        t = (altitude - self._a0) * cLapseRateKperFoot + self._t0
        if t < Atmo.cLowestTempC:
            t = Atmo.cLowestTempC
            warnings.warn(f"Temperature interpolated from altitude fell below minimum temperature limit.  "
                          f"Model not accurate here.  Temperature bounded at cLowestTempF: {cLowestTempF}°F."
                          , RuntimeWarning)
        return t

    def pressure_at_altitude(self, altitude: float) -> float:
        """
        Pressure at altitude interpolated from zero conditions using lapse rate.
        Ref: https://en.wikipedia.org/wiki/Barometric_formula#Pressure_equations
        Args:
            altitude: ASL in ft
        Returns:
            pressure in hPa
        """
        p = self._p0 * math.pow(1 + cLapseRateKperFoot * (altitude - self._a0) / (self._t0 + cDegreesCtoK),
                                cPressureExponent)
        return p

    def get_density_factor_and_mach_for_altitude(self, altitude: float) -> Tuple[float, float]:
        """
        Ref: https://en.wikipedia.org/wiki/Barometric_formula#Density_equations
        Args:
            altitude: ASL in units of feet.
                Note: Altitude above 36,000 ft not modelled this way.
        Returns:
            density ratio and Mach 1 (fps) for the specified altitude
        """
        # Within 30 ft of initial altitude use initial values to save compute
        if math.fabs(self._a0 - altitude) < 30:
            mach = self._mach
            density_ratio = self._density_ratio
        else:
            if altitude > 36089:
                warnings.warn("Density request for altitude above troposphere."
                               " Atmospheric model not valid here.", RuntimeWarning)
            t = self.temperature_at_altitude(altitude) + cDegreesCtoK
            mach = Velocity.MPS(Atmo.machK(t)) >> Velocity.FPS
            p = self.pressure_at_altitude(altitude)
            density_delta = ((self._t0 + cDegreesCtoK) * p) / (self._p0 * t)
            density_ratio = self._density_ratio * density_delta
            # # Alternative simplified model:
            # # Ref https://en.wikipedia.org/wiki/Density_of_air#Exponential_approximation
            # # see doc/'Air Density Models.svg' for comparison
            #density_ratio = self._density_ratio * math.exp(-(altitude - self._a0) / 34122)
        return density_ratio, mach

    def __str__(self):
        return (
            f"Atmo(altitude={self.altitude}, pressure={self.pressure}, "
            f"temperature={self.temperature}, humidity={self.humidity}, "
            f"density_ratio={self.density_ratio}, mach={self.mach})"
        )

    @staticmethod
    def standard_temperature(altitude: Distance) -> Temperature:
        """
        Note: This model only valid up to troposphere (~36,000 ft).
        Args:
            altitude: ASL in units of feet.
        Returns:
            ICAO standard temperature for altitude
        """
        return Temperature.Fahrenheit(cStandardTemperatureF
                                      + (altitude >> Distance.Foot) * cLapseRateImperial)

    @staticmethod
    def standard_pressure(altitude: Distance) -> Pressure:
        """
        Note: This model only valid up to troposphere (~36,000 ft).
            Ref: https://en.wikipedia.org/wiki/Barometric_formula#Pressure_equations
        Args:
            altitude: Distance above sea level (ASL)
        Returns:
            ICAO standard pressure for altitude
        """
        return Pressure.hPa(cStandardPressureMetric
            * math.pow(1 + cLapseRateMetric * (altitude >> Distance.Meter) / (cStandardTemperatureC + cDegreesCtoK),
                       cPressureExponent))

    @staticmethod
    def icao(altitude: Union[float, Distance] = 0, temperature: Optional[Temperature] = None, humidity: float = cStandardHumidity) -> 'Atmo':
        """
        Note: This model only valid up to troposphere (~36,000 ft).
        Args:
            altitude: relative to sea level
            temperature: air temperature
        Returns:
            Atmo instance of standard ICAO atmosphere at given altitude.
            If temperature not specified uses standard temperature.
        """
        altitude = PreferredUnits.distance(altitude)
        if temperature is None:
            temperature = Atmo.standard_temperature(altitude)
        pressure = Atmo.standard_pressure(altitude)

        return Atmo(altitude, pressure, temperature, humidity)
    # Synonym for ICAO standard atmosphere
    standard = icao

    @staticmethod
    def machF(fahrenheit: float) -> float:
        """
        Args:
            fahrenheit: Fahrenheit temperature
        Returns:
            Mach 1 in fps for given temperature
        """
        if fahrenheit < -cDegreesFtoR:
            fahrenheit = cLowestTempF
            warnings.warn(f"Invalid temperature: {fahrenheit}°F. Adjusted to ({cLowestTempF}°F)."
                          , RuntimeWarning)
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
            bad_temp = celsius
            celsius = Atmo.cLowestTempC
            warnings.warn(f"Invalid temperature: {bad_temp}°C. Adjusted to ({celsius}°C)."
                          , RuntimeWarning)
        return Atmo.machK(celsius + cDegreesCtoK)

    @staticmethod
    def machK(kelvin: float) -> float:
        """
        Args:
            kelvin: Kelvin temperature
        Returns:
            Mach 1 in m/s for Kelvin temperature
        """
        return math.sqrt(kelvin) * cSpeedOfSoundMetric

    @staticmethod
    def calculate_air_density(t: float, p: float, humidity: float) -> float:
        """
        Calculate the air density given temperature, pressure, and humidity.

        Parameters:
        t (float): Temperature in degrees Celsius.
        p (float): Pressure in hPa.
        humidity (float): The relative humidity as a fraction of max [0%-100%]

        Returns:
            float: Air density in kg/m^3.

        Notes:
        - Divide result by cDensityImperialToMetric to get density in lb/ft^3
        - Source: https://www.nist.gov/system/files/documents/calibrations/CIPM-2007.pdf
        """
        R = 8.314472  # J/(mol·K), universal gas constant
        M_a = 28.96546e-3  # kg/mol, molar mass of dry air
        M_v = 18.01528e-3  # kg/mol, molar mass of water vapor

        def saturation_vapor_pressure(T):
            # Calculation of saturated vapor pressure according to CIPM 2007
            A = [1.2378847e-5, -1.9121316e-2, 33.93711047, -6.3431645e3]
            return math.exp(A[0] * T ** 2 + A[1] * T + A[2] + A[3] / T)

        def enhancement_factor(p, T):
            # Calculation of enhancement factor according to CIPM 2007
            alpha = 1.00062
            beta = 3.14e-8
            gamma = 5.6e-7
            return alpha + beta * p + gamma * T ** 2

        def compressibility_factor(p, T, x_v):
            # Calculation of compressibility factor according to CIPM 2007
            a0 = 1.58123e-6
            a1 = -2.9331e-8
            a2 = 1.1043e-10
            b0 = 5.707e-6
            b1 = -2.051e-8
            c0 = 1.9898e-4
            c1 = -2.376e-6
            d = 1.83e-11
            e = -0.765e-8

            t = T - cDegreesCtoK
            Z = 1 - (p / T) * (a0 + a1 * t + a2 * t ** 2 + (b0 + b1 * t) * x_v + (c0 + c1 * t) * x_v ** 2) \
                + (p / T) ** 2 * (d + e * x_v ** 2)
            return Z

        # Temperature in Kelvin
        T_K = t + cDegreesCtoK

        # Calculation of saturated vapor pressure and enhancement factor
        p_sv = saturation_vapor_pressure(T_K)
        f = enhancement_factor(p, t)

        # Calculation of partial pressure and mole fraction of water vapor
        p_v = humidity / 100 * f * p_sv
        x_v = p_v / p

        # Calculation of compressibility factor
        Z = compressibility_factor(p, T_K, x_v)

        density = (p * M_a) / (Z * R * T_K) * (1 - x_v * (1 - M_v / M_a))
        return 100 * density


class Vacuum(Atmo):
    """Vacuum atmosphere has zero drag"""
    def __init__(self, 
                 altitude: Optional[Union[float, Distance]] = None,
                 temperature: Optional[Union[float, Temperature]] = None):
        super().__init__(altitude, 0, temperature, 0)
        self.cLowestTempC = cDegreesCtoK
        self._pressure = PreferredUnits.pressure(0)
        self._density_ratio = 0

    def update_density_ratio(self):
        pass


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
            max_distance_feet: Optional custom max wind distance

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
