"""Stress memory test for drag evaluation ensuring no unbounded growth.

Uses CythonEngineTestHarness to hammer drag evaluations and checks retained
Python-level allocations via tracemalloc snapshot diff. This does not
guarantee absence of native leaks, but will surface most inadvertent
Python/Cython reference leaks.
"""
from __future__ import annotations

import gc
import math
import random
import tracemalloc
import pytest

from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.conditions import Shot
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.unit import Velocity
from py_ballisticcalc_exts.test_engine import CythonEngineTestHarness

pytestmark = pytest.mark.stress

DRAG_CONST = 2.08551e-04


def _make_engine():
    dm = DragModel(0.31, TableG7)
    shot = Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(2790)), weapon=Weapon())
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)
    return eng, shot


def test_drag_eval_memory_growth():
    eng, shot = _make_engine()
    xs = [dp["Mach"] for dp in TableG7]
    rnd = random.Random(42)
    WARMUP = 2000
    BATCHES = 10
    BATCH_SIZE = 5000
    LEAK_THRESHOLD_BYTES = 1_000  # generous; adjust tighter if stable across CI

    # Warmup
    for _ in range(WARMUP):
        i = rnd.randint(0, len(xs) - 2)
        m = xs[i] + (xs[i + 1] - xs[i]) * rnd.random()
        _ = eng.drag(m)

    gc.collect()
    tracemalloc.start()
    snap0 = tracemalloc.take_snapshot()
    for _ in range(BATCHES):
        for _ in range(BATCH_SIZE):
            i = rnd.randint(0, len(xs) - 2)
            m = xs[i] + (xs[i + 1] - xs[i]) * rnd.random()
            _ = eng.drag(m)
        gc.collect()
    snap1 = tracemalloc.take_snapshot()
    stats = snap1.compare_to(snap0, "filename")
    total_diff = sum(s.size_diff for s in stats)
    # Allow small positive net retained size
    assert total_diff < LEAK_THRESHOLD_BYTES, f"Possible leak: {total_diff} bytes retained (>{LEAK_THRESHOLD_BYTES})"


def test_engine_alloc_free_churn_no_growth():
    import psutil, statistics
    from py_ballisticcalc.drag_tables import TableG7
    rss_samples = []
    proc = psutil.Process()
    for i in range(3000):
        dm = DragModel(0.31 + (i % 5)*0.001, TableG7)
        shot = Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(2700 + (i % 7)*5)), weapon=Weapon())
        eng = CythonEngineTestHarness({})
        eng.prepare(shot)
        # (Optional) call a few drags
        _ = eng.drag(1.2)
        del eng
        if (i+1) % 300 == 0:
            gc.collect()
            rss_samples.append(proc.memory_info().rss)
    # Simple monotonic-ish check: last sample not more than, say, 3% above median
    med = statistics.median(rss_samples)
    assert rss_samples[-1] <= med * 1.03, f"RSS drift: median={med} last={rss_samples[-1]}"