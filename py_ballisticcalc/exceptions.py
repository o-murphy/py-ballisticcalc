"""py_ballisticcalc exception types.

This module provides a comprehensive exception hierarchy for handling various error conditions
that can occur during ballistic calculations.

Exception Hierarchy
-------------------

The py_ballisticcalc library defines a structured exception hierarchy:

Exception (built-in Python)
├── TypeError
│   └── UnitTypeError
│       └── UnitConversionError
├── ValueError
│   └── UnitAliasError
└── RuntimeError
    └── SolverRuntimeError
        ├── ZeroFindingError
        ├── RangeError
        └── OutOfRangeError

Exception Types
---------------

Unit-Related Exceptions:

- UnitTypeError: Base class for unit-related type errors. Raised when invalid unit types
  are passed to unit conversion functions or there are type mismatches in unit operations.

- UnitConversionError: Raised when unit conversion fails. Occurs when attempting to convert
  between incompatible unit types or when a unit is not supported in the conversion factor table.

- UnitAliasError: Raised when unit alias parsing fails. Occurs when invalid unit alias
  strings are provided or when there are ambiguous unit abbreviations.

Solver-Related Exceptions:

- SolverRuntimeError: Base class for all solver-related runtime errors. This is the base
  class for all ballistic calculation errors and is typically not raised directly.

- ZeroFindingError: Raised when zero-finding algorithms fail to converge. Contains:
  - zero_finding_error: Error magnitude in feet
  - iterations_count: Number of iterations performed
  - last_barrel_elevation: Last computed barrel elevation (Angular instance)
  - reason: Specific reason for failure.  Enumerated reasons:
    - DISTANCE_NON_CONVERGENT: Distance calculation not converging
    - ERROR_NON_CONVERGENT: Error not decreasing

- RangeError: Raised when trajectory doesn't reach the requested distance. Contains:
  - reason: Specific reason for range limitation.  Enumerated reasons:
    - MinimumVelocityReached: Projectile velocity dropped below threshold
    - MaximumDropReached: Projectile dropped below maximum allowed drop
    - MinimumAltitudeReached: Projectile altitude dropped below minimum
  - incomplete_trajectory: Trajectory data computed before failure
  - last_distance: Last distance reached before failure

- OutOfRangeError: Raised when requested distance exceeds maximum possible range. Contains:
  - requested_distance: The distance that was requested
  - max_range: Maximum achievable range (optional)
  - look_angle: Look angle for the shot (optional)
"""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from py_ballisticcalc.trajectory_data import TrajectoryData
    from py_ballisticcalc.unit import Angular, Distance

__all__ = (
    'UnitTypeError',
    'UnitConversionError',
    'UnitAliasError',
    'SolverRuntimeError',
    'OutOfRangeError',
    'ZeroFindingError',
    'RangeError',
)


class UnitTypeError(TypeError):
    """Unit type error."""


class UnitConversionError(UnitTypeError):
    """Unit conversion error."""


class UnitAliasError(ValueError):
    """Unit alias error."""


class SolverRuntimeError(RuntimeError):
    """Solver error."""


class ZeroFindingError(SolverRuntimeError):
    """Exception for zero-finding issues.

    Contains:
    - Zero finding error magnitude
    - Iteration count
    - Last barrel elevation (Angular instance)
    """

    DISTANCE_NON_CONVERGENT = "Distance non-convergent"
    ERROR_NON_CONVERGENT = "Error non-convergent"

    def __init__(self,
                 zero_finding_error: float,
                 iterations_count: int,
                 last_barrel_elevation: Angular,
                 reason: str = ""):
        """
        Parameters:
        - zero_finding_error: The error magnitude
        - iterations_count: The number of iterations performed
        - last_barrel_elevation: The last computed barrel elevation
        """
        self.zero_finding_error: float = zero_finding_error
        self.iterations_count: int = iterations_count
        self.last_barrel_elevation: Angular = last_barrel_elevation
        self.reason: str = reason
        msg = (f'Vertical error {zero_finding_error} '
               f'feet with {last_barrel_elevation} elevation, '
               f'after {iterations_count} iterations.')
        if reason:
            msg = f"{reason}. " + msg
        super().__init__(msg)


class RangeError(SolverRuntimeError):
    """Exception for trajectories that don't reach requested distance.

    Contains:
    - The error reason
    - The trajectory data before the exception occurred
    - Last distance before the exception occurred
    """

    reason: str
    incomplete_trajectory: List[TrajectoryData]
    last_distance: Optional[Distance]

    MinimumVelocityReached: str = "Minimum velocity reached"
    MaximumDropReached: str = "Maximum drop reached"
    MinimumAltitudeReached: str = "Minimum altitude reached"

    def __init__(self, reason: str, ranges: List[TrajectoryData]):
        """
        Parameters:
        - reason: The error reason
        - ranges: The trajectory data before the exception occurred
        """
        self.reason: str = reason
        self.incomplete_trajectory = ranges

        message = f'Max range not reached: ({self.reason})'
        if len(ranges) > 0:
            self.last_distance = ranges[-1].distance
            message += f', last distance: {self.last_distance}'
        else:
            self.last_distance = None
        super().__init__(message)


class OutOfRangeError(SolverRuntimeError):
    """Exception raised when the requested distance is outside the possible range for the shot.

    Contains:
    - The requested distance
    - Optionally, the maximum achievable range
    - Optionally, the look-angle
    """

    def __init__(self, requested_distance: Distance, max_range: Optional[Distance] = None,
                 look_angle: Optional[Angular] = None,
                 note: str = ""):
        self.requested_distance = requested_distance
        self.max_range = max_range
        self.look_angle = look_angle
        msg = f"Requested distance {requested_distance}"

        if max_range is not None:
            msg += f" exceeds maximum possible range {max_range._feet} feet"

        if look_angle is not None and look_angle.raw_value:
            msg += f" with look-angle {look_angle._rad} rad"

        if note:
            msg += f". {note}"
        super().__init__(msg)
