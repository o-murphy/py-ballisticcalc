"""Parameters for computing ballistic trajectories.

Classes:
- Shot: A container aggregating ammo, weapon, angles (look/relative/cant), atmosphere, winds,
    latitude, azimuth; computes derived barrel_elevation and barrel_azimuth used by engines.
- ShotProps: A dataclass translating a Shot into engine-ready scalars in internal units
    (feet/seconds/grains), including precomputed drag curves and trigonometric terms.

Notes:
- End users typically work with Shot objects; engines construct ShotProps internally
    to avoid per-step unit conversions and repeated lookups.
- HitResult objects include the ShotProps instance used to calculate a trajectory.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from typing_extensions import List, Optional, Sequence, Tuple, Union
from py_ballisticcalc.conditions import Atmo, Coriolis, Wind
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.interpolation import PchipPrepared, pchip_prepare, pchip_eval
from py_ballisticcalc.munition import Weapon, Ammo
from py_ballisticcalc.trajectory_data import TrajFlag
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits, Pressure, Temperature, Velocity, Weight
from py_ballisticcalc.vector import Vector, ZERO_VECTOR

__all__ = ("Shot", "ShotProps")


@dataclass
class Shot:
    """All information needed to compute a ballistic trajectory.

    Attributes:
        ammo: Ammo used for shot.
        atmo: Atmosphere in effect during shot.
        weapon: Weapon used for shot.
        winds: List of Wind in effect during shot, sorted by `.until_distance`.
        look_angle (slant_angle): Angle of sight line relative to horizontal.
            If `look_angle != 0` then any target in sight crosshairs will be at a different altitude:
                With target_distance = sight distance to a target (i.e., as through a rangefinder):
                    * Horizontal distance X to target = cos(look_angle) * target_distance
                    * Vertical distance Y to target = sin(look_angle) * target_distance
        cant_angle: Tilt of gun from vertical. If `weapon.sight_height != 0` then this shifts any barrel elevation
            from the vertical plane into the horizontal plane (as `barrel_azimuth`) by `sine(cant_angle)`.
        relative_angle: Elevation adjustment (a.k.a. "hold") added to `weapon.zero_elevation`.
        azimuth: Azimuth of the shooting direction in degrees [0, 360). Optional, for Coriolis effects.
            Should be geographic bearing where 0 = North, 90 = East, 180 = South, 270 = West.
            Difference from magnetic bearing is usually negligible.
        latitude: Latitude of the shooting location in degrees [-90, 90]. Optional, for Coriolis effects.
        barrel_elevation: Total barrel elevation (in vertical plane) from horizontal.
            `= look_angle + cos(cant_angle) * zero_elevation + relative_angle`
        barrel_azimuth: Horizontal angle of barrel relative to sight line.
    """

    ammo: Ammo
    atmo: Atmo
    weapon: Weapon
    _winds: List[Wind]  # Stored sorted by .until_distance
    look_angle: Angular
    relative_angle: Angular
    cant_angle: Angular
    _azimuth: Optional[float] = field(default=None)
    _latitude: Optional[float] = field(default=None)

    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        *,
        ammo: Ammo,
        atmo: Optional[Atmo] = None,
        weapon: Optional[Weapon] = None,
        winds: Optional[Sequence[Wind]] = None,
        look_angle: Optional[Union[float, Angular]] = None,
        relative_angle: Optional[Union[float, Angular]] = None,
        cant_angle: Optional[Union[float, Angular]] = None,
        azimuth: Optional[float] = None,
        latitude: Optional[float] = None,
    ):
        """Initialize `Shot` for trajectory calculations.

        Args:
            ammo: Ammo instance used for shot.
            atmo: Atmosphere in effect during shot.
            weapon: Weapon instance used for shot.
            winds: List of Wind in effect during shot.
            look_angle: Angle of sight line relative to horizontal.
                If `look_angle != 0` then any target in sight crosshairs will be at a different altitude:
                    With target_distance = sight distance to a target (i.e., as through a rangefinder):
                        * Horizontal distance X to target = cos(look_angle) * target_distance
                        * Vertical distance Y to target = sin(look_angle) * target_distance
            cant_angle: Tilt of gun from vertical. If `weapon.sight_height != 0` then this shifts any barrel elevation
                from the vertical plane into the horizontal plane (as `barrel_azimuth`) by `sine(cant_angle)`.
            relative_angle: Elevation adjustment (a.k.a. "hold") added to `weapon.zero_elevation`.
            azimuth: Azimuth of the shooting direction in degrees [0, 360). Optional, for Coriolis effects.
                Should be geographic bearing where 0 = North, 90 = East, 180 = South, 270 = West.
                Difference from magnetic bearing is usually negligible.
            latitude: Latitude of the shooting location in degrees [-90, 90]. Optional, for Coriolis effects.

        Example:
            ```python
            from py_ballisticcalc import Weapon, Ammo, Atmo, Wind, Unit, Shot
            shot = Shot(
                ammo=Ammo(...),
                atmo=Atmo(...),
                weapon=Weapon(...),
                winds=[Wind(...), ... ]
                look_angle=Unit.Degree(5),
                cant_angle=Unit.Degree(0),
                relative_angle=Unit.Degree(1),
                azimuth=90.0,  # East
                latitude=45.0  # 45° North
            )
            ```
        """
        self.ammo = ammo
        self.atmo = atmo or Atmo.icao()
        self.weapon = weapon or Weapon()
        self.winds = winds or [Wind()]
        self.look_angle = PreferredUnits.angular(look_angle or 0)
        self.cant_angle = PreferredUnits.angular(cant_angle or 0)
        self.relative_angle = PreferredUnits.angular(relative_angle or 0)
        self._azimuth = azimuth
        self._latitude = latitude

    @property
    def azimuth(self) -> Optional[float]:
        """Azimuth of the shooting direction in degrees [0, 360)."""
        return self._azimuth

    @azimuth.setter
    def azimuth(self, value: Optional[float]) -> None:
        if value is not None and (value < 0.0 or value >= 360.0):
            raise ValueError("Azimuth must be in range [0, 360).")
        self._azimuth = value

    @property
    def latitude(self) -> Optional[float]:
        """Latitude of the shooting location in degrees [-90, 90]."""
        return self._latitude

    @latitude.setter
    def latitude(self, value: Optional[float]) -> None:
        if value is not None and (value < -90.0 or value > 90.0):
            raise ValueError("Latitude must be in range [-90, 90].")
        self._latitude = value

    @property
    def winds(self) -> Sequence[Wind]:
        """Sequence[Wind] sorted by until_distance."""
        return tuple(self._winds)

    @winds.setter
    def winds(self, winds: Optional[Sequence[Wind]]):
        """Property setter.  Ensures .winds is sorted by until_distance.

        Args:
            winds: list of the winds in effect during shot
        """
        self._winds = sorted(winds or [Wind()], key=lambda wind: wind.until_distance.raw_value)

    @property
    def barrel_azimuth(self) -> Angular:
        """Horizontal angle of barrel relative to sight line."""
        return Angular.Radian(
            math.sin(self.cant_angle >> Angular.Radian)
            * ((self.weapon.zero_elevation >> Angular.Radian) + (self.relative_angle >> Angular.Radian))
        )

    @property
    def barrel_elevation(self) -> Angular:
        """Total barrel elevation (in vertical plane) from horizontal.

        Returns:
            Angle of barrel elevation in vertical plane from horizontal
                `= look_angle + cos(cant_angle) * zero_elevation + relative_angle`
        """
        return Angular.Radian(
            (self.look_angle >> Angular.Radian)
            + math.cos(self.cant_angle >> Angular.Radian)
            * ((self.weapon.zero_elevation >> Angular.Radian) + (self.relative_angle >> Angular.Radian))
        )

    @barrel_elevation.setter
    def barrel_elevation(self, value: Angular) -> None:
        """Setter for barrel_elevation.

        Sets `.relative_angle` to achieve the desired elevation.
            Note: This does not change the `.weapon.zero_elevation`.

        Args:
            value: Desired barrel elevation in vertical plane from horizontal
        """
        self.relative_angle = Angular.Radian(
            (value >> Angular.Radian)
            - (self.look_angle >> Angular.Radian)
            - math.cos(self.cant_angle >> Angular.Radian) * (self.weapon.zero_elevation >> Angular.Radian)
        )

    @property
    def slant_angle(self) -> Angular:
        """Synonym for look_angle."""
        return self.look_angle

    @slant_angle.setter
    def slant_angle(self, value: Angular) -> None:
        self.look_angle = value


@dataclass
class ShotProps:
    """Shot configuration and parameters for ballistic trajectory calculations.

    Contains all shot-specific parameters converted to standard internal units (feet, seconds, grains, radians)
    used by the calculation engines. The class pre-computes expensive calculations (drag curve interpolation,
    atmospheric data, projectile properties) for repeated use during trajectory integration.

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

    Notes:
        This class is designed for internal use by ballistic calculation engines.
        User code should typically work with Shot objects and let the Calculator
        handle the conversion to ShotProps automatically.

        The original Shot object is retained for reference, but modifications
        to it after ShotProps creation will not affect the stored calculations.
        Create a new ShotProps instance if Shot parameters change.
    """

    """
    TODO: The `Shot` member object should either be a copy or immutable so that subsequent changes to its
          properties do not invalidate the calculations and data associated with this ShotProps instance.
    """

    shot: Shot  # Reference to the original Shot object
    bc: float  # Ballistic coefficient
    drag_curve: PchipPrepared  # Precomputed PCHIP spline for drag vs Mach

    look_angle_rad: float  # Slant angle in radians
    twist_inch: float  # Twist rate of barrel rifling, in inches of length to make one full rotation
    length_inch: float  # Length of the bullet in inches
    diameter_inch: float  # Diameter of the bullet in inches
    weight_grains: float  # Weight of the bullet in grains
    barrel_elevation_rad: float  # Barrel elevation angle in radians
    barrel_azimuth_rad: float  # Horizontal angle of barrel relative to sight line, in radians
    sight_height_ft: float  # Height of the sight above the bore in feet
    cant_cosine: float  # Cosine of the cant angle
    cant_sine: float  # Sine of the cant angle
    alt0_ft: float  # Initial altitude in feet
    muzzle_velocity_fps: float  # Muzzle velocity in feet per second
    coriolis: Optional[Coriolis] = field(default=None, repr=False)
    stability_coefficient: float = field(init=False)  # Miller stability coefficient
    calc_step: float = field(init=False)  # Calculation step size
    filter_flags: Union[TrajFlag, int] = field(init=False)  # Flags for special ballistic trajectory points

    def __post_init__(self):
        self.stability_coefficient = self._calc_stability_coefficient()

    @property
    def azimuth(self) -> Optional[float]:
        return self.shot.azimuth

    @property
    def latitude(self) -> Optional[float]:
        return self.shot.latitude

    @property
    def winds(self) -> Sequence[Wind]:
        return self.shot.winds

    @classmethod
    def from_shot(cls, shot: Shot) -> ShotProps:
        """Initialize a ShotProps instance from a Shot instance."""
        muzzle_velocity_fps = shot.ammo.get_velocity_for_temp(shot.atmo.powder_temp) >> Velocity.FPS
        return cls(
            shot=shot,
            bc=shot.ammo.dm.BC,
            drag_curve=cls._precalc_drag_curve(shot.ammo.dm.drag_table),
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
            muzzle_velocity_fps=muzzle_velocity_fps,
            coriolis=Coriolis.create(shot.latitude, shot.azimuth, muzzle_velocity_fps),
        )

    def coriolis_acceleration(self, velocity: Vector) -> Vector:
        if self.coriolis and self.coriolis.full_3d:
            return self.coriolis.coriolis_acceleration_local(velocity)
        return ZERO_VECTOR

    def adjust_range_for_coriolis(self, time: float, range_vector: Vector) -> Vector:
        if not self.coriolis:
            return range_vector
        return self.coriolis.adjust_range(time, range_vector)

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
        cd = pchip_eval(self.drag_curve, mach)
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
            return sign * (1.25 * (self.stability_coefficient + 1.2) * math.pow(time, 1.83)) / 12
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
            sd = (
                30
                * self.weight_grains
                / (math.pow(twist_rate, 2) * math.pow(self.diameter_inch, 3) * length * (1 + math.pow(length, 2)))
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
    def _precalc_drag_curve(data_points: List[DragDataPoint]) -> PchipPrepared:
        """Pre-calculate the drag curve for the shot.

        Args:
            data_points: List of DragDataPoint objects with Mach and CD values.

        Returns:
            PCHIP spline coefficients for interpolating $C_d$ vs Mach.
        """
        xs = [dp.Mach for dp in data_points]
        ys = [dp.CD for dp in data_points]
        return pchip_prepare(xs, ys)
