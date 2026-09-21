"""Ballistics calculator interface and engine loading system.

This module provides the main `Calculator` class that serves as the primary interface
for ballistic trajectory calculations. It implements a plugin-based architecture
that can dynamically load different integration engines through Python entry points.
The module relies on the EngineProtocol to ensure that engines offer the necessary methods.

Engines are selected by name as ``"<engine>+<method>"`` or ``"<engine>.<method>"`` (e.g.
``"python+rk4"``, ``"cython.rk4"``, ``"scipy+dop853"``), where the entry points are registered in
the ``py_ballisticcalc.engines.<engine>`` groups, or directly by a ``"<module>:<factory>"`` path.
The legacy flat names (``rk4_engine``, ``cythonized_rk4_engine``, ...) are deprecated.

Key Classes:
    - Calculator: Main ballistics calculator with pluggable engine support
    - _EngineLoader: Internal utility for discovering and loading engine plugins
"""

import ast
import re
import warnings
from collections.abc import Generator
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from functools import cache
from importlib.metadata import EntryPoint, entry_points
from types import TracebackType
from typing import Any, Self, TypeAlias, TypeVar, overload

from py_ballisticcalc.engines import RK4IntegrationEngine
from py_ballisticcalc.generics.engine import EngineFactoryProtocol, EngineProtocol
from py_ballisticcalc.logger import logger
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.trajectory_data import HitResult, TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, PreferredUnits

ConfigT = TypeVar("ConfigT")

EngineFactoryProtocolType: TypeAlias = EngineFactoryProtocol[Any]
EngineFactoryProtocolEntry: TypeAlias = str | EngineFactoryProtocolType | None

_CALL_VALUE_RE = re.compile(r"^(?P<target>[^()\s]+)\((?P<args>[^()]*)\)$")

DEFAULT_ENTRY_SUFFIX = "_engine"
DEFAULT_ENTRY_GROUP = "py_ballisticcalc"  # legacy flat group
DEFAULT_ENGINES_GROUP_PREFIX = "py_ballisticcalc.engines."
DEFAULT_ENTRY: EngineFactoryProtocolType = RK4IntegrationEngine


@dataclass
class _EngineLoader:
    """Discovers and loads engine factories.

    Supported entry point layouts:
        - New: group ``py_ballisticcalc.engines.<engine>`` with name ``<method>``,
          addressed as ``"<engine>+<method>"`` or ``"<engine>.<method>"`` (e.g. ``"cython+rk4"``).
        - Legacy (temporary): group ``py_ballisticcalc`` with names like ``rk4_engine``.
          Entries duplicating a new-style entry (same target) are skipped.
        - Direct: ``"<module>:<factory>"`` path.
    """

    _entry_point_group = DEFAULT_ENTRY_GROUP
    _entry_point_suffix = DEFAULT_ENTRY_SUFFIX
    _engines_group_prefix = DEFAULT_ENGINES_GROUP_PREFIX

    @classmethod
    @cache
    def _get_entries_by_group(cls) -> AbstractSet[EntryPoint]:
        return set(entry_points().select(group=cls._entry_point_group))

    @classmethod
    @cache
    def _get_engine_entries(cls) -> tuple[EntryPoint, ...]:
        eps = entry_points()
        found: list[EntryPoint] = []
        for group in sorted(g for g in eps.groups if g.startswith(cls._engines_group_prefix)):
            found.extend(sorted(eps.select(group=group), key=lambda ep: ep.name))
        return tuple(found)

    @classmethod
    def engine_id(cls, ep: EntryPoint) -> str:
        """Public identifier of an entry point: ``<engine>+<method>`` for new-style, plain name for legacy."""
        if ep.group.startswith(cls._engines_group_prefix):
            return f"{ep.group.removeprefix(cls._engines_group_prefix)}+{ep.name}"
        return ep.name

    @classmethod
    def iter_engines(cls) -> Generator[EntryPoint, None, None]:
        """Iterate over all available engines (new-style first, legacy deduplicated by target)."""
        seen: set[str] = set()
        for ep in cls._get_engine_entries():
            seen.add(ep.value)
            yield ep
        for ep in sorted(cls._get_entries_by_group(), key=lambda e: e.name):
            if ep.name.endswith(cls._entry_point_suffix) and ep.value not in seen:
                seen.add(ep.value)
                yield ep

    @staticmethod
    def _resolve(ep: EntryPoint) -> EngineFactoryProtocolType:
        """Load the entry point object; supports ``module:Factory(key=value, ...)`` call syntax."""
        m = _CALL_VALUE_RE.match(ep.value)
        if m is None:
            return ep.load()
        target = EntryPoint(ep.name, m["target"], ep.group).load()
        kwargs: dict[str, Any] = {}
        for arg in filter(None, (a.strip() for a in m["args"].split(","))):
            key, sep, raw = arg.partition("=")
            if not sep:
                raise ValueError(f"Invalid argument '{arg}' in entry point {ep.value}; expected key=value")
            try:
                kwargs[key.strip()] = ast.literal_eval(raw.strip())
            except (ValueError, SyntaxError):
                kwargs[key.strip()] = raw.strip()  # bare identifier, e.g. method=RK23
        return target(**kwargs)

    @classmethod
    def _load_from_entry(cls, ep: EntryPoint) -> EngineFactoryProtocolType | None:
        try:
            factory: EngineFactoryProtocolType = cls._resolve(ep)
            if not isinstance(factory, EngineFactoryProtocol):
                raise TypeError(f"Unsupported engine {ep.value} does not implement EngineFactoryProtocol")
            logger.info(f"Loaded calculator from: {ep.value} (Factory: {factory})")
            return factory  # type: ignore
        except ImportError as e:
            logger.error(f"Error loading engine from {ep.value}: {e}")
        except AttributeError as e:
            logger.error(f"Error loading attribute from {ep.value}: {e}")
        except Exception as e:  # noqa: BLE001 -- plugin boundary: third-party entry points may raise anything
            logger.exception(f"An unexpected error occurred loading {ep.value}: {e}")
        return None

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize ``<engine>.<method>`` to ``<engine>+<method>`` (paths with ':' are left as is)."""
        if ":" in name or "+" in name:
            return name
        engine, sep, method = name.partition(".")
        return f"{engine}+{method}" if sep else name

    @classmethod
    def _is_legacy_name(cls, name: str) -> bool:
        wanted = cls._normalize_name(name)
        if any(wanted == cls.engine_id(ep) for ep in cls.iter_engines() if ep.group != cls._entry_point_group):
            return False
        return any(ep.name == name for ep in cls._get_entries_by_group())

    @classmethod
    @cache
    def _load_by_name(cls, name: str) -> EngineFactoryProtocolType | None:
        wanted = cls._normalize_name(name)
        for ep in cls.iter_engines():
            if wanted == cls.engine_id(ep) and (factory := cls._load_from_entry(ep)):
                return factory
        # Legacy names are matched against the full legacy group, including entries hidden by deduplication
        for ep in sorted(cls._get_entries_by_group(), key=lambda e: e.name):
            if ep.name == name and (factory := cls._load_from_entry(ep)):
                return factory

        # Direct "<module>:<factory>" path
        ep = EntryPoint(name, name, cls._entry_point_group)
        if factory := cls._load_from_entry(ep):
            logger.info(f"Loaded calculator from: {ep.value} (Factory: {factory})")
            return factory
        return None

    @classmethod
    def load(cls, entry_point: EngineFactoryProtocolEntry = DEFAULT_ENTRY) -> EngineFactoryProtocolType:
        if entry_point is None:
            entry_point = DEFAULT_ENTRY
        if isinstance(entry_point, EngineFactoryProtocol):
            return entry_point  # type: ignore
        if isinstance(entry_point, str):
            if factory := cls._load_by_name(entry_point):
                if cls._is_legacy_name(entry_point):
                    warnings.warn(
                        f"Engine entry point '{entry_point}' from the legacy '{cls._entry_point_group}' group "
                        "is deprecated; use '<engine>+<method>' (e.g. 'python+rk4') or '<module>:<factory>' instead.",
                        DeprecationWarning,
                        stacklevel=3,  # caller of Calculator(...)
                    )
                return factory
            raise ValueError(
                f"No engine found for '{entry_point}' (expected '<engine>+<method>', '<engine>.<method>' or '<module>:<factory>')"
            )
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

    def aim(self, shot: Shot, target_distance: float | Distance) -> tuple[Angular, Angular, TrajectoryData]:
        """Calculate a target's zero solution and retain its trajectory point.

        Args:
            shot: Shot instance to solve.
            target_distance: Look-distance to the target.
                This is the distance that a rangefinder would return with no ballistic adjustment.

        Returns:
            The vertical hold relative to the weapon's zero, the windage
            angle, and the trajectory point evaluated by the successful
            zero-finding iteration.  The windage angle uses the sign
            convention of :attr:`TrajectoryData.windage_angle`.

        Raises:
            NotImplementedError: If the selected engine has no ``zero_point`` API.
        """
        target_distance = PreferredUnits.distance(target_distance)
        total_elevation, point = self._engine_instance.zero_point(shot, target_distance)
        target_zero_elevation = Angular.Radian(
            (total_elevation >> Angular.Radian) - (shot.look_angle >> Angular.Radian)
        )
        vertical_hold = Angular.Radian(
            (target_zero_elevation >> Angular.Radian) - (shot.weapon.zero_elevation >> Angular.Radian)
        )
        return vertical_hold, point.windage_angle, point

    def aiming_solution_for_target(
        self, shot: Shot, target_distance: float | Distance
    ) -> tuple[Angular, Angular, TrajectoryData]:
        """Return :meth:`aim`'s solution for callers using the descriptive API name.

        Args:
            shot: Shot instance to solve.
            target_distance: Look-distance to the target.

        Returns:
            The vertical hold relative to the weapon's zero, windage angle,
            and terminal trajectory point.
        """
        return self.aim(shot, target_distance)

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
