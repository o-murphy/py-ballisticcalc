"""Environmental and firing condition primitives used by ballistic engines.

What this module provides
- Atmo: Atmosphere model (actual or ICAO) with density ratio and Mach (speed of sound)
    calculations. Inputs are units-aware and can be provided as raw numbers or Unit-wrapped
    values; conversions are handled via PreferredUnits. Supports humidity and altitude
    lapse-rate formulas and exposes helpers for standard temperature/pressure.
- Vacuum: An Atmo subclass that models a vacuum (zero pressure/density) for dragless
    trajectories and benchmarks.
- Wind: Piecewise-constant wind segments described by speed, direction-from, and
    distance limit, with a 3D vector representation used by integrators.
- Shot: A container aggregating ammo, weapon, angles (look/relative/cant), atmosphere,
    and winds; computes derived barrel_elevation and barrel_azimuth used by engines.
- ShotProps: A dataclass translating a Shot into engine-ready scalars in internal units
    (feet/seconds/grains), including precomputed drag curves and trigonometric terms
    for efficient numeric integration.

Design notes
- Units: All public constructors accept either raw numbers or Unit instances; inputs
    are coerced to PreferredUnits to keep APIs ergonomic and strict. Use the Unit helpers
    (e.g., Unit.Foot, Unit.hPa, Unit.Celsius, Unit.FPS) for clarity in examples.
- Atmosphere: Use Atmo.icao(...) for standard atmosphere at an altitude; humidity is relative
    (0-100%). Changing temperature/pressure/humidity updates density_ratio and Mach.
- Wind.direction_from: 0° is from behind the shooter; 90° is from the shooter's left.
- Shot vs ShotProps: End users typically work with Shot objects; engines construct ShotProps
    internally to avoid per-step unit conversions and repeated lookups. HitResult objects
    include the ShotProps instance used to calculate a trajectory.

Examples:
>>> # Standard atmosphere at sea level:
>>> atmo = Atmo.icao()
>>> # Crosswind from left to right at 10 fps, in effect over the entire trajectory:
>>> from py_ballisticcalc import Unit
>>> breeze = Wind(velocity=Unit.FPS(10), direction_from=Unit.Degree(90))

See also
- Engines consuming these types: py_ballisticcalc.engines.*
- Units and conversions: py_ballisticcalc.unit
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

from typing_extensions import List, NamedTuple, Optional, Sequence, Tuple, Union

from py_ballisticcalc.constants import (cStandardDensity, cLapseRateKperFoot, cLowestTempF, cStandardDensityMetric,
    cDegreesCtoK, cPressureExponent, cStandardTemperatureF, cLapseRateImperial, cStandardPressureMetric,
    cLapseRateMetric, cStandardTemperatureC, cStandardHumidity, cSpeedOfSoundImperial, cDegreesFtoR,
    cSpeedOfSoundMetric, cMaxWindDistanceFeet)
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.munition import Weapon, Ammo
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits, Pressure, Temperature, Velocity, Weight
from py_ballisticcalc.vector import Vector

__all__ = ('Atmo', 'Vacuum', 'Wind', 'Shot', 'ShotProps')


class Atmo:  # pylint: disable=too-many-instance-attributes
    """
    Atmospheric conditions and density calculations.

    Attributes:
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
        """Altitude relative to sea level."""
        return self._altitude

    @property
    def pressure(self) -> Pressure:
        """Unadjusted barometric pressure, a.k.a. station pressure."""
        return self._pressure

    @property
    def temperature(self) -> Temperature:
        """Local air temperature."""
        return self._temperature

    @property
    def powder_temp(self) -> Temperature:
        """Powder temperature."""
        return self._powder_temp

    @property
    def mach(self) -> Velocity:
        """Velocity of sound (Mach 1) for current atmosphere."""
        return Velocity.FPS(self._mach)

    @property
    def density_ratio(self) -> float:
        """Ratio of current density to standard atmospheric density."""
        return self._density_ratio

    _humidity: float  # Relative humidity [0% to 100%]
    _mach: float  # Velocity of sound (Mach 1) for current atmosphere in fps
    _a0: float  # Zero Altitude in feet
    _t0: float  # Zero Temperature in Celsius
    _p0: float  # Zero Pressure in hPa
    cLowestTempC: float = Temperature.Fahrenheit(
        cLowestTempF) >> Temperature.Celsius  # Lowest modelled temperature in Celsius

    def __init__(self,
                 altitude: Optional[Union[float, Distance]] = None,
                 pressure: Optional[Union[float, Pressure]] = None,
                 temperature: Optional[Union[float, Temperature]] = None,
                 humidity: float = 0.0,
                 powder_t: Optional[Union[float, Temperature]] = None):
        """
        Create a new Atmo instance.

        Args:
            altitude: Altitude relative to sea level
            pressure: Atmospheric pressure
            temperature: Atmospheric temperature
            humidity: Atmospheric relative humidity [0% to 100%]
            powder_t: Custom temperature of powder different to atmospheric.
                Used when Ammo.use_powder_sensitivity is True

        Example:
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
        """Relative humidity [0% to 100%]."""
        return self._humidity

    @humidity.setter
    def humidity(self, value: float) -> None:
        if value < 0 or value > 100:
            raise ValueError(r"Humidity must be between 0% and 100%.")
        if value > 1:
            value = value / 100.0  # Convert to percentage terms
        self._humidity = value
        if not self._initializing:
            self.update_density_ratio()

    def update_density_ratio(self) -> None:
        """Update the density ratio based on current conditions."""
        self._density_ratio = Atmo.calculate_air_density(self._t0, self._p0, self.humidity) / cStandardDensityMetric

    @property
    def density_metric(self) -> float:
        """Air density in metric units (kg/m^3)."""
        return self._density_ratio * cStandardDensityMetric

    @property
    def density_imperial(self) -> float:
        """Air density in imperial units (lb/ft^3)."""
        return self._density_ratio * cStandardDensity

    def temperature_at_altitude(self, altitude: float) -> float:
        """Temperature at altitude interpolated from zero conditions using lapse rate.
        
        Args:
            altitude: ASL in ft
            
        Returns:
            temperature in °C
        """
        t = (altitude - self._a0) * cLapseRateKperFoot + self._t0
        if t < Atmo.cLowestTempC:
            t = Atmo.cLowestTempC
            warnings.warn(f"Temperature interpolated from altitude fell below minimum temperature limit.  "
                          f"Model not accurate here.  Temperature bounded at cLowestTempF: {cLowestTempF}°F.",
                          RuntimeWarning)
        return t

    def pressure_at_altitude(self, altitude: float) -> float:
        """Pressure at altitude interpolated from zero conditions using lapse rate.
        
        Ref: https://en.wikipedia.org/wiki/Barometric_formula#Pressure_equations
        
        Args:
            altitude: ASL in ft
            
        Returns:
            pressure in hPa
        """
        p = self._p0 * math.pow(1 + cLapseRateKperFoot * (altitude - self._a0) / (self._t0 + cDegreesCtoK),
                                cPressureExponent)
        return p

    def get_density_and_mach_for_altitude(self, altitude: float) -> Tuple[float, float]:
        """Calculate density ratio and Mach 1 for the specified altitude.
        
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
            # density_ratio = self._density_ratio * math.exp(-(altitude - self._a0) / 34122)
        return density_ratio, mach

    def __str__(self) -> str:
        return (
            f"Atmo(altitude={self.altitude}, pressure={self.pressure}, "
            f"temperature={self.temperature}, humidity={self.humidity}, "
            f"density_ratio={self.density_ratio}, mach={self.mach})"
        )

    @staticmethod
    def standard_temperature(altitude: Distance) -> Temperature:
        """Calculate ICAO standard temperature for altitude.
        
        Note: This model is only valid up to the troposphere (~36,000 ft).
        
        Args:
            altitude: ASL in units of feet.
            
        Returns:
            ICAO standard temperature for altitude
        """
        return Temperature.Fahrenheit(cStandardTemperatureF
                                      + (altitude >> Distance.Foot) * cLapseRateImperial)

    @staticmethod
    def standard_pressure(altitude: Distance) -> Pressure:
        """Calculate ICAO standard pressure for altitude.
        
        Note: This model only valid up to troposphere (~36,000 ft).
        Ref: https://en.wikipedia.org/wiki/Barometric_formula#Pressure_equations
        
        Args:
            altitude: Distance above sea level (ASL)
            
        Returns:
            ICAO standard pressure for altitude
        """
        return Pressure.hPa(cStandardPressureMetric
                            * math.pow(1 + cLapseRateMetric * (altitude >> Distance.Meter) /
                                           (cStandardTemperatureC + cDegreesCtoK),
                                       cPressureExponent))

    @staticmethod
    def icao(altitude: Union[float, Distance] = 0, temperature: Optional[Temperature] = None,
             humidity: float = cStandardHumidity) -> Atmo:
        """Create Atmo instance of standard ICAO atmosphere at given altitude.
        
        Note: This model is only valid up to the troposphere (~36,000 ft).
        
        Args:
            altitude: relative to sea level.  Default is sea level (0 ft).
            temperature: air temperature.  Default is standard temperature at altitude.
            
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
        """Calculate Mach 1 in fps for given Fahrenheit temperature.
        
        Args:
            fahrenheit: Fahrenheit temperature
            
        Returns:
            Mach 1 in fps for given temperature
        """
        if fahrenheit < -cDegreesFtoR:
            bad_temp = fahrenheit
            fahrenheit = cLowestTempF
            warnings.warn(f"Invalid temperature: {bad_temp}°F. Adjusted to ({cLowestTempF}°F).", RuntimeWarning)
        return math.sqrt(fahrenheit + cDegreesFtoR) * cSpeedOfSoundImperial

    @staticmethod
    def machC(celsius: float) -> float:
        """Calculate Mach 1 in mps for given Celsius temperature.
        
        Args:
            celsius: Celsius temperature
            
        Returns:
            Mach 1 in mps for given temperature
        """
        if celsius < -cDegreesCtoK:
            bad_temp = celsius
            celsius = Atmo.cLowestTempC
            warnings.warn(f"Invalid temperature: {bad_temp}°C. Adjusted to ({celsius}°C).", RuntimeWarning)
        return Atmo.machK(celsius + cDegreesCtoK)

    @staticmethod
    def machK(kelvin: float) -> float:
        """Calculate Mach 1 in mps for given Kelvin temperature.
        
        Args:
            kelvin: Kelvin temperature
            
        Returns:
            Mach 1 in mps for given temperature
        """
        return math.sqrt(kelvin) * cSpeedOfSoundMetric

    @staticmethod
    def calculate_air_density(t: float, p_hpa: float, humidity: float) -> float:
        """Calculate air density from temperature, pressure, and humidity.
        
        Args:
            t: Temperature in degrees Celsius.
            p_hpa: Pressure in hPa (hectopascals). Internally converted to Pa.
            humidity: Relative humidity. Accepts either fraction [0..1] or percent [0..100].

        Returns:
            Air density in kg/m³.

        Notes:
            - Divide result by cDensityImperialToMetric to get density in lb/ft³
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

        # Normalize humidity to fraction [0..1]
        rh = float(humidity)
        rh_frac = rh / 100.0 if rh > 1.0 else rh
        rh_frac = max(0.0, min(1.0, rh_frac))

        # Convert inputs for CIPM equations
        T_K = t + cDegreesCtoK           # Kelvin
        p = float(p_hpa) * 100.0         # hPa -> Pa

        # Calculation of saturated vapor pressure and enhancement factor
        p_sv = saturation_vapor_pressure(T_K)  # Pa (saturated vapor pressure)
        f = enhancement_factor(p, t)           # Enhancement factor (p in Pa, t in °C)

        # Partial pressure of water vapor and mole fraction
        p_v = rh_frac * f * p_sv               # Pa
        x_v = p_v / p                          # Mole fraction of water vapor

        # Calculation of compressibility factor
        Z = compressibility_factor(p, T_K, x_v)

        # Density (kg/m^3) using moist air composition and compressibility factor
        density = (p * M_a) / (Z * R * T_K) * (1.0 - x_v * (1.0 - M_v / M_a))
        return density


class Vacuum(Atmo):
    """Vacuum atmosphere (zero drag)."""

    cLowestTempC: float = cDegreesCtoK

    def __init__(self,
                 altitude: Optional[Union[float, Distance]] = None,
                 temperature: Optional[Union[float, Temperature]] = None):
        super().__init__(altitude, 0, temperature, 0)
        self._pressure = PreferredUnits.pressure(0)
        self._density_ratio = 0

    def update_density_ratio(self) -> None:
        pass


@dataclass
class Wind:
    """
    Describe wind in effect over a particular down-range distance.

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
        Create a new wind instance with given parameters.

        Args:
            velocity: speed of wind
            direction_from: 0 is blowing from behind shooter.
                90 degrees is blowing from shooter's left towards right.
            until_distance: until which distance the specified wind blows
            max_distance_feet: Optional custom max wind distance

        Example:
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
        """Vector representation of the Wind instance."""
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
    All information needed to compute a ballistic trajectory.

    Attributes:
        look_angle: Angle of sight line relative to horizontal.
            If the look_angle != 0 then any target in sight crosshairs will be at a different altitude:
                With target_distance = sight distance to a target (i.e., as through a rangefinder):
                    * Horizontal distance X to target = cos(look_angle) * target_distance
                    * Vertical distance Y to target = sin(look_angle) * target_distance
        relative_angle: Elevation adjustment added to weapon.zero_elevation for a particular shot.
        cant_angle: Tilt of gun from vertical, which shifts any barrel elevation
            from the vertical plane into the horizontal plane by sine(cant_angle)
        ammo: Ammo instance used for making shot
        weapon: Weapon instance used for making shot
        atmo: Atmo instance used for making shot
    """

    look_angle: Angular
    relative_angle: Angular
    cant_angle: Angular

    ammo: Ammo
    weapon: Weapon
    atmo: Atmo
    _winds: List[Wind]  # Stored sorted by .until_distance

    # pylint: disable=too-many-positional-arguments
    def __init__(self,
                 ammo: Ammo,
                 weapon: Optional[Weapon] = None,
                 look_angle: Optional[Union[float, Angular]] = None,
                 relative_angle: Optional[Union[float, Angular]] = None,
                 cant_angle: Optional[Union[float, Angular]] = None,
                 atmo: Optional[Atmo] = None,
                 winds: Optional[Sequence[Wind]] = None
                 ):
        """
        Initialize shot parameters for the trajectory calculation.

        Args:
            ammo: Ammo instance used for making shot
            weapon: Weapon instance used for making shot
            look_angle: Angle of sight line relative to horizontal.
                If the look_angle != 0 then any target in sight crosshairs will be at a different altitude:
                    With target_distance = sight distance to a target (i.e., as through a rangefinder):
                        * Horizontal distance X to target = cos(look_angle) * target_distance
                        * Vertical distance Y to target = sin(look_angle) * target_distance
            relative_angle: Elevation adjustment added to weapon.zero_elevation for a particular shot.
            cant_angle: Tilt of gun from vertical, which shifts any barrel elevation
                from the vertical plane into the horizontal plane by sine(cant_angle)
            atmo: Atmo instance used for making shot
            winds: list of winds used for making shot

        Example:
            ```python
            from py_ballisticcalc import Weapon, Ammo, Atmo, Wind
            shot = Shot(
                ammo=Ammo(...),
                weapon=Weapon(...),
                look_angle=Unit.Degree(5),
                relative_angle=Unit.Degree(0),
                cant_angle=Unit.Degree(0),
                atmo=Atmo(...),
                winds=[Wind(...), ... ]
            )
            ```
        """
        self.ammo = ammo
        self.weapon = weapon or Weapon()
        self.look_angle = PreferredUnits.angular(look_angle or 0)
        self.relative_angle = PreferredUnits.angular(relative_angle or 0)
        self.cant_angle = PreferredUnits.angular(cant_angle or 0)
        self.atmo = atmo or Atmo.icao()
        self.winds = winds or [Wind()]

    @property
    def winds(self) -> Sequence[Wind]:
        """Sequence[Wind] sorted by until_distance."""
        return tuple(self._winds)

    @winds.setter
    def winds(self, winds: Optional[Sequence[Wind]]):
        """Property setter.  Ensures .winds is sorted by until_distance.

        Args:
            winds: list of the winds for the shot
        """
        self._winds = sorted(winds or [Wind()], key=lambda wind: wind.until_distance.raw_value)

    @property
    def barrel_elevation(self) -> Angular:
        """Total barrel elevation (in vertical plane) from horizontal.

        Returns:
            Angle of barrel elevation in vertical plane from horizontal
                `= look_angle + cos(cant_angle) * zero_elevation + relative_angle`
        """
        return Angular.Radian((self.look_angle >> Angular.Radian)
                              + math.cos(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                                 + (self.relative_angle >> Angular.Radian)))

    @barrel_elevation.setter
    def barrel_elevation(self, value: Angular) -> None:
        """Setter for barrel_elevation.
        
        Sets `.relative_angle` to achieve the desired elevation.
            Note: This does not change the `.weapon.zero_elevation`.

        Args:
            value: Desired barrel elevation in vertical plane from horizontal
        """
        self.relative_angle = Angular.Radian((value >> Angular.Radian) - (self.look_angle >> Angular.Radian) \
                             - math.cos(self.cant_angle >> Angular.Radian) * (self.weapon.zero_elevation >> Angular.Radian))

    @property
    def barrel_azimuth(self) -> Angular:
        """Horizontal angle of barrel relative to sight line."""
        return Angular.Radian(math.sin(self.cant_angle >> Angular.Radian)
                              * ((self.weapon.zero_elevation >> Angular.Radian)
                                 + (self.relative_angle >> Angular.Radian)))

    @property
    def slant_angle(self) -> Angular:
        """Synonym for look_angle."""
        return self.look_angle
    @slant_angle.setter
    def slant_angle(self, value: Angular) -> None:
        self.look_angle = value


class CurvePoint(NamedTuple):
    """Coefficients for quadratic curve fitting.
    
    Attributes:
        a: Quadratic coefficient (x² term) in the equation y = ax² + bx + c.
        b: Linear coefficient (x term) in the equation y = ax² + bx + c.
        c: Constant coefficient (constant term) in the equation y = ax² + bx + c.
    """

    a: float
    b: float
    c: float

@dataclass
class ShotProps:
    """Shot configuration and parameters for ballistic trajectory calculations.
    
    Contains all shot-specific data converted to internal units for high-performance
    ballistic calculations. This class serves as the computational interface between
    user-friendly Shot objects and the numerical integration engines.
    
    The class pre-computes expensive calculations (ballistic coefficient curves,
    atmospheric data, projectile properties) and stores them in optimized formats
    for repeated use during trajectory integration. All values are converted to
    internal units (feet, seconds, grains) for computational efficiency.
        
    Examples:
        ```python
        from py_ballisticcalc import Shot, ShotProps
        
        # Create shot configuration
        shot = Shot(weapon=weapon, ammo=ammo, atmo=atmo)

        # Convert to ShotProps
        shot_props = ShotProps.from_shot(shot)
        
        # Access pre-computed values
        print(f"Stability coefficient: {shot_props.stability_coefficient}")

        # Get drag coefficient at specific Mach number
        drag = shot_props.drag_by_mach(1.5)
        
        # Calculate spin drift at flight time
        time = 1.2  # seconds
        drift = shot_props.spin_drift(time)  # inches
        
        # Get atmospheric conditions at altitude
        altitude = shot_props.alt0_ft + 100  # 100 feet above initial altitude
        density_ratio, mach_fps = shot_props.get_density_and_mach_for_altitude(altitude)
        ```
        
    Computational Optimizations:
        - Drag coefficient curves pre-computed for fast interpolation
        - Trigonometric values (cant_cosine, cant_sine) pre-calculated
        - Atmospheric parameters cached for repeated altitude lookups
        - Miller stability coefficient computed once during initialization
        
    Note:
        This class is designed for internal use by ballistic calculation engines.
        User code should typically work with Shot objects and let the Calculator
        handle the conversion to ShotProps automatically.
        
        The original Shot object is retained for reference, but modifications
        to it after ShotProps creation will not affect the stored calculations.
        Create a new ShotProps instance if Shot parameters change.
    """
    """
    TODO: The Shot member object should either be a copy or immutable so that subsequent changes to its
          properties do not invalidate the calculations and data associated with this ShotProps instance.
    """

    shot: Shot  # Reference to the original Shot object
    bc: float  # Ballistic coefficient
    curve: List[CurvePoint]  # Pre-computed drag curve points
    mach_list: List[float]  # List of Mach numbers for interpolation

    look_angle_rad: float  # Slant angle in radians
    twist_inch: float  # Twist rate of barrel rifling, in inches of length to make one full rotation
    length_inch: float  # Length of the bullet in inches
    diameter_inch: float  # Diameter of the bullet in inches
    weight_grains: float  # Weight of the bullet in grains
    barrel_elevation_rad: float  # Barrel elevation angle in radians
    barrel_azimuth_rad: float  # Barrel azimuth angle in radians
    sight_height_ft: float  # Height of the sight above the bore in feet
    cant_cosine: float  # Cosine of the cant angle
    cant_sine: float  # Sine of the cant angle
    alt0_ft: float  # Initial altitude in feet
    muzzle_velocity_fps: float  # Muzzle velocity in feet per second
    stability_coefficient: float = field(init=False)  # Miller stability coefficient
    calc_step: float = field(init=False)  # Calculation step size
    filter_flags: Union[TrajFlag, int] = field(init=False)  # Flags for special ballistic trajectory points

    def __post_init__(self):
        self.stability_coefficient = self._calc_stability_coefficient()

    @property
    def winds(self) -> Sequence[Wind]:
        return self.shot.winds

    @property
    def look_angle(self) -> Angular:
        return Angular.Radian(self.look_angle_rad)

    @classmethod
    def from_shot(cls, shot: Shot) -> ShotProps:
        """Initialize a ShotProps instance from a Shot instance."""
        return cls(
            shot=shot,
            bc=shot.ammo.dm.BC,
            curve=cls.calculate_curve(shot.ammo.dm.drag_table),
            mach_list=cls._get_only_mach_data(shot.ammo.dm.drag_table),
            look_angle_rad=shot.look_angle >> Angular.Radian,
            twist_inch=shot.weapon.twist >> Distance.Inch,
            length_inch=shot.ammo.dm.length >> Distance.Inch,
            diameter_inch=shot.ammo.dm.diameter >> Distance.Inch,
            weight_grains=shot.ammo.dm.weight >> Weight.Grain,
            barrel_elevation_rad=shot.barrel_elevation >> Angular.Radian,
            barrel_azimuth_rad=shot.barrel_azimuth >> Angular.Radian,
            sight_height_ft=shot.weapon.sight_height >> Distance.Foot,
            cant_cosine=math.cos(shot.cant_angle >> Angular.Radian),
            cant_sine=math.sin(shot.cant_angle >> Angular.Radian),
            alt0_ft=shot.atmo.altitude >> Distance.Foot,
            muzzle_velocity_fps=shot.ammo.get_velocity_for_temp(shot.atmo.powder_temp) >> Velocity.FPS,
        )

    def get_density_and_mach_for_altitude(self, drop: float) -> Tuple[float, float]:
        """Get the air density and Mach number for a given altitude.

        Args:
            drop: The change in feet from the initial altitude.

        Returns:
            A tuple containing the air density (in lb/ft³) and Mach number at the specified altitude.
        """
        return self.shot.atmo.get_density_and_mach_for_altitude(self.alt0_ft + drop)

    def drag_by_mach(self, mach: float) -> float:
        """Calculate a standard drag factor (SDF) for the given Mach number.
        ```
        Formula:
            Drag force = V^2 * AirDensity * C_d * S / 2m
                       = V^2 * density_ratio * SDF
        Where:
            - density_ratio = LocalAirDensity / StandardDensity = rho / rho_0
            - StandardDensity of Air = rho_0 = 0.076474 lb/ft^3
            - S is cross-section = d^2 pi/4, where d is bullet diameter in inches
            - m is bullet mass in pounds
            - bc contains m/d^2 in units lb/in^2, which is multiplied by 144 to convert to lb/ft^2
        Thus:
            - The magic constant found here = StandardDensity * pi / (4 * 2 * 144)
        ```

        Args:
            mach: The Mach number.

        Returns:
            The standard drag factor at the given Mach number.
        """
        # cd = calculate_by_curve(self._table_data, self._curve, mach)
        # use calculation over list[double] instead of list[DragDataPoint]
        cd = self._calculate_by_curve_and_mach_list(self.mach_list, self.curve, mach)
        return cd * 2.08551e-04 / self.bc

    def spin_drift(self, time: float) -> float:
        """Litz spin-drift approximation.

        Args:
            time: Time of flight

        Returns:
            float: Windage due to spin drift, in inches
        """
        if (self.stability_coefficient != 0) and (self.twist_inch != 0):
            sign = 1 if self.twist_inch > 0 else -1
            return sign * (1.25 * (self.stability_coefficient + 1.2)
                           * math.pow(time, 1.83)) / 12
        return 0

    def _calc_stability_coefficient(self) -> float:
        """Calculate the Miller stability coefficient.

        Returns:
            float: The Miller stability coefficient.
        """
        if self.twist_inch and self.length_inch and self.diameter_inch and self.shot.atmo.pressure.raw_value:
            twist_rate = math.fabs(self.twist_inch) / self.diameter_inch
            length = self.length_inch / self.diameter_inch
            # Miller stability formula
            sd = 30 * self.weight_grains / (
                    math.pow(twist_rate, 2) * math.pow(self.diameter_inch, 3) * length * (1 + math.pow(length, 2))
            )
            # Velocity correction factor
            fv = math.pow(self.muzzle_velocity_fps / 2800, 1.0 / 3.0)
            # Atmospheric correction
            ft = self.shot.atmo.temperature >> Temperature.Fahrenheit
            pt = self.shot.atmo.pressure >> Pressure.InHg
            ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
            return sd * fv * ftp
        return 0

    @staticmethod
    def calculate_curve(data_points: List[DragDataPoint]) -> List[CurvePoint]:
        """Piecewise quadratic interpolation of drag curve.

        Args:
            data_points: List[{Mach, CD}] data_points in ascending Mach order

        Returns:
            List[CurvePoints] to interpolate drag coefficient
        """
        rate = (data_points[1].CD - data_points[0].CD) / (data_points[1].Mach - data_points[0].Mach)
        curve = [CurvePoint(0, rate, data_points[0].CD - data_points[0].Mach * rate)]
        len_data_points = int(len(data_points))
        len_data_range = len_data_points - 1

        for i in range(1, len_data_range):
            x1 = data_points[i - 1].Mach
            x2 = data_points[i].Mach
            x3 = data_points[i + 1].Mach
            y1 = data_points[i - 1].CD
            y2 = data_points[i].CD
            y3 = data_points[i + 1].CD
            a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
                (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
            b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
            c = y1 - (a * x1 * x1 + b * x1)
            curve_point = CurvePoint(a, b, c)
            curve.append(curve_point)

        num_points = len_data_points
        rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
            (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
        curve_point = CurvePoint(
            0, rate, data_points[num_points - 1].CD - data_points[num_points - 2].Mach * rate
        )
        curve.append(curve_point)
        return curve

    @staticmethod
    def _get_only_mach_data(data: List[DragDataPoint]) -> List[float]:
        """Extract Mach values from a list of DragDataPoint objects.

        Args:
            data: A list of DragDataPoint objects.

        Returns:
            A list containing only the Mach values from the input data.
        """
        return [dp.Mach for dp in data]

    @staticmethod
    def _calculate_by_curve_and_mach_list(mach_list: List[float], curve: List[CurvePoint], mach: float) -> float:
        """Calculate a value based on a piecewise quadratic curve and a list of Mach values.

        This function performs a binary search on the `mach_list` to find the segment
        of the `curve` relevant to the input `mach` number and then interpolates
        the value using the quadratic coefficients of that curve segment.

        Args:
            mach_list: A sorted list of Mach values corresponding to the `curve` points.
            curve: A list of CurvePoint objects, where each object
                contains quadratic coefficients (a, b, c) for a Mach number segment.
            mach: The Mach number at which to calculate the value.

        Returns:
            The calculated value based on the interpolated curve at the given Mach number.
        """
        num_points = len(curve)
        mlo = 0
        mhi = num_points - 2

        while mhi - mlo > 1:
            mid = (mhi + mlo) // 2
            if mach_list[mid] < mach:
                mlo = mid
            else:
                mhi = mid

        if mach_list[mhi] - mach > mach - mach_list[mlo]:
            m = mlo
        else:
            m = mhi
        curve_m = curve[m]
        return curve_m.c + mach * (curve_m.b + curve_m.a * mach)
