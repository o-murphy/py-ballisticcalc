"""Ballistics calculator interface and engine loading system.

This module provides the main `Calculator` class that serves as the primary interface
for ballistic trajectory calculations. It implements a plugin-based architecture
that can dynamically load different integration engines through Python entry points.
The module relies on the EngineProtocol to ensure that engines offer the necessary methods.

Key Classes:
    - Calculator: Main ballistics calculator with pluggable engine support
    - _EngineLoader: Internal utility for discovering and loading engine plugins
"""

from collections.abc import Set
from dataclasses import dataclass
from importlib.metadata import entry_points, EntryPoint
from types import TracebackType
from typing import TypeVar, Generator, Any, overload
import warnings

from typing_extensions import Self

from py_ballisticcalc import RK4IntegrationEngine
from py_ballisticcalc.generics.engine import EngineProtocol, EngineFactoryProtocol
from py_ballisticcalc.logger import logger
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import HitResult, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits

ConfigT = TypeVar("ConfigT")

EngineFactoryProtocolType = EngineFactoryProtocol[Any]
EngineFactoryProtocolEntry = str | EngineFactoryProtocolType | None

DEFAULT_ENTRY_SUFFIX = "_engine"
DEFAULT_ENTRY_GROUP = "py_ballisticcalc"
DEFAULT_ENTRY: EngineFactoryProtocolType = RK4IntegrationEngine


@dataclass
class _EngineLoader:
    _entry_point_group = DEFAULT_ENTRY_GROUP
    _entry_point_suffix = DEFAULT_ENTRY_SUFFIX

    @classmethod
    def _get_entries_by_group(cls) -> Set[EntryPoint]:
        all_entry_points = entry_points()
        if hasattr(all_entry_points, "select"):  # for importlib >= 5
            ballistic_entry_points = all_entry_points.select(group=cls._entry_point_group)
        elif hasattr(all_entry_points, "get"):  # for importlib < 5
            ballistic_entry_points = all_entry_points.get(cls._entry_point_group, [])  # type: ignore[arg-type]
        else:
            raise RuntimeError("Entry point not supported")
        return set(ballistic_entry_points)

    @classmethod
    def iter_engines(cls) -> Generator[EntryPoint, None, None]:
        """Iterate over all available engines in the entry points."""
        ballistic_entry_points = cls._get_entries_by_group()
        for ep in ballistic_entry_points:
            if ep.name.endswith(cls._entry_point_suffix):
                yield ep

    @classmethod
    def _load_from_entry(cls, ep: EntryPoint) -> EngineFactoryProtocolType | None:
        try:
            factory: EngineFactoryProtocolType = ep.load()
            if not isinstance(factory, EngineFactoryProtocol):
                raise TypeError(f"Unsupported engine {ep.value} does not implement EngineFactoryProtocol")
            logger.info(f"Loaded calculator from: {ep.value} (Class: {factory})")
            return factory  # type: ignore
        except ImportError as e:
            logger.error(f"Error loading engine from {ep.value}: {e}")
        except AttributeError as e:
            logger.error(f"Error loading attribute from {ep.value}: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred loading {ep.value}: {e}")
        return None

    @classmethod
    def load(cls, entry_point: EngineFactoryProtocolEntry = DEFAULT_ENTRY) -> EngineFactoryProtocolType:
        if entry_point is None:
            entry_point = DEFAULT_ENTRY
        if isinstance(entry_point, EngineFactoryProtocol):
            return entry_point  # type: ignore
        if isinstance(entry_point, str):
            factory: EngineFactoryProtocolType | None = None
            for ep in cls.iter_engines():
                if ep.name == entry_point:
                    if factory := cls._load_from_entry(ep):
                        return factory

            if not factory:
                ep = EntryPoint(entry_point, entry_point, cls._entry_point_group)
                if factory := cls._load_from_entry(ep):
                    logger.info(f"Loaded calculator from: {ep.value} (Class: {factory})")
                    return factory
            raise ValueError(f"No 'engine' entry point found containing '{entry_point}'")
        raise TypeError("Invalid entry_point type, expected 'str' or 'EngineFactoryProtocol'")


class Calculator:
    """The main interface for the ballistics calculator.

    This class provides thread-safe access to the underlying integration engines
    by creating a new, isolated engine instance for every method call.
    """

    config: Any | None
    engine: EngineFactoryProtocolEntry
    _engine_factory: EngineFactoryProtocol[Any]

    # Type-safe overloads
    @overload
    def __init__(
        self,
        *,
        config: ConfigT,
        engine: EngineFactoryProtocol[ConfigT],
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        config: Any = None,
        engine: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        config: Any = None,
        engine: EngineFactoryProtocolEntry = None,
    ) -> None:
        """
        Loads the engine class.

        Crucially: The engine instance is not created here. To ensure
        thread safety (especially in free-threaded Python), each method call
        must operate on a new, isolated engine instance.
        """
        self.config = config
        self.engine = engine
        self._engine_factory = _EngineLoader.load(self.engine)

    def __enter__(self) -> Self:
        """Enter the runtime context for this Calculator.

        Returns:
            Self: The Calculator instance.

        Example:
            >>> with Calculator(config, RK4IntegrationEngine) as calc:
            ...     result = calc.fire(shot, Distance.Meter(1000))
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the runtime context.

        This is a no-op as Calculator is stateless and thread-safe
        by design — each method call creates an isolated engine instance.

        Args:
            exc_type: Exception type if an exception was raised, None otherwise.
            exc_val: Exception instance if an exception was raised, None otherwise.
            exc_tb: Traceback if an exception was raised, None otherwise.
        """
        pass

    @property
    def _engine_instance(self) -> EngineProtocol:
        """
        Creates and returns a **fresh, isolated engine instance** upon every access.

        This implementation is the core mechanism for ensuring **thread safety** in the `Calculator` class,
        particularly essential in **free-threaded Python** (e.g., CPython with GIL disabled, Python 3.13+).

        ## Thread Safety Rationale

        Instead of using traditional **synchronization primitives** (like `threading.Lock`)
        to protect a single, shared engine instance, this method employs **isolation**.
        Since the underlying engine instances are not guaranteed to be thread-safe
        internally, generating a new instance for each operation ensures that
        **no two concurrent threads will ever modify the same engine object**. This
        approach eliminates race conditions without introducing the overhead or
        potential deadlocks associated with locking mechanisms.

        ## Performance Consideration

        Note: The **overall performance** of concurrent operations critically depends
        on the **initialization cost** of the underlying engine class (`self._engine_class`).
        If the engine's constructor performs extensive I/O, loads large data tables,
        or executes complex setup, repeated instantiation may introduce significant
        overhead. For optimal performance, the engine's initialization (`__init__`)
        should be designed to be as **lightweight** as possible.

        Returns:
            EngineProtocol[Any]: A new, single-use engine instance configured
                                 with the `Calculator`'s current settings.
        """
        return self._engine_factory(self.config)

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
        engine_instance = self._engine_instance
        if hasattr(engine_instance, item):
            return getattr(engine_instance, item)
        raise AttributeError(
            f"'{self.__class__.__name__}' object or its underlying engine "
            f"'{engine_instance.__class__.__name__}' has no attribute '{item}'"
        )

    def __getstate__(self):
        """
        Called by pickle for serialization.
        We only serialize the public fields required for reconstruction.
        We explicitly exclude the calculated fields like _engine_class
        to ensure proper re-initialization in the new process.
        """
        return {"config": self.config, "engine": self.engine}

    def __setstate__(self, state):
        """
        Called by pickle for deserialization.
        We manually set the fields and call __post_init__ to reload the engine class.
        """
        # Set the serialized fields
        self.config = state["config"]
        self.engine = state["engine"]
        # Manually run __post_init__ to load the _engine_class
        self._engine_factory = _EngineLoader.load(self.engine)

    def barrel_elevation_for_target(self, shot: Shot, target_distance: float | Distance) -> Angular:
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
        return Angular.Radian((total_elevation >> Angular.Radian) - (shot.look_angle >> Angular.Radian))

    def set_weapon_zero(self, shot: Shot, zero_distance: float | Distance) -> Angular:
        """Set shot.weapon.zero_elevation so that it hits a target at zero_distance.

        Args:
            shot: Shot instance to zero.
            zero_distance: Look-distance to "zero," which is point we want to hit.
        """
        shot.weapon.zero_elevation = self.barrel_elevation_for_target(shot, zero_distance)
        return shot.weapon.zero_elevation

    def fire(
        self,
        shot: Shot,
        trajectory_range: float | Distance,
        trajectory_step: float | Distance | None = None,
        *,
        extra_data: bool = False,
        dense_output: bool = False,
        time_step: float = 0.0,
        flags: TrajFlag | int = TrajFlag.NONE,
        raise_range_error: bool = True,
    ) -> HitResult:
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
            warnings.warn(
                "extra_data is deprecated and will be removed in future versions. "
                "Explicitly specify desired TrajectoryData frequency and flags.",
                DeprecationWarning,
            )
            dist_step = PreferredUnits.distance(1.0)  # << For compatibility with v2.1
            filter_flags = TrajFlag.ALL

        result = self._engine_instance.integrate(
            shot, trajectory_range, dist_step, time_step, filter_flags, dense_output=dense_output
        )
        if result.error and raise_range_error:
            raise result.error
        return result

    @staticmethod
    def iter_engines() -> Generator[EntryPoint, None, None]:
        """Iterate all available engines in the entry points."""
        yield from _EngineLoader.iter_engines()


__all__ = (
    "Calculator",
    "_EngineLoader",
)
