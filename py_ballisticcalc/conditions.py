"""Environmental conditions used by ballistic engines.

What this module provides
- Atmo: Atmosphere model (actual or ICAO) with density ratio and Mach (speed of sound)
    calculations. Inputs are units-aware and can be provided as raw numbers or Unit-wrapped
    values; conversions are handled via PreferredUnits. Supports humidity and altitude
    lapse-rate formulas and exposes helpers for standard temperature/pressure.
- Vacuum: An Atmo subclass that models a vacuum (zero pressure/density) for dragless
    trajectories and benchmarks.
- Wind: Piecewise-constant wind segments described by speed, direction-from, and
    distance limit, with a 3D vector representation used by integrators.
- Coriolis: Description of Coriolis acceleration due to Earth's rotation.

Design notes
- Units: All public constructors accept either raw numbers or Unit instances; inputs
    are coerced to PreferredUnits to keep APIs ergonomic and strict. Use the Unit helpers
    (e.g., Unit.Foot, Unit.hPa, Unit.Celsius, Unit.FPS) for clarity in examples.
- Atmosphere: Use Atmo.icao(...) for standard atmosphere at an altitude; humidity is relative
    (0-100%). Changing temperature/pressure/humidity updates density_ratio and Mach.
- Wind.direction_from: 0° is from behind the shooter; 90° is from the shooter's left.
- Coriolis.latitude: Positive in northern hemisphere, negative in southern; 0 at equator.

Examples:
>>> # Standard atmosphere at sea level:
>>> atmo = Atmo.icao()
>>> # Crosswind from left to right at 10 fps, in effect over the entire trajectory:
>>> from py_ballisticcalc import Unit
>>> breeze = Wind(velocity=Unit.FPS(10), direction_from=Unit.Degree(90))
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

from typing_extensions import Optional, Tuple, Union

from py_ballisticcalc.constants import (
    cStandardDensity,
    cLapseRateKperFoot,
    cLowestTempF,
    cStandardDensityMetric,
    cDegreesCtoK,
    cPressureExponent,
    cStandardTemperatureF,
    cLapseRateImperial,
    cStandardPressureMetric,
    cLapseRateMetric,
    cStandardTemperatureC,
    cStandardHumidity,
    cSpeedOfSoundImperial,
    cDegreesFtoR,
    cSpeedOfSoundMetric,
    cMaxWindDistanceFeet,
    cGravityImperial,
    cEarthAngularVelocityRadS,
)
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits, Pressure, Temperature, Velocity
from py_ballisticcalc.vector import Vector, ZERO_VECTOR

__all__ = ("Atmo", "Vacuum", "Wind")


class Atmo:  # pylint: disable=too-many-instance-attributes
    """Atmospheric conditions and density calculations.

    This class encapsulates atmospheric conditions (altitude, pressure, temperature, relative humidity)
    and provides helpers to derive air density ratio, actual densities, and local speed of sound (Mach 1).
    The instance stores an internal "base" altitude/pressure/temperature snapshot (`_a0`, `_p0`, `_t0`)
    used to interpolate conditions at other altitudes using lapse-rate models.

    Attributes:
        altitude (Distance): Altitude relative to sea level.
        pressure (Pressure): Unadjusted barometric (station) pressure.
        temperature (Temperature): Ambient air temperature.
        humidity (float): Relative humidity expressed either as fraction [0..1] or percent [0..100].
        powder_temp (Temperature): Powder temperature (may differ from ambient when powder sensitivity enabled).
        density_ratio (float): Ratio of local air density to standard density.
        mach (Velocity): Local speed of sound (Mach 1).
        density_metric (float): Air density in kg/m^3.
        density_imperial (float): Air density in lb/ft^3.
    """

    # ---------------------------------------------------------------------
    # Class / instance private state annotations & class constants
    # ---------------------------------------------------------------------
    _humidity: float  # Relative humidity [0% to 100%]
    _mach: float  # Velocity of sound (Mach 1) for current atmosphere in fps
    _a0: float  # Base Altitude (ft)
    _t0: float  # Base Temperature (°C)
    _p0: float  # Base Pressure (hPa)
    cLowestTempC: float = Temperature.Fahrenheit(cLowestTempF) >> Temperature.Celsius  # Model lower bound (°C)

    # ---------------------------------------------------------------------
    # Construction / dunder methods
    # ---------------------------------------------------------------------
    def __init__(
        self,
        altitude: Optional[Union[float, Distance]] = None,
        pressure: Optional[Union[float, Pressure]] = None,
        temperature: Optional[Union[float, Temperature]] = None,
        humidity: float = 0.0,
        powder_t: Optional[Union[float, Temperature]] = None,
    ):
        """Initialize an `Atmo` instance.

        Args:
            altitude: Altitude relative to sea level. Defaults to 0.
            pressure: Station pressure (unadjusted). Defaults to standard pressure for altitude.
            temperature: Ambient temperature. Defaults to standard temperature for altitude.
            humidity: Relative humidity (fraction or percent). Defaults to 0.
            powder_t: Powder (propellant) temperature. Defaults to ambient temperature.

        Example:
            ```python
            from py_ballisticcalc import Atmo, Unit
            atmo = Atmo(
                altitude=Unit.Meter(100),
                pressure=Unit.hPa(1000),
                temperature=Unit.Celsius(20),
                humidity=50,
                powder_t=Unit.Celsius(15)
            )
            ```

        Notes:
            The constructor caches base conditions (`_t0` in °C, `_p0` in hPa, `_a0` in feet) and computes associated
            `_mach` and `_density_ratio`. Subsequent changes to humidity trigger an automatic density recomputation.
        """
        self._initializing = True
        self._altitude = PreferredUnits.distance(altitude or 0)
        self._pressure = PreferredUnits.pressure(pressure or Atmo.standard_pressure(self._altitude))
        self._temperature = PreferredUnits.temperature(temperature or Atmo.standard_temperature(self._altitude))
        # If powder_temperature not provided we use atmospheric temperature:
        self._powder_temp = PreferredUnits.temperature(powder_t or self._temperature)
        self._t0 = self._temperature >> Temperature.Celsius
        self._p0 = self._pressure >> Pressure.hPa
        self._a0 = self._altitude >> Distance.Foot
        self._mach = Atmo.machF(self._temperature >> Temperature.Fahrenheit)
        self.humidity = humidity
        self._initializing = False
        self.update_density_ratio()

    def __str__(self) -> str:  # noqa: D401 - short repr style acceptable
        return (
            f"Atmo(altitude={self.altitude}, pressure={self.pressure}, temperature={self.temperature}, "
            f"humidity={self.humidity}, density_ratio={self.density_ratio}, mach={self.mach})"
        )

    # ---------------------------------------------------------------------
    # Read-only public properties
    # ---------------------------------------------------------------------
    @property
    def altitude(self) -> Distance:
        """Altitude relative to sea level."""
        return self._altitude

    @property
    def pressure(self) -> Pressure:
        """Station barometric pressure (not altitude adjusted)."""
        return self._pressure

    @property
    def temperature(self) -> Temperature:
        """Air temperature."""
        return self._temperature

    @property
    def powder_temp(self) -> Temperature:
        """Powder temperature (falls back to ambient when unspecified)."""
        return self._powder_temp

    @property
    def mach(self) -> Velocity:
        """Local speed of sound (Mach 1)."""
        return Velocity.FPS(self._mach)

    @property
    def density_ratio(self) -> float:
        """Ratio of local density to standard density (dimensionless)."""
        return self._density_ratio

    @property
    def humidity(self) -> float:
        """Relative humidity as fraction [0..1]."""
        return self._humidity

    @humidity.setter
    def humidity(self, value: float) -> None:
        """Set relative humidity.

        Accepts either a fraction [0..1] or percent [0%..100%]. Values are clamped to valid range.
        Setting humidity triggers a density ratio update (unless during object initialization).
        """
        if value < 0 or value > 100:
            raise ValueError(r"Humidity must be between 0% and 100%.")
        if value > 1:  # treat as percent
            value /= 100.0
        self._humidity = value
        if not self._initializing:
            self.update_density_ratio()

    # ---------------------------------------------------------------------
    # Derived densities / conversions
    # ---------------------------------------------------------------------
    @property
    def density_metric(self) -> float:
        """Air density in metric units (kg/m^3)."""
        return self._density_ratio * cStandardDensityMetric

    @property
    def density_imperial(self) -> float:
        """Air density in imperial units (lb/ft^3)."""
        return self._density_ratio * cStandardDensity

    # ---------------------------------------------------------------------
    # Public computation helpers
    # ---------------------------------------------------------------------
    def update_density_ratio(self) -> None:
        """Recompute density ratio for changed humidity."""
        self._density_ratio = Atmo.calculate_air_density(self._t0, self._p0, self.humidity) / cStandardDensityMetric

    def temperature_at_altitude(self, altitude: float) -> float:
        """Interpolate temperature (°C) at altitude using lapse rate.

        Args:
            altitude: Altitude above mean sea level (ft).

        Returns:
            Temperature in degrees Celsius (bounded by model lower limit).
        """
        t = (altitude - self._a0) * cLapseRateKperFoot + self._t0
        if t < Atmo.cLowestTempC:
            t = Atmo.cLowestTempC
            warnings.warn(
                f"Temperature interpolated from altitude fell below minimum model limit. Bounded at {cLowestTempF}°F.",
                RuntimeWarning,
            )
        return t

    def pressure_at_altitude(self, altitude: float) -> float:
        """Interpolate pressure (hPa) at altitude using barometric formula.

        Args:
            altitude: Altitude above mean sea level (ft).

        Returns:
            Pressure in hPa.
        """
        return self._p0 * math.pow(
            1 + cLapseRateKperFoot * (altitude - self._a0) / (self._t0 + cDegreesCtoK), cPressureExponent
        )

    def get_density_and_mach_for_altitude(self, altitude: float) -> Tuple[float, float]:
        """Compute density ratio and Mach (fps) for the specified altitude.

        Uses lapse-rate interpolation unless altitude is within 30 ft of the base altitude,
            in which case the initial cached values are used for performance.

        Args:
            altitude: Altitude above mean sea level (ft).

        Returns:
            Tuple (density_ratio, mach_fps).
        """
        if math.fabs(self._a0 - altitude) < 30:  # fast path near base altitude
            return self._density_ratio, self._mach

        if altitude > 36089:  # troposphere limit ~36k ft
            warnings.warn(
                "Density request for altitude above modeled troposphere. Atmospheric model not valid here.",
                RuntimeWarning,
            )

        t_k = self.temperature_at_altitude(altitude) + cDegreesCtoK
        mach = Velocity.MPS(Atmo.machK(t_k)) >> Velocity.FPS
        p = self.pressure_at_altitude(altitude)
        density_delta = ((self._t0 + cDegreesCtoK) * p) / (self._p0 * t_k)
        density_ratio = self._density_ratio * density_delta
        # Alternative simplified exponential model (retained for reference):
        # density_ratio = self._density_ratio * math.exp(-(altitude - self._a0) / 34122)
        return density_ratio, mach

    # ---------------------------------------------------------------------
    # Standard atmosphere helpers and Mach calculations (static methods)
    # ---------------------------------------------------------------------
    @staticmethod
    def standard_temperature(altitude: Distance) -> Temperature:
        """ICAO standard temperature for altitude (valid to ~36,000 ft)."""
        return Temperature.Fahrenheit(cStandardTemperatureF + (altitude >> Distance.Foot) * cLapseRateImperial)

    @staticmethod
    def standard_pressure(altitude: Distance) -> Pressure:
        """ICAO standard pressure for altitude (valid to ~36,000 ft)."""
        return Pressure.hPa(
            cStandardPressureMetric
            * math.pow(
                1 + cLapseRateMetric * (altitude >> Distance.Meter) / (cStandardTemperatureC + cDegreesCtoK),
                cPressureExponent,
            )
        )

    @staticmethod
    def icao(
        altitude: Union[float, Distance] = 0,
        temperature: Optional[Temperature] = None,
        humidity: float = cStandardHumidity,
    ) -> Atmo:
        """Create a standard ICAO atmosphere at altitude.

        Args:
            altitude: Altitude (defaults to sea level).
            temperature: Optional override temperature (defaults to standard at altitude).
            humidity: Relative humidity (fraction or percent). Defaults to standard humidity.

        Returns:
            Atmo instance representing standard atmosphere at altitude.
        """
        altitude = PreferredUnits.distance(altitude)
        temperature = temperature or Atmo.standard_temperature(altitude)
        pressure = Atmo.standard_pressure(altitude)
        return Atmo(altitude, pressure, temperature, humidity)

    # Synonym for ICAO standard atmosphere
    standard = icao

    @staticmethod
    def machF(fahrenheit: float) -> float:
        """Mach 1 (fps) for given Fahrenheit temperature."""
        if fahrenheit < -cDegreesFtoR:
            bad_temp = fahrenheit
            fahrenheit = cLowestTempF
            warnings.warn(f"Invalid temperature: {bad_temp}°F. Adjusted to ({cLowestTempF}°F).", RuntimeWarning)
        return math.sqrt(fahrenheit + cDegreesFtoR) * cSpeedOfSoundImperial

    @staticmethod
    def machC(celsius: float) -> float:
        """Mach 1 (m/s) for given Celsius temperature."""
        if celsius < -cDegreesCtoK:
            bad_temp = celsius
            celsius = Atmo.cLowestTempC
            warnings.warn(f"Invalid temperature: {bad_temp}°C. Adjusted to ({celsius}°C).", RuntimeWarning)
        return Atmo.machK(celsius + cDegreesCtoK)

    @staticmethod
    def machK(kelvin: float) -> float:
        """Mach 1 (m/s) for given Kelvin temperature."""
        if kelvin < 0:
            bad_temp = kelvin
            kelvin = Atmo.cLowestTempC + cDegreesCtoK
            warnings.warn(f"Invalid temperature: {bad_temp}K. Adjusted to ({kelvin}K).", RuntimeWarning)
        return math.sqrt(kelvin) * cSpeedOfSoundMetric

    @staticmethod
    def calculate_air_density(t: float, p_hpa: float, humidity: float) -> float:
        """Air density from temperature (°C), pressure (hPa), and humidity.

        Args:
            t: Temperature in degrees Celsius.
            p_hpa: Pressure in hPa (hectopascals). Internally converted to Pa.
            humidity: Relative humidity (fraction or percent).

        Returns:
            Air density in kg/m³.

        Notes:
            - Divide result by `cDensityImperialToMetric` to get density in lb/ft³.
            - Source: CIPM-2007 (https://www.nist.gov/system/files/documents/calibrations/CIPM-2007.pdf)
        """
        R = 8.314472  # J/(mol·K), universal gas constant
        M_a = 28.96546e-3  # kg/mol, molar mass of dry air
        M_v = 18.01528e-3  # kg/mol, molar mass of water vapor

        def saturation_vapor_pressure(T):  # noqa: N802 (retain formula variable naming)
            A = [1.2378847e-5, -1.9121316e-2, 33.93711047, -6.3431645e3]
            return math.exp(A[0] * T**2 + A[1] * T + A[2] + A[3] / T)

        def enhancement_factor(p, T):  # noqa: N802
            alpha = 1.00062
            beta = 3.14e-8
            gamma = 5.6e-7
            return alpha + beta * p + gamma * T**2

        def compressibility_factor(p, T, x_v):  # noqa: N802
            a0 = 1.58123e-6
            a1 = -2.9331e-8
            a2 = 1.1043e-10
            b0 = 5.707e-6
            b1 = -2.051e-8
            c0 = 1.9898e-4
            c1 = -2.376e-6
            d = 1.83e-11
            e = -0.765e-8
            t_l = T - cDegreesCtoK
            Z = (
                1
                - (p / T) * (a0 + a1 * t_l + a2 * t_l**2 + (b0 + b1 * t_l) * x_v + (c0 + c1 * t_l) * x_v**2)
                + (p / T) ** 2 * (d + e * x_v**2)
            )
            return Z

        # Normalize humidity to fraction [0..1]
        rh = float(humidity)
        rh_frac = rh / 100.0 if rh > 1.0 else rh
        rh_frac = max(0.0, min(1.0, rh_frac))

        # Convert inputs for CIPM equations
        T_K = t + cDegreesCtoK  # Kelvin
        p = float(p_hpa) * 100.0  # hPa -> Pa

        # Calculation of saturated vapor pressure and enhancement factor
        p_sv = saturation_vapor_pressure(T_K)  # Pa (saturated vapor pressure)
        f = enhancement_factor(p, t)  # Enhancement factor (p in Pa, t in °C)

        # Partial pressure of water vapor and mole fraction
        p_v = rh_frac * f * p_sv  # Pa
        x_v = p_v / p  # Mole fraction of water vapor

        # Calculation of compressibility factor
        Z = compressibility_factor(p, T_K, x_v)
        return (p * M_a) / (Z * R * T_K) * (1.0 - x_v * (1.0 - M_v / M_a))


class Vacuum(Atmo):
    """Vacuum atmosphere (zero density => zero drag)."""

    def __init__(
        self, altitude: Optional[Union[float, Distance]] = None, temperature: Optional[Union[float, Temperature]] = None
    ):
        super().__init__(altitude, 0, temperature, 0)
        self._pressure = PreferredUnits.pressure(0)
        self._density_ratio = 0

    def update_density_ratio(self) -> None:
        self._density_ratio = 0.0


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

    def __init__(
        self,
        velocity: Optional[Union[float, Velocity]] = None,
        direction_from: Optional[Union[float, Angular]] = None,
        until_distance: Optional[Union[float, Distance]] = None,
        *,
        max_distance_feet: Optional[float] = cMaxWindDistanceFeet,
    ):
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


@dataclass(frozen=True)
class Coriolis:
    r"""Precomputed Coriolis helpers for applying Earth's rotation.

    The calculator keeps ballistic state in a local range/up/cross (*x, y, z*) frame where the *x* axis points
    down-range, *y* points up, and *z* points to the shooter's right.  Coriolis forces originate in the
    Earth-fixed East-North-Up (ENU) frame.  This class precumputes the scalars to transform between the two frames.

    If we are given latitude but not azimuth of the shot, this class falls back on a *flat-fire* approximation of
    Coriolis effects: north of the equator the deflection is to the right; south of the equator it is to the left.
    Given both azimuth $A$ and latitude $L$ we compute the full 3D Coriolis acceleration as:

    $$
    2 \Omega \begin{bmatrix}
        -V_y \cos(L) \sin(A) - V_z \sin(L) \\
        V_x \cos(L) \sin(A) + V_z \cos(L) \cos(A) \\
        V_x \sin(L) - V_y \cos(L) \cos(A)
    \end{bmatrix}
    $$

    Attributes:
        sin_lat: Sine of the firing latitude, used to project the Earth's rotation vector.
        cos_lat: Cosine of the firing latitude.
        sin_az: Sine of the firing azimuth, or `None` when azimuth is unknown (flat-fire fallback).
        cos_az: Cosine of the firing azimuth, or `None` when azimuth is unknown.
        range_east: Projection of the local range axis onto geographic east (None in flat-fire mode).
        range_north: Projection of the local range axis onto geographic north (None in flat-fire mode).
        cross_east: Projection of the local cross axis onto geographic east (None in flat-fire mode).
        cross_north: Projection of the local cross axis onto geographic north (None in flat-fire mode).
        flat_fire_only: `True` when no azimuth is provided and only the 2D flat-fire approximation should run.
        muzzle_velocity_fps: Muzzle velocity in feet per second (only needed by the flat-fire approximation).
    """

    sin_lat: float
    cos_lat: float
    sin_az: Optional[float]
    cos_az: Optional[float]
    range_east: Optional[float]
    range_north: Optional[float]
    cross_east: Optional[float]
    cross_north: Optional[float]
    flat_fire_only: bool
    muzzle_velocity_fps: float

    @classmethod
    def create(
        cls, latitude: Optional[float], azimuth: Optional[float], muzzle_velocity_fps: float
    ) -> Optional[Coriolis]:
        """Build a `Coriolis` helper for a shot when latitude is available.

        Args:
            latitude: Latitude of the shooting location in degrees [-90, 90].
            azimuth: Azimuth of the shooting direction in degrees [0, 360).
            muzzle_velocity_fps: Muzzle velocity in feet per second for the projectile.

        Returns:
            A populated `Coriolis` instance when the shot specifies a latitude, otherwise `None`.

        Notes:
            When azimuth is omitted we fall back to the *flat fire* approximation, which only corrects
            for the horizontal drift term that dominates short-range, low-arc engagements.
        """
        if latitude is None:
            return None

        lat_rad = math.radians(latitude)
        sin_lat = math.sin(lat_rad)
        cos_lat = math.cos(lat_rad)

        if azimuth is None:
            return cls(
                sin_lat=sin_lat,
                cos_lat=cos_lat,
                muzzle_velocity_fps=muzzle_velocity_fps,
                sin_az=None,
                cos_az=None,
                range_east=None,
                range_north=None,
                cross_east=None,
                cross_north=None,
                flat_fire_only=True,
            )

        azimuth_rad = math.radians(azimuth)

        return cls(
            sin_lat=sin_lat,
            cos_lat=cos_lat,
            muzzle_velocity_fps=muzzle_velocity_fps,
            sin_az=math.sin(azimuth_rad),
            cos_az=math.cos(azimuth_rad),
            range_east=math.sin(azimuth_rad),
            range_north=math.cos(azimuth_rad),
            cross_east=math.cos(azimuth_rad),
            cross_north=-math.sin(azimuth_rad),
            flat_fire_only=False,
        )

    @property
    def full_3d(self) -> bool:
        """Whether full 3D Coriolis terms are available for this shot."""
        return not self.flat_fire_only

    def coriolis_acceleration_local(self, velocity: Vector) -> Vector:
        """Compute the Coriolis acceleration for a velocity expressed in the local frame.

        Args:
            velocity: Projectile velocity vector in the local range/up/cross basis (feet per second).

        Returns:
            A `Vector` containing the Coriolis acceleration components in the same local basis.
            Returns the `ZERO_VECTOR` when only the flat-fire approximation is available.
        """
        if not self.full_3d:
            return ZERO_VECTOR

        assert self.range_east is not None and self.range_north is not None
        assert self.cross_east is not None and self.cross_north is not None

        vel_east = velocity.x * self.range_east + velocity.z * self.cross_east
        vel_north = velocity.x * self.range_north + velocity.z * self.cross_north
        vel_up = velocity.y

        factor = -2.0 * cEarthAngularVelocityRadS
        accel_east = factor * (self.cos_lat * vel_up - self.sin_lat * vel_north)
        accel_north = factor * (self.sin_lat * vel_east)
        accel_up = factor * (-self.cos_lat * vel_east)

        accel_range = accel_east * self.range_east + accel_north * self.range_north
        accel_cross = accel_east * self.cross_east + accel_north * self.cross_north
        return Vector(accel_range, accel_up, accel_cross)

    def flat_fire_offsets(self, time: float, distance_ft: float, drop_ft: float) -> Tuple[float, float]:
        """Estimate flat-fire vertical and horizontal corrections.

        Args:
            time: Time of flight in seconds for the sample point.
            distance_ft: Down-range distance in feet at the sample point.
            drop_ft: Local vertical displacement in feet (positive is up).

        Returns:
            A tuple `(vertical_ft, horizontal_ft)` of offsets that should be applied to the range/up/cross vector.
            Both values are zero when `Shot` has both latitude and azimuth and so can compute a full 3D solution.
        """
        if not self.flat_fire_only:
            return 0.0, 0.0

        horizontal = cEarthAngularVelocityRadS * distance_ft * self.sin_lat * time
        vertical = 0.0
        if self.sin_az is not None:  # This should not happen if not full_3d, but approximation provided for reference
            vertical_factor = -2.0 * cEarthAngularVelocityRadS * self.muzzle_velocity_fps * self.cos_lat * self.sin_az
            vertical = drop_ft * (vertical_factor / cGravityImperial)
        return vertical, horizontal

    def adjust_range(self, time: float, range_vector: Vector) -> Vector:
        """Apply the flat-fire offsets to a range vector when necessary.

        Args:
            time: Time of flight in seconds for the sample point.
            range_vector: Original range/up/cross vector (feet) produced by the integrator.

        Returns:
            Either the original vector (for full 3D solutions) or a new vector with the flat-fire offsets applied.
        """
        if not self.flat_fire_only:
            return range_vector

        delta_y, delta_z = self.flat_fire_offsets(time, range_vector.x, range_vector.y)
        if delta_y == 0.0 and delta_z == 0.0:
            return range_vector
        return Vector(range_vector.x, range_vector.y + delta_y, range_vector.z + delta_z)
