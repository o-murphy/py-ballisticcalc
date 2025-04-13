"""Implements a point of trajectory class in applicable data types"""
from dataclasses import dataclass, field

from typing_extensions import NamedTuple, Optional, Union, Any, Tuple, Final

from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.unit import Angular, Distance, Weight, Velocity, Energy, AbstractDimension, Unit, PreferredUnits

__all__ = ('TrajectoryData', 'HitResult', 'TrajFlag', 'DangerSpace')

DataFrame: Any
Axes: Any

_TrajFlagNames = {
    0: 'NONE',
    1: 'ZERO_UP',
    2: 'ZERO_DOWN',
    3: 'ZERO',
    4: 'MACH',
    8: 'RANGE',
    16: 'APEX',
    31: 'ALL',
}


class TrajFlag(int):
    """Flags for marking trajectory row if Zero or Mach crossing
    Also uses to set a filters for a trajectory calculation loop
    """
    NONE: Final[int] = 0
    ZERO_UP: Final[int] = 1
    ZERO_DOWN: Final[int] = 2
    ZERO: Final[int] = ZERO_UP | ZERO_DOWN
    MACH: Final[int] = 4
    RANGE: Final[int] = 8
    APEX: Final[int] = 16
    ALL: Final[int] = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX

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
    Data for one point in ballistic trajectory

    Attributes:
        time (float): bullet flight time
        distance (Distance): x-axis coordinate
        velocity (Velocity): velocity
        mach (float): velocity in Mach prefer_units
        height (Distance): y-axis coordinate
        target_drop (Distance): drop relative to sight-line
        drop_adj (Angular): sight adjustment to zero target_drop at this distance
        windage (Distance):
        windage_adj (Angular):
        look_distance (Distance): sight-line distance = .distance/cosine(look_angle)
        # look_height (Distance): y-coordinate of sight-line = .distance*tan(look_angle)
        angle (Angular): Angle of velocity vector relative to x-axis
        density_factor (float): Ratio of air density here to standard density
        drag (float): Current drag coefficient
        energy (Energy):
        ogw (Weight): optimal game weight
        flag (Union[TrajFlag, int]): row type
    """

    time: float
    distance: Distance
    velocity: Velocity
    mach: float
    height: Distance
    target_drop: Distance
    drop_adj: Angular
    windage: Distance
    windage_adj: Angular
    look_distance: Distance
    angle: Angular
    density_factor: float
    drag: float
    energy: Energy
    ogw: Weight
    flag: Union[TrajFlag, int]

    def formatted(self) -> Tuple[str, ...]:
        """
        :return: matrix of formatted strings for each value of trajectory in default prefer_units
        """

        def _fmt(v: AbstractDimension, u: Unit) -> str:
            """simple formatter"""
            return f"{v >> u:.{u.accuracy}f} {u.symbol}"

        return (
            f'{self.time:.3f} s',
            _fmt(self.distance, PreferredUnits.distance),
            _fmt(self.velocity, PreferredUnits.velocity),
            f'{self.mach:.2f} mach',
            _fmt(self.height, PreferredUnits.drop),
            _fmt(self.target_drop, PreferredUnits.drop),
            _fmt(self.drop_adj, PreferredUnits.adjustment),
            _fmt(self.windage, PreferredUnits.drop),
            _fmt(self.windage_adj, PreferredUnits.adjustment),
            _fmt(self.look_distance, PreferredUnits.distance),
            _fmt(self.angle, PreferredUnits.angular),
            f'{self.density_factor:.3e}',
            f'{self.drag:.3f}',
            _fmt(self.energy, PreferredUnits.energy),
            _fmt(self.ogw, PreferredUnits.ogw),

            TrajFlag.name(self.flag)
        )

    def in_def_units(self) -> Tuple[float, ...]:
        """
        :return: matrix of floats of the trajectory in default prefer_units
        """
        return (
            self.time,
            self.distance >> PreferredUnits.distance,
            self.velocity >> PreferredUnits.velocity,
            self.mach,
            self.height >> PreferredUnits.drop,
            self.target_drop >> PreferredUnits.drop,
            self.drop_adj >> PreferredUnits.adjustment,
            self.windage >> PreferredUnits.drop,
            self.windage_adj >> PreferredUnits.adjustment,
            self.look_distance >> PreferredUnits.distance,
            self.angle >> PreferredUnits.angular,
            self.density_factor,
            self.drag,
            self.energy >> PreferredUnits.energy,
            self.ogw >> PreferredUnits.ogw,
            self.flag
        )


class DangerSpace(NamedTuple):
    """Stores the danger space data for distance specified"""
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
        """Highlights danger-space region on plot"""
        try:
            from py_ballisticcalc.visualize.plot import add_danger_space_overlay  # type: ignore
            add_danger_space_overlay(self, ax, label)
        except ImportError as err:
            raise ImportError(
                "Use `pip install py_ballisticcalc[charts]` to get results as a plot"
            ) from err


@dataclass(frozen=True)
class HitResult:
    """Results of the shot"""
    shot: Shot
    trajectory: list[TrajectoryData] = field(repr=False)
    extra: bool = False

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
        """:return: zero crossing points"""
        self.__check_extra__()
        data = [row for row in self.trajectory if row.flag & TrajFlag.ZERO]
        if len(data) < 1:
            raise ArithmeticError("Can't find zero crossing points")
        return data

    def index_at_distance(self, d: Distance) -> int:
        """
        :param d: Distance for which we want Trajectory Data
        :return: Index of first trajectory row with .distance >= d; otherwise -1
        """
        # Get index of first trajectory point with distance >= at_range
        return next((i for i in range(len(self.trajectory))
                     if self.trajectory[i].distance >= d), -1)

    def get_at_distance(self, d: Distance) -> TrajectoryData:
        """
        :param d: Distance for which we want Trajectory Data
        :return: First trajectory row with .distance >= d
        """
        if (i := self.index_at_distance(d)) < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested distance {d}"
            )
        return self.trajectory[i]

    # pylint: disable=import-outside-toplevel
    def danger_space(self,
                     at_range: Union[float, Distance],
                     target_height: Union[float, Distance],
                     look_angle: Optional[Union[float, Angular]] = None
                     ) -> DangerSpace:
        """
        Assume that the trajectory hits the center of a target at any distance.
        Now we want to know how much ranging error we can tolerate if the critical region
        of the target has height *h*.  I.e., we want to know how far forward and backward
        along the line of sight we can move a target such that the trajectory is still
        within *h*/2 of the original drop.

        :param at_range: Danger space is calculated for a target centered at this sight distance
        :param target_height: Target height (*h*) determines danger space
        :param look_angle: Ranging errors occur along the look angle to the target
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
            :param row_num: Index of the trajectory point for which we are calculating danger space
            :return: Distance marking beginning of danger space
            """
            center_row = self.trajectory[row_num]
            for prime_row in reversed(self.trajectory[:row_num]):
                if (prime_row.target_drop.raw_value - center_row.target_drop.raw_value) >= target_height_half:
                    return prime_row
            return self.trajectory[0]

        def find_end_danger(row_num: int) -> TrajectoryData:
            """
            End of danger space is first .distance' > .distance where
                (target_center - .drop') >= target_height/2
            :param row_num: Index of the trajectory point for which we are calculating danger space
            :return: Distance marking end of danger space
            """
            center_row = self.trajectory[row_num]
            for prime_row in self.trajectory[row_num + 1:]:
                if (center_row.target_drop.raw_value - prime_row.target_drop.raw_value) >= target_height_half:
                    return prime_row
            return self.trajectory[-1]

        return DangerSpace(self.trajectory[index],
                           target_height,
                           find_begin_danger(index),
                           find_end_danger(index),
                           _look_angle)

    # pylint: disable=import-outside-toplevel
    def dataframe(self, formatted: bool = False) -> 'DataFrame':  # type: ignore
        """
        :param formatted: False for values as floats; True for strings with prefer_units
        :return: the trajectory table as a DataFrame
        """
        try:
            from py_ballisticcalc.visualize.dataframe import hit_result_as_dataframe
            return hit_result_as_dataframe(self, formatted)
        except ImportError as err:
            raise ImportError(
                "Use `pip install py_ballisticcalc[charts]` to get trajectory as pandas.DataFrame"
            )from err

    # pylint: disable=import-outside-toplevel
    def plot(self, look_angle: Optional[Angular] = None) -> 'Axes':  # type: ignore
        """:return: graph of the trajectory"""
        try:
            from py_ballisticcalc.visualize.plot import hit_result_as_plot  # type: ignore
            return hit_result_as_plot(self, look_angle)
        except ImportError as err:
            raise ImportError(
                "Use `pip install py_ballisticcalc[charts]` to get results as a plot"
            ) from err
