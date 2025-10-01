"""Stress / integrity tests around Cython ShotProps allocation lifecycle.

Layers provided:
1. Drag evaluation retained-size check via `tracemalloc`.
2. Allocation/free churn across randomized BC / muzzle velocity to detect monotonic RSS growth.
3. Per-iteration C struct integrity validation (curve_len & mach_len zeroed after free).
4. Table edge cases: parametrize over full tables (G1, G7) and a synthetic 2-point minimal table
    to exercise shortest-path spline init.

NOTE: These tests focus on Python-visible retention characteristics. Native heap leaks that
stay out of Python's allocator will require external tools (ASan / Valgrind) or optional
allocation counters compiled behind a macro. This suite is intentionally lightweight enough
to run under a `@pytest.mark.stress` opt-in.
"""
from __future__ import annotations

import gc
import random
import tracemalloc
import pytest

from py_ballisticcalc.drag_tables import TableG7, TableG1
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot
from py_ballisticcalc.unit import Velocity
from py_ballisticcalc_exts.test_engine import CythonEngineTestHarness
from py_ballisticcalc_exts.test_helpers import init_shot, free_shot, shot_props_addr, introspect_shot

pytestmark = pytest.mark.stress

DRAG_CONST = 2.08551e-04


def _make_engine(dm=None, mv_fps: float = 2790.0):
    if dm is None:
        dm = DragModel(0.31, TableG7)
    shot = Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(mv_fps)), weapon=Weapon())
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)
    return eng, shot


def _minimal_two_point_table():
    # Smallest reasonable monotone table (Mach, CD) entries
    from py_ballisticcalc.drag_model import DragDataPoint
    return [DragDataPoint(0.5, 0.2), DragDataPoint(1.5, 0.18)]


@pytest.mark.parametrize(
    "table_variant",
    [
        ("G7", TableG7),
        ("G1", TableG1),
        ("MIN2", _minimal_two_point_table()),
    ],
    ids=lambda p: p[0]
)
def test_drag_eval_memory_growth(table_variant):
    # Freeze GC to reduce allocator noise (Python 3.12+) – safe if available
    if hasattr(gc, "freeze"):
        try:
            gc.freeze()
        except RuntimeError:  # already frozen / edge case
            pass

    _, table = table_variant
    # Build unique DM so we trigger full drag curve interpolation each parametrization
    dm = DragModel(0.305, table)
    eng, _ = _make_engine(dm=dm, mv_fps=2790.0)
    # Table can be list of dict-like or DragDataPoint objects depending on variant
    def _mach(dp):
        return dp["Mach"] if isinstance(dp, dict) else dp.Mach
    xs = [_mach(dp) for dp in table]
    rnd = random.Random(42)
    WARMUP = 1000
    BATCHES = 5
    BATCH_SIZE = 5000
    LEAK_THRESHOLD_BYTES = 1_000  # keep tight; adjust if CI noise observed

    for _ in range(WARMUP):
        if len(xs) < 2:
            continue
        i = rnd.randint(0, len(xs) - 2)
        m = xs[i] + (xs[i + 1] - xs[i]) * rnd.random()
        _ = eng.drag(m)

    gc.collect()
    tracemalloc.start()
    snap0 = tracemalloc.take_snapshot()
    for _ in range(BATCHES):
        inner = BATCH_SIZE if len(xs) > 2 else max(1000, BATCH_SIZE // 4)
        for _ in range(inner):
            if len(xs) < 2:
                continue
            i = rnd.randint(0, len(xs) - 2)
            m = xs[i] + (xs[i + 1] - xs[i]) * rnd.random()
            _ = eng.drag(m)
        gc.collect()
    snap1 = tracemalloc.take_snapshot()
    total_diff = sum(s.size_diff for s in snap1.compare_to(snap0, "filename"))
    assert total_diff < LEAK_THRESHOLD_BYTES, (
        f"Possible leak for table {table_variant[0]}: {total_diff} bytes retained (> {LEAK_THRESHOLD_BYTES})"
    )


def test_engine_alloc_free_churn_no_growth_and_struct_zeroing():
    """Churn allocations with random BC / MV and assert no RSS drift + post-free zeroing.

    Also validates the helper-reported struct fields are cleared after free.
    """
    import psutil, statistics
    rss_samples = []
    proc = psutil.Process()
    rnd = random.Random(42)
    ITER = 2000
    SAMPLE_EVERY = 200
    for i in range(ITER):
        # Randomize BC slightly & pick table alternately (exercise both)
        table = TableG7 if (i % 2) else TableG1
        bc = 0.28 + (rnd.random() * 0.02)
        mv = 2500 + rnd.randint(-40, 40)
        dm = DragModel(bc, table)
        shot = Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(mv)), weapon=Weapon())
        eng = CythonEngineTestHarness({})
        # Use low-level init + introspection path first
        addr = shot_props_addr(eng)
        # Not yet initialized; introspect should show zeros
        pre = introspect_shot(addr)
        assert pre["curve_len"] == 0 and pre["mach_len"] == 0
        eng.prepare(shot)
        # Introspect live struct (non-zero lengths)
        addr = shot_props_addr(eng)
        mid = introspect_shot(addr)
        assert mid["curve_len"] > 1 and mid["mach_len"] == mid["curve_len"], "Curve & Mach list length mismatch"
        # Touch a few drags and stability branch
        _ = eng.drag(1.1)
        _ = eng.update_stability()
        # Free via helper to exercise zeroing implemented in _free_trajectory
        free_shot(eng)
        post = introspect_shot(addr)
        assert post["curve_len"] == 0 and post["mach_len"] == 0, "Struct not zeroed after free"
        del eng
        if (i + 1) % SAMPLE_EVERY == 0:
            gc.collect()
            rss_samples.append(proc.memory_info().rss)
    med = statistics.median(rss_samples)
    assert rss_samples[-1] <= med * 1.04, f"RSS drift: median={med} last={rss_samples[-1]}"


def test_high_volume_reinitialization_randomized_parameters():
    """Rapid reinitialization stressing stability coefficient & wind branches.

    Does not focus on RSS; instead ensures no crashes and struct reset invariants.
    """
    rnd = random.Random(1337)
    for i in range(1000):
        table = TableG1 if (i % 3 == 0) else TableG7
        # Random BC + muzzle velocity + slight shape variation (weight/diameter proxies left default)
        bc = 0.25 + rnd.random() * 0.05
        mv = 2500 + rnd.random() * 400
        dm = DragModel(bc, table)
        shot = Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(mv)))
        eng = CythonEngineTestHarness({})
        eng.prepare(shot)
        # Evaluate a random Mach in table span
        xs = [dp["Mach"] for dp in table]
        if len(xs) >= 2:
            j = rnd.randint(0, len(xs) - 2)
            m = xs[j] + (xs[j + 1] - xs[j]) * rnd.random()
            _ = eng.drag(m)
        _ = eng.update_stability()
        # Free and verify zeroed
        addr = shot_props_addr(eng)
        free_shot(eng)
        post = introspect_shot(addr)
        assert post["curve_len"] == 0 and post["mach_len"] == 0
        del eng
        if (i + 1) % 400 == 0:
            gc.collect()