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
from py_ballisticcalc.munition import Ammo, Weapon
from py_ballisticcalc.shot import Shot, ShotProps
from py_ballisticcalc.trajectory_data import TrajectoryData
from py_ballisticcalc.unit import Velocity, Distance, Weight

from py_ballisticcalc_exts import CythonEngineTestHarness

DRAG_CONST = 2.08551e-04
RND = random.Random(42)


def _make_shot() -> Shot:
    # Provide weight/diameter/length and a non-zero twist so stability/energy > 0
    dm = DragModel(0.29, TableG7, Weight.Grain(175), Distance.Inch(0.308), Distance.Inch(1.25))
    weapon = Weapon(twist=Distance.Inch(10))
    return Shot(ammo=Ammo(dm=dm, mv=Velocity.FPS(2780)), weapon=weapon)


def test_drag_curve_parity():
    """Ensure that Cython engine gives same C_d values as Python."""
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
    # Random interpolated point checks
    for _ in range(300):
        i = RND.randint(0, len(xs) - 2)
        lo, hi = xs[i], xs[i + 1]
        m = lo + (hi - lo) * RND.random()
        py_val = sp.drag_by_mach(m)  # Python interpolated C_d value
        c_val = eng.drag(m)  # Cython interpolated C_d value
        if py_val != 0:
            assert abs(c_val - py_val) / py_val < 1e-6


def test_atmosphere_density_and_mach_parity():
    """Parity of density_ratio + Mach speed against Python Atmo API."""
    shot = _make_shot()
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)

    last_density = None
    for alt in [0, 250, 500, 1000, 2000, 5000, 10000]:
        c_dens, c_mach = eng.density_and_mach(alt)
        py_dens, py_mach = shot.atmo.get_density_and_mach_for_altitude(alt)
        assert math.isclose(c_dens, py_dens, rel_tol=1e-6, abs_tol=1e-9), f"density mismatch alt={alt}"
        assert math.isclose(c_mach, py_mach, rel_tol=1e-6, abs_tol=1e-6), f"mach mismatch alt={alt}"
        if last_density is not None:
            assert c_dens <= last_density + 1e-12
        last_density = c_dens
        assert c_mach > 0


def test_spin_drift_and_stability_parity():
    """Compare spin drift & stability coefficient with Python ShotProps reference.

    Uses ShotProps.stability_coefficient and ShotProps.spin_drift as authoritative Python values.
    """
    shot = _make_shot()
    sp = ShotProps.from_shot(shot)
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)

    c_stab = eng.update_stability()
    py_stab = sp.stability_coefficient
    assert py_stab > 0
    assert math.isclose(c_stab, py_stab, rel_tol=1e-9, abs_tol=1e-9)

    prev = 0.0
    for t in [0.01, 0.05, 0.1, 0.25, 0.5]:
        c_val = eng.spin_drift(t)
        py_val = sp.spin_drift(t)
        assert math.isclose(c_val, py_val, rel_tol=1e-9, abs_tol=1e-12)
        assert c_val >= prev - 1e-12
        prev = c_val


def test_energy_and_ogw_parity():
    shot = _make_shot()
    sp = ShotProps.from_shot(shot)
    eng = CythonEngineTestHarness({})
    eng.prepare(shot)
    v = 2500.0  # fps
    c_e = eng.energy(v)
    c_ogw = eng.ogw(v)
    py_e = TrajectoryData.calculate_energy(sp.weight_grains, v)
    py_ogw = TrajectoryData.calculate_ogw(sp.weight_grains, v)
    assert math.isclose(c_e, py_e, rel_tol=1e-11, abs_tol=1e-11)
    assert math.isclose(c_ogw, py_ogw, rel_tol=1e-11, abs_tol=1e-11)
