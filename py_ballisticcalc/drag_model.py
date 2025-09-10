"""Drag model implementations for ballistic projectiles.

This module provides classes and functions for modeling aerodynamic drag of
projectiles, including single and multi-BC (ballistic coefficient) models.
Supports standard drag tables and custom drag data points.

Key Components:
    - DragDataPoint: Individual drag coefficient at specific Mach number
    - BCPoint: Ballistic coefficient point for multi-BC models
    - DragModel: Primary drag model with ballistic coefficient and drag table
    - DragModelMultiBC: Multi-BC drag model for varying ballistic coefficients

Functions:
    - make_data_points: Convert drag table data to DragDataPoint objects
    - sectional_density: Calculate sectional density from weight and diameter
    - linear_interpolation: Linear interpolation utility function

The drag models use standard ballistic reference tables (G1, G7, etc.) and
allow for custom drag functions based on Mach number vs drag coefficient data.
"""

# Standard library imports
import math
import warnings
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

# Third-party imports
from typing_extensions import TypeAlias

# Local imports
from py_ballisticcalc.constants import cDegreesCtoK, cSpeedOfSoundMetric, cStandardTemperatureC
from py_ballisticcalc.drag_tables import DragTablePointDictType
from py_ballisticcalc.unit import Distance, PreferredUnits, Velocity, Weight


@dataclass
class DragDataPoint:
    """Drag coefficient at a specific Mach number.
    
    Attributes:
        Mach: Velocity in Mach units (dimensionless)
        CD: Drag coefficient (dimensionless)
    """

    Mach: float  # Velocity in Mach units
    CD: float  # Drag coefficient


# Type alias for drag table data formats
DragTableDataType: TypeAlias = Union[List[DragTablePointDictType], List[DragDataPoint]]


class DragModel:
    """Aerodynamic drag model for ballistic projectiles.
    
    Represents the drag characteristics of a projectile using a ballistic coefficient and drag table.
    
    The ballistic coefficient (BC) is defined as:
        BC = weight / (diameter^2 * form_factor)
    where weight is in pounds, diameter is in inches, and form_factor is relative to the selected drag model.
    
    Attributes:
        BC: Ballistic coefficient (scales drag model for a particular projectile)
        drag_table: List of DragDataPoint objects defining Mach vs CD
        weight: Projectile weight (only needed for spin drift calculations)
        diameter: Projectile diameter (only needed for spin drift calculations) 
        length: Projectile length (only needed for spin drift calculations)
        sectional_density: Calculated sectional density (lb/in²)
        form_factor: Calculated form factor (dimensionless)
        
    Note:
        The weight, diameter, and length parameters are only required when computing spin drift.
        For basic trajectory calculations, only BC and drag_table are needed.
    """

    def __init__(self,
                 bc: float,
                 drag_table: DragTableDataType,
                 weight: Union[float, Weight] = 0,
                 diameter: Union[float, Distance] = 0,
                 length: Union[float, Distance] = 0) -> None:
        """Initialize a drag model with ballistic coefficient and drag table.
        
        Args:
            bc: Ballistic coefficient
            drag_table: Either list of DragDataPoint objects or list of
                        dictionaries with 'Mach' and 'CD' keys
            weight: Projectile weight in grains (default: 0)
            diameter: Projectile diameter in inches (default: 0)
            length: Projectile length in inches (default: 0)
            
        Raises:
            ValueError: If BC is not positive or drag_table is empty
            TypeError: If drag_table format is invalid
        """
        if len(drag_table) <= 0:
            raise ValueError('Received empty drag table')
        if bc <= 0:
            raise ValueError('Ballistic coefficient must be positive')
        if len(drag_table) < 2:
            warnings.warn('Drag table needs at least 2 entries to enable interpolation', UserWarning)

        self.drag_table = make_data_points(drag_table)

        self.BC = bc
        self.length = PreferredUnits.length(length)
        self.weight = PreferredUnits.weight(weight)
        self.diameter = PreferredUnits.diameter(diameter)
        if weight > 0 and diameter > 0:
            self.sectional_density = self._get_sectional_density()
            self.form_factor = self._get_form_factor(self.BC)

    def __repr__(self) -> str:
        """Return string representation of the drag model.
        
        Returns:
            String representation showing key parameters
        """
        return f"DragModel(BC={self.BC}, wgt={self.weight}, dia={self.diameter}, len={self.length})"

    def _get_form_factor(self, bc: float) -> float:
        """Calculate form factor relative to this drag model.
        
        Args:
            bc: Ballistic coefficient to calculate form factor for
            
        Returns:
            Form factor (dimensionless)
            
        Note:
            Requires sectional_density to be calculated (weight and diameter > 0)
        """
        return self.sectional_density / bc

    def _get_sectional_density(self) -> float:
        """Calculate sectional density from weight and diameter.
        
        Returns:
            Sectional density in lb/in²
            
        Note:
            Requires weight and diameter to be greater than 0
        """
        w = self.weight >> Weight.Grain
        d = self.diameter >> Distance.Inch
        return sectional_density(w, d)


def make_data_points(drag_table: DragTableDataType) -> List[DragDataPoint]:
    """Convert drag table from list of dictionaries to list of DragDataPoints.
    
    Handles both DragDataPoint objects and dictionaries with 'Mach' and 'CD' keys.
    Validates input format and provides clear error messages for invalid data.
    
    Args:
        drag_table: Either list of DragDataPoint objects or list of dictionaries
                    with 'Mach' and 'CD' keys
                   
    Returns:
        List of DragDataPoint objects ready for use in ballistic calculations
        
    Raises:
        TypeError: If drag_table items are not DragDataPoint objects or valid
                   dictionaries with required keys
    """
    try:
        return [
            point if isinstance(point, DragDataPoint) else DragDataPoint(point['Mach'], point['CD'])
            for point in drag_table
        ]
    except (KeyError, TypeError) as exc:
        raise TypeError(
            "All items in drag_table must be of type DragDataPoint or dict with 'Mach' and 'CD' keys"
        ) from exc


def sectional_density(weight: float, diameter: float) -> float:
    """Calculate sectional density of a projectile.
    
    Args:
        weight: Projectile weight in grains
        diameter: Projectile diameter in inches
        
    Returns:
        Sectional density in lb/in² (pounds per square inch)
        
    Note:
        Formula: SD = weight / (diameter² * 7000)
        where 7000 converts grains to pounds (7000 grains = 1 pound)
    """
    return weight / math.pow(diameter, 2) / 7000


@dataclass(order=True)
class BCPoint:
    """Ballistic coefficient point for multi-BC drag models.
    
    Represents a single ballistic coefficient at a specific velocity or Mach number.
        Sorts by Mach number for constructing drag models (see `DragModelMultiBC`).

    Attributes:
        BC: Ballistic coefficient
        Mach: Mach number corresponding to this BC measurement
        V: Velocity corresponding to this BC measurement (optional)

    Examples:
        ```python
        # Create a BCPoint with BC=0.5 at Mach 2.0
        point1 = BCPoint(BC=0.5, Mach=2.0)
        
        # Create a BCPoint with BC=0.4 at 1500fps
        point2 = BCPoint(BC=0.4, V=Velocity.FPS(1500))
        
        # Sort points by Mach number
        points = [point2, point1]
        points.sort()  # point1 will come before point2 since Mach 2.0 < Mach at 1500fps
        ```
        
    Note:
        Either `Mach` or `V` must be specified, but not both. If `V` is provided then `Mach`
            will be calculated automatically using standard atmospheric conditions.
    """

    BC: float = field(compare=False)
    Mach: float = field(compare=True)
    V: Optional[Velocity] = field(compare=False)

    def __init__(self,
                 BC: float,
                 Mach: Optional[float] = None,
                 V: Optional[Union[float, Velocity]] = None) -> None:
        """Initialize a BCPoint.
        
        Args:
            BC: Ballistic coefficient (must be positive)
            Mach: Mach number (optional, mutually exclusive with `V`)
            V: Velocity (optional, mutually exclusive with `Mach`)
            
        Raises:
            ValueError: If `BC` is not positive, or if both or neither of `Mach` and `V` are specified.
        """
        if BC <= 0:
            raise ValueError('Ballistic coefficient must be positive')
        if Mach and V:
            raise ValueError("You cannot specify both 'Mach' and 'V' at the same time")
        if not Mach and not V:
            raise ValueError("One of 'Mach' and 'V' must be specified")

        self.BC = BC
        self.V = PreferredUnits.velocity(V or 0)
        if V:
            self.Mach = (self.V >> Velocity.MPS) / self._machC()
        elif Mach:
            self.Mach = Mach

    @staticmethod
    def _machC() -> float:
        """Calculate Mach 1 velocity in m/s for standard Celsius temperature.
        
        Returns:
            Speed of sound in m/s at standard atmospheric conditions
        """
        return math.sqrt(cStandardTemperatureC + cDegreesCtoK) * cSpeedOfSoundMetric


def DragModelMultiBC(bc_points: List[BCPoint],
                     drag_table: DragTableDataType,
                     weight: Union[float, Weight] = 0,
                     diameter: Union[float, Distance] = 0,
                     length: Union[float, Distance] = 0) -> DragModel:
    """Create a drag model with multiple ballistic coefficients.
    
    Constructs a DragModel using multiple BC measurements at different velocities,
    interpolating between them to create a more accurate drag function. This is
    useful for projectiles whose BC varies significantly with velocity.
    
    Args:
        bc_points: List of BCPoint objects with BC measurements at specific velocities
        drag_table: Standard drag table (G1, G7, etc.) or custom drag data
        weight: Projectile weight in grains (default: 0)
        diameter: Projectile diameter in inches (default: 0) 
        length: Projectile length in inches (default: 0)
        
    Returns:
        DragModel with interpolated drag coefficients based on multiple BCs
        
    Example:
        ```python
        from py_ballisticcalc.drag_tables import TableG7
        DragModelMultiBC([BCPoint(.21, V=Velocity.FPS(1500)), BCPoint(.22, V=Velocity.FPS(2500))],
                         drag_table=TableG7)
        ```
    
    Note:
        If weight and diameter are provided, BC is set to sectional density.
        Otherwise, BC=1 and the drag_table contains final drag terms.
        BC points are automatically sorted by Mach number for interpolation.
    """
    weight = PreferredUnits.weight(weight)
    diameter = PreferredUnits.diameter(diameter)
    if weight > 0 and diameter > 0:
        bc = sectional_density(weight >> Weight.Grain, diameter >> Distance.Inch)
    else:
        bc = 1.0

    drag_table = make_data_points(drag_table)  # Convert from list of dicts to list of DragDataPoints

    bc_points.sort(key=lambda p: p.Mach)  # Make sure bc_points are sorted for linear interpolation
    bc_interp = linear_interpolation([x.Mach for x in drag_table],
                                     [x.Mach for x in bc_points],
                                     [x.BC / bc for x in bc_points])

    for i, point in enumerate(drag_table):
        point.CD = point.CD / bc_interp[i]
    return DragModel(bc, drag_table, weight, diameter, length)


def linear_interpolation(x: Union[List[float], Tuple[float]],
                         xp: Union[List[float], Tuple[float]],
                         yp: Union[List[float], Tuple[float]]) -> Union[List[float], Tuple[float]]:
    """Perform piecewise linear interpolation.
    
    Interpolates y-values for given x-values using linear interpolation between known data points.
    Handles extrapolation by returning boundary values for x-values outside the range of xp.
    
    Args:
        x: List of points for which we want interpolated values
        xp: List of existing x-coordinates (must be sorted in ascending order)
        yp: List of corresponding y-values for existing points
        
    Returns:
        List of interpolated y-values corresponding to input x-values
        
    Raises:
        AssertionError: If `xp` and `yp` lists have different lengths
        
    Note:
        - For x-values below `min(xp)`, returns `yp[0]`
        - For x-values above `max(xp)`, returns `yp[-1]`
        - Uses binary search for efficient interval location
    """
    assert len(xp) == len(yp), "xp and yp lists must have same length"
    # Validate xp strictly increasing to prevent zero-division and undefined intervals
    for i in range(1, len(xp)):
        if xp[i] <= xp[i - 1]:
            raise ValueError("xp must be strictly increasing with no duplicates")

    y = []
    for xi in x:
        if xi <= xp[0]:
            y.append(yp[0])
        elif xi >= xp[-1]:
            y.append(yp[-1])
        else:
            # Binary search to find interval containing xi
            left, right = 0, len(xp) - 1
            while left < right:
                mid = (left + right) // 2
                if xp[mid] <= xi < xp[mid + 1]:
                    slope = (yp[mid + 1] - yp[mid]) / (xp[mid + 1] - xp[mid])
                    y.append(yp[mid] + slope * (xi - xp[mid]))  # Interpolated value for xi
                    break
                if xi < xp[mid]:
                    right = mid
                else:
                    left = mid + 1
            if left == right:
                y.append(yp[left])
    return y


__all__ = ('DragModel', 'DragDataPoint', 'BCPoint', 'DragModelMultiBC')
