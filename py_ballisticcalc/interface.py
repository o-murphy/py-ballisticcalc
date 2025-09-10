"""Ballistics calculator interface and engine loading system.

This module provides the main `Calculator` class that serves as the primary interface
for ballistic trajectory calculations. It implements a plugin-based architecture
that can dynamically load different integration engines through Python entry points.
The module relies on the EngineProtocol to ensure that engines offer the necessary methods.

Key Classes:
    - Calculator: Main ballistics calculator with pluggable engine support
    - _EngineLoader: Internal utility for discovering and loading engine plugins
"""
from dataclasses import dataclass, field
from importlib.metadata import entry_points, EntryPoint
from typing import Generic, Any
import warnings

from deprecated import deprecated
from typing_extensions import Union, List, Optional, TypeVar, Type, Generator

from py_ballisticcalc import RK4IntegrationEngine
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits

ConfigT = TypeVar('ConfigT', covariant=True)

DEFAULT_ENTRY_SUFFIX = '_engine'
DEFAULT_ENTRY_GROUP = 'py_ballisticcalc'
DEFAULT_ENTRY: Type[EngineProtocol] = RK4IntegrationEngine

EngineProtocolType = Type[EngineProtocol[ConfigT]]
EngineProtocolEntry = Union[str, EngineProtocolType, None]


@dataclass
class _EngineLoader:
    _entry_point_group = DEFAULT_ENTRY_GROUP
    _entry_point_suffix = DEFAULT_ENTRY_SUFFIX

    @classmethod
    def _get_entries_by_group(cls) -> set:
        all_entry_points = entry_points()
        if hasattr(all_entry_points, 'select'):  # for importlib >= 5
            ballistic_entry_points = all_entry_points.select(group=cls._entry_point_group)
        elif hasattr(all_entry_points, 'get'):  # for importlib < 5
            ballistic_entry_points = all_entry_points.get(cls._entry_point_group, [])  # type: ignore[arg-type]
        else:
            raise RuntimeError('Entry point not supported')
        return set(ballistic_entry_points)

    @classmethod
    def iter_engines(cls) -> Generator[EntryPoint, None, None]:
        """Iterate over all available engines in the entry points."""
        ballistic_entry_points = cls._get_entries_by_group()
        for ep in ballistic_entry_points:
            if ep.name.endswith(cls._entry_point_suffix):
                yield ep

    @classmethod
    def _load_from_entry(cls, ep: EntryPoint) -> Optional[EngineProtocolType]:
        try:
            handle: EngineProtocolType = ep.load()
            if not isinstance(handle, EngineProtocol):
                raise TypeError(f"Unsupported engine {ep.value} does not implement EngineProtocol")
            logger.info(f"Loaded calculator from: {ep.value} (Class: {handle})")
            return handle  # type: ignore
        except ImportError as e:
            logger.error(f"Error loading engine from {ep.value}: {e}")
        except AttributeError as e:
            logger.error(f"Error loading attribute from {ep.value}: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred loading {ep.value}: {e}")
        return None

    @classmethod
    def load(cls, entry_point: EngineProtocolEntry = DEFAULT_ENTRY) -> Type[EngineProtocol[Any]]:
        if entry_point is None:
            entry_point = DEFAULT_ENTRY
        if isinstance(entry_point, EngineProtocol):
            return entry_point  # type: ignore
        if isinstance(entry_point, str):
            handle: Optional[EngineProtocolType] = None
            for ep in cls.iter_engines():
                if ep.name == entry_point:
                    if handle := cls._load_from_entry(ep):
                        return handle

            if not handle:
                ep = EntryPoint(entry_point, entry_point, cls._entry_point_group)
                if handle := cls._load_from_entry(ep):
                    logger.info(f"Loaded calculator from: {ep.value} (Class: {handle})")
                    return handle
            raise ValueError(f"No 'engine' entry point found containing '{entry_point}'")
        raise TypeError("Invalid entry_point type, expected 'str' or 'EngineProtocol'")


@dataclass
class Calculator(Generic[ConfigT]):
    """Basic interface for the ballistics calculator."""

    config: Optional[ConfigT] = field(default=None)
    engine: EngineProtocolEntry = field(default=DEFAULT_ENTRY)
    _engine_instance: EngineProtocol[Any] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._engine_instance = _EngineLoader.load(self.engine)(self.config)

    def __getattr__(self, item: str) -> Any:
        """Delegate attribute access to the underlying engine instance.

        This method is called when an attribute is requested on the `Calculator`
        instance that is not found through normal attribute lookup (i.e., it's
        not a direct attribute of `Calculator` or its class). It then attempts
        to retrieve the attribute from the `_engine_instance`.

        Args:
            item: The name of the attribute to retrieve.

        Returns:
            Any: The value of the attribute from `_engine_instance`.

        Raises:
            AttributeError: If the attribute is not found on either the
                `Calculator` object or its `_engine_instance`.

        Examples:
            >>> calc = Calculator(engine=DEFAULT_ENTRY)
            >>> calc_step = calc.get_calc_step()
            >>> print(calc_step)
            0.0025
            >>> try:
            ...     calc.unknown_method()
            ... except AttributeError as e:
            ...     print(e)
            'Calculator' object or its underlying engine 'RK4IntegrationEngine' has no attribute 'unknown_method'
        """
        if hasattr(self._engine_instance, item):
            return getattr(self._engine_instance, item)
        raise AttributeError(
            f"'{self.__class__.__name__}' object or its underlying engine "
            f"'{self._engine_instance.__class__.__name__}' has no attribute '{item}'"
        )

    @property
    @deprecated(reason="`Calculator.cdm` is no longer supported by EngineProtocol. "
                       "Please use `DragModel.drag_table` instead.")
    def cdm(self) -> List[DragDataPoint]:
        """Return custom drag function based on input data."""
        raise NotImplementedError("`Calculator.cdm` is no longer supported by EngineProtocol. "
                                  "Please use `DragModel.drag_table` instead.")

    def barrel_elevation_for_target(self, shot: Shot, target_distance: Union[float, Distance]) -> Angular:
        """Calculate barrel elevation to hit target at zero_distance.
        
        Args:
            shot: Shot instance we want to zero.
            target_distance: Look-distance to "zero," which is point we want to hit.
                This is the distance that a rangefinder would return with no ballistic adjustment.
                
        Note:
            Some rangefinders offer an adjusted distance based on inclinometer measurement.
            However, without a complete ballistic model these can only approximate the effects
            on ballistic trajectory of shooting uphill or downhill. Therefore:
            For maximum accuracy, use the raw sight distance and look_angle as inputs here.
        """
        target_distance = PreferredUnits.distance(target_distance)
        total_elevation = self._engine_instance.zero_angle(shot, target_distance)
        return Angular.Radian(
            (total_elevation >> Angular.Radian) - (shot.look_angle >> Angular.Radian)
        )

    def set_weapon_zero(self, shot: Shot, zero_distance: Union[float, Distance]) -> Angular:
        """Set shot.weapon.zero_elevation so that it hits a target at zero_distance.
        
        Args:
            shot: Shot instance to zero.
            zero_distance: Look-distance to "zero," which is point we want to hit.
        """
        shot.weapon.zero_elevation = self.barrel_elevation_for_target(shot, zero_distance)
        return shot.weapon.zero_elevation

    def fire(self, shot: Shot,
             trajectory_range: Union[float, Distance],
             trajectory_step: Optional[Union[float, Distance]] = None, *,
             extra_data: bool = False,
             dense_output: bool = False,
             time_step: float = 0.0,
             flags: Union[TrajFlag, int] = TrajFlag.NONE,
             raise_range_error: bool = True) -> HitResult:
        """Calculate the trajectory for the given shot parameters.

        Args:
            shot: Shot parameters, including position and barrel angle.
            trajectory_range: Distance at which to stop computing the trajectory.
            trajectory_step: Distance between recorded trajectory points. Defaults to `trajectory_range`.
            extra_data: [DEPRECATED] Requests flags=TrajFlags.ALL and trajectory_step=PreferredUnits.distance(1).
            dense_output: HitResult stores all calculation steps so it can interpolate any point.
            time_step: Maximum time between recorded points. If > 0, points are recorded at least this frequently.
                       Defaults to 0.0.
            flags: Flags for specific points of interest. Defaults to TrajFlag.NONE.
            raise_range_error: If True, raises RangeError if returned by integration.

        Returns:
            HitResult: Object containing computed trajectory.
        """
        trajectory_range = PreferredUnits.distance(trajectory_range)
        dist_step = trajectory_range
        filter_flags = flags
        if trajectory_step:
            dist_step = PreferredUnits.distance(trajectory_step)
            filter_flags |= TrajFlag.RANGE
            if dist_step.raw_value > trajectory_range.raw_value:
                dist_step = trajectory_range

        if extra_data:
            warnings.warn("extra_data is deprecated and will be removed in future versions. "
                "Explicitly specify desired TrajectoryData frequency and flags.",
                DeprecationWarning
            )
            dist_step = PreferredUnits.distance(1.0)  # << For compatibility with v2.1
            filter_flags = TrajFlag.ALL

        result = self._engine_instance.integrate(shot, trajectory_range, dist_step, time_step,
                                                 filter_flags, dense_output=dense_output)
        if result.error and raise_range_error:
            raise result.error
        return result

    @staticmethod
    def iter_engines() -> Generator[EntryPoint, None, None]:
        """Iterate all available engines in the entry points."""
        yield from _EngineLoader.iter_engines()


__all__ = ('Calculator', '_EngineLoader',)
