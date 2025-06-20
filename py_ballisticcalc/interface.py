"""Implements basic interface for the ballistics calculator"""
from dataclasses import dataclass, field
from importlib.metadata import entry_points, EntryPoint
from typing import Generic

from typing_extensions import Union, List, Optional, TypeVar, Type

from py_ballisticcalc import EulerIntegrationEngine, BaseEngineConfigDict
# pylint: disable=import-error,no-name-in-module,wildcard-import
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import HitResult
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits

ConfigT = TypeVar('ConfigT', bound=BaseEngineConfigDict, covariant=True)

DEFAULT_ENTRY_SUFFIX = '_engine'
DEFAULT_ENTRY_GROUP = 'py_ballisticcalc'
DEFAULT_ENTRY: Type[EngineProtocol[ConfigT]] = EulerIntegrationEngine


@dataclass
class _EngineLoader:
    _entry_point_group = DEFAULT_ENTRY_GROUP
    _entry_point_suffix = DEFAULT_ENTRY_SUFFIX

    @classmethod
    def _get_entries_by_group(cls):
        all_entry_points = entry_points()
        if hasattr(all_entry_points, 'select'):  # for importlib >= 5
            ballistic_entry_points = all_entry_points.select(group=cls._entry_point_group)
        elif hasattr(all_entry_points, 'get'):  # for importlib < 5
            ballistic_entry_points = all_entry_points.get(cls._entry_point_group, [])
        else:
            raise RuntimeError('Entry point not supported')
        return set(ballistic_entry_points)

    @classmethod
    def iter_engines(cls):
        ballistic_entry_points = cls._get_entries_by_group()
        for ep in ballistic_entry_points:
            if ep.name.endswith(cls._entry_point_suffix):
                yield ep

    @classmethod
    def _load_from_entry(cls, ep: EntryPoint) -> Optional[Type[EngineProtocol[ConfigT]]]:
        try:
            handle: Type[EngineProtocol[ConfigT]] = ep.load()
            if not isinstance(handle, EngineProtocol):
                raise TypeError(f"Unsupported engine type {ep.value}, must implements EngineProtocol")
            logger.info(f"Loaded calculator from: {ep.value} (Class: {handle})")
            return handle
        except ImportError as e:
            logger.error(f"Error loading engine from {ep.value}: {e}")
        except AttributeError as e:
            logger.error(f"Error loading attribute from {ep.value}: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred loading {ep.value}: {e}")
        return None

    @classmethod
    def load(cls, entry_point: Union[str, Type[EngineProtocol[ConfigT]], None] = DEFAULT_ENTRY) -> Type[
        EngineProtocol[ConfigT]]:
        if entry_point is None:
            entry_point = DEFAULT_ENTRY
        if isinstance(entry_point, EngineProtocol):
            return entry_point
        if isinstance(entry_point, str):
            handle: Optional[Type[EngineProtocol[ConfigT]]] = None
            for ep in cls.iter_engines():
                if ep.name == entry_point or entry_point in ep.value:
                    if handle := cls._load_from_entry(ep):
                        logger.info(f"Loaded calculator from: {ep.value} (Class: {handle})")
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
    """Basic interface for the ballistics calculator"""

    config: Optional[ConfigT] = field(default=None)
    engine: Union[str, Type[EngineProtocol[ConfigT]]] = field(default=DEFAULT_ENTRY)
    _engine_instance: EngineProtocol[ConfigT] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        engine: Type[EngineProtocol[ConfigT]] = _EngineLoader.load(self.engine)
        self._engine_instance = engine(self.config)

    @property
    def cdm(self) -> List[DragDataPoint]:
        """returns custom drag function based on input data"""
        return self._engine_instance.table_data

    def barrel_elevation_for_target(self, shot: Shot, target_distance: Union[float, Distance]) -> Angular:
        """Calculates barrel elevation to hit target at zero_distance.
        :param shot: Shot instance for which calculate barrel elevation is
        :param target_distance: Look-distance to "zero," which is point we want to hit.
            This is the distance that a rangefinder would return with no ballistic adjustment.
            NB: Some rangefinders offer an adjusted distance based on inclinometer measurement.
                However, without a complete ballistic model these can only approximate the effects
                on ballistic trajectory of shooting uphill or downhill.  Therefore:
                For maximum accuracy, use the raw sight distance and look_angle as inputs here.
        """
        target_distance = PreferredUnits.distance(target_distance)
        total_elevation = self._engine_instance.zero_angle(shot, target_distance)
        return Angular.Radian(
            (total_elevation >> Angular.Radian) - (shot.look_angle >> Angular.Radian)
        )

    def set_weapon_zero(self, shot: Shot, zero_distance: Union[float, Distance]) -> Angular:
        """Sets shot.weapon.zero_elevation so that it hits a target at zero_distance.
        :param shot: Shot instance from which we take a zero
        :param zero_distance: Look-distance to "zero," which is point we want to hit.
        """
        shot.weapon.zero_elevation = self.barrel_elevation_for_target(shot, zero_distance)
        return shot.weapon.zero_elevation

    def fire(self, shot: Shot, trajectory_range: Union[float, Distance],
             trajectory_step: Union[float, Distance] = 0,
             extra_data: bool = False,
             time_step: float = 0.0) -> HitResult:
        """Calculates trajectory
        :param shot: shot parameters (initial position and barrel angle)
        :param trajectory_range: Downrange distance at which to stop computing trajectory
        :param trajectory_step: step between trajectory points to record
        :param extra_data: True => store TrajectoryData for every calculation step;
            False => store TrajectoryData only for each trajectory_step
        :param time_step: (seconds) If > 0 then record TrajectoryData at least this frequently
        """
        trajectory_range = PreferredUnits.distance(trajectory_range)
        if not trajectory_step:
            # need to use raw value in order to avoid unit conversion
            trajectory_step = trajectory_range.raw_value / 10.0
            # default unit for distance is Inch, therefore, specifying value directly in it
            step: Distance = Distance.Inch(trajectory_step)
        else:
            step = PreferredUnits.distance(trajectory_step)
        data = self._engine_instance.trajectory(shot, trajectory_range, step, extra_data, time_step)
        return HitResult(shot, data, extra_data)

    @staticmethod
    def iter_engines():
        yield from _EngineLoader.iter_engines()


__all__ = ('Calculator', '_EngineLoader',)
