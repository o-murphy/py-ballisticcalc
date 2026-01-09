"""Engine benchmark script.

Implements two fixed benchmark cases (Trajectory, Zero) and records results.

Usage examples:
    uv run python scripts/benchmark.py --engine rk4_engine
    uv run python scripts/benchmark.py --engine="rk4_engine"  # same as pytest style
    uv run python scripts/benchmark.py --all

Outputs:
    - ./benchmarks/<timestamp>_bench.json (full JSON array)
    - ./benchmarks/benchmarks.csv (appended row-wise summary)
    - Markdown or CSV emitted to stdout (default CSV)

Notes:
    * Collects git branch + short hash if repo present.
    * Includes package version for longitudinal tracking.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gc
import json
import statistics
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from collections.abc import Sequence

# Local imports (package must be importable)
from py_ballisticcalc import (
    Calculator,
    DragModel,
    TableG7,
    Ammo,
    Weapon,
    Shot,
    Atmo,
    TrajFlag,
    __version__ as PACKAGE_VERSION,
)
from py_ballisticcalc.unit import Distance, Velocity, Weight, Angular

from importlib.metadata import metadata
__version__ = metadata('py-ballisticcalc').get('Version', 'unknown')

BENCH_DIR = Path("./benchmarks")
BENCH_DIR.mkdir(exist_ok=True)

# ---------------------------- Data Structures ---------------------------------
@dataclass(slots=True)
class BenchmarkCase:
    name: str
    description: str
    # Marker describing which operation(s) to perform
    kind: str  # 'trajectory' or 'zero'

@dataclass(slots=True)
class BenchmarkResult:
    case: str
    engine: str
    repeats: int
    mean_ms: float
    stdev_ms: float
    min_ms: float
    max_ms: float
    branch: str
    git_hash: str
    version: str
    timestamp: str

    def to_row(self) -> list[str]:
        return [
            self.timestamp,
            self.version,
            self.branch,
            self.git_hash,
            self.case,
            self.engine,
            str(self.repeats),
            f"{self.mean_ms:.3f}",
            f"{self.stdev_ms:.3f}",
            f"{self.min_ms:.3f}",
            f"{self.max_ms:.3f}",
        ]

CSV_HEADER = [
    "timestamp","version","branch","git_hash","case","engine","repeats","mean_ms","stdev_ms","min_ms","max_ms"
]

# ---------------------------- Fixed Scenarios ---------------------------------
# Shared physical setup base parameters
_WEAPON_BASE = dict(sight_height=Distance.Centimeter(4), twist=Distance.Centimeter(30))
_DRAG_MODEL = DragModel(0.22, TableG7, weight=Weight.Gram(10), diameter=Distance.Centimeter(7.62), length=Distance.Centimeter(3.0))
_AMMO = Ammo(dm=_DRAG_MODEL, mv=Velocity.MPS(800))
_ATMO = Atmo.icao()
_RANGE = Distance.Meter(2000)
_RANGE_STEP = Distance.Meter(100)

CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        name="Trajectory",
        description="Full trajectory integration to 2000m with 100m step flags=ALL",
        kind="trajectory",
    ),
    BenchmarkCase(
        name="Zero",
        description="Compute zero angle at 2000m (set_weapon_zero operation)",
        kind="zero",
    ),
]

# ---------------------------- Helpers -----------------------------------------

def _git_info() -> tuple[str, str]:
    def run(cmd: Sequence[str]) -> str:
        try:
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return "unknown"
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit = run(["git", "rev-parse", "--short", "HEAD"])
    return branch, commit


def _build_shot(for_zero: bool) -> Shot:
    if for_zero:
        weapon = Weapon(**_WEAPON_BASE)
    else:
        weapon = Weapon(**_WEAPON_BASE, zero_elevation=Angular.Mil(60.0))
    return Shot(weapon=weapon, ammo=_AMMO, atmo=_ATMO)


def _bench_single(case: BenchmarkCase, engine: str, repeats: int, warmup: int, suppress_gc: bool) -> BenchmarkResult:
    calc = Calculator(engine=engine)
    # Warmup
    shot = _build_shot(case.kind == "zero")
    if case.kind == "trajectory":
        for _ in range(max(0, warmup)):
            calc.fire(shot=shot, trajectory_range=_RANGE, trajectory_step=_RANGE_STEP, flags=TrajFlag.ALL)
    else:  # zero
        for _ in range(max(0, warmup)):
            calc.set_weapon_zero(shot, _RANGE)
    if suppress_gc:
        gc.collect()
        was_enabled = gc.isenabled()
        if was_enabled:
            gc.disable()
    else:
        was_enabled = gc.isenabled()

    timings: list[float] = []
    try:
        import time
        for _ in range(repeats):
            shot_local = _build_shot(case.kind == "zero")  # isolate state changes
            start = time.perf_counter()
            if case.kind == "trajectory":
                result = calc.fire(shot=shot_local, trajectory_range=_RANGE, trajectory_step=_RANGE_STEP, flags=TrajFlag.ALL)
            else:
                # measure zero calculation
                calc.set_weapon_zero(shot_local, _RANGE)
            end = time.perf_counter()
            timings.append((end - start) * 1000.0)
    finally:
        if suppress_gc and was_enabled:
            gc.enable()
    mean_ms = statistics.fmean(timings)
    stdev_ms = statistics.pstdev(timings) if len(timings) > 1 else 0.0
    branch, gh = _git_info()
    # Timezone-aware UTC timestamp (display + file-safe variant)
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    iso_ts = now_utc.isoformat().replace('+00:00', 'Z')  # e.g. 2025-09-30T21:37:36Z
    return BenchmarkResult(
        case=case.name,
        engine=engine,
        repeats=repeats,
        mean_ms=mean_ms,
        stdev_ms=stdev_ms,
        min_ms=min(timings),
        max_ms=max(timings),
        branch=branch,
        git_hash=gh,
        version=PACKAGE_VERSION,
        timestamp=iso_ts,
    )


# ---------------------------- Output Formatting -------------------------------

def _format_markdown(results: list[BenchmarkResult]) -> str:
    header = "| Case | Engine | Mean (ms) | StdDev | Min | Max |"
    sep = "| --- | --- | --- | --- | --- | --- |"
    rows = [
        f"| {r.case} | {r.engine} | {r.mean_ms:.2f} | {r.stdev_ms:.2f} | {r.min_ms:.2f} | {r.max_ms:.2f} |"  # noqa: E501
        for r in results
    ]
    return "\n".join([header, sep, *rows])


def _format_csv(results: list[BenchmarkResult]) -> str:
    # For stdout emission only; persistent CSV handled separately
    lines = [",".join(CSV_HEADER)]
    for r in results:
        lines.append(",".join(r.to_row()))
    return "\n".join(lines)


# ---------------------------- Persistence -------------------------------------

def _persist(results: list[BenchmarkResult]) -> None:
    if results:
        # Use file-system safe timestamp: 20250930T213736Z
        file_ts = results[0].timestamp.replace('-', '').replace(':', '').replace('T', 'T').replace('Z', 'Z')
    else:
        now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        file_ts = now_utc.strftime('%Y%m%dT%H%M%SZ')
    json_path = BENCH_DIR / f"{file_ts}_bench.json"
    with json_path.open("w", encoding="utf-8") as fp:
        json.dump([asdict(r) for r in results], fp, indent=2, sort_keys=True)
    csv_path = BENCH_DIR / "benchmarks.csv"
    exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        if not exists:
            writer.writerow(CSV_HEADER)
        for r in results:
            writer.writerow(r.to_row())


# ---------------------------- CLI ---------------------------------------------

def get_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("py_ballisticcalc benchmark", description="Benchmark py_ballisticcalc engines (fixed scenarios)")
    engine_group = p.add_mutually_exclusive_group(required=True)
    engine_group.add_argument("-e", "--engine", nargs="+", dest="engine",
                              help="Single engine entry point (e.g. rk4_engine)")
    engine_group.add_argument("-A", "--all", action="store_true", help="Benchmark all discovered engines")
    p.add_argument("-r", "--repeats", type=int, default=100, help="Timed repetitions (default 100)")
    p.add_argument("-w", "--warmup", type=int, default=10, help="Warmup iterations (default 10)")
    p.add_argument("-f", "--format", choices=["markdown", "json", "csv"], default="csv", help="Stdout format (default csv)")
    p.add_argument("--no-gc-suppress", action="store_true", help="Do not disable GC during timing")
    p.add_argument("-V", "--version", action='version', version=__version__)
    return p


def iter_engine_names() -> list[str]:
    return [ep.name for ep in Calculator.iter_engines()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = get_parser()
    ns: argparse.Namespace = parser.parse_args(argv)

    engines: list[str]
    if ns.all:
        engines = iter_engine_names()
    else:
        engines = ns.engine

    results: list[BenchmarkResult] = []
    for engine in engines:
        for case in CASES:
            try:
                results.append(
                    _bench_single(
                        case,
                        engine=engine,
                        repeats=ns.repeats,
                        warmup=ns.warmup,
                        suppress_gc=not ns.no_gc_suppress,
                    )
                )
            except Exception as exc:  # pragma: no cover
                print(f"[WARN] Failed benchmark {case.name} on {engine}: {exc}")
    if not results:
        parser.error("No results produced", file=sys.stderr)

    _persist(results)
    if ns.format == "markdown":
        print(_format_markdown(results))
    elif ns.format == "json":
        print(json.dumps([asdict(r) for r in results], indent=2, sort_keys=True))
    else:
        print(_format_csv(results))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
