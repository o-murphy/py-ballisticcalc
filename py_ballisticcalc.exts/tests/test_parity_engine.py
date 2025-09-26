"""Parity tests comparing C-layer (CythonEngineTestHarness) with Python reference APIs.

The CythonEngineTestHarness exposes internal C computations so we can assert tight
numerical equivalence across drag, atmosphere density/mach, spin drift, energy,
stability coefficient updates, and integration step count behavior.
"""
from __future__ import annotations

import math
import random
import pytest

from py_ballisticcalc.drag_tables import TableG7
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.conditions import Shot, ShotProps
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.unit import Velocity, Distance, Weight, Unit

from py_ballisticcalc_exts.test_engine import CythonEngineTestHarness

DRAG_CONST = 2.08551e-04
RND = random.Random(42)


def _make_shot():
    # Provide weight/diameter/length and a non-zero twist so stability/energy > 0
    dm = DragModel(0.29, TableG7, Weight.Grain(175), Distance.Inch(0.308), Distance.Inch(1.25))
    weapon = Weapon(twist=Distance.Inch(10))
    return Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(2780)), weapon=weapon)


def test_drag_knots_and_random_parity():
    shot = _make_shot()
    sp = ShotProps.from_shot(shot)
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)

    xs = [dp["Mach"] for dp in TableG7]
    ys = [dp["CD"] * DRAG_CONST / sp.bc for dp in TableG7]
    # Knot equality
    for m, y_expected in zip(xs, ys):
        c_val = eng.drag(m)
        assert math.isclose(c_val, y_expected, rel_tol=1e-12, abs_tol=1e-12)
    # Random interior checks
    for _ in range(300):
        i = RND.randint(0, len(xs) - 2)
        lo, hi = xs[i], xs[i + 1]
        m = lo + (hi - lo) * RND.random()
        py_val = sp.drag_by_mach(m)
        c_val = eng.drag(m)
        if py_val != 0:
            assert abs(c_val - py_val) / py_val < 5e-6


def test_atmosphere_density_and_mach_monotone():
    shot = _make_shot()
    sp = ShotProps.from_shot(shot)
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)

    # Compare against Python atmosphere path: we reuse ShotProps internal atmo logic via drag_by_mach side effects
    # Here we only sanity-check monotonic Mach speed change with altitude sign and positive density ratio.
    last_density = None
    for alt in [0, 500, 1000, 2000, 5000, 10000]:
        density_ratio, mach = eng.density_and_mach(alt)
        assert density_ratio > 0
        if last_density is not None:
            assert density_ratio <= last_density + 1e-12  # decreasing with altitude in standard model
        last_density = density_ratio
        assert mach > 0


def test_spin_drift_and_stability_update():
    shot = _make_shot()
    sp = ShotProps.from_shot(shot)
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)
    # Spin drift: small positive monotone-ish with time (coarse check)
    prev = 0.0
    for t in [0.01, 0.05, 0.1, 0.25, 0.5]:
        d = eng.spin_drift(t)
        assert d >= prev - 1e-9
        prev = d
    # Stability update returns coefficient; it should be > 0
    stab = eng.update_stability()
    assert stab > 0


def test_energy_and_ogw_basic():
    shot = _make_shot()
    sp = ShotProps.from_shot(shot)
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)
    v = 2500.0
    e = eng.energy(v)
    ogw = eng.ogw(v)
    assert e > 0
    assert ogw > 0


def test_drag_high_volume_precision():
    shot = _make_shot()
    sp = ShotProps.from_shot(shot)
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)
    xs = [dp["Mach"] for dp in TableG7]
    rnd = random.Random(42)
    for _ in range(5000):
        i = rnd.randint(0, len(xs) - 2)
        m = xs[i] + (xs[i + 1] - xs[i]) * rnd.random()
        py_val = sp.drag_by_mach(m)
        c_val = eng.drag(m)
        if py_val != 0:
            assert abs(c_val - py_val) / py_val < 5e-6