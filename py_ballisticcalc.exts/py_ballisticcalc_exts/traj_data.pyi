"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.traj_data`
to improve IDE completion for low-level trajectory buffer and interpolation helpers.
"""

from typing import overload
from typing_extensions import Iterator

from py_ballisticcalc.unit import Vector
from py_ballisticcalc.trajectory_data import BaseTrajDataAttribute

__all__ = ("CythonizedBaseTrajSeq", "CythonizedBaseTrajData")

class CythonizedBaseTrajSeq:
    """Contiguous C buffer of BCLIBC_BaseTrajData points with fast append and interpolation.

    Python-facing access lazily creates lightweight CythonizedBaseTrajData objects; internal
        nogil helpers work directly on the C buffer for speed.
    """

    def __cinit__(self) -> None: ...
    def __dealloc__(self) -> None: ...
    def append(
        self,
        time: float,
        px: float,
        py: float,
        pz: float,
        vx: float,
        vy: float,
        vz: float,
        mach: float,
    ) -> None:
        """Append a new point to the sequence."""
        ...

    def reserve(self, min_capacity: int) -> None:
        """Ensure capacity is at least min_capacity (no-op if already large enough)."""
        ...

    def __len__(self) -> int:
        """Number of points in the sequence."""
        ...

    def __getitem__(self, idx: int) -> CythonizedBaseTrajData:
        """Return CythonizedBaseTrajData for the given index.  Supports negative indices."""
        ...

    def interpolate_at(
        self, idx: int, key_attribute: BaseTrajDataAttribute, key_value: float
    ) -> CythonizedBaseTrajData:
        """Interpolate using points (idx-1, idx, idx+1) keyed by key_attribute at key_value."""
        ...

    def get_at(
        self, key_attribute: BaseTrajDataAttribute, key_value: float, start_from_time: float | None = None
    ) -> CythonizedBaseTrajData:
        """Get CythonizedBaseTrajData where key_attribute == key_value (via monotone PCHIP interpolation).

        If start_from_time > 0, search is centered from the first point where time >= start_from_time,
        and proceeds forward or backward depending on local direction, mirroring
        trajectory_data.HitResult.get_at().
        """
        ...

    def get_at_slant_height(self, look_angle_rad: float, value: float) -> CythonizedBaseTrajData:
        """Get CythonizedBaseTrajData where value == slant_height === position.y*cos(a) - position.x*sin(a)."""
        ...

class CythonizedBaseTrajData:
    """Lightweight wrapper for a single BCLIBC_BaseTrajData point."""

    __slots__ = ("time", "position", "velocity", "mach")

    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __len__(self) -> int:
        return ...

    def __iter__(self) -> Iterator[float | Vector]:
        """Yields time, position, velocity, mach."""
        ...

    @overload
    def __getitem__(self, index: int) -> float | Vector: ...
    @overload
    def __getitem__(self, index: slice) -> tuple[float | Vector, ...]: ...
    def __getitem__(self, index: int | slice) -> float | Vector | tuple[float | Vector, ...]:
        """
        Implements access to fields by index (0-3 or -4--1) or slice.
        """
        ...

    def __eq__(self, other: object) -> bool:
        """Implements self comparing (self == other)."""
        ...

    @property
    def time(self) -> float: ...
    @property
    def mach(self) -> float: ...
    @property
    def position(self) -> Vector:
        """Return position as Vector."""
        ...

    @property
    def velocity(self) -> Vector:
        """Return velocity as Vector."""
        ...

    @staticmethod
    def interpolate(
        key_attribute: str,
        key_value: float,
        p0: CythonizedBaseTrajData,
        p1: CythonizedBaseTrajData,
        p2: CythonizedBaseTrajData,
    ) -> CythonizedBaseTrajData:
        """
        Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) interpolation
        of a BaseTrajData point.

        Args:
            key_attribute (str): Can be 'time', 'mach',
                or a vector component like 'position.x' or 'velocity.z'.
            key_value (float): The value to interpolate.
            p0, p1, p2 (CythonizedBaseTrajData):
                Any three points surrounding the point where key_attribute==value.

        Returns:
            BaseTrajData: The interpolated data point.

        Raises:
            AttributeError: If the key_attribute is not a member of BaseTrajData.
            ZeroDivisionError: If the interpolation fails due to zero division.
                               (This will result if two of the points are identical).
        """
        ...
