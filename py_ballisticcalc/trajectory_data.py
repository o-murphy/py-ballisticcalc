"""Implements a point of trajectory class in applicable data types"""
import typing
from dataclasses import dataclass, field
from deprecated import deprecated
from typing_extensions import NamedTuple, Optional, Union, Tuple, Final

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.unit import Angular, Distance, Weight, Velocity, Energy, GenericDimension, Unit, PreferredUnits
from py_ballisticcalc.exceptions import RangeError

if typing.TYPE_CHECKING:
    from pandas import DataFrame
    from matplotlib.axes import Axes

__all__ = ('TrajectoryData', 'HitResult', 'TrajFlag', 'DangerSpace')

_TrajFlagNames = {
    0: 'NONE',
    1: 'ZERO_UP',
    2: 'ZERO_DOWN',
    3: 'ZERO',
    4: 'MACH',
    8: 'RANGE',
    16: 'APEX',
    32: 'MRT',  # Mid-Range Trajectory (a.k.a. Maximum Ordinate): highest point of trajectory over the sight line
    63: 'ALL',
}


class TrajFlag(int):
    """Flags for marking trajectory row if Zero or Mach crossing.
    Also used to set filters for a trajectory calculation loop.
    """
    NONE: Final[int] = 0
    ZERO_UP: Final[int] = 1
    ZERO_DOWN: Final[int] = 2
    ZERO: Final[int] = ZERO_UP | ZERO_DOWN
    MACH: Final[int] = 4
    RANGE: Final[int] = 8
    APEX: Final[int] = 16
    MRT: Final[int] = 32
    ALL: Final[int] = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX | MRT

    @staticmethod
    def name(value: Union[int, 'TrajFlag']) -> str:
        """Return a concatenated name representation of the given flag value."""
        if value in _TrajFlagNames:
            return _TrajFlagNames[value]

        parts = [name for bit, name in _TrajFlagNames.items() if bit and (value & bit) == bit]
        if "ZERO_UP" in parts and "ZERO_DOWN" in parts:
            parts.remove("ZERO_UP")
            parts.remove("ZERO_DOWN")
        return "|".join(parts) if parts else "UNKNOWN"


class TrajectoryData(NamedTuple):
    """
    Data for one point in ballistic trajectory.

    Attributes:
        time (float): Bullet flight time in seconds.
        distance (Distance): Down-range (x-axis) coordinate of this point.
        velocity (Velocity): Velocity.
        mach (float): Velocity in Mach terms.
        height (Distance): Vertical (y-axis) coordinate of this point.
        slant_height (Distance): Distance orthogonal to sight-line
        drop_adj (Angular): Sight adjustment to zero slant_height at this distance.
        windage (Distance): Windage (z-axis) coordinate of this point.
        windage_adj (Angular): Windage adjustment.
        slant_distance (Distance): Distance along sight line that is closest to this point.
        angle (Angular): Angle of velocity vector relative to x-axis.
        density_ratio (float): Ratio of air density here to standard density.
        drag (float): Standard Drag Factor at this point.
        energy (Energy): Energy of bullet at this point.
        ogw (Weight): Optimal game weight, given .energy.
        flag (Union[TrajFlag, int]): Row type.
    """

    time: float
    distance: Distance
    velocity: Velocity
    mach: float
    height: Distance
    slant_height: Distance
    drop_adj: Angular
    windage: Distance
    windage_adj: Angular
    slant_distance: Distance
    angle: Angular
    density_ratio: float
    drag: float
    energy: Energy
    ogw: Weight
    flag: Union[TrajFlag, int]

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


class DangerSpace(NamedTuple):
    """Stores the danger space data for distance specified.

    Attributes:
        at_range (TrajectoryData): Trajectory data at the specified range.
        target_height (Distance): Target height.
        begin (TrajectoryData): Beginning of danger space.
        end (TrajectoryData): End of danger space.
        look_angle (Angular): Slant angle.
    """
    at_range: TrajectoryData
    target_height: Distance
    begin: TrajectoryData
    end: TrajectoryData
    look_angle: Angular

    def __str__(self) -> str:
        return f'Danger space at {self.at_range.distance << PreferredUnits.distance} ' \
            + f'for {self.target_height << PreferredUnits.drop} tall target ' \
            + (f'at {self.look_angle << Angular.Degree} look-angle ' if self.look_angle != 0 else '') \
            + f'ranges from {self.begin.distance << PreferredUnits.distance} ' \
            + f'to {self.end.distance << PreferredUnits.distance}'

    # pylint: disable=import-outside-toplevel
    def overlay(self, ax: 'Axes', label: Optional[str] = None):  # type: ignore
        """Highlights danger-space region on plot.

        Args:
            ax (Axes): The axes to overlay on.
            label (Optional[str], optional): Label for the overlay. Defaults to None.

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
        shot (Shot): The shot conditions.
        trajectory (list[TrajectoryData]): The trajectory data.
        extra (bool): Whether special points (TrajFlag > 0) were requested.
    """
    shot: Shot
    trajectory: list[TrajectoryData] = field(repr=False)
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

    def zeros(self) -> list[TrajectoryData]:
        """
        Returns:
            list[TrajectoryData]: Zero crossing points.

        Raises:
            AttributeError: If extra_data was not requested.
            ArithmeticError: If zero crossing points are not found.
        """
        self.__check_extra__()
        data = [row for row in self.trajectory if row.flag & TrajFlag.ZERO]
        if len(data) < 1:
            raise ArithmeticError("Can't find zero crossing points")
        return data

    def flag(self, flag: Union[TrajFlag, int]) -> Optional[TrajectoryData]:
        """
        Returns:
            TrajectoryData: Trajectory row with the specified flag.

        Raises:
            AttributeError: If extra_data was not requested.
        """
        self.__check_extra__()
        for row in self.trajectory:
            if row.flag & flag:
                return row
        return None

    def index_at_distance(self, d: Distance) -> int:
        """
        Args:
            d (Distance): Distance for which we want Trajectory Data.

        Returns:
            int: Index of first trajectory row with .distance >= d; otherwise -1.
        """
        epsilon = 1e-1  # small value to avoid floating point issues
        return next((i for i in range(len(self.trajectory))
                     if self.trajectory[i].distance.raw_value >= d.raw_value - epsilon), -1)

    def get_at_distance(self, d: Distance) -> TrajectoryData:
        """
        Args:
            d (Distance): Distance for which we want Trajectory Data.

        Returns:
            TrajectoryData: First trajectory row with .distance >= d.

        Raises:
            ArithmeticError: If trajectory doesn't reach requested distance.
        """
        if (i := self.index_at_distance(d)) < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested distance {d}"
            )
        return self.trajectory[i]

    def get_at_time(self, t: float) -> TrajectoryData:
        """
        Args:
            t (float): Time for which we want Trajectory Data.

        Returns:
            TrajectoryData: First trajectory row with .time >= t.

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
                     look_angle: Optional[Union[float, Angular]] = None
                     ) -> DangerSpace:
        """
        Calculates the danger space for a given range and target height.

        Assumes that the trajectory hits the center of a target at any distance.
        Determines how much ranging error can be tolerated if the critical region
        of the target has height *h*. Finds how far forward and backward along the
        line of sight a target can move such that the trajectory is still within *h*/2
        of the original drop.

        Args:
            at_range (Union[float, Distance]): Danger space is calculated for a target centered at this sight distance.
            target_height (Union[float, Distance]): Target height (*h*) determines danger space.
            look_angle (Optional[Union[float, Angular]], optional): Ranging errors occur along the look angle to the target.

        Returns:
            DangerSpace: The calculated danger space.

        Raises:
            AttributeError: If extra_data wasn't requested.
            ArithmeticError: If trajectory doesn't reach requested distance.
        """
        self.__check_extra__()

        at_range = PreferredUnits.distance(at_range)
        target_height = PreferredUnits.distance(target_height)
        target_height_half = target_height.raw_value / 2.0

        _look_angle: Angular
        if look_angle is None:
            _look_angle = self.shot.look_angle
        else:
            _look_angle = PreferredUnits.angular(look_angle)

        # Get index of first trajectory point with distance >= at_range
        if (index := self.index_at_distance(at_range)) < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested distance {at_range}"
            )

        def find_begin_danger(row_num: int) -> TrajectoryData:
            """
            Beginning of danger space is last .distance' < .distance where
                (.drop' - target_center) >= target_height/2

            Args:
                row_num (int): Index of the trajectory point for which we are calculating danger space.

            Returns:
                TrajectoryData: Distance marking beginning of danger space.
            """
            center_row = self.trajectory[row_num]
            for prime_row in reversed(self.trajectory[:row_num]):
                if (prime_row.slant_height.raw_value - center_row.slant_height.raw_value) >= target_height_half:
                    return prime_row
            return self.trajectory[0]

        def find_end_danger(row_num: int) -> TrajectoryData:
            """
            End of danger space is first .distance' > .distance where
                (target_center - .drop') >= target_height/2

            Args:
                row_num (int): Index of the trajectory point for which we are calculating danger space.

            Returns:
                TrajectoryData: Distance marking end of danger space.
            """
            center_row = self.trajectory[row_num]
            for prime_row in self.trajectory[row_num + 1:]:
                if (center_row.slant_height.raw_value - prime_row.slant_height.raw_value) >= target_height_half:
                    return prime_row
            return self.trajectory[-1]

        return DangerSpace(self.trajectory[index],
                           target_height,
                           find_begin_danger(index),
                           find_end_danger(index),
                           _look_angle)

    def dataframe(self, formatted: bool = False) -> 'DataFrame':  # type: ignore
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

    def plot(self, look_angle: Optional[Angular] = None) -> 'Axes':  # type: ignore
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
