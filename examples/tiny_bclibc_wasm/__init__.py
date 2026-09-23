"""tiny_bclibc integration engines running as WebAssembly inside a JavaScript engine.

Made for Pythonista (iOS): it can't load native extensions or `ctypes` a self-built library, but
it can reach JavaScriptCore's `JSContext` through `objc_util`, and JSContext runs WebAssembly.
So tiny_bclibc (pure C99, see https://github.com/ballistics-lab/bclibc/tree/main/tiny_bclibc)
is compiled to an import-free `.wasm` module, and these engines drive it through JS. On a
desktop the same JS runs under Node instead, which is how the py_ballisticcalc test suite is run
against these engines (see `_runner.py`).

This is the WebAssembly counterpart of `examples/tiny_bclibc` (the ctypes engines) and returns
the same results: same tiny_bclibc calls (`tiny_bclibc_integrate_stream`,
`tiny_bclibc_find_zero_point`), same Python-side row sorting/finalizing. What differs is only
the transport:

- bclibc's `tiny_bclibc/wasm/tiny_bclibc_wasm.c` flattens tiny_bclibc's struct/callback API
  into a few exports that take and return plain numbers plus two `double` buffers in linear
  memory (a bare JS engine can't pass a C struct or a callback pointer). Rows are collected inside the module instead of being
  streamed to a Python callback, so one engine call is one JS round trip.
- Buffers are always `double`, so the single- and double-precision modules share one layout.

Engines:
    TinyBclibcWasmDoubleIntegrationEngine: `build/tiny_bclibc_dp.wasm` (real_t = double).
    TinyBclibcWasmSingleIntegrationEngine: `build/tiny_bclibc_sp.wasm` (real_t = float), with the
        same looser default `cZeroFindingAccuracy` (1e-3 ft) and the same float32 limits as
        `examples/tiny_bclibc`'s `TinyBclibcSingleIntegrationEngine`.

Building the modules (from the repo root; runs bclibc's `tiny_bclibc/build_wasm.sh` from the
submodule, which needs a wasm32 C toolchain -- `pip install ziglang` is enough):
    git submodule update --init py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc
    examples/tiny_bclibc_wasm/build_wasm.sh

Which module is loaded: `$PYBALLISTICCALC_TINY_BCLIBC_WASM` (double) /
`$PYBALLISTICCALC_TINY_BCLIBC_WASM_SP` (single) if set, else the file in `build/` next to this
package. Which JS engine runs it: see `_runner.default_runner` (JSContext when `objc_util`
imports, Node otherwise). The module is loaded lazily on first engine construction and shared by
every engine instance of that precision.

Running the test suite against it (desktop: Node on PATH, or
`PYBALLISTICCALC_TINY_BCLIBC_WASM_RUNNER=gi-jsc` for WebKitGTK's JavaScriptCore -- the same
engine as Pythonista's JSContext):
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc_wasm:TinyBclibcWasmDoubleIntegrationEngine
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc_wasm:TinyBclibcWasmSingleIntegrationEngine

On Pythonista: copy `py_ballisticcalc` and this directory (with `build/*.wasm`) next to your
script -- see `run_example.py`.

dense_output is NOT supported (raises NotImplementedError), same as the ctypes engines: the
module only ever returns filtered/interpolated rows, never raw per-step data.
"""

from __future__ import annotations

import math
import os
from functools import cache

from typing_extensions import override

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict, BaseIntegrationEngine
from py_ballisticcalc.exceptions import RangeError, SolverRuntimeError
from py_ballisticcalc.logger import logger
from py_ballisticcalc.shot import Shot, ShotProps
from py_ballisticcalc.trajectory_data import HitResult, TrajectoryData, TrajFlag
from py_ballisticcalc.unit import Angular, Distance, Pressure, Temperature, Velocity
from py_ballisticcalc.vector import Vector

from ._runner import WasmCallError, WasmRunner, default_runner

__all__ = ("TinyBclibcWasmDoubleIntegrationEngine", "TinyBclibcWasmSingleIntegrationEngine")

# tiny_bclibc/include/tiny_bclibc/base_types.h: TINY_BCLIBC_TerminationReason
_TERM_NO_TERMINATE = 0
_TERM_TARGET_RANGE_REACHED = 1
_TERM_REASON_MAP = {
    2: RangeError.MinimumVelocityReached,
    3: RangeError.MaximumDropReached,
    4: RangeError.MinimumAltitudeReached,
}

# tiny_bclibc/wasm/tiny_bclibc_wasm.c: output layout
_ROW = 16
_INTEGRATE_HEADER = 12
_ZERO_HEADER = 2

_HERE = os.path.dirname(os.path.abspath(__file__))


@cache
def _load_module(env_var: str, filename: str, sizeof_real: int) -> WasmRunner:
    path = os.environ.get(env_var) or os.path.join(_HERE, "build", filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"tiny_bclibc wasm module not found at '{path}'. Build it with "
            "examples/tiny_bclibc_wasm/build_wasm.sh, or point "
            f"{env_var} at an existing {filename}."
        )
    runner = default_runner()
    runner.load_file(path)
    if runner.sizeof_real != sizeof_real:
        raise RuntimeError(
            f"{path} was built with sizeof(real_t) == {runner.sizeof_real}, expected {sizeof_real}: "
            "the single- and double-precision modules are swapped."
        )
    logger.debug(f"tiny_bclibc wasm {runner.version} loaded from {path} via {type(runner).__name__}")
    return runner


def _row_to_trajectory_data(v: list[float], i: int) -> TrajectoryData:
    return TrajectoryData(
        time=v[i],
        distance=TrajectoryData._new_feet(v[i + 1]),
        velocity=TrajectoryData._new_fps(v[i + 2]),
        mach=v[i + 3],
        height=TrajectoryData._new_feet(v[i + 4]),
        slant_height=TrajectoryData._new_feet(v[i + 5]),
        drop_angle=TrajectoryData._new_rad(v[i + 6]),
        windage=TrajectoryData._new_feet(v[i + 7]),
        windage_angle=TrajectoryData._new_rad(v[i + 8]),
        slant_distance=TrajectoryData._new_feet(v[i + 9]),
        angle=TrajectoryData._new_rad(v[i + 10]),
        density_ratio=v[i + 11],
        drag=v[i + 12],
        energy=TrajectoryData._new_ft_lb(v[i + 13]),
        ogw=TrajectoryData._new_lb(v[i + 14]),
        flag=int(v[i + 15]),
    )


def _maybe_finalize(
    props: ShotProps, records: list[TrajectoryData], reason: int, fin: list[float]
) -> list[TrajectoryData]:
    """Append the exact terminal point when the trajectory ended other than by reaching range.

    Same as examples/tiny_bclibc/_common.py's `_maybe_finalize` (which mirrors
    BCLIBC_TrajectoryDataFilter's destructor); `fin` is (time, px, py, pz, vx, vy, vz, mach).
    """
    if reason in (_TERM_NO_TERMINATE, _TERM_TARGET_RANGE_REACHED):
        return records
    if records and fin[0] <= records[-1].time:
        return records
    position = Vector(fin[1], fin[2], fin[3])
    velocity = Vector(fin[4], fin[5], fin[6])
    _density_ratio, mach = props.get_density_and_mach_for_altitude(position.y)
    return [*records, TrajectoryData.from_props(props, fin[0], position, velocity, mach, TrajFlag.NONE)]


class TinyBclibcWasmIntegrationEngineBase(BaseIntegrationEngine):
    """Shared implementation; subclasses pick the module (precision)."""

    DEFAULT_TIME_STEP = 0.0025  # matches tiny_bclibc_build_shot_props' calc_step formula

    WASM_ENV_VAR: str
    WASM_FILENAME: str
    SIZEOF_REAL: int
    PRECISION_LABEL: str
    # See examples/tiny_bclibc: TinyBclibcSingleIntegrationEngine.DEFAULT_ZERO_FINDING_ACCURACY.
    DEFAULT_ZERO_FINDING_ACCURACY: float | None = None

    def __init__(self, config: BaseEngineConfigDict | None) -> None:
        if self.DEFAULT_ZERO_FINDING_ACCURACY is not None and (config is None or "cZeroFindingAccuracy" not in config):
            config = {**(config or {}), "cZeroFindingAccuracy": self.DEFAULT_ZERO_FINDING_ACCURACY}
        super().__init__(config)
        self._runner = _load_module(self.WASM_ENV_VAR, self.WASM_FILENAME, self.SIZEOF_REAL)
        self.integration_step_count: int = 0
        self.trajectory_count = 0

    @override
    def get_calc_step(self) -> float:
        return super().get_calc_step() * self.DEFAULT_TIME_STEP

    def _serialize_shot(self, props: ShotProps) -> list[float]:
        """Flatten ShotProps into tiny_bclibc_wasm.c's input layout."""
        cfg = self._config
        drag_table = props.shot.ammo.dm.drag_table
        winds = props.winds
        values = [
            props.bc,
            props.weight_grains,
            props.diameter_inch,
            props.length_inch,
            props.muzzle_velocity_fps,
            props.sight_height_ft,
            props.twist_inch,
            props.shot.atmo.temperature >> Temperature.Celsius,
            props.shot.atmo.pressure >> Pressure.hPa,
            props.alt0_ft,
            props.shot.atmo.humidity,
            props.look_angle_rad,
            props.barrel_elevation_rad,
            props.barrel_azimuth_rad,
            props.shot.cant_angle >> Angular.Radian,
            props.latitude if props.latitude is not None else math.nan,
            props.azimuth if props.azimuth is not None else math.nan,
            cfg.cStepMultiplier,
            cfg.cZeroFindingAccuracy,
            cfg.cMinimumVelocity,
            cfg.cMaximumDrop,
            cfg.cMaxIterations,
            cfg.cGravityConstant,
            cfg.cMinimumAltitude,
            len(drag_table),
            len(winds),
        ]
        values.extend(dp.Mach for dp in drag_table)
        values.extend(dp.CD for dp in drag_table)
        for w in winds:
            values.extend(
                (
                    w.velocity >> Velocity.FPS,
                    w.direction_from >> Angular.Radian,
                    w.until_distance >> Distance.Foot,
                    w.MAX_DISTANCE_FEET,
                )
            )
        return values

    def _native_zero_point(self, props: ShotProps, distance: Distance) -> tuple[Angular, TrajectoryData]:
        try:
            out = self._runner.zero_point(self._serialize_shot(props), distance >> Distance.Foot)
        except WasmCallError as exc:
            raise SolverRuntimeError(f"tiny_bclibc_find_zero_point failed: {exc.message}") from exc
        return Angular.Radian(out[1]), _row_to_trajectory_data(out, _ZERO_HEADER)

    @override
    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        """Native zero solver, falling back to BaseIntegrationEngine outside its domain.

        Same as the ctypes engines: tiny_bclibc's compact solver has no special cases for a
        vertical shot or a zero at/near the muzzle.
        """
        try:
            return self._native_zero_point(self._init_trajectory(shot_info), distance)[0]
        except SolverRuntimeError:
            return super().zero_angle(shot_info, distance)

    @override
    def zero_point(self, shot_info: Shot, distance: Distance) -> tuple[Angular, TrajectoryData]:
        return self._native_zero_point(self._init_trajectory(shot_info), distance)

    @override
    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool = False) -> Angular:
        """Same native solver as zero_point, so find_zero_angle and find_zero_point agree."""
        return self._native_zero_point(self._init_trajectory(shot_info), distance)[0]

    @override
    def find_zero_point(
        self, shot_info: Shot, distance: Distance, lofted: bool = False
    ) -> tuple[Angular, TrajectoryData]:
        return self._native_zero_point(self._init_trajectory(shot_info), distance)

    @override
    def _integrate(
        self,
        props: ShotProps,
        range_limit_ft: float,
        range_step_ft: float,
        time_step: float = 0.0,
        filter_flags: TrajFlag | int = TrajFlag.NONE,
        dense_output: bool = False,
        **kwargs,
    ) -> HitResult:
        """Run tiny_bclibc_integrate_stream inside the module, then sort/finalize rows in Python."""
        if dense_output:
            raise NotImplementedError(
                f"{type(self).__name__} doesn't support dense_output (the wasm module only "
                "returns filtered rows, no raw per-step data)."
            )
        self.trajectory_count += 1
        props.filter_flags = filter_flags

        try:
            out = self._runner.integrate(
                self._serialize_shot(props), range_limit_ft, range_step_ft, time_step, int(filter_flags)
            )
        except WasmCallError as exc:
            raise SolverRuntimeError(f"tiny_bclibc_integrate_stream failed: {exc.message}") from exc

        reason = int(out[1])
        total = int(out[2])
        n_rows = int(out[3])
        records = [_row_to_trajectory_data(out, _INTEGRATE_HEADER + k * _ROW) for k in range(n_rows)]
        # Rows arrive in the module's per-interval emission order; see _common._sort_rows in
        # examples/tiny_bclibc for why a stable sort by time (and no merging) is right.
        records.sort(key=lambda row: row.time)
        records = _maybe_finalize(props, records, reason, out[4:12])

        logger.debug(f"tiny_bclibc wasm ({self.PRECISION_LABEL}) emitted {total} rows")
        self.integration_step_count += total
        termination_reason = _TERM_REASON_MAP.get(reason)
        error = RangeError(termination_reason, records) if termination_reason is not None else None
        return HitResult(props, records, [], filter_flags > 0, error)


class TinyBclibcWasmDoubleIntegrationEngine(TinyBclibcWasmIntegrationEngineBase):
    """tiny_bclibc (real_t = double) as WebAssembly: `build/tiny_bclibc_dp.wasm`.

    Examples:
        >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
        >>> engine = TinyBclibcWasmDoubleIntegrationEngine(BaseEngineConfigDict(cMinimumVelocity=0.0))
    """

    WASM_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_WASM"
    WASM_FILENAME = "tiny_bclibc_dp.wasm"
    SIZEOF_REAL = 8
    PRECISION_LABEL = "double precision"


class TinyBclibcWasmSingleIntegrationEngine(TinyBclibcWasmIntegrationEngineBase):
    """tiny_bclibc (real_t = float) as WebAssembly: `build/tiny_bclibc_sp.wasm`.

    Exists for parity with `examples/tiny_bclibc` and carries the same float32 limitations --
    see that package's `TinyBclibcSingleIntegrationEngine` docstring.
    """

    WASM_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_WASM_SP"
    WASM_FILENAME = "tiny_bclibc_sp.wasm"
    SIZEOF_REAL = 4
    PRECISION_LABEL = "single precision"
    DEFAULT_ZERO_FINDING_ACCURACY = 1e-3
