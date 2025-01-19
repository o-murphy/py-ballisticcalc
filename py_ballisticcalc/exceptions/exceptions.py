"""py_ballisticcalc exception types"""
from typing_extensions import List, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from py_ballisticcalc.unit import Angular, Distance  # Only for type checking
    from py_ballisticcalc.trajectory_data import TrajectoryData

__all__ = (
    'UnitTypeError',
    'UnitConversionError',
    'UnitAliasError',
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
                 last_barrel_elevation: 'Angular'):
        """
        Parameters:
        - zero_finding_error: The error magnitude (float)
        - iterations_count: The number of iterations performed (int)
        - last_barrel_elevation: The last computed barrel elevation (Angular)
        """
        self.zero_finding_error: float = zero_finding_error
        self.iterations_count: int = iterations_count
        self.last_barrel_elevation: 'Angular' = last_barrel_elevation
        super().__init__(f'Zero vertical error {zero_finding_error} '
                         f'feet, after {iterations_count} iterations.')


class RangeError(RuntimeError):
    """
    Exception for zero-finding issues.
    Contains:
    - The error reason
    - The trajectory data before the exception occurred
    - Last distance before the exception occurred
    """

    reason: str
    incomplete_trajectory: List['TrajectoryData']
    last_distance: Union['Distance', None]

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
