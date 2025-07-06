"""py_ballisticcalc exception types"""
from typing_extensions import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from py_ballisticcalc.trajectory_data import TrajectoryData
    from py_ballisticcalc.unit import Angular, Distance

__all__ = (
    'UnitTypeError',
    'UnitConversionError',
    'UnitAliasError',
    'OutOfRangeError',
    'ZeroFindingError',
    'RangeError',
)


class UnitTypeError(TypeError):
    """Unit type error"""


class UnitConversionError(UnitTypeError):
    """Unit conversion error"""


class UnitAliasError(ValueError):
    """Unit alias error"""


class ZeroFindingError(RuntimeError):
    """
    Exception for zero-finding issues.
    Contains:
    - Zero finding error magnitude
    - Iteration count
    - Last barrel elevation (Angular instance)
    """

    def __init__(self,
                 zero_finding_error: float,
                 iterations_count: int,
                 last_barrel_elevation: 'Angular',
                 note: str = ""):
        """
        Parameters:
        - zero_finding_error: The error magnitude (float)
        - iterations_count: The number of iterations performed (int)
        - last_barrel_elevation: The last computed barrel elevation (Angular)
        """
        self.zero_finding_error: float = zero_finding_error
        self.iterations_count: int = iterations_count
        self.last_barrel_elevation: 'Angular' = last_barrel_elevation
        self.note: str = note
        super().__init__(note + f' Vertical error {zero_finding_error} '
            f'feet with {last_barrel_elevation} elevation, after {iterations_count} iterations.')


class RangeError(RuntimeError):
    """
    Exception for trajectories that don't reach requested distance.
    Contains:
    - The error reason
    - The trajectory data before the exception occurred
    - Last distance before the exception occurred
    """
    reason: str
    incomplete_trajectory: List['TrajectoryData']
    last_distance: Optional['Distance']

    MinimumVelocityReached: str = "Minimum velocity reached"
    MaximumDropReached: str = "Maximum drop reached"
    MinimumAltitudeReached: str = "Minimum altitude reached"

    def __init__(self, reason: str, ranges: List['TrajectoryData']):
        """
        Parameters:
        - reason: The error reason (str)
        - trajectory: The trajectory data before
                    the exception occurred (List[TrajectoryData])
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


class OutOfRangeError(RuntimeError):
    """
    Exception raised when the requested distance is outside the possible range for the shot.
    Contains:
    - The requested distance
    - Optionally, the maximum achievable range
    - Optionally, the look-angle
    """
    def __init__(self, requested_distance: 'Distance', max_range: Optional['Distance'] = None, look_angle: Optional['Angular'] = None,
                 note: str = ""):
        from py_ballisticcalc.unit import PreferredUnits
        self.requested_distance = requested_distance
        self.max_range = max_range
        self.look_angle = look_angle
        msg = (f"Requested distance {requested_distance << PreferredUnits.distance}"
            + (f" exceeds maximum possible range {max_range << PreferredUnits.distance}" if max_range is not None else "")
            + (f" with look-angle {look_angle << PreferredUnits.angular}" if (look_angle is not None and look_angle.raw_value) else "")
            + (f". {note}" if note else "")
        )
        super().__init__(msg)
