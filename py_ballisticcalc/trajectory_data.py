"""Ballistic Trajectory Data Structures and Post-Processing Classes.

Core Components:
    - TrajFlag: Ballistic points of interest
    - TrajectoryData: Detailed ballistic state at a single trajectory point
    - BaseTrajData: Minimal trajectory data required for a single point
    - HitResult: Complete trajectory results with metadata
    - ShotProps: All metadata used to compute the trajectory
    - DangerSpace: Target engagement zone analysis

Key Features:
    - Immutable trajectory data structures for thread safety
    - Quadratic interpolation for smooth trajectory analysis
    - Support for multiple coordinate systems and unit conversions
    - Integration with visualization libraries (matplotlib)
    - Zero-crossing detection and special point identification
    - Danger space analysis for tactical applications

Typical Usage:
    ```python
    from py_ballisticcalc import Calculator, Shot, DragModel
    from py_ballisticcalc.trajectory_data import TrajFlag
    
    # Calculate trajectory
    calc = Calculator()
    shot = Shot(...)
    
    hit_result = calc.fire(shot, trajectory_range=1000, flags=TrajFlag.ALL)
    
    # Access trajectory data
    for point in hit_result.trajectory:
        print(f"Time: {point.time:.3f}s, Distance: {point.distance}, "
              f"Height: {point.height}, Velocity: {point.velocity}")
    
    # Find specific points
    zero_data = hit_result.zeros()  # Zero crossings
    max_range_point = hit_result.get_at('distance', Distance.Meter(1000))

    # Quadratic interpolation for specific point
    interpolated = TrajectoryData.interpolate('time', 1.5, point1, point2, point3)
    
    # Danger space analysis
    danger = hit_result.danger_space(at_range=Distance.Meter(500),
                                     target_height=Distance.Feet(2))
    ```

See Also:
    - py_ballisticcalc.interface: Calculator class to generate HitResults
    - py_ballisticcalc.unit: Unit system for all measurement values
    - py_ballisticcalc.vector: Vector mathematics for position/velocity
"""
from __future__ import annotations
import math
import typing
import warnings
from dataclasses import dataclass, field
from deprecated import deprecated
from typing_extensions import Final, List, Literal, NamedTuple, Optional, Sequence, Tuple, Union

from py_ballisticcalc.conditions import Shot, Wind
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.exceptions import RangeError
from py_ballisticcalc.unit import (Angular, Distance, Energy, Pressure, Temperature, Velocity, Weight,
                                   GenericDimension, Unit, PreferredUnits
)
from py_ballisticcalc.vector import Vector
from py_ballisticcalc.interpolation import (
    InterpolationMethod,
    interpolate_3_pt,
    interpolate_2_pt,
)

if typing.TYPE_CHECKING:
    from pandas import DataFrame
    from matplotlib.axes import Axes

__all__ = (
    'TrajFlag',
    'BaseTrajData',
    'TrajectoryData',
    'ShotProps',
    'HitResult',
    'DangerSpace',
    'CurvePoint',
    'create_trajectory_row',
    'calculate_energy',
    'calculate_ogw',
    'get_correction',
    'calculate_curve',
)
 

class TrajFlag(int):
    """Trajectory point classification flags for marking special trajectory events.
    
    Provides enumeration values for identifying and filtering special points in
    ballistic trajectories. The flags can be combined using bitwise operations.
    
    Flag Values:
        NONE (0): Standard trajectory point with no special events
        ZERO_UP (1): Upward zero crossing (trajectory rising through sight line)
        ZERO_DOWN (2): Downward zero crossing (trajectory falling through sight line)
        ZERO (3): Any zero crossing (ZERO_UP | ZERO_DOWN)
        MACH (4): Mach 1 transition point (sound barrier crossing)
        RANGE (8): User requested point, typically by distance or time step
        APEX (16): Trajectory apex (maximum height point)
        ALL (31): All special points (combination of all above flags)
        MRT (32): Mid-Range Trajectory/Maximum Ordinate (largest slant height) [PROPOSED]
        
    Examples:
        Basic flag usage:
        
        ```python
        from py_ballisticcalc.trajectory_data import TrajFlag
        
        # Filter for zero crossings only
        flags = TrajFlag.ZERO
        
        # Filter for multiple event types
        flags = TrajFlag.ZERO | TrajFlag.APEX | TrajFlag.MACH
        
        # Filter for all special points
        flags = TrajFlag.ALL
        
        # Check if a trajectory point has specific flags
        if point.flag & TrajFlag.APEX:
            print("Trajectory apex")
        ```
        
        Trajectory calculation with flags:
        
        ```python
        # Calculate trajectory with zero crossings and apex
        hit_result = calc.fire(shot, 1000, filter_flags=TrajFlag.ZERO | TrajFlag.APEX)
        
        # Find all zero crossing points
        zeros = [p for p in hit_result.trajectory if p.flag & TrajFlag.ZERO]
        
        # Find apex point
        apex = next((p for p in hit_result.trajectory if p.flag & TrajFlag.APEX), None)
        ```
    """
    NONE: Final[int] = 0
    ZERO_UP: Final[int] = 1
    ZERO_DOWN: Final[int] = 2
    ZERO: Final[int] = ZERO_UP | ZERO_DOWN
    MACH: Final[int] = 4
    RANGE: Final[int] = 8
    APEX: Final[int] = 16
    ALL: Final[int] = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX
    MRT: Final[int] = 32

    @classmethod
    def _value_to_name(cls) -> dict[int, str]:
        return {
            v: k
            for k, v in vars(cls).items()
            if k.isupper() and isinstance(v, int)
        }

    @staticmethod
    def name(value: Union[int, TrajFlag]) -> str:
        """Get the human-readable name for a trajectory flag value.
        
        Converts a numeric flag value to its corresponding string name for
        display, logging, or debugging purposes. Supports both individual
        flags and combined flag values with intelligent formatting.
        
        Args:
            value: The TrajFlag enum value or integer flag to convert.
            
        Returns:
            String name of the flag. For combined flags, returns names joined
            with "|". For unknown flags, returns "UNKNOWN". Special handling
            for ZERO flag combinations.
            
        Examples:
            ```python
            # Individual flag names
            print(TrajFlag.name(TrajFlag.ZERO))      # "ZERO"
            print(TrajFlag.name(TrajFlag.APEX))      # "APEX"
            
            # Combined flags
            combined = TrajFlag.ZERO | TrajFlag.APEX
            print(TrajFlag.name(combined))           # "ZERO|APEX"
            
            # Unknown flags
            print(TrajFlag.name(999))                # "UNKNOWN"
            ```
        """
        v = int(value)
        mapping = TrajFlag._value_to_name()
        if v in mapping:
            return mapping[v]
        parts = [mapping[bit] for bit in sorted(mapping) if bit and (v & bit) == bit]
        if "ZERO_UP" in parts and "ZERO_DOWN" in parts:
            parts.remove("ZERO_UP")
            parts.remove("ZERO_DOWN")
        return "|".join(parts) if parts else "UNKNOWN"


# Interpolation helpers moved to py_ballisticcalc.interpolation


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


class BaseTrajData(NamedTuple):
    """Minimal ballistic trajectory point data.
    
    Represents the minimum state information for a single point in a ballistic trajectory.
    The data are kept in basic units (seconds, feet) to avoid unit tracking and conversion overhead.

    Attributes:
        time: Time since projectile launch in seconds.
        position: 3D position vector in feet (x=downrange, y=height, z=windage).
        velocity: 3D velocity vector in feet per second.
        mach: Local speed of sound in feet per second.

    Examples:
        ```python
        from py_ballisticcalc.vector import Vector
        
        # Create trajectory point at launch
        launch_pt = BaseTrajData(
            time=0.0,
            position=Vector(0.0, -0.1, 0.0),   # 0.1 ft scope height
            velocity=Vector(2640.0, 0.0, 0.0), # 800 m/s ≈ 2640 fps
            mach=1115.5                        # Standard conditions
        )
        
        # Interpolate between points
        interpolated = BaseTrajData.interpolate('time', 1.25, launch_pt, mid_pt, end_pt)
        ```
        
    Note:
        This class is designed for efficiency in calculation engines that may compute
        thousands of points over a trajectory. For detailed data with units and derived quantities,
        use TrajectoryData which can be constructed from BaseTrajData using from_base_data().
    """
    time: float  # Units: seconds
    position: Vector  # Units: feet
    velocity: Vector  # Units: fps
    mach: float  # Units: fps

    @staticmethod
    def interpolate(key_attribute: str, key_value: float,
                    p0: BaseTrajData, p1: BaseTrajData, p2: BaseTrajData,
                    method: InterpolationMethod = "pchip") -> BaseTrajData:
        """
        Interpolate a BaseTrajData point using monotone PCHIP (default) or linear.

        Args:
            key_attribute: Can be 'time', 'mach', or a vector component like 'position.x' or 'velocity.z'.
            key_value: The value to interpolate for.
            p0, p1, p2: Three points surrounding the key_value.
            method: 'pchip' (default, monotone cubic Hermite) or 'linear'.

        Returns:
            The interpolated data point.

        Raises:
            AttributeError: If the key_attribute is not a member of BaseTrajData.
            ZeroDivisionError: If the interpolation fails due to zero division.
                               (This will result if two of the points are identical).
            ValueError: If method is not one of 'pchip' or 'linear'.
        """
        def get_key_val(td: "BaseTrajData", path: str) -> float:
            """Helper to get the key value from a BaseTrajData point."""
            if '.' in path:
                top, component = path.split('.', 1)
                obj = getattr(td, top)
                return getattr(obj, component)
            else:
                return getattr(td, path)

        # independent variable values
        x0 = get_key_val(p0, key_attribute)
        x1 = get_key_val(p1, key_attribute)
        x2 = get_key_val(p2, key_attribute)
        def _interp_scalar(y0, y1, y2):
            if method == "pchip":
                return interpolate_3_pt(key_value, x0, y0, x1, y1, x2, y2)
            elif method == "linear":
                pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[0])
                (sx0, sy0), (sx1, sy1), (sx2, sy2) = pts
                if key_value <= sx1:
                    return interpolate_2_pt(key_value, sx0, sy0, sx1, sy1)
                else:
                    return interpolate_2_pt(key_value, sx1, sy1, sx2, sy2)
            else:
                raise ValueError("method must be 'pchip' or 'linear'")

        time = _interp_scalar(p0.time, p1.time, p2.time) if key_attribute != 'time' else key_value
        px = _interp_scalar(p0.position.x, p1.position.x, p2.position.x)
        py = _interp_scalar(p0.position.y, p1.position.y, p2.position.y)
        pz = _interp_scalar(p0.position.z, p1.position.z, p2.position.z)
        position = Vector(px, py, pz)
        vx = _interp_scalar(p0.velocity.x, p1.velocity.x, p2.velocity.x)
        vy = _interp_scalar(p0.velocity.y, p1.velocity.y, p2.velocity.y)
        vz = _interp_scalar(p0.velocity.z, p1.velocity.z, p2.velocity.z)
        velocity = Vector(vx, vy, vz)
        mach = _interp_scalar(p0.mach, p1.mach, p2.mach) if key_attribute != 'mach' else key_value

        return BaseTrajData(time=time, position=position, velocity=velocity, mach=mach)


TRAJECTORY_DATA_ATTRIBUTES = Literal[
    'time', 'distance', 'velocity', 'mach', 'height', 'slant_height', 'drop_adj',
    'windage', 'windage_adj', 'slant_distance', 'angle', 'density_ratio', 'drag',
    'energy', 'ogw', 'flag', 'x', 'y', 'z'
]
TRAJECTORY_DATA_SYNONYMS: dict[TRAJECTORY_DATA_ATTRIBUTES, TRAJECTORY_DATA_ATTRIBUTES] = {
    'x': 'distance',
    'y': 'height',
    'z': 'windage',
}
class TrajectoryData(NamedTuple):
    """Data for one point in ballistic trajectory."""

    time: float  # Flight time in seconds
    distance: Distance  # Down-range (x-axis) coordinate of this point
    velocity: Velocity
    mach: float  # Velocity in Mach terms
    height: Distance  # Vertical (y-axis) coordinate of this point
    slant_height: Distance  # Distance orthogonal to sight-line
    drop_adj: Angular  # Sight adjustment to zero slant_height at this distance
    windage: Distance  # Windage (z-axis) coordinate of this point
    windage_adj: Angular  # Windage adjustment
    slant_distance: Distance  # Distance along sight line that is closest to this point
    angle: Angular  # Angle of velocity vector relative to x-axis
    density_ratio: float  # Ratio of air density here to standard density
    drag: float  # Standard Drag Factor at this point
    energy: Energy  # Energy of bullet at this point
    ogw: Weight  # Optimal game weight, given .energy
    flag: Union[TrajFlag, int]  # Row type

    @property
    def x(self) -> Distance:
        """Synonym for .distance."""
        return self.distance

    @property
    def y(self) -> Distance:
        """Synonym for .height."""
        return self.height

    @property
    def z(self) -> Distance:
        """Synonym for .windage."""
        return self.windage

    @deprecated(reason="Use .slant_distance instead of .look_distance", version="2.2.0")
    def look_distance(self) -> Distance:
        """Synonym for slant_distance."""
        return self.slant_distance

    @property
    @deprecated(reason="Use .slant_height instead of .target_drop", version="2.2.0")
    def target_drop(self) -> Distance:
        """Synonym for slant_height."""
        return self.slant_height

    def formatted(self) -> Tuple[str, ...]:
        """
        Returns:
            Tuple[str, ...]: Matrix of formatted strings for this point, in PreferredUnits.
        """

        def _fmt(v: GenericDimension, u: Unit) -> str:
            """simple formatter"""
            return f"{v >> u:.{u.accuracy}f} {u.symbol}"

        return (
            f'{self.time:.3f} s',
            _fmt(self.distance, PreferredUnits.distance),
            _fmt(self.velocity, PreferredUnits.velocity),
            f'{self.mach:.2f} mach',
            _fmt(self.height, PreferredUnits.drop),
            _fmt(self.slant_height, PreferredUnits.drop),
            _fmt(self.drop_adj, PreferredUnits.adjustment),
            _fmt(self.windage, PreferredUnits.drop),
            _fmt(self.windage_adj, PreferredUnits.adjustment),
            _fmt(self.slant_distance, PreferredUnits.distance),
            _fmt(self.angle, PreferredUnits.angular),
            f'{self.density_ratio:.5e}',
            f'{self.drag:.3e}',
            _fmt(self.energy, PreferredUnits.energy),
            _fmt(self.ogw, PreferredUnits.ogw),
            TrajFlag.name(self.flag)
        )

    def in_def_units(self) -> Tuple[float, ...]:
        """
        Returns:
            Tuple[float, ...]: Matrix of floats of this point, in PreferredUnits.
        """
        return (
            self.time,
            self.distance >> PreferredUnits.distance,
            self.velocity >> PreferredUnits.velocity,
            self.mach,
            self.height >> PreferredUnits.drop,
            self.slant_height >> PreferredUnits.drop,
            self.drop_adj >> PreferredUnits.adjustment,
            self.windage >> PreferredUnits.drop,
            self.windage_adj >> PreferredUnits.adjustment,
            self.slant_distance >> PreferredUnits.distance,
            self.angle >> PreferredUnits.angular,
            self.density_ratio,
            self.drag,
            self.energy >> PreferredUnits.energy,
            self.ogw >> PreferredUnits.ogw,
            self.flag
        )

    @staticmethod
    def from_base_data(props: ShotProps, data: BaseTrajData,
                       flag: Union[TrajFlag, int] = TrajFlag.NONE) -> TrajectoryData:
        """Creates a TrajectoryData object from BaseTrajData."""
        return TrajectoryData.from_props(props, data.time, data.position, data.velocity, data.mach, flag)

    @staticmethod
    def from_props(props: ShotProps,
                    time: float,
                    range_vector: Vector,
                    velocity_vector: Vector,
                    mach: float,
                    flag: Union[TrajFlag, int] = TrajFlag.NONE) -> TrajectoryData:
        """Creates a TrajectoryData object, which corresponds to one point in the ballistic trajectory."""
        spin_drift = props.spin_drift(time)
        velocity = velocity_vector.magnitude()
        windage = range_vector.z + spin_drift
        drop_adjustment = get_correction(range_vector.x, range_vector.y)
        windage_adjustment = get_correction(range_vector.x, windage)
        trajectory_angle = math.atan2(velocity_vector.y, velocity_vector.x)
        look_angle_cos = math.cos(props.look_angle_rad)
        look_angle_sin = math.sin(props.look_angle_rad)
        density_ratio, _ = props.get_density_and_mach_for_altitude(range_vector.y)
        drag = props.drag_by_mach(velocity / mach)
        return TrajectoryData(
            time=time,
            distance=_new_feet(range_vector.x),
            velocity=_new_fps(velocity),
            mach=velocity / mach,
            height=_new_feet(range_vector.y),
            slant_height=_new_feet(range_vector.y * look_angle_cos - range_vector.x * look_angle_sin),
            drop_adj=_new_rad(drop_adjustment - (props.look_angle_rad if range_vector.x else 0)),
            windage=_new_feet(windage),
            windage_adj=_new_rad(windage_adjustment),
            slant_distance=_new_feet(range_vector.x * look_angle_cos + range_vector.y * look_angle_sin),
            angle=_new_rad(trajectory_angle),
            density_ratio=density_ratio,
            drag=drag,
            energy=_new_ft_lb(calculate_energy(props.weight_grains, velocity)),
            ogw=_new_lb(calculate_ogw(props.weight_grains, velocity)),
            flag=flag
        )

    @staticmethod
    def interpolate(key_attribute: TRAJECTORY_DATA_ATTRIBUTES, value: Union[float, GenericDimension],
                    p0: TrajectoryData, p1: TrajectoryData, p2: TrajectoryData,
                    flag: Union[TrajFlag, int]=TrajFlag.NONE,
                    method: InterpolationMethod = "pchip") -> TrajectoryData:
        """
        Interpolate TrajectoryData where key_attribute==value using PCHIP (default) or linear.

        Args:
            key_attribute: Attribute to key on (e.g., 'time', 'distance').
            value: Target value for the key attribute. A bare float is treated as
                   raw value for dimensioned fields.
            p0, p1, p2: Three points surrounding the target.
            flag: Flag to assign to the new point.
            method: 'pchip' (monotone cubic Hermite) or 'linear'.

        Returns:
            Interpolated point with key_attribute==value.

        Raises:
            AttributeError: If TrajectoryData doesn't have the specified attribute.
            KeyError: If the key_attribute is 'flag'.
            ZeroDivisionError: If interpolation fails due to zero division.
            ValueError: If method is not one of 'pchip' or 'linear'.
        """
        key_attribute = TRAJECTORY_DATA_SYNONYMS.get(key_attribute, key_attribute)  # Resolve synonyms
        if not hasattr(TrajectoryData, key_attribute):
            raise AttributeError(f"TrajectoryData has no attribute '{key_attribute}'")
        if key_attribute == 'flag':
            raise KeyError("Cannot interpolate based on 'flag' attribute")
        key_value = value.raw_value if isinstance(value, GenericDimension) else value
        
        def get_key_val(td):
            """Helper to get the raw value of the key attribute from a TrajectoryData point"""
            val = getattr(td, key_attribute)
            return val.raw_value if hasattr(val, 'raw_value') else float(val)

        # The independent variable for interpolation (x-axis)
        x_val = key_value
        x0, x1, x2 = get_key_val(p0), get_key_val(p1), get_key_val(p2)

        # Use reflection to build the new TrajectoryData object
        interpolated_fields: typing.Dict[str, typing.Any] = {}
        for field_name in TrajectoryData._fields:
            if field_name == 'flag':
                continue

            p0_field = getattr(p0, field_name)

            if field_name == key_attribute:
                if isinstance(value, GenericDimension):
                    interpolated_fields[field_name] = value
                else:  # value is a float, assume it's in the same unit as the original data
                    if isinstance(p0_field, GenericDimension):
                        interpolated_fields[field_name] = type(p0_field).new_from_raw(float(value), p0_field.units)
                    else:
                        interpolated_fields[field_name] = float(value)
                continue

            # Interpolate all other fields
            y0_val = p0_field
            y1_val = getattr(p1, field_name)
            y2_val = getattr(p2, field_name)

            if isinstance(y0_val, GenericDimension):
                y0, y1, y2 = y0_val.raw_value, y1_val.raw_value, y2_val.raw_value
                if method == "pchip":
                    interpolated_raw = interpolate_3_pt(x_val, x0, y0, x1, y1, x2, y2)
                elif method == "linear":
                    interpolated_raw = interpolate_2_pt(x_val, x0, y0, x1, y1) if x_val <= x1 else interpolate_2_pt(x_val, x1, y1, x2, y2)
                else:
                    raise ValueError("method must be 'pchip' or 'linear'")
                interpolated_fields[field_name] = type(y0_val).new_from_raw(interpolated_raw, y0_val.units)
            elif isinstance(y0_val, (float, int)):
                fy0, fy1, fy2 = float(y0_val), float(y1_val), float(y2_val)
                if method == "pchip":
                    interpolated_fields[field_name] = interpolate_3_pt(x_val, x0, fy0, x1, fy1, x2, fy2)
                elif method == "linear":
                    interpolated_fields[field_name] = interpolate_2_pt(x_val, x0, fy0, x1, fy1) if x_val <= x1 else interpolate_2_pt(x_val, x1, fy1, x2, fy2)
                else:
                    raise ValueError("method must be 'pchip' or 'linear'")
            else:
                raise TypeError(f"Cannot interpolate field '{field_name}' of type {type(y0_val)}")

        interpolated_fields['flag'] = flag
        return TrajectoryData(**interpolated_fields)


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
        Create ShotProps from Shot object:
        
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
        drop = 100  # feet above initial altitude
        density_ratio, mach_fps = shot_props.get_density_and_mach_for_altitude(drop)
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
        """Initializes a ShotProps instance from a Shot instance."""
        return cls(
            shot=shot,
            bc=shot.ammo.dm.BC,
            curve=calculate_curve(shot.ammo.dm.drag_table),
            mach_list=_get_only_mach_data(shot.ammo.dm.drag_table),
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
    
    def drag_by_mach(self, mach: float) -> float:
        """Calculates a standard drag factor (SDF) for the given Mach number:
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

        Args:
            mach: The Mach number.

        Returns:
            The standard drag factor at the given Mach number.
        """
        # cd = calculate_by_curve(self._table_data, self._curve, mach)
        # use calculation over list[double] instead of list[DragDataPoint]
        cd = _calculate_by_curve_and_mach_list(self.mach_list, self.curve, mach)
        return cd * 2.08551e-04 / self.bc

    def spin_drift(self, time) -> float:
        """Litz spin-drift approximation

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
        """Calculates the Miller stability coefficient.

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

    def get_density_and_mach_for_altitude(self, drop: float):
        return self.shot.atmo.get_density_and_mach_for_altitude(self.alt0_ft + drop)


# pylint: disable=too-many-positional-arguments
@deprecated(reason="Use TrajectoryData.from_props instead.")
def create_trajectory_row(time: float, range_vector: Vector, velocity_vector: Vector,
                          velocity: float, mach: float, spin_drift: float, look_angle: float,
                          density_ratio: float, drag: float, weight: float,
                          flag: Union[TrajFlag, int]) -> TrajectoryData:
    """Creates a TrajectoryData object representing a single row of trajectory data.

    Args:
        time: Time of flight in seconds.
        range_vector: Position vector in feet.
        velocity_vector: Velocity vector in fps.
        velocity: Velocity magnitude in fps.
        mach: Mach number.
        spin_drift: Spin drift in feet.
        look_angle: Slant angle in radians.
        density_ratio: Density ratio (rho / rho_0).
        drag: Drag value.
        weight: Weight value.
        flag: Flag value.

    Returns:
        A TrajectoryData object representing the trajectory data.
    """
    warnings.warn("This method is deprecated", DeprecationWarning)

    windage = range_vector.z + spin_drift
    drop_adjustment = get_correction(range_vector.x, range_vector.y)
    windage_adjustment = get_correction(range_vector.x, windage)
    trajectory_angle = math.atan2(velocity_vector.y, velocity_vector.x)

    return TrajectoryData(
        time=time,
        distance=_new_feet(range_vector.x),
        velocity=_new_fps(velocity),
        mach=velocity / mach,
        height=_new_feet(range_vector.y),
        slant_height=_new_feet(range_vector.y * math.cos(look_angle) - range_vector.x * math.sin(look_angle)),
        drop_adj=_new_rad(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=_new_feet(windage),
        windage_adj=_new_rad(windage_adjustment),
        slant_distance=_new_feet(range_vector.x * math.cos(look_angle) + range_vector.y * math.sin(look_angle)),
        angle=_new_rad(trajectory_angle),
        density_ratio=density_ratio,
        drag=drag,
        energy=_new_ft_lb(calculate_energy(weight, velocity)),
        ogw=_new_lb(calculate_ogw(weight, velocity)),
        flag=flag
    )


def _new_feet(v: float):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


def _new_fps(v: float):
    d = object.__new__(Velocity)
    d._value = v / 3.2808399
    d._defined_units = Unit.FPS
    return d


def _new_rad(v: float):
    d = object.__new__(Angular)
    d._value = v
    d._defined_units = Unit.Radian
    return d


def _new_ft_lb(v: float):
    d = object.__new__(Energy)
    d._value = v
    d._defined_units = Unit.FootPound
    return d


def _new_lb(v: float):
    d = object.__new__(Weight)
    d._value = v / 0.000142857143
    d._defined_units = Unit.Pound
    return d


def get_correction(distance: float, offset: float) -> float:
    """Calculates the sight adjustment in radians.

    Args:
        distance: The distance to the target in feet.
        offset: The offset from the target in feet.

    Returns:
        The sight adjustment in radians.
    """
    if distance != 0:
        return math.atan(offset / distance)
    return 0  # None


def calculate_energy(bullet_weight: float, velocity: float) -> float:
    """Calculates the kinetic energy of a projectile.

    Args:
        bullet_weight: The weight of the bullet in pounds.
        velocity: The velocity of the bullet in feet per second.

    Returns:
        The kinetic energy of the projectile in foot-pounds.
    """
    return bullet_weight * math.pow(velocity, 2) / 450400


def calculate_ogw(bullet_weight: float, velocity: float) -> float:
    """Calculates the optimal game weight for a projectile.

    Args:
        bullet_weight: The weight of the bullet in pounds.
        velocity: The velocity of the bullet in feet per second.

    Returns:
        The optimal game weight in pounds.
    """
    return math.pow(bullet_weight, 2) * math.pow(velocity, 3) * 1.5e-12


def calculate_curve(data_points: List[DragDataPoint]) -> List[CurvePoint]:
    """Piecewise quadratic interpolation of drag curve

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


def _get_only_mach_data(data: List[DragDataPoint]) -> List[float]:
    """Extracts Mach values from a list of DragDataPoint objects.

    Args:
        data: A list of DragDataPoint objects.

    Returns:
        A list containing only the Mach values from the input data.
    """
    return [dp.Mach for dp in data]

# # use ._get_only_mach_data with ._calculate_by_curve_and_mach_list because it's faster
# def calculate_by_curve(data: List[DragDataPoint], curve: List[CurvePoint], mach: float) -> float:
#     """
#     Binary search for drag coefficient based on Mach number
#     :param data: data
#     :param curve: Output of calculate_curve(data)
#     :param mach: Mach value for which we're searching for CD
#     :return float: drag coefficient
#     """
#     num_points = int(len(curve))
#     mlo = 0
#     mhi = num_points - 2
#
#     while mhi - mlo > 1:
#         mid = int(math.floor(mhi + mlo) / 2.0)
#         if data[mid].Mach < mach:
#             mlo = mid
#         else:
#             mhi = mid
#
#     if data[mhi].Mach - mach > mach - data[mlo].Mach:
#         m = mlo
#     else:
#         m = mhi
#     curve_m = curve[m]
#     return curve_m.c + mach * (curve_m.b + curve_m.a * mach)


def _calculate_by_curve_and_mach_list(mach_list: List[float], curve: List[CurvePoint], mach: float) -> float:
    """Calculates a value based on a piecewise quadratic curve and a list of Mach values.

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


class DangerSpace(NamedTuple):
    """Stores the danger space data for distance specified."""
    at_range: TrajectoryData  # TrajectoryData at the target range
    target_height: Distance  # Target height
    begin: TrajectoryData  # TrajectoryData at beginning of danger space
    end: TrajectoryData  # TrajectoryData at end of danger space
    look_angle: Angular  # Look angle

    def __str__(self) -> str:
        return f'Danger space at {self.at_range.slant_distance << PreferredUnits.distance} ' \
            + f'for {self.target_height << PreferredUnits.drop} tall target ' \
            + (f'at {self.look_angle << Angular.Degree} look-angle ' if self.look_angle != 0 else '') \
            + f'ranges from {self.begin.slant_distance << PreferredUnits.distance} ' \
            + f'to {self.end.slant_distance << PreferredUnits.distance}' \
            + (f'\n\t(horizontal {self.begin.distance << PreferredUnits.distance} to {self.end.distance << PreferredUnits.distance})'
               if self.look_angle != 0 else '')

    # pylint: disable=import-outside-toplevel
    def overlay(self, ax: Axes, label: Optional[str] = None) -> None:
        """Highlights danger-space region on plot.

        Args:
            ax: The axes to overlay on.
            label: Label for the overlay. Defaults to None.

        Raises:
            ImportError: If plotting dependencies are not installed.
        """
        try:
            from py_ballisticcalc.visualize.plot import add_danger_space_overlay  # type: ignore[attr-defined]
            add_danger_space_overlay(self, ax, label)
        except ImportError as err:
            raise ImportError(
                "Use `pip install py_ballisticcalc[charts]` to get results as a plot"
            ) from err


# pylint: disable=import-outside-toplevel
@dataclass(frozen=True)
class HitResult:
    """Computed trajectory data of the shot.

    Attributes:
        shot: The parameters of the shot calculation.
        trajectory: Computed TrajectoryData points.
        base_data: Base trajectory data points for interpolation.
        extra: [DEPRECATED] Whether extra_data was requested.
        error: RangeError, if any.

    TODO:
    * Implement dense_output in cythonized engines to populate base_data
    * Use base_data for interpolation if present
    """
    props: ShotProps
    trajectory: list[TrajectoryData] = field(repr=False)
    base_data: Optional[list[BaseTrajData]] = field(repr=False)
    extra: bool = False
    error: Optional[RangeError] = None

    def __len__(self) -> int:
        return len(self.trajectory)

    def __iter__(self):
        yield from self.trajectory

    def __getitem__(self, item):
        return self.trajectory[item]

    def __check_extra__(self):
        if not self.extra:
            raise AttributeError(
                f"{object.__repr__(self)} has no extra data. "
                f"Use Calculator.fire(..., extra_data=True)"
            )

    def __check_flag__(self, flag: Union[TrajFlag, int]):
        if not self.props.filter_flags & flag:
            flag_name = TrajFlag.name(flag)
            raise AttributeError(f"{flag_name} was not requested in trajectory. "
                                 f"Use Calculator.fire(..., flags=TrajFlag.{flag_name}) to include it.")

    def zeros(self) -> list[TrajectoryData]:
        """
        Returns:
            list[TrajectoryData]: Zero crossing points.

        Raises:
            AttributeError: If extra_data was not requested.
            ArithmeticError: If zero crossing points are not found.
        """
        self.__check_flag__(TrajFlag.ZERO)
        data = [row for row in self.trajectory if row.flag & TrajFlag.ZERO]
        if len(data) < 1:
            raise ArithmeticError("Can't find zero crossing points")
        return data

    def flag(self, flag: Union[TrajFlag, int]) -> Optional[TrajectoryData]:
        """
        Returns:
            TrajectoryData: First TrajectoryData row with the specified flag.

        Raises:
            AttributeError: If flag was not requested.
        """
        self.__check_flag__(flag)
        for row in self.trajectory:
            if row.flag & flag:
                return row
        return None

    def get_at(self, key_attribute: TRAJECTORY_DATA_ATTRIBUTES,
                     value: Union[float, GenericDimension],
                     start_from_time: float=0.0) -> TrajectoryData:
        """
        Gets TrajectoryData where key_attribute==value, interpolating to create new object if necessary.
            Preserves the units of the original trajectory data.

        Args:
            key_attribute: The name of the TrajectoryData attribute to key on (e.g., 'time', 'distance').
            value: The value of the key attribute to find. If a float is provided
                   for a dimensioned attribute, it's assumed to be a .raw_value.
            start_from_time: The time to center the search from (default is 0.0).  If the target value is
                             at a local extremum then the search will only go forward in time.

        Returns:
            TrajectoryData: (where key_attribute==value)

        Raises:
            AttributeError: If TrajectoryData doesn't have the specified attribute.
            KeyError: If the key_attribute is 'flag'.
            ValueError: If interpolation is required and len(self.trajectory) < 3.
            ArithmeticError: If trajectory doesn't reach the requested value.

        Notes:
            * Not all attributes are monotonic.  Height typically goes up and then down.
                Velocity typically goes down, but for lofted trajectories can begin to increase.
                Windage can wander back and forth in complex winds.  We even have (see ExtremeExamples.ipynb)
                backward-bending scenarios in which distance reverses!
            * The only guarantee is that time is strictly increasing.
        """
        key_attribute = TRAJECTORY_DATA_SYNONYMS.get(key_attribute, key_attribute)  # Resolve synonyms
        if not hasattr(TrajectoryData, key_attribute):
            raise AttributeError(f"TrajectoryData has no attribute '{key_attribute}'")
        if key_attribute == 'flag':
            raise KeyError("Cannot interpolate based on 'flag' attribute")

        traj = self.trajectory
        n = len(traj)
        epsilon = 1e-9  # Very small tolerance for floating point comparison
        key_value = value.raw_value if isinstance(value, GenericDimension) else value
        
        def get_key_val(td):
            """Helper to get the raw value of the key attribute from a TrajectoryData point"""
            val = getattr(td, key_attribute)
            return val.raw_value if hasattr(val, 'raw_value') else val

        if n < 3:  # We won't interpolate on less than 3 points, but check for an exact match in the existing rows.
            if abs(get_key_val(traj[0]) - key_value) < epsilon:
                return traj[0]
            if n > 1 and abs(get_key_val(traj[1]) - key_value) < epsilon:
                return traj[1]
            raise ValueError("Interpolation requires at least 3 TrajectoryData points.")

        # Find the starting index based on start_from_time
        start_idx = 0
        if start_from_time > 0:
            start_idx = next((i for i, td in enumerate(traj) if td.time >= start_from_time), 0)
        curr_val = get_key_val(traj[start_idx])
        if abs(curr_val - key_value) < epsilon:  # Check for exact match
            return traj[start_idx]
        # Determine search direction from the starting point
        search_forward = True  # Default to forward search
        if start_idx == n - 1:  # We're at the last point, search backwards            
            search_forward = False
        if start_idx > 0 and start_idx < n - 1:
            # We're in the middle of the trajectory, determine local direction towards key_value
            next_val = get_key_val(traj[start_idx + 1])
            if (next_val > curr_val and key_value > curr_val) or (next_val < curr_val and key_value < curr_val):
                search_forward = True
            else:
                search_forward = False

        # Search for the target value in the determined direction
        target_idx = -1
        if search_forward:  # Search forward from start_idx            
            for i in range(start_idx, n - 1):
                curr_val = get_key_val(traj[i])
                next_val = get_key_val(traj[i + 1])
                # Check if key_value is between curr_val and next_val
                if ((curr_val < key_value <= next_val) or (next_val <= key_value < curr_val)):
                    target_idx = i + 1
                    break
        if not search_forward or target_idx == -1:  # Search backward from start_idx
            for i in range(start_idx, 0, -1):
                curr_val = get_key_val(traj[i])
                prev_val = get_key_val(traj[i - 1])
                # Check if key_value is between prev_val and curr_val
                if ((prev_val <= key_value < curr_val) or (curr_val < key_value <= prev_val)):
                    target_idx = i
                    break

        # Check if we found a valid index
        if target_idx == -1:
            raise ArithmeticError(f"Trajectory does not reach {key_attribute} = {value}")
        # Check for exact match here
        if abs(get_key_val(traj[target_idx]) - key_value) < epsilon:
            return traj[target_idx]
        if target_idx == 0:  # Step forward from first point so we can interpolate
            target_idx = 1
        # Choose three bracketing points (p0, p1, p2)
        if target_idx >= n - 1:  # At or after the last point
            p0, p1, p2 = traj[n - 3], traj[n - 2], traj[n - 1]
        else:
            p0, p1, p2 = traj[target_idx - 1], traj[target_idx], traj[target_idx + 1]
        return TrajectoryData.interpolate(key_attribute, value, p0, p1, p2)

    @deprecated(reason="Use get_at() instead for better flexibility.")
    def index_at_distance(self, d: Distance) -> int:
        """
        Args:
            d: Distance for which we want Trajectory Data.

        Returns:
            Index of first trajectory row with .distance >= d; otherwise -1.
        """
        epsilon = 1e-1  # small value to avoid floating point issues
        return next((i for i in range(len(self.trajectory))
                     if self.trajectory[i].distance.raw_value >= d.raw_value - epsilon), -1)

    @deprecated(reason="Use get_at('distance', d)")
    def get_at_distance(self, d: Distance) -> TrajectoryData:
        """
        Args:
            d: Distance for which we want Trajectory Data.

        Returns:
            First trajectory row with .distance >= d.

        Raises:
            ArithmeticError: If trajectory doesn't reach requested distance.
        """
        if (i := self.index_at_distance(d)) < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested distance {d}"
            )
        return self.trajectory[i]

    @deprecated(reason="Use get_at('time', t)")
    def get_at_time(self, t: float) -> TrajectoryData:
        """
        Args:
            t: Time for which we want Trajectory Data.

        Returns:
            First trajectory row with .time >= t.

        Raises:
            ArithmeticError: If trajectory doesn't reach requested time.
        """
        epsilon = 1e-6  # small value to avoid floating point issues
        idx = next((i for i in range(len(self.trajectory))
                     if self.trajectory[i].time >= t - epsilon), -1)
        if idx < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested time {t}"
            )
        return self.trajectory[idx]

    def danger_space(self,
                     at_range: Union[float, Distance],
                     target_height: Union[float, Distance],
                     ) -> DangerSpace:
        """
        Calculates the danger space for a given range and target height:
            Assumes that the trajectory hits the center of a target at any distance.
            Determines how much ranging error can be tolerated if the critical region
            of the target has target_height *h*. Finds how far forward and backward along the
            line of sight a target can move such that the trajectory is still within *h*/2
            of the original drop at_range.

        Args:
            at_range (Union[float, Distance]): Danger space is calculated for a target centered at this sight distance.
            target_height (Union[float, Distance]): Target height (*h*) determines danger space.

        Returns:
            DangerSpace: The calculated danger space.

        Raises:
            ArithmeticError: If trajectory doesn't reach requested distance.
        """
        target_at_range = PreferredUnits.distance(at_range)
        target_height = PreferredUnits.target_height(target_height)
        target_height_half = target_height.raw_value / 2.0

        target_row = self.get_at('slant_distance', target_at_range)
        is_climbing = target_row.angle.raw_value - self.props.look_angle.raw_value > 0
        slant_height_begin = target_row.slant_height.raw_value + (-1 if is_climbing else 1) * target_height_half
        slant_height_end = target_row.slant_height.raw_value - (-1 if is_climbing else 1) * target_height_half
        try:
            begin_row = self.get_at('slant_height', slant_height_begin, target_row.time)
        except ArithmeticError:
            begin_row = self.trajectory[0]
        try:
            end_row = self.get_at('slant_height', slant_height_end, target_row.time)
        except ArithmeticError:
            end_row = self.trajectory[-1]

        return DangerSpace(target_row,
                           target_height,
                           begin_row,
                           end_row,
                           self.props.look_angle)

    def dataframe(self, formatted: bool = False) -> DataFrame:
        """
        Returns the trajectory table as a DataFrame.

        Args:
            formatted (bool, optional): False for values as floats; True for strings in PreferredUnits. Defaults to False.

        Returns:
            DataFrame: The trajectory table as a DataFrame.

        Raises:
            ImportError: If pandas or plotting dependencies are not installed.
        """
        try:
            from py_ballisticcalc.visualize.dataframe import hit_result_as_dataframe
            return hit_result_as_dataframe(self, formatted)
        except ImportError as err:
            raise ImportError(
                "Use `pip install py_ballisticcalc[charts]` to get trajectory as pandas.DataFrame"
            ) from err

    def plot(self, look_angle: Optional[Angular] = None) -> Axes:
        """
        Returns a graph of the trajectory.

        Args:
            look_angle (Optional[Angular], optional): Look angle for the plot. Defaults to None.

        Returns:
            Axes: The plot axes.

        Raises:
            ImportError: If plotting dependencies are not installed.
        """
        try:
            from py_ballisticcalc.visualize.plot import hit_result_as_plot  # type: ignore[attr-defined]
            return hit_result_as_plot(self, look_angle)
        except ImportError as err:
            raise ImportError(
                "Use `pip install py_ballisticcalc[charts]` to get results as a plot"
            ) from err
