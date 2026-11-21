"""Type stubs of the compiled ``_native`` module (its public names are re-exported by ``py_ballisticcalc_exts``)."""

from collections.abc import Iterator
from typing import Any

from py_ballisticcalc.engines.base_engine import BaseIntegrationEngine
from py_ballisticcalc.trajectory_data import BaseTrajDataAttribute
from py_ballisticcalc.unit import Vector

__all__ = (
    "CythonizedBaseIntegrationEngine",
    "CythonizedBaseTrajData",
    "CythonizedBaseTrajSeq",
    "CythonizedCashKarpIntegrationEngine",
    "CythonizedDormandPrinceIntegrationEngine",
    "CythonizedEulerIntegrationEngine",
    "CythonizedRK4IntegrationEngine",
    "CythonizedTsitourasIntegrationEngine",
    "CythonizedVelocityVerletIntegrationEngine",
)

class CythonizedBaseTrajData:
    """One point of a trajectory (time, position, velocity, Mach) held as a C struct."""

    @property
    def time(self) -> float: ...
    @property
    def mach(self) -> float: ...
    @property
    def position(self) -> Vector: ...
    @property
    def velocity(self) -> Vector: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[Any]: ...
    def __getitem__(self, index: int) -> Any: ...
    @staticmethod
    def interpolate(
        key_attribute: BaseTrajDataAttribute | str,
        key_value: float,
        p0: CythonizedBaseTrajData,
        p1: CythonizedBaseTrajData,
        p2: CythonizedBaseTrajData,
    ) -> CythonizedBaseTrajData:
        """PCHIP interpolation through three points surrounding where key_attribute == key_value."""

def make_base_traj_data(
    time: float, px: float, py: float, pz: float, vx: float, vy: float, vz: float, mach: float
) -> CythonizedBaseTrajData: ...

class CythonizedBaseTrajSeq:
    """Contiguous C buffer of trajectory points with fast append and interpolation."""

    def append(
        self, time: float, px: float, py: float, pz: float, vx: float, vy: float, vz: float, mach: float
    ) -> None:
        """Append a new point to the sequence."""

    def reserve(self, min_capacity: int) -> None:
        """Ensure capacity is at least min_capacity."""

    def __len__(self) -> int: ...
    def __getitem__(self, idx: int) -> CythonizedBaseTrajData: ...
    def interpolate_at(
        self, idx: int, key_attribute: BaseTrajDataAttribute | str, key_value: float
    ) -> CythonizedBaseTrajData:
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""

    def get_at(
        self, key_attribute: BaseTrajDataAttribute | str, key_value: float, start_from_time: float | None = None
    ) -> CythonizedBaseTrajData:
        """Get the point where key_attribute == key_value (monotone PCHIP interpolation)."""

    def get_at_slant_height(self, look_angle_rad: float, value: float) -> CythonizedBaseTrajData: ...

class CythonizedBaseIntegrationEngine(BaseIntegrationEngine):
    """Native engine: fixed-step (RK4, Euler, Verlet) or adaptive (Cash-Karp, Dormand-Prince, Tsitouras)."""

    def get_step_stats(self) -> Any: ...
    @property
    def integration_step_count(self) -> int: ...

class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine): ...
class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine): ...
class CythonizedVelocityVerletIntegrationEngine(CythonizedBaseIntegrationEngine): ...

class _CythonizedAdaptiveEngine(CythonizedBaseIntegrationEngine):
    @property
    def relative_tolerance(self) -> float: ...
    @relative_tolerance.setter
    def relative_tolerance(self, value: float) -> None: ...
    @property
    def absolute_tolerance(self) -> float: ...
    @absolute_tolerance.setter
    def absolute_tolerance(self, value: float) -> None: ...

class CythonizedCashKarpIntegrationEngine(_CythonizedAdaptiveEngine): ...
class CythonizedDormandPrinceIntegrationEngine(_CythonizedAdaptiveEngine): ...
class CythonizedTsitourasIntegrationEngine(_CythonizedAdaptiveEngine): ...
