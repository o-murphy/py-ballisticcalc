"""Direct C drag evaluation parity tests.

These extend the existing parity tests by directly invoking the C spline
(ShotProps_t_dragByMach) via a test helper to ensure numerical equivalence
with the Python reference implementation for knot, midpoint, random interior,
and extrapolation queries.
"""
from __future__ import annotations

import math
import random
import pytest

from py_ballisticcalc.drag_tables import TableG7, TableG1
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.conditions import Shot, ShotProps
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.unit import Velocity, Distance
from py_ballisticcalc.interface import _EngineLoader

from py_ballisticcalc_exts.test_helpers import drag_eval_current, init_shot, free_shot

DRAG_CONST = 2.08551e-04
RND = random.Random(42)


def _make_shot(dm: DragModel) -> Shot:
    return Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(2810)), weapon=Weapon())


@pytest.mark.parametrize("table_cls", [TableG7, TableG1])
def test_c_drag_matches_python_knots_midpoints_random(table_cls):
    # Build Python reference
    dm = DragModel(0.27, table_cls)
    shot = _make_shot(dm)
    sp = ShotProps.from_shot(shot)

    # Prepare engine to initialize C ShotProps_t (curve + mach list)
    engine_cls = _EngineLoader.load("cythonized_rk4_engine")
    engine = engine_cls({})
    # Initialize (do NOT integrate then free) so underlying ShotProps_t stays alive
    init_shot(engine, shot)

    xs = [dp["Mach"] for dp in table_cls]
    ys = [dp["CD"] * DRAG_CONST / sp.bc for dp in table_cls]

    try:
        # Quick sanity check
        _first_m = xs[0]
        _first_val = drag_eval_current(engine, _first_m)
        print(f"DEBUG: first knot Mach={_first_m} drag_eval={_first_val}")
        # 1. Knot parity (tight absolute tolerance)
        for m, y_expected in zip(xs, ys):
            c_val = drag_eval_current(engine, m)
            assert math.isclose(c_val, y_expected, rel_tol=1e-12, abs_tol=1e-12), (
                f"knot mismatch at Mach={m}: C={c_val} PY={y_expected}"
            )

        # 2. Midpoints between consecutive knots
        for i in range(len(xs) - 1):
            mid = 0.5 * (xs[i] + xs[i + 1])
            py_val = sp.drag_by_mach(mid)
            c_val = drag_eval_current(engine, mid)
            # Floating diffs should be extremely small; allow tight rel tolerance
            assert math.isclose(c_val, py_val, rel_tol=2e-10, abs_tol=2e-12), (
                f"midpoint mismatch seg {i} Mach={mid}: C={c_val} PY={py_val}"
            )

        # 3. Random interior samples
        for _ in range(300):
            i = RND.randint(0, len(xs) - 2)
            lo, hi = xs[i], xs[i + 1]
            m = lo + (hi - lo) * RND.random()
            py_val = sp.drag_by_mach(m)
            c_val = drag_eval_current(engine, m)
            if py_val == 0:
                assert c_val == 0
            else:
                rel_err = abs(c_val - py_val) / py_val
                assert rel_err < 5e-10, f"random rel diff {rel_err:.2e} too large at Mach={m}"

        # 4. Extrapolation checks (reuse tolerance scheme)
        first_m, last_m = xs[0], xs[-1]
        first_y, last_y = ys[0], ys[-1]
        for query, base, limit in [
            (first_m - 0.001, first_y, 0.03),
            (first_m - 0.05, first_y, 0.03),
            (last_m + 0.001, last_y, 0.03),
            (last_m + 0.1, last_y, 0.03),
            (last_m + 1.0, last_y, 0.15),
        ]:
            c_val = drag_eval_current(engine, query)
            py_val = sp.drag_by_mach(query)
            # Ensure the two methods also agree within same relative window; whichever deviates from endpoint should track each other
            if base != 0:
                rel_err_c = abs(c_val - base) / base
                rel_err_diff = abs(c_val - py_val) / base
                assert rel_err_c < limit, f"C extrap rel err {rel_err_c:.2%} > {limit:.0%} at Mach={query}"
                assert rel_err_diff < limit, f"C vs PY extrap diff {rel_err_diff:.2%} > {limit:.0%} at Mach={query}"
    finally:
        free_shot(engine)


@pytest.mark.parametrize("table_cls", [TableG7, TableG1])
def test_c_drag_high_volume_consistency(table_cls):
    # High iteration parity stress (not leak detection itself; leak strategy handled elsewhere)
    dm = DragModel(0.31, table_cls)
    shot = _make_shot(dm)
    sp = ShotProps.from_shot(shot)
    engine_cls = _EngineLoader.load("cythonized_rk4_engine")
    engine = engine_cls({})
    init_shot(engine, shot)

    xs = [dp["Mach"] for dp in table_cls]
    rnd = random.Random(42)
    try:
        for _ in range(2000):
            i = rnd.randint(0, len(xs) - 2)
            m = xs[i] + (xs[i + 1] - xs[i]) * rnd.random()
            py_val = sp.drag_by_mach(m)
            c_val = drag_eval_current(engine, m)
            if py_val != 0:
                assert abs(c_val - py_val) / py_val < 5e-10
            else:
                assert c_val == 0
    finally:
        free_shot(engine)
